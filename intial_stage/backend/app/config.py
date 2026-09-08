"""Runtime configuration, read once from environment / .env file."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# backend/ directory (this file is backend/app/config.py)
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings:
    """Plain settings object; one instance is cached for the process."""

    def __init__(self) -> None:
        self.gemini_api_key: str = os.getenv("GEMINI_API_KEY", "").strip()
        self.gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

        excel_raw = os.getenv("EXCEL_PATH", "data/leads_master.xlsx").strip()
        excel_path = Path(excel_raw).expanduser()
        self.excel_path: Path = (
            excel_path if excel_path.is_absolute() else (BASE_DIR / excel_path)
        )

        self.assignees: list[str] = _split_csv(
            os.getenv("ASSIGNEES", "NITISH,HARSHAD")
        ) or ["NITISH", "HARSHAD"]

        self.gemini_timeout_ms: int = int(os.getenv("GEMINI_TIMEOUT_MS", "30000"))
        self.confidence_threshold: int = int(os.getenv("CONFIDENCE_THRESHOLD", "95"))
        self.blur_threshold: float = float(os.getenv("BLUR_THRESHOLD", "120"))
        self.cors_origins: list[str] = _split_csv(os.getenv("CORS_ORIGINS", "*")) or ["*"]
        self.max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "12"))

    @property
    def mock_mode(self) -> bool:
        """True when no API key is configured -> serve sample data."""
        return not self.gemini_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()
