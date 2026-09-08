"""Test setup: in-memory SQLite, test env, fresh schema per session."""

from __future__ import annotations

import os

os.environ.update(
    APP_ENV="test",
    DATABASE_URL="sqlite://",  # in-memory (StaticPool keeps it shared)
    JWT_SECRET="test-secret",
    JWT_EXPIRES_DAYS="7",
    ADMIN_EMAIL="admin@referral-card-qa.com",
    ADMIN_PASSWORD="AdminPass1",
    GROQ_API_KEY="",
    CORS_ORIGINS="*",
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

ADMIN_EMAIL = os.environ["ADMIN_EMAIL"]
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]


@pytest.fixture(scope="session")
def client():
    # importing app triggers lifespan (init_db + seed_admin) via the context mgr
    from app.main import app

    with TestClient(app) as c:
        yield c
