"""User creation, authentication, and the first-boot admin seed."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.logging import log_event
from app.core.security import hash_password, verify_password
from app.db.base import engine
from app.db.models import User


class EmailTakenError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class InactiveUserError(Exception):
    pass


def get_user_by_email(session: Session, email: str) -> User | None:
    return session.exec(select(User).where(User.email == email.lower())).first()


def register_user(session: Session, email: str, password: str) -> User:
    email = email.lower()
    if get_user_by_email(session, email) is not None:
        raise EmailTakenError()
    user = User(email=email, password_hash=hash_password(password), role="user")
    session.add(user)
    session.commit()
    session.refresh(user)
    log_event("USER_REGISTERED", session=session, actor=email, user_id=user.id)
    return user


def authenticate(session: Session, email: str, password: str) -> User:
    user = get_user_by_email(session, email)
    if user is None or not verify_password(password, user.password_hash):
        log_event("LOGIN_FAILED", session=session, actor=email.lower())
        raise InvalidCredentialsError()
    if not user.is_active:
        log_event("LOGIN_FAILED", session=session, actor=email.lower(), reason="inactive")
        raise InactiveUserError()
    log_event("USER_LOGIN", session=session, actor=user.email, user_id=user.id)
    return user


def seed_admin() -> None:
    """Create the admin on first boot; keep its password in sync with the env
    afterwards (so ADMIN_PASSWORD is also the recovery mechanism)."""
    settings = get_settings()
    if not settings.admin_email or not settings.admin_password:
        log_event("ADMIN_SEED_SKIPPED", reason="ADMIN_EMAIL or ADMIN_PASSWORD blank")
        return

    email = settings.admin_email.lower()
    with Session(engine) as session:
        user = get_user_by_email(session, email)
        if user is None:
            session.add(
                User(
                    email=email,
                    password_hash=hash_password(settings.admin_password),
                    role="admin",
                )
            )
            session.commit()
            log_event("ADMIN_SEEDED", session=session, actor=email)
            return

        changed = False
        if user.role != "admin":
            user.role = "admin"
            changed = True
        if not user.is_active:
            user.is_active = True
            changed = True
        if not verify_password(settings.admin_password, user.password_hash):
            user.password_hash = hash_password(settings.admin_password)
            user.password_changed_at = datetime.now(timezone.utc)
            changed = True
        if changed:
            session.add(user)
            session.commit()
            log_event("ADMIN_SYNCED", session=session, actor=email)
