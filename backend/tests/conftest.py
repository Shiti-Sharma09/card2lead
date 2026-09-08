"""Test setup: in-memory SQLite, test env, fresh schema per session."""

from __future__ import annotations

import os
import uuid

os.environ.update(
    APP_ENV="test",
    DATABASE_URL="sqlite://",  # in-memory (StaticPool keeps it shared)
    JWT_SECRET="test-secret",
    JWT_EXPIRES_DAYS="7",
    ADMIN_EMAIL="admin@referral-card-qa.com",
    ADMIN_PASSWORD="AdminPass1",
    GROQ_API_KEY="",
    GOOGLE_SHEET_ID="",  # Sheets disabled in tests -> no real Google calls
    SEED_ASSIGNEES="NITISH,HARSHAD",
    CORS_ORIGINS="*",
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

ADMIN_EMAIL = os.environ["ADMIN_EMAIL"]
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]


@pytest.fixture(scope="session")
def client():
    # importing app triggers lifespan (init_db + seed_admin + seed_assignees)
    from app.main import app

    with TestClient(app) as c:
        yield c


# --- helpers ---------------------------------------------------------------
def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def admin_token(client) -> str:
    r = client.post(
        "/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def new_user_token(client) -> str:
    email = f"u-{uuid.uuid4().hex[:10]}@referral-card-qa.com"
    r = client.post("/auth/register", json={"email": email, "password": "secret123"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]
