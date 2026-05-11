from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from loguru import logger

from app.core.config import Settings, get_settings
from app.core.dependencies import validate_images
from app.schemas import ConvertResponse
from app.services.conversion import MultiPageConversion, SingleDocConversion

router = APIRouter(prefix="/api/convert", tags=["convert"])

# ── In-memory job registry ─────────────────────────────────────────────────────
# job_id → {"queue": Queue, "result_dir": Path|None, "files": list[str], "error": str|None}
# NOTE: single-process only. For multi-worker deployments, replace with Redis.
_jobs: dict[str, dict] = {}


# ── Background conversion task ─────────────────────────────────────────────────

async def _run_job(
    job_id: str,
    images_data: list[tuple[str, bytes]],
    doc_structure: str,
    output_format: str,
    job_dir: Path,
) -> None:
    queue: asyncio.Queue = _jobs[job_id]["queue"]
    log = logger.bind(job_id=job_id)
    try:
        cls = MultiPageConversion if doc_structure == "multi" else SingleDocConversion
        log.info(
            "Pipeline started | mode={} images={} format={}",
            cls.__name__, len(images_data), output_format,
        )
        output_files = await cls(images_data, output_format, job_dir, job_id).run(queue)

        filenames = [f.name for f in output_files]
        _jobs[job_id]["result_dir"] = job_dir
        _jobs[job_id]["files"] = filenames
        log.info("Pipeline complete | files={}", filenames)

        await queue.put({
            "step": "done",
            "label": "Conversion complete",
            "percentage": 100,
            "status": "done",
            "files": [
                {"filename": f.name, "url": f"/api/convert/{job_id}/result/{f.name}"}
                for f in output_files
            ],
        })
    except Exception as exc:
        log.exception("Pipeline failed | error={}", exc)
        _jobs[job_id]["error"] = str(exc)
        await queue.put({
            "step": "error",
            "label": "Conversion failed",
            "percentage": 0,
            "status": "error",
            "message": str(exc),
        })


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post("", response_model=ConvertResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_conversion(
    settings: Annotated[Settings, Depends(get_settings)],
    images: Annotated[list[UploadFile], Depends(validate_images)],
    doc_structure: Annotated[str, Form()] = "multi",
    output_format: Annotated[str, Form()] = "pdf",
) -> ConvertResponse:
    """
    Accept images + conversion settings, start the ML pipeline in the background,
    and return a job_id immediately. Poll GET /{job_id}/progress for SSE events.
    """
    if doc_structure not in ("single", "multi"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid doc_structure {doc_structure!r}. Use 'single' or 'multi'.",
        )
    if output_format not in ("txt", "pdf", "doc"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid output_format {output_format!r}. Use 'txt', 'pdf', or 'doc'.",
        )

    # Read file bytes now — UploadFile is not safe to read inside a background task
    images_data: list[tuple[str, bytes]] = [
        (img.filename or f"image_{i}.jpg", await img.read())
        for i, img in enumerate(images)
    ]

    job_id = uuid.uuid4().hex
    job_dir = Path(settings.temp_dir) / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    _jobs[job_id] = {
        "queue": asyncio.Queue(),
        "result_dir": None,
        "files": [],
        "error": None,
    }

    logger.info(
        "Job created | job_id={} images={} doc_structure={} output_format={}",
        job_id, len(images_data), doc_structure, output_format,
    )
    logger.debug("Job temp dir | path={}", job_dir)

    asyncio.create_task(
        _run_job(job_id, images_data, doc_structure, output_format, job_dir)
    )

    return ConvertResponse(job_id=job_id)


@router.get("/{job_id}/progress")
async def stream_progress(job_id: str) -> StreamingResponse:
    """
    SSE stream that emits progress events while the conversion runs.
    Each event is a JSON object: {step, label, percentage, status, ...}.
    The final event has status="done" and includes a "files" list,
    or status="error" with a "message" field.
    """
    if job_id not in _jobs:
        logger.warning("SSE requested for unknown job | job_id={}", job_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    logger.debug("SSE client connected | job_id={}", job_id)
    queue: asyncio.Queue = _jobs[job_id]["queue"]

    async def event_stream():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=600.0)
                except asyncio.TimeoutError:
                    logger.warning("SSE job timed out | job_id={}", job_id)
                    yield (
                        'data: {"step":"error","label":"Timed out",'
                        '"percentage":0,"status":"error","message":"job timed out"}\n\n'
                    )
                    break
                logger.debug(
                    "SSE event | job_id={} step={} pct={}",
                    job_id, event.get("step"), event.get("percentage"),
                )
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("status") in ("done", "error"):
                    logger.debug("SSE stream closing | job_id={} status={}", job_id, event.get("status"))
                    break
        except asyncio.CancelledError:
            logger.debug("SSE client disconnected | job_id={}", job_id)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{job_id}/result/{filename}")
async def download_result(job_id: str, filename: str) -> FileResponse:
    """Download an output file produced by a completed conversion job."""
    if job_id not in _jobs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    result_dir: Path | None = _jobs[job_id].get("result_dir")
    if not result_dir:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Result not ready yet"
        )

    safe_name = Path(filename).name
    file_path = result_dir / safe_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    logger.info("File download | job_id={} filename={}", job_id, safe_name)
    return FileResponse(file_path, filename=safe_name)
