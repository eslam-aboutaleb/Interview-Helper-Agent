"""Service for recording user interaction history with questions."""

import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from models import QuestionHistory

logger = logging.getLogger(__name__)

VALID_ACTIONS = {"generated", "viewed", "rated", "flagged", "created", "deleted"}


def record_action(
    db: Session,
    action: str,
    user_id: Optional[int] = None,
    question_id: Optional[int] = None,
    context: Optional[dict[str, Any]] = None,
) -> Optional[QuestionHistory]:
    """Record a user action in the question history.

    History recording is best-effort: failures are logged but never
    interrupt the primary workflow.

    Args:
        db: Database session.
        action: One of VALID_ACTIONS.
        user_id: ID of the acting user, if authenticated.
        question_id: ID of the related question, if any.
        metadata: Optional JSON-serializable context.

    Returns:
        The created QuestionHistory row, or None on failure.
    """
    if action not in VALID_ACTIONS:
        logger.warning("Ignoring invalid history action: %s", action)
        return None

    try:
        entry = QuestionHistory(
            user_id=user_id,
            question_id=question_id,
            action=action,
            context=context,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("Failed to record history action %s: %s", action, e)
        db.rollback()
        return None


def get_user_history(
    db: Session,
    user_id: int,
    limit: int = 100,
    action: Optional[str] = None,
) -> list[QuestionHistory]:
    """Retrieve recent history entries for a user."""
    query = db.query(QuestionHistory).filter(QuestionHistory.user_id == user_id)
    if action:
        query = query.filter(QuestionHistory.action == action)
    return query.order_by(QuestionHistory.created_at.desc()).limit(limit).all()
