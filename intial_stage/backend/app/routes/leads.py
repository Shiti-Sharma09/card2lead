"""POST /api/leads — validate the reviewed lead and append it to Excel."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..config import get_settings
from ..models import LeadRequest
from ..services.excel_store import append_lead
from ..services.normalize import normalize_email, normalize_phone

router = APIRouter()
log = logging.getLogger("card2lead.leads")

# Per AQ1: every field is required before a lead can be saved.
REQUIRED_FIELDS = ["name", "company", "title", "email", "phone", "notes", "assignedTo"]


def _email_looks_valid(value: str) -> bool:
    first = value.split(",")[0].strip()
    return "@" in first and "." in first.split("@")[-1]


def _phone_has_enough_digits(value: str) -> bool:
    return len([c for c in value if c.isdigit()]) >= 10


@router.post("/leads")
def create_lead(lead: LeadRequest) -> JSONResponse:
    settings = get_settings()
    data = lead.model_dump()

    missing = [key for key in REQUIRED_FIELDS if not str(data.get(key, "")).strip()]
    if missing:
        return JSONResponse(
            status_code=422,
            content={"ok": False, "error": "validation", "fields": missing},
        )

    if data["assignedTo"] not in settings.assignees:
        return JSONResponse(
            status_code=422,
            content={"ok": False, "error": "validation", "fields": ["assignedTo"]},
        )

    if not _email_looks_valid(data["email"]):
        return JSONResponse(
            status_code=422,
            content={"ok": False, "error": "validation", "fields": ["email"]},
        )

    if not _phone_has_enough_digits(data["phone"]):
        return JSONResponse(
            status_code=422,
            content={"ok": False, "error": "validation", "fields": ["phone"]},
        )

    # defensive final tidy (the frontend sends already-normalized values)
    data["email"] = normalize_email(data["email"])
    data["phone"] = normalize_phone(data["phone"])[0]

    try:
        row = append_lead(settings.excel_path, data)
    except PermissionError:
        return JSONResponse(
            status_code=409,
            content={
                "ok": False,
                "error": "excel_locked",
                "message": (
                    f"{settings.excel_path.name} is open in Excel. "
                    "Close it and press Save again."
                ),
            },
        )
    except Exception as exc:  # noqa: BLE001
        log.exception("excel write failed")
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": "write_failed", "message": str(exc)},
        )

    return JSONResponse(status_code=200, content={"ok": True, "row": row})
