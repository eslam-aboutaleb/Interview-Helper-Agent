"""Shared FastAPI dependencies."""

from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import User
from services import auth_service


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the current user from the Authorization header.

    Expects a header of the form ``Authorization: Bearer <token>``.
    Raises 401 when the header is missing or the token is invalid.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
        )
    token = authorization.split(" ", 1)[1].strip()
    user = auth_service.get_user_from_token(db, token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token",
        )
    return user


async def get_optional_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Resolve the current user when a valid token is present.

    Returns None when no token is provided, so endpoints remain
    usable both anonymously and authenticated.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    return auth_service.get_user_from_token(db, token)


async def get_current_admin_user(
    user: User = Depends(get_current_user),
) -> User:
    """Resolve the current user and require the admin role.

    Raises 403 when the authenticated user is not an admin.
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return user
