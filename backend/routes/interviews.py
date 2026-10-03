"""Mock interview session routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models import User
from schemas import (
    InterviewSessionCreate,
    InterviewSessionResponse,
    InterviewAnswerRequest,
    InterviewTurnResponse,
    InterviewMessageResponse,
    AnswerEvaluationResponse,
    ModelAnswerRequest,
    ModelAnswerResponse,
)
from services.interview_service import InterviewService, InterviewServiceError
from services.gemini_service import GeminiService
from services.evaluation_service import EvaluationService

router = APIRouter()

# Lazily-initialized services so a missing API key does not crash imports.
_gemini_service = None
_interview_service: Optional[InterviewService] = None


def _get_interview_service() -> InterviewService:
    global _gemini_service, _interview_service
    if _interview_service is None:
        try:
            _gemini_service = GeminiService()
        except Exception:
            _gemini_service = None  # heuristic fallback
        _interview_service = InterviewService(
            gemini_service=_gemini_service,
            evaluation_service=EvaluationService(_gemini_service),
        )
    return _interview_service


@router.post("/sessions", response_model=InterviewSessionResponse, status_code=status.HTTP_201_CREATED)
async def start_interview(
    request: InterviewSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start a new mock interview session."""
    service = _get_interview_service()
    session = service.start_session(
        db,
        user_id=current_user.id,
        job_title=request.job_title,
        session_type=request.session_type,
        difficulty=request.difficulty,
        max_turns=request.max_turns,
        document_id=request.document_id,
    )
    return InterviewSessionResponse.model_validate(session)


@router.get("/sessions", response_model=list[InterviewSessionResponse], status_code=status.HTTP_200_OK)
async def list_interviews(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List the current user's interview sessions."""
    service = _get_interview_service()
    return [InterviewSessionResponse.model_validate(s) for s in service.list_sessions(db, current_user.id, limit=limit)]


@router.get("/sessions/{session_id}", response_model=InterviewSessionResponse, status_code=status.HTTP_200_OK)
async def get_interview(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single interview session."""
    service = _get_interview_service()
    session = service.get_session(db, session_id, current_user.id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return InterviewSessionResponse.model_validate(session)


@router.get(
    "/sessions/{session_id}/messages", response_model=list[InterviewMessageResponse], status_code=status.HTTP_200_OK
)
async def get_interview_messages(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the full transcript of an interview session."""
    service = _get_interview_service()
    session = service.get_session(db, session_id, current_user.id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return [InterviewMessageResponse.model_validate(m) for m in session.messages]


@router.get(
    "/sessions/{session_id}/evaluations", response_model=list[AnswerEvaluationResponse], status_code=status.HTTP_200_OK
)
async def get_interview_evaluations(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all evaluations for an interview session."""
    service = _get_interview_service()
    session = service.get_session(db, session_id, current_user.id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return [AnswerEvaluationResponse.model_validate(e) for e in session.evaluations]


@router.post("/sessions/{session_id}/answer", response_model=InterviewTurnResponse, status_code=status.HTTP_200_OK)
async def submit_answer(
    session_id: int,
    request: InterviewAnswerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit an answer, receive scoring, and get the next question."""
    service = _get_interview_service()
    try:
        result = service.submit_answer(db, session_id, current_user.id, request.answer)
    except InterviewServiceError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return InterviewTurnResponse(**result)


@router.post("/model-answer", response_model=ModelAnswerResponse, status_code=status.HTTP_200_OK)
async def get_model_answer(
    request: ModelAnswerRequest,
    current_user: User = Depends(get_current_user),
):
    """Generate a model answer for a question."""
    service = _get_interview_service()
    model_answer = service.evaluation_service.generate_model_answer(
        question=request.question,
        question_type=request.question_type,
    )
    return ModelAnswerResponse(question=request.question, model_answer=model_answer)
