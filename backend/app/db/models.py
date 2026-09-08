"""Database tables (SQLModel).

Phase 0: AuditLog
Phase 1: User
Later phases add Event, EventAccess, Assignee, IdempotencyKey.
"""

from __future__ import annotations

from datetime import datetime, timezone

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


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_log"

    id: int | None = Field(default=None, primary_key=True)
    ts: datetime = Field(default_factory=_utcnow, index=True)
    actor_email: str | None = Field(default=None, index=True)
    action: str = Field(index=True)
    detail: str | None = Field(default=None)  # JSON string, no secrets
    ip: str | None = Field(default=None)
