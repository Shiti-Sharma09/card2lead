import uuid

from tests.conftest import admin_token, auth_header, new_user_token


def _name() -> str:
    return f"Event {uuid.uuid4().hex[:8]}"


def test_user_cannot_create_or_list_events(client):
    tok = new_user_token(client)
    assert client.get("/events", headers=auth_header(tok)).status_code == 403
    assert client.post(
        "/events", json={"name": _name()}, headers=auth_header(tok)
    ).status_code == 403


def test_admin_creates_event(client):
    tok = admin_token(client)
    name = _name()
    r = client.post(
        "/events",
        json={
            "name": name,
            "description": "a test",
            "location": "Dubai",
            "organizer": "Antino",
            "start_date": "2026-10-01",
            "end_date": "2026-10-03",
        },
        headers=auth_header(tok),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == name
    assert body["slug"]
    assert body["is_active"] is True
    # Sheets disabled in tests -> no tab created
    assert body["google_tab_name"] is None


def test_duplicate_event_name_is_409(client):
    tok = admin_token(client)
    name = _name()
    assert client.post("/events", json={"name": name}, headers=auth_header(tok)).status_code == 201
    assert client.post("/events", json={"name": name}, headers=auth_header(tok)).status_code == 409


def test_list_and_get_and_patch(client):
    tok = admin_token(client)
    name = _name()
    created = client.post(
        "/events", json={"name": name}, headers=auth_header(tok)
    ).json()
    eid = created["id"]

    listed = client.get("/events", headers=auth_header(tok)).json()
    assert any(e["id"] == eid for e in listed)

    got = client.get(f"/events/{eid}", headers=auth_header(tok))
    assert got.status_code == 200
    assert got.json()["name"] == name

    patched = client.patch(
        f"/events/{eid}",
        json={"description": "updated", "is_active": False},
        headers=auth_header(tok),
    )
    assert patched.status_code == 200
    assert patched.json()["description"] == "updated"
    assert patched.json()["is_active"] is False


def test_get_missing_event_is_404(client):
    tok = admin_token(client)
    assert client.get("/events/999999", headers=auth_header(tok)).status_code == 404
