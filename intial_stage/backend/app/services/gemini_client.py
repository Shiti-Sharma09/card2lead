"""Business-card extraction via Google Gemini (vision -> structured JSON).

Falls back to sample data when no API key is set so the whole app is
testable before the key arrives.
"""

from __future__ import annotations

import json
import logging
import time

from ..config import get_settings
from ..models import Confidence, ExtractedFields, ExtractResponse

log = logging.getLogger("card2lead.gemini")

PROMPT = """You are extracting contact details from a photo of ONE business card.

Return ONLY a JSON object with exactly this shape:
{
  "fields": {
    "name": "",
    "company": "",
    "title": "",
    "email": "",
    "phone": ""
  },
  "confidence": {
    "name": 0, "company": 0, "title": 0, "email": 0, "phone": 0
  }
}

Rules:
- "name" = the person's full name. "company" = the organisation.
  "title" = their job title / designation.
- "email" = email address(es). "phone" = phone number(s).
- If a field is not clearly printed on the card, use an empty string "" and
  confidence 0. DO NOT guess.
- If there are multiple emails or phone numbers, separate them with a comma
  and a space, e.g. "+91 98765 43210, +91 12345 67890". Never run two numbers
  together without a comma between them.
- Keep each phone number's digits exactly as printed (with its +, -, spaces or
  parentheses). Do not invent or merge country codes.
- confidence is an integer 0-100 describing how clearly YOU could read that
  specific value (legibility + certainty) - not how important it is.
- Output must be valid JSON. No markdown fences, no commentary.
"""

_MOCK = ExtractResponse(
    blurry=False,
    mock=True,
    fields=ExtractedFields(
        name="Rahul Sharma",
        company="ABC Technologies Pvt. Ltd.",
        title="Sales Director",
        email="rahul.sharma@abctech.com",
        phone="+91 98765 43210",
    ),
    confidence=Confidence(name=97, company=92, title=84, email=99, phone=96),
    message="MOCK MODE — no GEMINI_API_KEY set. Showing sample data so the flow is testable.",
)


def _coerce_conf(value: object) -> int:
    try:
        return max(0, min(100, int(round(float(value)))))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def _parse(raw_text: str) -> tuple[ExtractedFields, Confidence]:
    text = (raw_text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text[:4].lower() == "json":
            text = text[4:]
        text = text.strip()

    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("model returned JSON that is not an object")
    f = data.get("fields")
    if not isinstance(f, dict):
        f = data  # some responses inline the fields at the top level
    c = data.get("confidence")
    if not isinstance(c, dict):
        c = {}

    fields = ExtractedFields(
        name=str(f.get("name") or ""),
        company=str(f.get("company") or ""),
        title=str(f.get("title") or ""),
        email=str(f.get("email") or ""),
        phone=str(f.get("phone") or ""),
    )
    conf = Confidence(
        name=_coerce_conf(c.get("name")),
        company=_coerce_conf(c.get("company")),
        title=_coerce_conf(c.get("title")),
        email=_coerce_conf(c.get("email")),
        phone=_coerce_conf(c.get("phone")),
    )
    return fields, conf


def extract_fields(image_bytes: bytes) -> ExtractResponse:
    settings = get_settings()

    if settings.mock_mode:
        log.warning("GEMINI_API_KEY not set — returning MOCK extraction.")
        return _MOCK.model_copy(deep=True)

    # imported lazily so the package is optional until a key exists
    from google import genai
    from google.genai import types

    client = genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(timeout=settings.gemini_timeout_ms),
    )
    last_err: Exception | None = None

    for attempt in (1, 2):
        try:
            resp = client.models.generate_content(
                model=settings.gemini_model,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                    PROMPT,
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0,
                ),
            )
            fields, conf = _parse(getattr(resp, "text", "") or "")
            return ExtractResponse(blurry=False, mock=False, fields=fields, confidence=conf)
        except Exception as exc:  # noqa: BLE001 - retry once, then surface
            last_err = exc
            log.warning("Gemini attempt %s failed: %s", attempt, exc)
            if attempt == 1:
                time.sleep(1.0)  # brief pause helps with transient 429/503

    raise RuntimeError(f"Gemini extraction failed: {last_err}")
