"""Event creation / listing / updating."""

from __future__ import annotations

import re

from sqlmodel import Session, select

from app.core.logging import log_event
from app.db.models import Event
from app.events.schemas import EventCreate, EventUpdate
from app.sheets import client as sheets


class EventNameTakenError(Exception):
    pass


class EventNotFoundError(Exception):
    pass


def _slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "event"


def _unique_slug(session: Session, name: str) -> str:
    base = _slugify(name)
    slug = base
    n = 2
    while session.exec(select(Event).where(Event.slug == slug)).first() is not None:
        slug = f"{base}-{n}"
        n += 1
    return slug


def create_event(session: Session, data: EventCreate, actor_email: str) -> Event:
    if session.exec(select(Event).where(Event.name == data.name)).first() is not None:
        raise EventNameTakenError()

    slug = _unique_slug(session, data.name)

    tab_id: int | None = None
    tab_name: str | None = None
    if sheets.is_configured():
        # raises SheetsError -> the route returns 502 and no event is created
        tab_id, tab_name = sheets.create_event_tab(data.name)
    else:
        log_event("SHEET_TAB_SKIPPED", actor=actor_email, reason="GOOGLE_SHEET_ID blank")

    event = Event(
        name=data.name,
        slug=slug,
        description=data.description,
        location=data.location,
        organizer=data.organizer,
        start_date=data.start_date,
        end_date=data.end_date,
        google_tab_id=tab_id,
        google_tab_name=tab_name,
        created_by=actor_email,
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    log_event(
        "EVENT_CREATED",
        session=session,
        actor=actor_email,
        event_id=event.id,
        name=event.name,
        tab=tab_name,
    )
    return event


def list_events(session: Session) -> list[Event]:
    return list(session.exec(select(Event).order_by(Event.created_at.desc())).all())


def get_event(session: Session, event_id: int) -> Event:
    event = session.get(Event, event_id)
    if event is None:
        raise EventNotFoundError()
    return event


def update_event(
    session: Session, event_id: int, data: EventUpdate, actor_email: str
) -> Event:
    event = get_event(session, event_id)
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(event, field, value)
    session.add(event)
    session.commit()
    session.refresh(event)
    log_event(
        "EVENT_UPDATED",
        session=session,
        actor=actor_email,
        event_id=event.id,
        fields=list(changes.keys()),
    )
    return event
