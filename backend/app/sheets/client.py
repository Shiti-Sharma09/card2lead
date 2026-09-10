"""Google Sheets access.

One spreadsheet (GOOGLE_SHEET_ID), one tab per event. This module only knows
how to add a tab with the header row; row appends come in Phase 5.

If GOOGLE_SHEET_ID is blank the whole module is a no-op (`is_configured()`
returns False) so the app still runs without Google configured.
"""

from __future__ import annotations

import logging
import re
from functools import lru_cache

from app.core.config import get_settings

log = logging.getLogger("sheets")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

HEADER_ROW = [
    "Timestamp",
    "User Email",
    "Event",
    "Name",
    "Company",
    "Title",
    "Email",
    "Phone",
    "Notes",
    "Assigned To",
]

# Characters Google forbids in a tab title
_FORBIDDEN = re.compile(r"[\[\]\:\*\?\/\\]")
_MAX_TAB_LEN = 95  # leave headroom for a " (2)" suffix


class SheetsError(RuntimeError):
    """A Google Sheets call failed."""


def is_configured() -> bool:
    return get_settings().sheets_configured


@lru_cache(maxsize=1)
def _service():
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    settings = get_settings()
    creds = Credentials.from_service_account_file(
        settings.google_service_account_file, scopes=SCOPES
    )
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def sanitize_tab_name(name: str) -> str:
    cleaned = _FORBIDDEN.sub(" ", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:_MAX_TAB_LEN] or "Event"


def _existing_titles(svc, sheet_id: str) -> set[str]:
    meta = svc.spreadsheets().get(spreadsheetId=sheet_id).execute()
    return {s["properties"]["title"] for s in meta.get("sheets", [])}


def create_event_tab(desired_name: str) -> tuple[int, str]:
    """Create a new tab, write the header row, return (tab_id, tab_name).

    The final tab name may differ from `desired_name` (sanitised / de-duplicated).
    Raises SheetsError on any Google failure — the caller should NOT create the
    event if this fails.
    """
    settings = get_settings()
    sheet_id = settings.google_sheet_id
    try:
        svc = _service()
        titles = _existing_titles(svc, sheet_id)

        base = sanitize_tab_name(desired_name)
        name = base
        n = 2
        while name in titles:
            name = f"{base} ({n})"
            n += 1

        resp = (
            svc.spreadsheets()
            .batchUpdate(
                spreadsheetId=sheet_id,
                body={"requests": [{"addSheet": {"properties": {"title": name}}}]},
            )
            .execute()
        )
        tab_id = resp["replies"][0]["addSheet"]["properties"]["sheetId"]

        svc.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"'{name}'!A1",
            valueInputOption="RAW",
            body={"values": [HEADER_ROW]},
        ).execute()

        log.info("created sheet tab %r (id=%s)", name, tab_id)
        return int(tab_id), name
    except Exception as exc:  # noqa: BLE001 — surface as one error type
        log.exception("failed to create sheet tab for %r", desired_name)
        raise SheetsError(str(exc)) from exc
