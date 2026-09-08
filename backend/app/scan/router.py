"""POST /events/{event_id}/scan — image in, extracted (normalised) fields out.

Does NOT save anything. The reviewed fields are saved via /leads in Phase 5.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlmodel import Session

from app.access.deps import require_event_access
from app.auth.deps import get_current_user
from app.core.config import get_settings
from app.core.logging import log_event
from app.db.base import get_session
from app.db.models import Event, User
from app.groq import client as groq
from app.groq import quota
from app.lib.image_prep import prepare_image
from app.lib.normalize import clean_text, normalize_email, normalize_phone

router = APIRouter()


class ScanFields(BaseModel):
    name: str = ""
    company: str = ""
    title: str = ""
    email: str = ""
    phone: str = ""


class ScanResponse(BaseModel):
    mock: bool
    fields: ScanFields


@router.post("/{event_id}/scan", response_model=ScanResponse)
def scan(
    event: Event = Depends(require_event_access),
    image: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ScanResponse:
    settings = get_settings()
    raw = image.file.read()

    if not raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded image is empty."
        )
    if len(raw) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image is larger than {settings.max_upload_mb} MB.",
        )

    prepared, mime = prepare_image(raw)

    if not groq.is_mock():
        try:
            quota.check_and_consume()
        except quota.QuotaExceeded as exc:
            log_event(
                "RATE_LIMIT_HIT",
                session=session,
                actor=user.email,
                event_id=event.id,
                scope=exc.scope,
            )
            msg = (
                "The daily card-reading limit has been reached. Try again tomorrow "
                "or ask an admin to raise the limit."
                if exc.scope == "day"
                else "Too many scans in the last minute. Please wait a moment and retry."
            )
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=msg)

    log_event(
        "GROQ_REQUEST",
        session=session,
        actor=user.email,
        event_id=event.id,
        mock=groq.is_mock(),
    )
    try:
        fields = groq.extract_card(prepared, mime)
    except groq.GroqError as exc:
        log_event(
            "GROQ_FAILED",
            session=session,
            actor=user.email,
            event_id=event.id,
            error=str(exc)[:200],
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not read the card. Please retake the photo and try again.",
        )

    return ScanResponse(
        mock=groq.is_mock(),
        fields=ScanFields(
            name=clean_text(fields["name"]),
            company=clean_text(fields["company"]),
            title=clean_text(fields["title"]),
            email=normalize_email(fields["email"]),
            phone=normalize_phone(fields["phone"])[0],
        ),
    )
