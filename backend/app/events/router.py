"""/events routes. Admin-only in Phase 2; Phase 3 opens listing to assigned users."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.access.service import list_accessible_events, user_can_access_event
from app.auth.deps import get_current_user, require_admin
from app.db.base import get_session
from app.db.models import Event, User
from app.events.schemas import EventCreate, EventOut, EventUpdate
from app.events.service import (
    EventNameTakenError,
    EventNotFoundError,
    create_event,
    get_event,
    update_event,
)
from app.sheets.client import SheetsError

router = APIRouter()


def _out(e: Event) -> EventOut:
    return EventOut(
        id=e.id,
        name=e.name,
        slug=e.slug,
        description=e.description,
        location=e.location,
        organizer=e.organizer,
        start_date=e.start_date,
        end_date=e.end_date,
        is_active=e.is_active,
        google_tab_name=e.google_tab_name,
        created_at=e.created_at,
    )


@router.post("", response_model=EventOut, status_code=status.HTTP_201_CREATED)
def create(
    body: EventCreate,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
) -> EventOut:
    try:
        event = create_event(session, body, admin.email)
    except EventNameTakenError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An event with this name already exists.",
        )
    except SheetsError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not create the event's Google Sheet tab: {exc}",
        )
    return _out(event)


@router.get("", response_model=list[EventOut])
def list_(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[EventOut]:
    # admin -> all events; other users -> only active events they're assigned to
    return [_out(e) for e in list_accessible_events(session, user)]


@router.get("/{event_id}", response_model=EventOut)
def detail(
    event_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> EventOut:
    try:
        event = get_event(session, event_id)
    except EventNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")
    if not user_can_access_event(session, user, event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this event.",
        )
    return _out(event)


@router.patch("/{event_id}", response_model=EventOut)
def patch(
    event_id: int,
    body: EventUpdate,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
) -> EventOut:
    try:
        return _out(update_event(session, event_id, body, admin.email))
    except EventNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")
