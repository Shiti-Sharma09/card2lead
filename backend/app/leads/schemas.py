"""Lead-submission request / response models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LeadCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    company: str = Field(default="", max_length=200)
    title: str = Field(default="", max_length=200)
    email: str = Field(default="", max_length=320)
    phone: str = Field(default="", max_length=100)
    notes: str = Field(default="", max_length=2000)
    assigned_to: str = Field(min_length=1, max_length=80)
    # a fresh id the client generates when the review screen opens
    request_id: str = Field(min_length=8, max_length=100)


class LeadResponse(BaseModel):
    ok: bool
    duplicate: bool = False
    row: list[str] | None = None
