"""Admin-only platform management routes.

Every endpoint in this router requires the admin role.
Admins manage users, moderate the question bank, and
inspect platform-wide activity and audit history.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_admin_user
from models import (
    User,
    Question,
    QuestionHistory,
    UserDocument,
    InterviewSession,
    AnswerEvaluation,
)
from schemas import (
    AdminUserUpdate,
    AdminStatsResponse,
    Question as QuestionSchema,
    QuestionHistoryResponse,
    UserResponse,
)
from services import auth_service

router = APIRouter()


@router.get("/users", response_model=list[UserResponse], status_code=status.HTTP_200_OK)
async def list_users(
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=1000, description="Pagination limit"),
    role: Optional[str] = Query(None, description="Filter by role: 'user' or 'admin'"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """List all users with optional role filtering."""
    query = db.query(User)
    if role:
        if role not in {"user", "admin"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="role must be 'user' or 'admin'",
            )
        query = query.filter(User.role == role)
    return query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()


@router.patch("/users/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def update_user(
    user_id: int,
    request: AdminUserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Update a user's role or active status.

    Admins cannot demote or deactivate themselves, which
    would lock the platform into having no admin.
    """
    if user_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id must be a positive integer",
        )

    target = db.query(User).filter(User.id == user_id).first()
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )

    update_data = request.model_dump(exclude_unset=True)

    if "role" in update_data and update_data["role"] is not None:
        if target.id == current_user.id and update_data["role"] != "admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admins cannot remove their own admin role",
            )
        try:
            auth_service.set_user_role(db, target.id, update_data["role"])
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if "is_active" in update_data and update_data["is_active"] is not None:
        if target.id == current_user.id and not update_data["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admins cannot deactivate their own account",
            )
        auth_service.set_user_active(db, target.id, update_data["is_active"])

    db.refresh(target)
    return target


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Permanently delete a user account."""
    if user_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id must be a positive integer",
        )
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admins cannot delete their own account",
        )
    if not auth_service.delete_user(db, user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )
    return None


@router.get("/stats", response_model=AdminStatsResponse, status_code=status.HTTP_200_OK)
async def get_platform_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Platform-wide usage overview for the admin dashboard."""
    total_users = db.query(func.count(User.id)).scalar() or 0
    active_users = db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar() or 0
    admin_count = db.query(func.count(User.id)).filter(User.role == "admin").scalar() or 0
    recent_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    recent_users = db.query(func.count(User.id)).filter(User.created_at >= recent_cutoff).scalar() or 0

    total_questions = db.query(func.count(Question.id)).scalar() or 0
    flagged_questions = db.query(func.count(Question.id)).filter(Question.is_flagged.is_(True)).scalar() or 0
    total_documents = db.query(func.count(UserDocument.id)).scalar() or 0
    total_sessions = db.query(func.count(InterviewSession.id)).scalar() or 0
    completed_sessions = (
        db.query(func.count(InterviewSession.id)).filter(InterviewSession.status == "completed").scalar() or 0
    )
    total_evaluations = db.query(func.count(AnswerEvaluation.id)).scalar() or 0
    average_score = db.query(func.avg(AnswerEvaluation.overall_score)).scalar()

    return AdminStatsResponse(
        total_users=total_users,
        active_users=active_users,
        admin_count=admin_count,
        total_questions=total_questions,
        flagged_questions=flagged_questions,
        total_documents=total_documents,
        total_interview_sessions=total_sessions,
        completed_sessions=completed_sessions,
        total_evaluations=total_evaluations,
        average_score=round(float(average_score), 1) if average_score is not None else None,
        recent_users=recent_users,
    )


@router.get("/history", response_model=list[QuestionHistoryResponse], status_code=status.HTTP_200_OK)
async def get_audit_history(
    limit: int = Query(100, ge=1, le=1000, description="Maximum entries to return"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Platform-wide audit log of user actions."""
    query = db.query(QuestionHistory)
    if action:
        query = query.filter(QuestionHistory.action == action)
    if user_id is not None:
        query = query.filter(QuestionHistory.user_id == user_id)
    return query.order_by(QuestionHistory.created_at.desc()).limit(limit).all()


@router.get("/questions/flagged", response_model=list[QuestionSchema], status_code=status.HTTP_200_OK)
async def get_flagged_questions(
    limit: int = Query(100, ge=1, le=1000, description="Maximum questions to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Questions flagged for moderation review."""
    return (
        db.query(Question).filter(Question.is_flagged.is_(True)).order_by(Question.created_at.desc()).limit(limit).all()
    )


@router.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_any_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Delete any question (moderation override)."""
    if question_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="question_id must be a positive integer",
        )
    question = db.query(Question).filter(Question.id == question_id).first()
    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question with ID {question_id} not found",
        )
    db.delete(question)
    db.commit()
    return None
