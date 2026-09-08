"""Password hashing (bcrypt) and JWT access tokens."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import get_settings

_ALGO = "HS256"
_BCRYPT_MAX_BYTES = 72  # bcrypt only uses the first 72 bytes


def _prep(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prep(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_prep(password), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: int, issued_at: datetime | None = None) -> str:
    settings = get_settings()
    now = issued_at or datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=settings.jwt_expires_days)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGO)


def decode_access_token(token: str) -> dict:
    """Raises jwt.PyJWTError on any problem (expired, bad signature, malformed)."""
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[_ALGO])
