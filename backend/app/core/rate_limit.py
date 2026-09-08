"""Tiny in-memory rate limiter used as a FastAPI dependency.

Fixed-window per (route-name, client-IP). Fine for a single instance and
10-30 users. Disabled automatically when APP_ENV=test.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, Request, status

from app.core.config import get_settings

_WINDOW_SECONDS = 60
_hits: dict[str, deque[float]] = defaultdict(deque)


def rate_limit(name: str, limit: int):
    """Return a dependency that allows `limit` requests per minute per IP."""

    def _dep(request: Request) -> None:
        if get_settings().is_test:
            return
        ip = request.client.host if request.client else "unknown"
        key = f"{name}:{ip}"
        now = time.monotonic()
        bucket = _hits[key]
        cutoff = now - _WINDOW_SECONDS
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please wait a minute and try again.",
            )
        bucket.append(now)

    return Depends(_dep)
