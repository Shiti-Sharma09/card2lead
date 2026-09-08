"""/auth routes: register, login, me, forgot/reset (stubbed until SMTP)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.auth.deps import get_current_user
from app.auth.schemas import (
    ForgotPasswordIn,
    LoginIn,
    MessageOut,
    RegisterIn,
    ResetPasswordIn,
    TokenOut,
    UserOut,
)
from app.auth.service import (
    EmailTakenError,
    InactiveUserError,
    InvalidCredentialsError,
    authenticate,
    register_user,
)
from app.core.rate_limit import rate_limit
from app.core.security import create_access_token
from app.db.base import get_session
from app.db.models import User

router = APIRouter()


@router.post("/register", response_model=TokenOut, dependencies=[rate_limit("register", 3)])
def register(body: RegisterIn, session: Session = Depends(get_session)) -> TokenOut:
    try:
        user = register_user(session, body.email, body.password)
    except EmailTakenError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )
    return TokenOut(access_token=create_access_token(user.id))


@router.post("/login", response_model=TokenOut, dependencies=[rate_limit("login", 5)])
def login(body: LoginIn, session: Session = Depends(get_session)) -> TokenOut:
    try:
        user = authenticate(session, body.email, body.password)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    except InactiveUserError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="This account is disabled."
        )
    return TokenOut(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut(id=user.id, email=user.email, role=user.role, is_active=user.is_active)


# --- forgot / reset password -------------------------------------------------
# Stubbed until SMTP credentials are configured (see plan.md §8). Returns a
# generic message and never reveals whether the email exists.
_EMAIL_STUB = MessageOut(
    status="email_not_configured",
    message="Password reset by email is not available yet. Ask an admin.",
)


@router.post(
    "/forgot-password", response_model=MessageOut, dependencies=[rate_limit("forgot", 3)]
)
def forgot_password(body: ForgotPasswordIn) -> MessageOut:
    return _EMAIL_STUB


@router.post(
    "/reset-password", response_model=MessageOut, dependencies=[rate_limit("reset", 3)]
)
def reset_password(body: ResetPasswordIn) -> MessageOut:
    return _EMAIL_STUB
