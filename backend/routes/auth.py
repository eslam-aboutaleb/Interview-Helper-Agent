"""Authentication and user-management API routes."""

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models import User
from schemas import (
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse,
    QuestionHistoryResponse,
)
from services import auth_service
from services.history_service import get_user_history

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: UserCreate, db: Session = Depends(get_db)):
    """Register a new user and return an auth token."""
    try:
        user = auth_service.create_user(
            db,
            email=request.email,
            password=request.password,
            full_name=request.full_name,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    token = auth_service.create_session(db, user.id)
    return TokenResponse(token=token, user=UserResponse.model_validate(user))


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(request: UserLogin, db: Session = Depends(get_db)):
    """Authenticate a user and return an auth token."""
    user = auth_service.authenticate_user(db, request.email, request.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token = auth_service.create_session(db, user.id)
    return TokenResponse(token=token, user=UserResponse.model_validate(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    authorization: Optional[str] = Header(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke the current session token."""
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()
        auth_service.revoke_session(db, token)
    return None


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_me(user: User = Depends(get_current_user)):
    """Get the current authenticated user."""
    return UserResponse.model_validate(user)


@router.get("/history", response_model=list[QuestionHistoryResponse], status_code=status.HTTP_200_OK)
async def get_history(
    limit: int = Query(100, ge=1, le=1000),
    action: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the authenticated user's question interaction history."""
    return get_user_history(db, user_id=user.id, limit=limit, action=action)
