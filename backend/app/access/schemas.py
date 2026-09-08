"""Event-access request / response models."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, EmailStr


class GrantIn(BaseModel):
    email: EmailStr


class AccessUserOut(BaseModel):
    user_id: int
    email: str
    granted_at: datetime


class AccessibleEventOut(BaseModel):
    id: int
    name: str
    slug: str
    location: str | None
    organizer: str | None
    start_date: date | None
    end_date: date | None
