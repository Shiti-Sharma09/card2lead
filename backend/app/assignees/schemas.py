"""Assigned-To list request / response models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AssigneeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class AssigneeOut(BaseModel):
    id: int
    name: str
    is_active: bool
