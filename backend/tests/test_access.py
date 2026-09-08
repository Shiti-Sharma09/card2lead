import uuid

from tests.conftest import admin_token, auth_header, new_user


def _event(client, admin_tok) -> dict:
    name = f"Event {uuid.uuid4().hex[:8]}"
    r = client.post("/events", json={"name": name}, headers=auth_header(admin_tok))
    assert r.status_code == 201, r.text
    return r.json()


def test_unassigned_user_sees_nothing(client):
    atok = admin_token(client)
    _event(client, atok)  # exists, but not granted
    _, utok = new_user(client)

    assert client.get("/events", headers=auth_header(utok)).json() == []
    assert client.get("/me/events", headers=auth_header(utok)).json() == []


def test_grant_then_user_sees_event(client):
    atok = admin_token(client)
    ev = _event(client, atok)
    email, utok = new_user(client)

    # before grant: no access to the specific event
    assert client.get(f"/events/{ev['id']}", headers=auth_header(utok)).status_code == 403

    g = client.post(
        f"/events/{ev['id']}/access", json={"email": email}, headers=auth_header(atok)
    )
    assert g.status_code == 201
    uid = g.json()["user_id"]

    # after grant
    assert client.get(f"/events/{ev['id']}", headers=auth_header(utok)).status_code == 200
    ids = [e["id"] for e in client.get("/events", headers=auth_header(utok)).json()]
    assert ev["id"] in ids
    mine = [e["id"] for e in client.get("/me/events", headers=auth_header(utok)).json()]
    assert ev["id"] in mine

    # revoke
    r = client.delete(
        f"/events/{ev['id']}/access/{uid}", headers=auth_header(atok)
    )
    assert r.status_code == 204
    assert client.get(f"/events/{ev['id']}", headers=auth_header(utok)).status_code == 403
    assert client.get("/events", headers=auth_header(utok)).json() == []


def test_grant_is_idempotent(client):
    atok = admin_token(client)
    ev = _event(client, atok)
    email, _ = new_user(client)
    a = client.post(f"/events/{ev['id']}/access", json={"email": email}, headers=auth_header(atok))
    b = client.post(f"/events/{ev['id']}/access", json={"email": email}, headers=auth_header(atok))
    assert a.status_code == 201 and b.status_code == 201
    assert a.json()["user_id"] == b.json()["user_id"]


def test_grant_unregistered_email_is_404(client):
    atok = admin_token(client)
    ev = _event(client, atok)
    r = client.post(
        f"/events/{ev['id']}/access",
        json={"email": "nobody-here@referral-card-qa.com"},
        headers=auth_header(atok),
    )
    assert r.status_code == 404


def test_user_cannot_manage_access(client):
    atok = admin_token(client)
    ev = _event(client, atok)
    email, utok = new_user(client)
    assert client.get(f"/events/{ev['id']}/access", headers=auth_header(utok)).status_code == 403
    assert client.post(
        f"/events/{ev['id']}/access", json={"email": email}, headers=auth_header(utok)
    ).status_code == 403


def test_inactive_event_hidden_from_assigned_user(client):
    atok = admin_token(client)
    ev = _event(client, atok)
    email, utok = new_user(client)
    client.post(f"/events/{ev['id']}/access", json={"email": email}, headers=auth_header(atok))
    assert client.get(f"/events/{ev['id']}", headers=auth_header(utok)).status_code == 200

    client.patch(f"/events/{ev['id']}", json={"is_active": False}, headers=auth_header(atok))
    assert client.get(f"/events/{ev['id']}", headers=auth_header(utok)).status_code == 403
    assert client.get("/events", headers=auth_header(utok)).json() == []
    # admin still sees it
    assert client.get(f"/events/{ev['id']}", headers=auth_header(atok)).status_code == 200


def test_revoke_missing_is_404(client):
    atok = admin_token(client)
    ev = _event(client, atok)
    assert client.delete(
        f"/events/{ev['id']}/access/999999", headers=auth_header(atok)
    ).status_code == 404


def test_list_access_shows_granted_users(client):
    atok = admin_token(client)
    ev = _event(client, atok)
    e1, _ = new_user(client)
    e2, _ = new_user(client)
    client.post(f"/events/{ev['id']}/access", json={"email": e1}, headers=auth_header(atok))
    client.post(f"/events/{ev['id']}/access", json={"email": e2}, headers=auth_header(atok))
    rows = client.get(f"/events/{ev['id']}/access", headers=auth_header(atok)).json()
    emails = {r["email"] for r in rows}
    assert {e1, e2} <= emails


def test_me_events_requires_auth(client):
    assert client.get("/me/events").status_code == 401
