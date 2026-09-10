"""Event-access management (admin) + GET /me/events (any user)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session

from app.access.schemas import AccessibleEventOut, AccessUserOut, GrantIn
from app.access.service import (
    AccessNotFoundError,
    UserNotRegisteredError,
    grant_access,
    list_access,
    list_accessible_events,
    revoke_access,
)
from app.auth.deps import get_current_user, require_admin
from app.db.base import get_session
from app.db.models import User
from app.events.service import EventNotFoundError

# mounted at /events
router = APIRouter()
# mounted at /me
me_router = APIRouter()


@router.get("/{event_id}/access", response_model=list[AccessUserOut])
def list_grants(
    event_id: int,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
) -> list[AccessUserOut]:
    try:
        rows = list_access(session, event_id)
    except EventNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")
    return [
        AccessUserOut(user_id=u.id, email=u.email, granted_at=a.granted_at)
        for (u, a) in rows
    ]


@router.post(
    "/{event_id}/access",
    response_model=AccessUserOut,
    status_code=status.HTTP_201_CREATED,
)
def grant(
    event_id: int,
    body: GrantIn,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
) -> AccessUserOut:
    try:
        user, row = grant_access(session, event_id, body.email, admin.email)
    except EventNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")
    except UserNotRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account for that email yet — ask them to register first.",
        )
    return AccessUserOut(user_id=user.id, email=user.email, granted_at=row.granted_at)


@router.delete(
    "/{event_id}/access/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
def revoke(
    event_id: int,
    user_id: int,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
) -> Response:
    try:
        revoke_access(session, event_id, user_id, admin.email)
    except AccessNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="That user is not assigned to this event.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@me_router.get("/events", response_model=list[AccessibleEventOut])
def my_events(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[AccessibleEventOut]:
    return [
        AccessibleEventOut(
            id=e.id,
            name=e.name,
            slug=e.slug,
            location=e.location,
            organizer=e.organizer,
            start_date=e.start_date,
            end_date=e.end_date,
        )
        for e in list_accessible_events(session, user)
    ]
