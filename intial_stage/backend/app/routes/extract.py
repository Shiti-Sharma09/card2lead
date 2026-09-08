"""POST /api/extract — image in, structured (normalized) fields out."""

from __future__ import annotations

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..config import get_settings
from ..models import ExtractResponse
from ..services.gemini_client import extract_fields
from ..services.image_ops import is_decodable, light_cleanup, sharpness_score
from ..services.normalize import clean_text, normalize_email, normalize_phone

router = APIRouter()
log = logging.getLogger("card2lead.extract")


# Sync def -> Starlette runs it in a threadpool, so the blocking OpenCV / Gemini
# work never stalls the event loop for other requests.
@router.post("/extract", response_model=ExtractResponse)
def extract(image: UploadFile = File(...)) -> ExtractResponse:
    settings = get_settings()
    raw = image.file.read()

    if not raw:
        raise HTTPException(status_code=400, detail="The uploaded image was empty.")
    if len(raw) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"Image is larger than {settings.max_upload_mb} MB.",
        )
    if not is_decodable(raw):
        raise HTTPException(
            status_code=400,
            detail="That file isn't a readable image. Use a JPEG or PNG photo of the card.",
        )

    # Safety-net sharpness gate (the camera screen already checks client-side,
    # but uploaded photos come straight here).
    score = sharpness_score(raw)
    log.info("sharpness=%.1f threshold=%.1f", score, settings.blur_threshold)
    if score < settings.blur_threshold:
        return ExtractResponse(blurry=True, message="Image looks blurry. Please retake.")

    try:
        cleaned = light_cleanup(raw)
    except Exception as exc:  # noqa: BLE001 - fall back to the original bytes
        log.warning("cleanup failed, using original image: %s", exc)
        cleaned = raw

    try:
        result = extract_fields(cleaned)
    except Exception as exc:  # noqa: BLE001
        log.exception("extraction failed")
        raise HTTPException(
            status_code=502,
            detail="Could not read the card. Please try again.",
        ) from exc

    # normalize the values before they reach the review form
    result.fields.name = clean_text(result.fields.name)
    result.fields.company = clean_text(result.fields.company)
    result.fields.title = clean_text(result.fields.title)
    result.fields.email = normalize_email(result.fields.email)

    phone, clean = normalize_phone(result.fields.phone)
    result.fields.phone = phone
    if not clean and result.confidence.phone >= settings.confidence_threshold:
        # force the amber "please verify" flag when the number looked off
        result.confidence.phone = settings.confidence_threshold - 1

    return result
