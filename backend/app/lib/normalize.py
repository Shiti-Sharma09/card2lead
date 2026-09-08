"""Text tidy-up: collapse whitespace, normalize emails, force phones to +91."""

from __future__ import annotations

import re

# Split on explicit separators plus "|" and runs of 2+ spaces (cards often
# separate two numbers with "  |  " or wide gaps).
_SPLIT_RE = re.compile(r"[,;/|\n]+|\s{2,}")


def clean_text(raw: str) -> str:
    if not raw:
        return ""
    return re.sub(r"\s+", " ", raw).strip()


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def normalize_email(raw: str) -> str:
    if not raw:
        return ""
    parts = [p.strip().lower() for p in _SPLIT_RE.split(raw) if p.strip()]
    return ", ".join(_dedupe(parts))


def _strip_prefix(digits: str) -> str:
    """Remove a leading 0091 / 91 / 0 trunk or country code from one number."""
    if digits.startswith("0091"):
        return digits[4:]
    if digits.startswith("91") and len(digits) > 10:
        return digits[2:]
    if digits.startswith("0") and len(digits) == 11:
        return digits[1:]
    return digits


def _split_concatenated(digits: str) -> list[str] | None:
    """Try to break a run of digits into clean 10-digit numbers.

    Handles the common case where the model glued two Indian numbers together,
    optionally with a stray "91" country code between them. Returns None when
    the run does not resolve cleanly, so the caller can fall back.
    """
    remaining = digits
    out: list[str] = []
    while len(remaining) >= 10:
        if (
            remaining.startswith("91")
            and (len(remaining) - 2) % 10 == 0
            and len(remaining) - 2 >= 10
        ):
            remaining = remaining[2:]
        out.append(remaining[:10])
        remaining = remaining[10:]
    if remaining:
        return None  # leftover digits -> not a clean split
    return out or None


def normalize_phone(raw: str) -> tuple[str, bool]:
    """Return (normalized, all_clean).

    Every number is rendered as "+91 XXXXX XXXXX". If a chunk does not resolve
    to a clean 10-digit number it is still prefixed with "+91 " (best effort)
    and all_clean is set to False so the caller can lower the confidence.
    """
    if not raw or not raw.strip():
        return "", True

    parts = [p for p in _SPLIT_RE.split(raw) if p.strip()]
    numbers: list[str] = []
    all_clean = True

    for part in parts:
        digits = _strip_prefix(re.sub(r"\D", "", part))
        if not digits:
            continue

        if len(digits) == 10:
            numbers.append(digits)
        elif len(digits) > 10:
            split = _split_concatenated(digits)
            if split:
                numbers.extend(split)
            else:
                all_clean = False
                numbers.append(digits)  # best effort, keep raw run
        else:
            all_clean = False
            numbers.append(digits)  # too short, keep as-is

    formatted = [
        f"+91 {n[:5]} {n[5:]}" if len(n) == 10 else f"+91 {n}".strip()
        for n in _dedupe(numbers)
    ]
    return ", ".join(formatted), all_clean
