"""The admin-managed "Assigned To" name list."""

from __future__ import annotations

from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.logging import log_event
from app.db.base import engine
from app.db.models import Assignee


class AssigneeExistsError(Exception):
    pass


class AssigneeNotFoundError(Exception):
    pass


def list_assignees(session: Session, *, include_inactive: bool = False) -> list[Assignee]:
    stmt = select(Assignee)
    if not include_inactive:
        stmt = stmt.where(Assignee.is_active == True)  # noqa: E712
    return list(session.exec(stmt.order_by(Assignee.name)).all())


def _by_name(session: Session, name: str) -> Assignee | None:
    return session.exec(select(Assignee).where(Assignee.name == name)).first()


def add_assignee(session: Session, name: str, actor_email: str) -> Assignee:
    name = name.strip()
    existing = _by_name(session, name)
    if existing is not None:
        if existing.is_active:
            raise AssigneeExistsError()
        # re-adding a previously removed name reactivates it
        existing.is_active = True
        session.add(existing)
        session.commit()
        session.refresh(existing)
        log_event("ASSIGNEE_REACTIVATED", session=session, actor=actor_email, name=name)
        return existing

    a = Assignee(name=name, created_by=actor_email)
    session.add(a)
    session.commit()
    session.refresh(a)
    log_event("ASSIGNEE_ADDED", session=session, actor=actor_email, name=name)
    return a


def remove_assignee(session: Session, assignee_id: int, actor_email: str) -> None:
    a = session.get(Assignee, assignee_id)
    if a is None:
        raise AssigneeNotFoundError()
    if a.is_active:
        a.is_active = False
        session.add(a)
        session.commit()
        log_event("ASSIGNEE_REMOVED", session=session, actor=actor_email, name=a.name)


def seed_assignees() -> None:
    """Create the starting names on first boot (idempotent)."""
    names = get_settings().seed_assignee_names
    if not names:
        return
    with Session(engine) as session:
        for name in names:
            if _by_name(session, name) is None:
                session.add(Assignee(name=name, created_by="system"))
        session.commit()
    log_event("ASSIGNEES_SEEDED", names=names)
