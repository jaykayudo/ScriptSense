from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api import api_router
from app.core.config import get_settings
from app.core.logging import setup_logging

settings = get_settings()

# Initialise logging before anything else can emit a message
setup_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ScriptSense API starting up | env={}", settings.app_env)
    yield
    logger.info("ScriptSense API shutting down")


app = FastAPI(
    title="ScriptSense API",
    version="0.1.0",
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health", tags=["meta"])
def health_check():
    logger.debug("Health check requested")
    return {"status": "ok", "env": settings.app_env}
