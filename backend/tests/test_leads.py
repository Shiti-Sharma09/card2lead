import uuid

from tests.conftest import admin_token, auth_header, new_user


def _event(client, atok) -> int:
    r = client.post(
        "/events", json={"name": f"Leads {uuid.uuid4().hex[:8]}"}, headers=auth_header(atok)
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _payload(**over) -> dict:
    base = {
        "name": "Meera Iyer",
        "company": "Cobalt Labs",
        "title": "CTO",
        "email": "meera@cobaltlabs.com",
        "phone": "+91 98765 43210",
        "notes": "met at booth 4",
        "assigned_to": "NITISH",
        "request_id": uuid.uuid4().hex,
    }
    base.update(over)
    return base


def test_submit_lead_builds_the_row(client):
    atok = admin_token(client)
    eid = _event(client, atok)
    r = client.post(
        f"/events/{eid}/leads", json=_payload(), headers=auth_header(atok)
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True and body["duplicate"] is False
    row = body["row"]
    assert len(row) == 10
    assert row[1] == "card.admin@gmail.com" or "@" in row[1]  # user email from session
    assert row[3] == "Meera Iyer"
    assert row[9] == "NITISH"


def test_duplicate_request_id_writes_nothing_new(client):
    atok = admin_token(client)
    eid = _event(client, atok)
    p = _payload()
    a = client.post(f"/events/{eid}/leads", json=p, headers=auth_header(atok))
    b = client.post(f"/events/{eid}/leads", json=p, headers=auth_header(atok))
    assert a.status_code == 200 and a.json()["duplicate"] is False
    assert b.status_code == 200 and b.json()["duplicate"] is True


def test_unknown_assigned_to_is_422(client):
    atok = admin_token(client)
    eid = _event(client, atok)
    r = client.post(
        f"/events/{eid}/leads",
        json=_payload(assigned_to="NOBODY"),
        headers=auth_header(atok),
    )
    assert r.status_code == 422


def test_removed_assignee_is_rejected(client):
    atok = admin_token(client)
    eid = _event(client, atok)
    add = client.post("/assignees", json={"name": "TEMPGUY"}, headers=auth_header(atok))
    client.delete(f"/assignees/{add.json()['id']}", headers=auth_header(atok))
    r = client.post(
        f"/events/{eid}/leads",
        json=_payload(assigned_to="TEMPGUY"),
        headers=auth_header(atok),
    )
    assert r.status_code == 422


def test_bad_email_is_422(client):
    atok = admin_token(client)
    eid = _event(client, atok)
    r = client.post(
        f"/events/{eid}/leads",
        json=_payload(email="not-an-email"),
        headers=auth_header(atok),
    )
    assert r.status_code == 422


def test_blank_name_is_422(client):
    atok = admin_token(client)
    eid = _event(client, atok)
    r = client.post(
        f"/events/{eid}/leads", json=_payload(name=""), headers=auth_header(atok)
    )
    assert r.status_code == 422


def test_lead_requires_event_access(client):
    atok = admin_token(client)
    eid = _event(client, atok)
    _, utok = new_user(client)
    r = client.post(
        f"/events/{eid}/leads", json=_payload(), headers=auth_header(utok)
    )
    assert r.status_code == 403


def test_lead_requires_auth(client):
    assert client.post("/events/1/leads", json=_payload()).status_code == 401


def test_granted_user_can_submit(client):
    atok = admin_token(client)
    eid = _event(client, atok)
    email, utok = new_user(client)
    client.post(f"/events/{eid}/access", json={"email": email}, headers=auth_header(atok))
    r = client.post(
        f"/events/{eid}/leads", json=_payload(), headers=auth_header(utok)
    )
    assert r.status_code == 200
    assert r.json()["row"][1] == email


# --- unit: writer retries then fails ------------------------------------
def test_writer_retries_then_raises(monkeypatch):
    from app.sheets import client as sc
    from app.sheets import writer
    from app.sheets.client import SheetsError

    monkeypatch.setattr(writer.time, "sleep", lambda *_: None)
    calls = {"n": 0}

    class _Boom:
        def spreadsheets(self):
            raise RuntimeError("google is down")

    def _fake_service():
        calls["n"] += 1
        return _Boom()

    monkeypatch.setattr(writer, "_service", _fake_service)
    try:
        writer.append_row("Tab", ["a"] * 10)
        raise AssertionError("expected SheetsError")
    except SheetsError:
        pass
    assert calls["n"] == 3  # 3 attempts
