"""Application + audit logging.

- Human-readable structured lines go to stdout AND a rotating file (logs/app.log).
- `log_event(...)` records an important action to the log and, when a DB session
  is passed, also writes a row to the `audit_log` table.
- Never pass secrets (passwords, tokens, keys) into the detail fields.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

_CONFIGURED = False


def setup_logging(level: str = "INFO") -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    Path("logs").mkdir(exist_ok=True)

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-7s %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    stream = logging.StreamHandler()
    stream.setFormatter(fmt)

    rotating = RotatingFileHandler(
        "logs/app.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    rotating.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(stream)
    root.addHandler(rotating)

    # uvicorn brings its own handlers; let them propagate to ours instead
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.propagate = True

    _CONFIGURED = True


_audit = logging.getLogger("audit")


def log_event(
    action: str,
    *,
    session: Any | None = None,
    actor: str | None = None,
    ip: str | None = None,
    **detail: Any,
) -> None:
    """Record an important action. `action` is an UPPER_SNAKE verb-ish label."""
    safe_detail = json.dumps(detail, default=str, ensure_ascii=False) if detail else "{}"
    _audit.info("%s actor=%s ip=%s %s", action, actor or "-", ip or "-", safe_detail)

    if session is not None:
        # local import to avoid a circular import at module load
        from app.db.models import AuditLog

        session.add(
            AuditLog(
                ts=datetime.now(timezone.utc),
                actor_email=actor,
                action=action,
                ip=ip,
                detail=safe_detail,
            )
        )
        session.commit()
