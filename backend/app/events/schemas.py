"""Event request / response models."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class EventCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    location: str | None = Field(default=None, max_length=200)
    organizer: str | None = Field(default=None, max_length=200)
    start_date: date | None = None
    end_date: date | None = None


class EventUpdate(BaseModel):
    # name is intentionally not editable — it is tied to the Google Sheet tab
    description: str | None = Field(default=None, max_length=2000)
    location: str | None = Field(default=None, max_length=200)
    organizer: str | None = Field(default=None, max_length=200)
    start_date: date | None = None
    end_date: date | None = None
    is_active: bool | None = None


class EventOut(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None
    location: str | None
    organizer: str | None
    start_date: date | None
    end_date: date | None
    is_active: bool
    google_tab_name: str | None
    created_at: datetime
