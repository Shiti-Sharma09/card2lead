"""`require_event_access` — the dependency guarding /scan and /leads (Phase 4/5).

Reads `event_id` from the path. Admins always pass. Everyone else must have an
active event with an access grant.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlmodel import Session

from app.access.service import _grant_row
from app.auth.deps import get_current_user
from app.core.logging import log_event
from app.db.base import get_session
from app.db.models import Event, User

_NO_ACCESS = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="You don't have access to this event.",
)


def require_event_access(
    event_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Event:
    event = session.get(Event, event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found."
        )

    if user.role == "admin":
        return event

    if not event.is_active or _grant_row(session, user.id, event_id) is None:
        log_event(
            "ACCESS_DENIED",
            session=session,
            actor=user.email,
            event_id=event_id,
            reason="inactive" if not event.is_active else "not-assigned",
        )
        raise _NO_ACCESS

    return event
