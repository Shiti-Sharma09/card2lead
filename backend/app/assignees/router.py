"""/assignees routes — the "Assigned To" dropdown list."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlmodel import Session

from app.assignees.schemas import AssigneeCreate, AssigneeOut
from app.assignees.service import (
    AssigneeExistsError,
    AssigneeNotFoundError,
    add_assignee,
    list_assignees,
    remove_assignee,
)
from app.auth.deps import get_current_user, require_admin
from app.db.base import get_session
from app.db.models import User

router = APIRouter()


@router.get("", response_model=list[AssigneeOut])
def list_(
    include_all: bool = Query(False, alias="all"),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[AssigneeOut]:
    if include_all and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    rows = list_assignees(session, include_inactive=include_all)
    return [AssigneeOut(id=a.id, name=a.name, is_active=a.is_active) for a in rows]


@router.post("", response_model=AssigneeOut, status_code=status.HTTP_201_CREATED)
def add(
    body: AssigneeCreate,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
) -> AssigneeOut:
    try:
        a = add_assignee(session, body.name, admin.email)
    except AssigneeExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="That name is already in the list."
        )
    return AssigneeOut(id=a.id, name=a.name, is_active=a.is_active)


@router.delete("/{assignee_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove(
    assignee_id: int,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
) -> Response:
    try:
        remove_assignee(session, assignee_id, admin.email)
    except AssigneeNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Name not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
