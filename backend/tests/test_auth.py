import uuid

from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD


def _email() -> str:
    return f"user-{uuid.uuid4().hex[:10]}@referral-card-qa.com"


def test_register_returns_token_and_me_works(client):
    email = _email()
    r = client.post("/auth/register", json={"email": email, "password": "secret123"})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]

    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == email
    assert body["role"] == "user"
    assert body["is_active"] is True


def test_login_after_register(client):
    email = _email()
    client.post("/auth/register", json={"email": email, "password": "secret123"})

    r = client.post("/auth/login", json={"email": email, "password": "secret123"})
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"


def test_wrong_password_is_401(client):
    email = _email()
    client.post("/auth/register", json={"email": email, "password": "secret123"})

    r = client.post("/auth/login", json={"email": email, "password": "WRONG-one"})
    assert r.status_code == 401


def test_duplicate_email_is_409(client):
    email = _email()
    a = client.post("/auth/register", json={"email": email, "password": "secret123"})
    assert a.status_code == 200
    b = client.post("/auth/register", json={"email": email, "password": "secret123"})
    assert b.status_code == 409


def test_short_password_is_422(client):
    r = client.post("/auth/register", json={"email": _email(), "password": "short"})
    assert r.status_code == 422


def test_me_requires_token(client):
    assert client.get("/auth/me").status_code == 401
    assert (
        client.get(
            "/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
        ).status_code
        == 401
    )


def test_admin_is_seeded_and_can_log_in(client):
    r = client.post(
        "/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert r.status_code == 200
    token = r.json()["access_token"]
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.json()["role"] == "admin"


def test_forgot_password_is_stubbed(client):
    r = client.post(
        "/auth/forgot-password", json={"email": "whoever@referral-card-qa.com"}
    )
    assert r.status_code == 200
    assert r.json()["status"] == "email_not_configured"
