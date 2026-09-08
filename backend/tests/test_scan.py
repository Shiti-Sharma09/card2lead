import io
import uuid

import pytest
from PIL import Image

from tests.conftest import admin_token, auth_header, new_user


def _jpeg(w: int = 8, h: int = 8) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), "white").save(buf, format="JPEG")
    return buf.getvalue()


def _make_event(client, atok) -> int:
    r = client.post(
        "/events", json={"name": f"Scan {uuid.uuid4().hex[:8]}"}, headers=auth_header(atok)
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_scan_mock_mode_returns_sample_fields(client):
    atok = admin_token(client)
    eid = _make_event(client, atok)
    r = client.post(
        f"/events/{eid}/scan",
        files={"image": ("card.jpg", _jpeg(), "image/jpeg")},
        headers=auth_header(atok),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mock"] is True
    f = body["fields"]
    assert f["name"] == "Rahul Sharma"
    assert f["company"].startswith("ABC Technologies")
    assert "@" in f["email"]
    assert f["phone"].startswith("+91")


def test_scan_requires_auth(client):
    r = client.post(
        "/events/1/scan", files={"image": ("c.jpg", _jpeg(), "image/jpeg")}
    )
    assert r.status_code == 401


def test_scan_blocks_user_without_access(client):
    atok = admin_token(client)
    eid = _make_event(client, atok)
    _, utok = new_user(client)
    r = client.post(
        f"/events/{eid}/scan",
        files={"image": ("c.jpg", _jpeg(), "image/jpeg")},
        headers=auth_header(utok),
    )
    assert r.status_code == 403


def test_scan_granted_user_can_scan(client):
    atok = admin_token(client)
    eid = _make_event(client, atok)
    email, utok = new_user(client)
    client.post(
        f"/events/{eid}/access", json={"email": email}, headers=auth_header(atok)
    )
    r = client.post(
        f"/events/{eid}/scan",
        files={"image": ("c.jpg", _jpeg(), "image/jpeg")},
        headers=auth_header(utok),
    )
    assert r.status_code == 200
    assert r.json()["fields"]["name"] == "Rahul Sharma"


def test_scan_missing_event_is_404(client):
    atok = admin_token(client)
    r = client.post(
        "/events/999999/scan",
        files={"image": ("c.jpg", _jpeg(), "image/jpeg")},
        headers=auth_header(atok),
    )
    assert r.status_code == 404


def test_scan_empty_file_is_400(client):
    atok = admin_token(client)
    eid = _make_event(client, atok)
    r = client.post(
        f"/events/{eid}/scan",
        files={"image": ("empty.jpg", b"", "image/jpeg")},
        headers=auth_header(atok),
    )
    assert r.status_code == 400


# --- unit: parser + quota -------------------------------------------------
def test_parser_tolerates_fences_and_alt_keys():
    from app.groq.client import parse_fields

    raw = '```json\n{"name":"A B","company_name":"X Ltd","designation":"CEO",' \
          '"mail_address":"a@b.com","phone_number":"+91 1"}\n```'
    out = parse_fields(raw)
    assert out == {
        "name": "A B",
        "company": "X Ltd",
        "title": "CEO",
        "email": "a@b.com",
        "phone": "+91 1",
    }


def test_quota_blocks_after_limit(monkeypatch):
    from app.core.config import get_settings
    from app.groq import quota

    quota._reset()
    s = get_settings()
    monkeypatch.setattr(s, "groq_max_per_min", 2)
    monkeypatch.setattr(s, "groq_max_per_day", 100)

    quota.check_and_consume()
    quota.check_and_consume()
    with pytest.raises(quota.QuotaExceeded) as ei:
        quota.check_and_consume()
    assert ei.value.scope == "minute"
    quota._reset()
