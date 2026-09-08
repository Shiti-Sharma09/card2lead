"""Process-wide guard so we stay under Groq's free-tier ceilings
(~25 requests/minute, ~1,000/day by default; both from .env).

Single instance only — that's the whole deployment model.
"""

from __future__ import annotations

import threading
import time
from collections import deque

from app.core.config import get_settings

_lock = threading.Lock()
_minute: deque[float] = deque()
_day: deque[float] = deque()


class QuotaExceeded(Exception):
    def __init__(self, scope: str) -> None:  # "minute" | "day"
        super().__init__(scope)
        self.scope = scope


def check_and_consume() -> None:
    settings = get_settings()
    now = time.time()
    with _lock:
        while _minute and _minute[0] <= now - 60:
            _minute.popleft()
        while _day and _day[0] <= now - 86_400:
            _day.popleft()

        if len(_day) >= settings.groq_max_per_day:
            raise QuotaExceeded("day")
        if len(_minute) >= settings.groq_max_per_min:
            raise QuotaExceeded("minute")

        _minute.append(now)
        _day.append(now)


def _reset() -> None:  # tests only
    with _lock:
        _minute.clear()
        _day.clear()
