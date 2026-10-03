"""Tests for the interview session engine using SQLite in-memory DB."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import User
from services.interview_service import InterviewService, InterviewServiceError
from services.evaluation_service import EvaluationService


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture()
def user(db):
    u = User(email="test@example.com", hashed_password="x")
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture()
def service():
    return InterviewService(
        gemini_service=None,
        evaluation_service=EvaluationService(gemini_service=None),
    )


class TestInterviewService:
    def test_start_session_asks_first_question(self, db, user, service):
        session = service.start_session(
            db,
            user_id=user.id,
            job_title="Software Engineer",
            session_type="technical",
            difficulty=3,
            max_turns=3,
        )
        assert session.status == "active"
        assert session.current_turn == 0
        messages = session.messages
        assert len(messages) == 1
        assert messages[0].role == "interviewer"
        assert messages[0].content

    def test_submit_answer_progresses(self, db, user, service):
        session = service.start_session(
            db,
            user_id=user.id,
            job_title="Software Engineer",
            max_turns=3,
        )
        result = service.submit_answer(
            db,
            session.id,
            user.id,
            "I would use a token bucket with Redis because it handles bursts well.",
        )
        assert result["completed"] is False
        assert "next_question" in result
        assert "evaluation" in result
        assert result["turn"] == 1

    def test_session_completes_after_max_turns(self, db, user, service):
        session = service.start_session(
            db,
            user_id=user.id,
            job_title="Software Engineer",
            max_turns=1,
        )
        result = service.submit_answer(db, session.id, user.id, "A reasonable answer.")
        assert result["completed"] is True
        assert "summary" in result
        refreshed = service.get_session(db, session.id, user.id)
        assert refreshed.status == "completed"

    def test_submit_to_missing_session_raises(self, db, user, service):
        with pytest.raises(InterviewServiceError):
            service.submit_answer(db, 99999, user.id, "answer")

    def test_adaptive_difficulty_raises(self, db, user, service):
        session = service.start_session(
            db,
            user_id=user.id,
            job_title="Software Engineer",
            difficulty=2,
            max_turns=5,
        )
        # Submit strong answers to push difficulty up.
        for _ in range(3):
            service.submit_answer(
                db,
                session.id,
                user.id,
                "Because the trade-off favors consistency, I implemented a "
                "distributed lock with Redis, specifically using Redlock. "
                "For example, we reduced conflicts. As a result, throughput improved.",
            )
        refreshed = service.get_session(db, session.id, user.id)
        assert refreshed.difficulty >= 2

    def test_list_sessions(self, db, user, service):
        service.start_session(db, user_id=user.id, job_title="SWE", max_turns=1)
        service.start_session(db, user_id=user.id, job_title="PM", max_turns=1)
        sessions = service.list_sessions(db, user.id)
        assert len(sessions) == 2
