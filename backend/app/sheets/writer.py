"""Append one lead row to an event's tab.

- All appends are serialised through a process-wide lock (single instance).
- Up to 3 attempts with exponential backoff on any Google failure.
- Values are written RAW, so a card value like "=cmd()" can never become a
  live formula.
- Raises SheetsError if every attempt fails — the caller must NOT report
  success.
"""

from __future__ import annotations

import logging
import threading
import time

from app.core.config import get_settings
from app.sheets.client import SheetsError, _service

log = logging.getLogger("sheets")

_write_lock = threading.Lock()
_MAX_ATTEMPTS = 3


def append_row(tab_name: str, row: list[str]) -> None:
    settings = get_settings()
    sheet_id = settings.google_sheet_id
    delay = 1.0
    last_err: Exception | None = None

    with _write_lock:
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                svc = _service()
                svc.spreadsheets().values().append(
                    spreadsheetId=sheet_id,
                    range=f"'{tab_name}'!A1",
                    valueInputOption="RAW",
                    insertDataOption="INSERT_ROWS",
                    body={"values": [row]},
                ).execute()
                return
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                log.warning(
                    "append attempt %s/%s to %r failed: %s",
                    attempt,
                    _MAX_ATTEMPTS,
                    tab_name,
                    exc,
                )
                if attempt < _MAX_ATTEMPTS:
                    time.sleep(delay)
                    delay *= 2

    raise SheetsError(str(last_err))
