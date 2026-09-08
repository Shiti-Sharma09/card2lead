"""Append one reviewed lead per row into a single master .xlsx file.

All writes are serialised through a process-wide lock: routes run in Starlette's
threadpool, so without this two concurrent saves race on the file and one reads
a half-written workbook (BadZipFile). This makes concurrent captures safe for a
single-process server (how the app is run). A multi-worker / multi-machine
deployment would additionally need a cross-process file lock.
"""

from __future__ import annotations

import logging
import re
import threading
from datetime import datetime
from pathlib import Path
from zipfile import BadZipFile

from openpyxl import Workbook, load_workbook
from openpyxl.utils.exceptions import InvalidFileException
from openpyxl.worksheet.worksheet import Worksheet

log = logging.getLogger("card2lead.excel")

_WRITE_LOCK = threading.Lock()

HEADERS = [
    "Name",
    "Company",
    "Title",
    "Email",
    "Phone Number",
    "Notes",
    "Assigned To",
    "Timestamp",
]

_COLUMN_WIDTHS = [22, 26, 22, 30, 22, 44, 14, 20]

# Characters openpyxl refuses to write.
_ILLEGAL_XLSX_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
# Excel treats a leading one of these as the start of a formula.
_FORMULA_LEAD = ("=", "+", "-", "@", "\t", "\r")
_MAX_CELL_LEN = 32_767


def _safe_cell(value: object) -> str:
    """Make a value safe to write into an .xlsx cell.

    - strips control characters openpyxl rejects
    - caps length at Excel's per-cell limit
    - neutralises spreadsheet formula injection by prefixing a quote, which
      Excel renders invisibly and also stops "+91 ..." being evaluated
    """
    text = "" if value is None else str(value)
    text = _ILLEGAL_XLSX_CHARS.sub("", text)
    if len(text) > _MAX_CELL_LEN:
        text = text[: _MAX_CELL_LEN - 1] + "…"
    if text[:1] in _FORMULA_LEAD:
        text = "'" + text
    return text


def _fresh_workbook(path: Path) -> tuple[Workbook, Worksheet]:
    wb = Workbook()
    ws = wb.active
    ws.title = "Leads"
    ws.append(HEADERS)
    for idx, width in enumerate(_COLUMN_WIDTHS, start=1):
        ws.column_dimensions[chr(64 + idx)].width = width
    ws.freeze_panes = "A2"
    return wb, ws


def _load_or_create(path: Path) -> tuple[Workbook, Worksheet]:
    path.parent.mkdir(parents=True, exist_ok=True)

    if not (path.exists() and path.stat().st_size > 0):
        return _fresh_workbook(path)

    try:
        wb = load_workbook(path)
    except (BadZipFile, InvalidFileException, KeyError) as exc:
        # Genuinely corrupt file (killed mid-save, disk issue, ...). Quarantine
        # it so new captures aren't blocked, and start a clean sheet.
        quarantine = path.with_name(
            f"{path.stem}.corrupt-{datetime.now():%Y%m%d-%H%M%S}{path.suffix}"
        )
        path.rename(quarantine)
        log.error(
            "master workbook unreadable (%s); moved to %s and started a fresh file",
            exc,
            quarantine.name,
        )
        return _fresh_workbook(path)

    ws = wb.active
    first_row = [cell.value for cell in ws[1]] if ws.max_row >= 1 else []
    if first_row[: len(HEADERS)] != HEADERS and ws.max_row <= 1 and not any(first_row):
        if ws.max_row >= 1:
            ws.delete_rows(1, 1)
        ws.insert_rows(1)
        for idx, header in enumerate(HEADERS, start=1):
            ws.cell(row=1, column=idx, value=header)
    return wb, ws


def append_lead(path: Path, lead: dict) -> int:
    """Append the lead. Raises PermissionError if the file is open in Excel."""
    row = [
        _safe_cell(lead.get("name")),
        _safe_cell(lead.get("company")),
        _safe_cell(lead.get("title")),
        _safe_cell(lead.get("email")),
        _safe_cell(lead.get("phone")),
        _safe_cell(lead.get("notes")),
        _safe_cell(lead.get("assignedTo")),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ]
    with _WRITE_LOCK:
        wb, ws = _load_or_create(path)
        ws.append(row)
        wb.save(path)  # PermissionError bubbles up to the route
        return ws.max_row
