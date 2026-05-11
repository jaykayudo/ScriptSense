from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Application ──────────────────────────────────────────────────────────
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    secret_key: str = "change-this-to-a-secure-secret-key"

    # ── CORS ─────────────────────────────────────────────────────────────────
    # Comma-separated list of allowed origins
    allowed_origins: str = "http://localhost:5173"

    # ── Model paths ──────────────────────────────────────────────────────────
    # Root directory that contains serialised model artifacts
    model_path: str = "../model/saved_models"

    # YOLO weights file used for line segmentation
    yolo_model_path: str = "../model/saved_models/line_detector_best.pt"

    # HuggingFace model ID for Handwritten Text Recognition
    trocr_model_name: str = "microsoft/trocr-large-handwritten"

    # ── External API keys ────────────────────────────────────────────────────
    ollama_api_key: str = ""
    deepseek_secret_key: str = ""

    # ── File upload constraints ───────────────────────────────────────────────
    max_upload_size_mb: int = 50
    max_images_per_request: int = 30

    # ── Temp / scratch space ─────────────────────────────────────────────────
    # Each conversion job gets its own sub-directory inside this path
    temp_dir: str = "/tmp/scriptsense"

    # ── Logging ───────────────────────────────────────────────────────────────
    # TRACE | DEBUG | INFO | WARNING | ERROR | CRITICAL  (case-insensitive)
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()

SETTINGS = get_settings()