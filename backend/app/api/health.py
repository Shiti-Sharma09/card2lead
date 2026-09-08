"""GET /health — liveness + a peek at what's configured."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["meta"])


@router.get("/health")
def health() -> dict:
    s = get_settings()
    return {
        "status": "ok",
        "env": s.app_env,
        "groq": "mock" if s.groq_mock_mode else "configured",
        "sheets": "configured" if s.google_sheet_id else "not-configured",
    }
