"""Grant / revoke / check per-event access."""

from __future__ import annotations

from sqlmodel import Session, select

from app.auth.service import get_user_by_email
from app.core.logging import log_event
from app.db.models import Event, EventAccess, User
from app.events.service import EventNotFoundError, get_event


class UserNotRegisteredError(Exception):
    pass


class AccessNotFoundError(Exception):
    pass


def _grant_row(session: Session, user_id: int, event_id: int) -> EventAccess | None:
    return session.exec(
        select(EventAccess).where(
            EventAccess.user_id == user_id, EventAccess.event_id == event_id
        )
    ).first()


def grant_access(
    session: Session, event_id: int, email: str, actor_email: str
) -> tuple[User, EventAccess]:
    get_event(session, event_id)  # raises EventNotFoundError

    user = get_user_by_email(session, email)
    if user is None:
        raise UserNotRegisteredError()

    row = _grant_row(session, user.id, event_id)
    if row is None:
        row = EventAccess(user_id=user.id, event_id=event_id, granted_by=actor_email)
        session.add(row)
        session.commit()
        session.refresh(row)
        log_event(
            "ACCESS_GRANTED",
            session=session,
            actor=actor_email,
            event_id=event_id,
            target=user.email,
        )
    return user, row


def revoke_access(
    session: Session, event_id: int, user_id: int, actor_email: str
) -> None:
    row = _grant_row(session, user_id, event_id)
    if row is None:
        raise AccessNotFoundError()
    session.delete(row)
    session.commit()
    log_event(
        "ACCESS_REVOKED",
        session=session,
        actor=actor_email,
        event_id=event_id,
        target_user_id=user_id,
    )


def list_access(session: Session, event_id: int) -> list[tuple[User, EventAccess]]:
    get_event(session, event_id)  # raises EventNotFoundError
    rows = session.exec(
        select(User, EventAccess)
        .where(EventAccess.event_id == event_id, User.id == EventAccess.user_id)
        .order_by(EventAccess.granted_at)
    ).all()
    return list(rows)


def user_can_access_event(session: Session, user: User, event_id: int) -> bool:
    if user.role == "admin":
        return session.get(Event, event_id) is not None
    event = session.get(Event, event_id)
    if event is None or not event.is_active:
        return False
    return _grant_row(session, user.id, event_id) is not None


def list_accessible_events(session: Session, user: User) -> list[Event]:
    if user.role == "admin":
        return list(
            session.exec(select(Event).order_by(Event.created_at.desc())).all()
        )
    stmt = (
        select(Event)
        .join(EventAccess, EventAccess.event_id == Event.id)
        .where(EventAccess.user_id == user.id, Event.is_active == True)  # noqa: E712
        .order_by(Event.created_at.desc())
    )
    return list(session.exec(stmt).all())
