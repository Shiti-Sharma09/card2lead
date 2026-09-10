"""Validate a reviewed lead and append it as one row to the event's Sheet tab."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.logging import log_event
from app.db.models import Assignee, Event, IdempotencyKey, User
from app.leads.schemas import LeadCreate
from app.sheets import client as sheets
from app.sheets import writer
from app.sheets.client import SheetsError

COLUMNS = [
    "Timestamp",
    "User Email",
    "Event",
    "Name",
    "Company",
    "Title",
    "Email",
    "Phone",
    "Notes",
    "Assigned To",
]


class DuplicateSubmission(Exception):
    def __init__(self, stored: dict) -> None:
        super().__init__("duplicate")
        self.stored = stored


class AssigneeInvalidError(Exception):
    pass


class EmailInvalidError(Exception):
    pass


def _now_ts() -> str:
    settings = get_settings()
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo(settings.timezone)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:  # pragma: no cover - tz data missing
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _email_ok(value: str) -> bool:
    if not value:
        return True  # optional
    head = value.split(",")[0].strip()
    return "@" in head and "." in head.rsplit("@", 1)[-1]


def submit_lead(
    session: Session, event: Event, user: User, data: LeadCreate
) -> dict:
    # 1. already seen this request_id?
    existing = session.exec(
        select(IdempotencyKey).where(IdempotencyKey.key == data.request_id)
    ).first()
    if existing is not None:
        log_event(
            "DUPLICATE_IGNORED",
            session=session,
            actor=user.email,
            event_id=event.id,
            request_id=data.request_id,
        )
        stored = json.loads(existing.result) if existing.result else {"ok": True}
        raise DuplicateSubmission(stored)

    # 2. validate
    if not _email_ok(data.email):
        raise EmailInvalidError()
    active = session.exec(
        select(Assignee).where(
            Assignee.name == data.assigned_to.strip(),
            Assignee.is_active == True,  # noqa: E712
        )
    ).first()
    if active is None:
        raise AssigneeInvalidError()

    # 3. claim the key (unique constraint stops a double-tap race)
    claim = IdempotencyKey(
        key=data.request_id, user_id=user.id, event_id=event.id, result=None
    )
    session.add(claim)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise DuplicateSubmission({"ok": True})
    session.refresh(claim)

    # 4. build + write the row
    row = [
        _now_ts(),
        user.email,
        event.name,
        data.name,
        data.company,
        data.title,
        data.email,
        data.phone,
        data.notes,
        data.assigned_to.strip(),
    ]

    try:
        if sheets.is_configured():
            if not event.google_tab_name:
                raise SheetsError(
                    "this event has no Sheet tab (created before Sheets was configured)"
                )
            writer.append_row(event.google_tab_name, row)
            log_event(
                "SHEET_WRITE_OK",
                session=session,
                actor=user.email,
                event_id=event.id,
                tab=event.google_tab_name,
            )
        else:
            log_event(
                "SHEET_WRITE_SKIPPED",
                session=session,
                actor=user.email,
                event_id=event.id,
                reason="GOOGLE_SHEET_ID blank",
            )
    except SheetsError:
        # release the claim so the client can retry with the same request_id
        session.delete(claim)
        session.commit()
        raise

    # 5. finalise
    result = {"ok": True, "row": row}
    claim.result = json.dumps(result)
    session.add(claim)
    session.commit()
    log_event(
        "LEAD_SUBMITTED",
        session=session,
        actor=user.email,
        event_id=event.id,
        assigned_to=data.assigned_to.strip(),
    )
    return result
