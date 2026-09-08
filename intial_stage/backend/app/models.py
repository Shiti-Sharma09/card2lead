"""Pydantic request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, field_validator


class ExtractedFields(BaseModel):
    name: str = ""
    company: str = ""
    title: str = ""
    email: str = ""
    phone: str = ""


class Confidence(BaseModel):
    name: int = 0
    company: int = 0
    title: int = 0
    email: int = 0
    phone: int = 0


class ExtractResponse(BaseModel):
    blurry: bool = False
    mock: bool = False
    fields: ExtractedFields = ExtractedFields()
    confidence: Confidence = Confidence()
    message: str | None = None


class LeadRequest(BaseModel):
    name: str = ""
    company: str = ""
    title: str = ""
    email: str = ""
    phone: str = ""
    notes: str = ""
    assignedTo: str = ""

    @field_validator("*", mode="before")
    @classmethod
    def _none_to_blank(cls, value: object) -> object:
        """Tolerate an explicit null from a misbehaving client."""
        return "" if value is None else value
