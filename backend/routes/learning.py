"""Learning plan routes (plan 08)."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models import User
from schemas import LearningPlanResponse
from services.learning_plan import generate_learning_plan
from services.llm_service import LLMService

logger = logging.getLogger(__name__)

router = APIRouter()

# Lazy singleton for the LLM service so a missing or unconfigured API key does
# not crash the application at import time. ``None`` means "no key configured",
# which makes the service answer with the deterministic heuristic plan.
_llm_service: Optional[LLMService] = None


def get_llm_service() -> Optional[LLMService]:
    """Dependency that returns a configured LLM service, or None.

    Returning ``None`` (instead of raising) is what selects the heuristic
    fallback inside the learning-plan service.
    """
    global _llm_service
    if _llm_service is None:
        service = LLMService()
        if not service.is_configured():
            return None
        _llm_service = service
    return _llm_service


def _build_plan(db: Session, user: User, llm_service: Optional[LLMService]) -> LearningPlanResponse:
    """Generate the plan and wrap failures in a 500."""
    try:
        return LearningPlanResponse.model_validate(generate_learning_plan(db, user.id, llm_service=llm_service))
    except Exception:
        logger.exception("Failed to generate learning plan")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/plan", response_model=LearningPlanResponse, status_code=status.HTTP_200_OK)
async def get_learning_plan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    llm_service: Optional[LLMService] = Depends(get_llm_service),
):
    """Get the current user's learning plan

    Builds the plan from the latest resume-vs-job-description skill gap and
    the user's weakest evaluated question types. Uses the LLM when one is
    configured and a deterministic heuristic plan otherwise.

    Args:
        db: Database session dependency
        current_user: Authenticated user
        llm_service: Configured LLM service, or None when no key is set

    Returns:
        LearningPlanResponse with the ordered study items

    Raises:
        HTTPException 401: If the request is not authenticated
        HTTPException 500: If the plan cannot be generated
    """
    return _build_plan(db, current_user, llm_service)


@router.post("/plan", response_model=LearningPlanResponse, status_code=status.HTTP_200_OK)
async def regenerate_learning_plan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    llm_service: Optional[LLMService] = Depends(get_llm_service),
):
    """Force-regenerate the current user's learning plan

    Recomputes the plan from the current documents, evaluations and question
    library, discarding any previously generated plan. Used by the
    "Regenerate" button on the learning-plan page.

    Args:
        db: Database session dependency
        current_user: Authenticated user
        llm_service: Configured LLM service, or None when no key is set

    Returns:
        A freshly generated LearningPlanResponse

    Raises:
        HTTPException 401: If the request is not authenticated
        HTTPException 500: If the plan cannot be generated
    """
    return _build_plan(db, current_user, llm_service)
