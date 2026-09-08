"""FastAPI dependencies: current user, admin gate."""

from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.core.security import decode_access_token
from app.db.base import get_session
from app.db.models import User

_bearer = HTTPBearer(auto_error=False)

_UNAUTH = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: Session = Depends(get_session),
) -> User:
    if creds is None or not creds.credentials:
        raise _UNAUTH
    try:
        payload = decode_access_token(creds.credentials)
        user_id = int(payload["sub"])
        issued_at = int(payload["iat"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise _UNAUTH

    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise _UNAUTH

    # a token minted before the last password change is no longer valid
    if int(user.password_changed_at.timestamp()) > issued_at:
        raise _UNAUTH

    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return user
