from tests.conftest import admin_token, auth_header, new_user_token


def test_seeded_names_present_for_any_user(client):
    tok = new_user_token(client)
    r = client.get("/assignees", headers=auth_header(tok))
    assert r.status_code == 200
    names = {a["name"] for a in r.json()}
    assert {"NITISH", "HARSHAD"} <= names


def test_list_requires_auth(client):
    assert client.get("/assignees").status_code == 401


def test_user_cannot_add_or_see_all(client):
    tok = new_user_token(client)
    assert client.post("/assignees", json={"name": "X"}, headers=auth_header(tok)).status_code == 403
    assert client.get("/assignees?all=true", headers=auth_header(tok)).status_code == 403


def test_admin_add_remove_reactivate(client):
    tok = admin_token(client)

    # add
    r = client.post("/assignees", json={"name": "PRIYA"}, headers=auth_header(tok))
    assert r.status_code == 201
    aid = r.json()["id"]

    # duplicate -> 409
    assert client.post("/assignees", json={"name": "PRIYA"}, headers=auth_header(tok)).status_code == 409

    # visible in the active list
    active = {a["name"] for a in client.get("/assignees", headers=auth_header(tok)).json()}
    assert "PRIYA" in active

    # remove -> gone from active, still in ?all=true
    assert client.delete(f"/assignees/{aid}", headers=auth_header(tok)).status_code == 204
    active = {a["name"] for a in client.get("/assignees", headers=auth_header(tok)).json()}
    assert "PRIYA" not in active
    all_names = {a["name"] for a in client.get("/assignees?all=true", headers=auth_header(tok)).json()}
    assert "PRIYA" in all_names

    # re-add reactivates the same row
    r = client.post("/assignees", json={"name": "PRIYA"}, headers=auth_header(tok))
    assert r.status_code == 201
    assert r.json()["id"] == aid
    assert r.json()["is_active"] is True


def test_remove_missing_is_404(client):
    tok = admin_token(client)
    assert client.delete("/assignees/999999", headers=auth_header(tok)).status_code == 404
