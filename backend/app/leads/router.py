"""POST /events/{event_id}/leads — save the reviewed lead as one Sheet row."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.access.deps import require_event_access
from app.auth.deps import get_current_user
from app.core.logging import log_event
from app.db.base import get_session
from app.db.models import Event, User
from app.leads.schemas import LeadCreate, LeadResponse
from app.leads.service import (
    AssigneeInvalidError,
    DuplicateSubmission,
    EmailInvalidError,
    submit_lead,
)
from app.sheets.client import SheetsError

router = APIRouter()


@router.post("/{event_id}/leads", response_model=LeadResponse)
def create_lead(
    body: LeadCreate,
    event: Event = Depends(require_event_access),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> LeadResponse:
    try:
        result = submit_lead(session, event, user, body)
    except DuplicateSubmission as dup:
        return LeadResponse(ok=True, duplicate=True, row=dup.stored.get("row"))
    except EmailInvalidError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The email address doesn't look valid.",
        )
    except AssigneeInvalidError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Assigned To must be a name from the current list.",
        )
    except SheetsError as exc:
        log_event(
            "SHEET_WRITE_FAILED",
            session=session,
            actor=user.email,
            event_id=event.id,
            error=str(exc)[:200],
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Nothing was saved — the Google Sheet did not accept the row. "
                "Please try again in a moment."
            ),
        )
    return LeadResponse(**result)
