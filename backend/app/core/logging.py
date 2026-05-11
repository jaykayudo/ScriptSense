import logging
import sys

from loguru import logger


def setup_logging(log_level: str = "INFO") -> None:
    """
    Configure loguru as the single logging sink for the entire application.
    Also intercepts uvicorn's standard-library logging and routes it through loguru
    so all output shares one format and one level setting.

    Args:
        log_level: Any loguru level string — TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL.
                   Controlled at runtime via the LOG_LEVEL environment variable.
    """
    level = log_level.upper()

    # Remove loguru's default stderr handler (no format, no colour)
    logger.remove()

    logger.add(
        sys.stderr,
        level=level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        colorize=True,
        backtrace=True,   # full traceback on exceptions
        diagnose=True,    # variable values in tracebacks (disable in prod)
    )

    # Intercept standard-library logging (uvicorn, fastapi, httpx, etc.)
    class _InterceptHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            try:
                level_ = logger.level(record.levelname).name
            except ValueError:
                level_ = str(record.levelno)
            frame, depth = logging.currentframe(), 2
            while frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back  # type: ignore[assignment]
                depth += 1
            logger.opt(depth=depth, exception=record.exc_info).log(
                level_, record.getMessage()
            )

    handler = _InterceptHandler()
    logging.basicConfig(handlers=[handler], level=0, force=True)
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"):
        log = logging.getLogger(name)
        log.handlers = [handler]
        log.propagate = False

    logger.info(f"Logging ready | level={level}")
