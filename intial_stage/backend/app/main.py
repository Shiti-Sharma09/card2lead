"""CARD2LEAD FastAPI application.

Serves the JSON API under /api and, when a production frontend build exists,
the React app itself from / (single origin -> one ngrok tunnel, no CORS).
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .routes import extract, leads

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
# quiet the Gemini SDK's per-call info + AFC-recommendation chatter
logging.getLogger("google_genai").setLevel(logging.ERROR)

settings = get_settings()

app = FastAPI(title="CARD2LEAD API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(extract.router, prefix="/api")
app.include_router(leads.router, prefix="/api")


@app.get("/api/health")
def health() -> dict:
    return {
        "ok": True,
        "mock_mode": settings.mock_mode,
        "model": settings.gemini_model,
        "assignees": settings.assignees,
        "excel_path": str(settings.excel_path),
    }


@app.get("/api/config")
def client_config() -> dict:
    """Values the frontend reads on startup."""
    return {
        "appName": "CARD2LEAD",
        "assignees": settings.assignees,
        "confidenceThreshold": settings.confidence_threshold,
        "mockMode": settings.mock_mode,
    }


# ---------------------------------------------------------------------------
# Static frontend (optional). Built by `npm run build` in ../frontend.
# Mounted last so it never shadows /api routes.
# ---------------------------------------------------------------------------
_FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

if _FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIST), html=True), name="frontend")
else:

    @app.get("/")
    def root() -> dict:
        return {
            "ok": True,
            "note": (
                "Frontend not built. Run `npm run build` in frontend/ to serve it "
                "here, or use the Vite dev server on port 5173."
            ),
        }
