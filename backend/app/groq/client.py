"""Business-card extraction via Groq (vision -> flat JSON).

Returns sample data when GROQ_API_KEY is blank ("mock mode") so the whole flow
is testable without a key.
"""

from __future__ import annotations

import base64
import json
import logging
import time

from app.core.config import get_settings

log = logging.getLogger("groq")

PROMPT = (
    "You are reading ONE business card from the image. Extract these fields and "
    "return ONLY a compact JSON object — no prose, no code fences:\n"
    '{"name": "", "company": "", "title": "", "email": "", "phone": ""}\n'
    "Rules:\n"
    "- name    = the person's full name.\n"
    "- company = the organisation / company name.\n"
    "- title   = the person's job title / designation.\n"
    "- email   = the email address (if several, the main one).\n"
    "- phone   = the phone number exactly as printed (keep +, spaces, hyphens).\n"
    "- If a field is not on the card, use an empty string.\n"
    "- Output valid JSON only."
)

MOCK_FIELDS = {
    "name": "Rahul Sharma",
    "company": "ABC Technologies Pvt. Ltd.",
    "title": "Sales Director",
    "email": "rahul.sharma@abctech.com",
    "phone": "+91 98765 43210",
}


class GroqError(RuntimeError):
    """A Groq call failed after retrying."""


def is_mock() -> bool:
    return get_settings().groq_mock_mode


def _data_url(image_bytes: bytes, mime: str) -> str:
    b64 = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _pick(data: dict, *keys: str) -> str:
    for k in keys:
        v = data.get(k)
        if v:
            return str(v).strip()
    return ""


def parse_fields(text: str) -> dict:
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t[:4].lower() == "json":
            t = t[4:]
        t = t.strip()
    # slice to the outermost { ... } in case the model added stray text
    start, end = t.find("{"), t.rfind("}")
    if start != -1 and end != -1 and end > start:
        t = t[start : end + 1]

    data = json.loads(t)
    if not isinstance(data, dict):
        raise ValueError("model did not return a JSON object")

    return {
        "name": _pick(data, "name", "full_name", "fullName"),
        "company": _pick(
            data, "company", "company_name", "companyName", "organisation", "organization"
        ),
        "title": _pick(
            data, "title", "designation", "job_title", "jobTitle", "position"
        ),
        "email": _pick(data, "email", "mail_address", "mailAddress", "mail", "email_address"),
        "phone": _pick(
            data, "phone", "phone_number", "phoneNumber", "mobile", "contact", "tel"
        ),
    }


def extract_card(image_bytes: bytes, mime: str = "image/jpeg") -> dict:
    """Return {name, company, title, email, phone} (values may be "")."""
    settings = get_settings()

    if settings.groq_mock_mode:
        log.warning("GROQ_API_KEY not set — returning MOCK extraction")
        return dict(MOCK_FIELDS)

    from groq import Groq

    client = Groq(api_key=settings.groq_api_key, timeout=float(settings.groq_timeout_s))
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url", "image_url": {"url": _data_url(image_bytes, mime)}},
            ],
        }
    ]

    last_err: Exception | None = None
    for attempt in (1, 2):
        try:
            resp = client.chat.completions.create(
                model=settings.groq_model,
                messages=messages,
                temperature=0.2,
                max_completion_tokens=1024,
                stream=False,
            )
            content = resp.choices[0].message.content or ""
            return parse_fields(content)
        except Exception as exc:  # noqa: BLE001 — retry once, then surface
            last_err = exc
            log.warning("groq attempt %s failed: %s", attempt, exc)
            if attempt == 1:
                time.sleep(1.0)

    raise GroqError(str(last_err))
