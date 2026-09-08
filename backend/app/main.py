"""FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.access.router import me_router, router as access_router
from app.api.health import router as health_router
from app.assignees.router import router as assignees_router
from app.auth.router import router as auth_router
from app.core.config import get_settings
from app.events.router import router as events_router
from app.leads.router import router as leads_router
from app.scan.router import router as scan_router
from app.core.logging import log_event, setup_logging
from app.db.base import init_db

log = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging()
    for warn in settings.startup_warnings():
        log.warning("config: %s", warn)

    init_db()

    from app.assignees.service import seed_assignees
    from app.auth.service import seed_admin

    seed_admin()
    seed_assignees()
    log_event("APP_START", env=settings.app_env)
    yield
    log_event("APP_STOP")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="card2lead API", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    app.include_router(events_router, prefix="/events", tags=["events"])
    app.include_router(access_router, prefix="/events", tags=["access"])
    app.include_router(scan_router, prefix="/events", tags=["scan"])
    app.include_router(leads_router, prefix="/events", tags=["leads"])
    app.include_router(me_router, prefix="/me", tags=["me"])
    app.include_router(assignees_router, prefix="/assignees", tags=["assignees"])
    return app


app = create_app()
