"""Mock interview session engine with adaptive difficulty."""

import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from models import InterviewSession, InterviewMessage, AnswerEvaluation, Question
from services.evaluation_service import EvaluationService
from services.history_service import record_action

logger = logging.getLogger(__name__)

# Minimum rolling window of scores before difficulty is adjusted.
DIFFICULTY_WINDOW = 3
# Score thresholds that drive difficulty adaptation.
RAISE_THRESHOLD = 7.0
LOWER_THRESHOLD = 4.5


class InterviewServiceError(Exception):
    """Custom exception for interview service errors."""


class InterviewService:
    """Orchestrates a multi-turn mock interview with adaptive difficulty."""

    def __init__(self, gemini_service=None, evaluation_service: Optional[EvaluationService] = None):
        self.gemini_service = gemini_service
        self.evaluation_service = evaluation_service or EvaluationService(gemini_service)

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------
    def start_session(
        self,
        db: Session,
        user_id: int,
        job_title: str,
        session_type: str = "mixed",
        difficulty: int = 3,
        max_turns: int = 7,
        document_id: Optional[int] = None,
    ) -> InterviewSession:
        """Create a new interview session and ask the first question."""
        session = InterviewSession(
            user_id=user_id,
            job_title=job_title,
            session_type=session_type,
            difficulty=difficulty,
            target_difficulty=difficulty,
            max_turns=max(1, min(20, max_turns)),
            document_id=document_id,
            status="active",
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        first_question = self._next_question(db, session)
        self._add_message(db, session, "interviewer", first_question)
        record_action(
            db,
            action="viewed",
            user_id=user_id,
            context={"interview_session_id": session.id, "event": "session_started"},
        )
        # record_action only stages the history entry; persist it.
        db.commit()
        db.refresh(session)
        return session

    def submit_answer(
        self,
        db: Session,
        session_id: int,
        user_id: int,
        answer: str,
    ) -> dict[str, Any]:
        """Record a candidate answer, evaluate it, adapt difficulty,
        and return the next question (or a completion summary)."""
        session = (
            db.query(InterviewSession)
            .filter(InterviewSession.id == session_id, InterviewSession.user_id == user_id)
            .first()
        )
        if session is None:
            raise InterviewServiceError("Interview session not found")
        if session.status != "active":
            raise InterviewServiceError("Interview session is already completed")

        # Record the candidate's answer.
        self._add_message(db, session, "candidate", answer)

        # Evaluate the answer against the last interviewer question.
        last_question = self._last_interviewer_question(db, session)
        evaluation = self.evaluation_service.evaluate_answer(
            question=last_question,
            answer=answer,
            question_type=session.session_type if session.session_type != "mixed" else "technical",
        )

        # Persist the evaluation.
        eval_row = AnswerEvaluation(
            session_id=session.id,
            user_id=user_id,
            overall_score=evaluation["overall"],
            technical_score=evaluation["technical"],
            communication_score=evaluation["communication"],
            completeness_score=evaluation["completeness"],
            feedback={
                "strengths": evaluation["strengths"],
                "gaps": evaluation["gaps"],
                "tips": evaluation["tips"],
            },
            next_action=evaluation["next_action"],
        )
        db.add(eval_row)

        # Adapt difficulty based on a rolling window of recent scores.
        session.current_turn += 1
        self._adapt_difficulty(db, session)

        # Decide whether to continue or finish.
        if session.current_turn >= session.max_turns:
            session.status = "completed"
            session.completed_at = None  # set by server_default on update
            db.commit()
            summary = self._build_summary(db, session)
            record_action(
                db,
                action="viewed",
                user_id=user_id,
                context={"interview_session_id": session.id, "event": "session_completed"},
            )
            # record_action only stages the history entry; persist it.
            db.commit()
            return {"completed": True, "summary": summary, "evaluation": evaluation}

        next_question = self._next_question(db, session)
        self._add_message(db, session, "interviewer", next_question)
        db.commit()

        record_action(
            db,
            action="viewed",
            user_id=user_id,
            context={"interview_session_id": session.id, "event": "question_asked"},
        )
        # record_action only stages the history entry; persist it.
        db.commit()
        return {
            "completed": False,
            "next_question": next_question,
            "evaluation": evaluation,
            "current_difficulty": session.difficulty,
            "turn": session.current_turn,
        }

    def get_session(self, db: Session, session_id: int, user_id: int) -> Optional[InterviewSession]:
        """Return a session owned by ``user_id``, or ``None`` if it does not exist."""
        return (
            db.query(InterviewSession)
            .filter(InterviewSession.id == session_id, InterviewSession.user_id == user_id)
            .first()
        )

    def list_sessions(self, db: Session, user_id: int, limit: int = 50) -> list[InterviewSession]:
        """Return a user's sessions, most recent first."""
        return (
            db.query(InterviewSession)
            .filter(InterviewSession.user_id == user_id)
            .order_by(InterviewSession.created_at.desc())
            .limit(limit)
            .all()
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _next_question(self, db: Session, session: InterviewSession) -> str:
        """Generate the next question, preferring the LLM with a
        deterministic fallback drawn from the question bank."""
        if self.gemini_service is not None:
            try:
                prompt = (
                    f"You are conducting a {session.session_type} interview for a "
                    f"{session.job_title} role at difficulty level {session.difficulty}/5. "
                    f"This is question {session.current_turn + 1} of {session.max_turns}. "
                    "Ask ONE realistic interview question, appropriate to the difficulty, "
                    "and nothing else. Do not answer it."
                )
                response = self.gemini_service.generate_content(prompt)
                if response:
                    return response
            except Exception as e:
                logger.warning(f"LLM question generation failed: {e}")

        # Fallback: pull a relevant question from the bank.
        return self._fallback_question(db, session)

    @staticmethod
    def _fallback_question(db: Session, session: InterviewSession) -> str:
        query = db.query(Question).filter(Question.job_title.ilike(f"%{session.job_title}%"))
        if session.session_type != "mixed":
            query = query.filter(Question.question_type == session.session_type)
        question = query.order_by(Question.id.desc()).first()
        if question:
            return question.question_text
        return (
            f"Tell me about your experience as a {session.job_title} and the "
            "most challenging project you have worked on."
        )

    def _adapt_difficulty(self, db: Session, session: InterviewSession) -> None:
        """Adjust difficulty from the rolling mean of recent scores."""
        recent = (
            db.query(AnswerEvaluation.overall_score)
            .filter(AnswerEvaluation.session_id == session.id)
            .order_by(AnswerEvaluation.created_at.desc())
            .limit(DIFFICULTY_WINDOW)
            .all()
        )
        if not recent:
            return
        scores = [row[0] for row in recent]
        mean = sum(scores) / len(scores)

        if mean >= RAISE_THRESHOLD and session.difficulty < 5:
            session.difficulty += 1
        elif mean <= LOWER_THRESHOLD and session.difficulty > 1:
            session.difficulty -= 1

    @staticmethod
    def _add_message(db: Session, session: InterviewSession, role: str, content: str) -> InterviewMessage:
        message = InterviewMessage(session_id=session.id, role=role, content=content)
        db.add(message)
        db.commit()
        db.refresh(message)
        return message

    @staticmethod
    def _last_interviewer_question(db: Session, session: InterviewSession) -> str:
        message = (
            db.query(InterviewMessage)
            .filter(
                InterviewMessage.session_id == session.id,
                InterviewMessage.role == "interviewer",
            )
            .order_by(InterviewMessage.id.desc())
            .first()
        )
        return message.content if message else ""

    @staticmethod
    def _build_summary(db: Session, session: InterviewSession) -> dict[str, Any]:
        evaluations = (
            db.query(AnswerEvaluation)
            .filter(AnswerEvaluation.session_id == session.id)
            .order_by(AnswerEvaluation.id.asc())
            .all()
        )
        if not evaluations:
            return {"overall_average": 0.0, "turns": 0, "strengths": [], "gaps": []}

        scores = [e.overall_score for e in evaluations]
        avg = round(sum(scores) / len(scores), 1)

        all_gaps: list[str] = []
        all_strengths: list[str] = []
        for e in evaluations:
            feedback = e.feedback or {}
            all_gaps.extend(feedback.get("gaps", []))
            all_strengths.extend(feedback.get("strengths", []))

        # Deduplicate while preserving order.
        def dedupe(items: list[str]) -> list[str]:
            """Return ``items`` with duplicates removed, order preserved."""
            seen: set[str] = set()
            out: list[str] = []
            for item in items:
                if item not in seen:
                    seen.add(item)
                    out.append(item)
            return out

        return {
            "overall_average": avg,
            "turns": len(evaluations),
            "min_score": min(scores),
            "max_score": max(scores),
            "strengths": dedupe(all_strengths)[:5],
            "gaps": dedupe(all_gaps)[:5],
            "final_difficulty": session.difficulty,
        }
