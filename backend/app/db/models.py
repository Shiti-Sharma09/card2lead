"""Database tables (SQLModel).

Phase 0: AuditLog
Phase 1: User
Phase 2: Event, Assignee
Phase 3: EventAccess
Later phases add IdempotencyKey.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    password_hash: str
    role: str = Field(default="user")  # "admin" | "user"
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_utcnow)
    # bumped whenever the password changes; tokens issued before this are rejected
    password_changed_at: datetime = Field(default_factory=_utcnow)


class Event(SQLModel, table=True):
    __tablename__ = "events"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    slug: str = Field(unique=True, index=True)
    description: str | None = None
    location: str | None = None
    organizer: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_active: bool = Field(default=True)
    # the tab we created in the Google Sheet for this event
    google_tab_id: int | None = Field(default=None)
    google_tab_name: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow)
    created_by: str | None = Field(default=None)


class Assignee(SQLModel, table=True):
    """A name in the "Assigned To" dropdown. Admin-managed."""

    __tablename__ = "assignees"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    is_active: bool = Field(default=True)  # soft-remove: hidden from the dropdown
    created_at: datetime = Field(default_factory=_utcnow)
    created_by: str | None = Field(default=None)


class EventAccess(SQLModel, table=True):
    """Which users may use which event. One row = one grant. Delete = revoke."""

    __tablename__ = "event_access"
    __table_args__ = (UniqueConstraint("user_id", "event_id", name="uq_user_event"),)

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    event_id: int = Field(foreign_key="events.id", index=True)
    granted_by: str | None = Field(default=None)
    granted_at: datetime = Field(default_factory=_utcnow)


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_log"

    id: int | None = Field(default=None, primary_key=True)
    ts: datetime = Field(default_factory=_utcnow, index=True)
    actor_email: str | None = Field(default=None, index=True)
    action: str = Field(index=True)
    detail: str | None = Field(default=None)  # JSON string, no secrets
    ip: str | None = Field(default=None)
