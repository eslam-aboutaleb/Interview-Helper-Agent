"""Tests for SQLAlchemy model validators and properties."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import (
    AnswerEvaluation,
    InterviewSession,
    Question,
    QuestionHistory,
    User,
    UserDocument,
    UserSession,
)


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


class TestUserModel:
    def test_is_admin_property(self, db):
        admin = User(email="admin@example.com", hashed_password="x", role="admin")
        regular = User(email="user@example.com", hashed_password="x", role="user")
        assert admin.is_admin is True
        assert regular.is_admin is False

    def test_email_validator_lowercases(self, db):
        user = User(email="  User@Example.COM  ", hashed_password="x")
        db.add(user)
        db.commit()
        assert user.email == "user@example.com"

    def test_email_validator_rejects_empty(self, db):
        with pytest.raises(ValueError):
            User(email="   ", hashed_password="x")

    def test_email_validator_rejects_missing_at(self, db):
        with pytest.raises(ValueError):
            User(email="not-an-email", hashed_password="x")

    def test_email_validator_rejects_too_long(self, db):
        with pytest.raises(ValueError):
            User(email="a" * 250 + "@example.com", hashed_password="x")

    def test_repr(self, db):
        user = User(email="repr@example.com", hashed_password="x")
        db.add(user)
        db.commit()
        assert "repr@example.com" in repr(user)


class TestUserSessionModel:
    def test_create_session(self, db):
        user = User(email="session@example.com", hashed_password="x")
        db.add(user)
        db.commit()
        session = UserSession(
            user_id=user.id,
            token_hash="abc123",
            expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
        )
        db.add(session)
        db.commit()
        assert session.id is not None


class TestUserDocumentModel:
    def test_document_type_validator(self, db):
        user = User(email="doc@example.com", hashed_password="x")
        db.add(user)
        db.commit()
        doc = UserDocument(
            user_id=user.id,
            document_type="RESUME",
            filename="resume.pdf",
            content_text="Some text content",
        )
        db.add(doc)
        db.commit()
        assert doc.document_type == "resume"

    def test_document_type_validator_rejects_invalid(self, db):
        user = User(email="doc2@example.com", hashed_password="x")
        db.add(user)
        db.commit()
        with pytest.raises(ValueError):
            UserDocument(
                user_id=user.id,
                document_type="invalid",
                filename="f.txt",
                content_text="text",
            )


class TestQuestionModel:
    def _valid(self, **overrides):
        data = dict(
            job_title="SWE",
            question_text="Explain how a hash table works?",
            question_type="technical",
        )
        data.update(overrides)
        return Question(**data)

    def test_valid_question(self, db):
        q = self._valid()
        db.add(q)
        db.commit()
        assert q.id is not None

    def test_job_title_validator_rejects_empty(self, db):
        with pytest.raises(ValueError):
            self._valid(job_title="  ")

    def test_job_title_validator_rejects_short(self, db):
        with pytest.raises(ValueError):
            self._valid(job_title="A")

    def test_question_text_validator_rejects_empty(self, db):
        with pytest.raises(ValueError):
            self._valid(question_text="  ")

    def test_question_text_validator_rejects_short(self, db):
        with pytest.raises(ValueError):
            self._valid(question_text="short")

    def test_question_type_validator_normalizes(self, db):
        q = self._valid(question_type="TECHNICAL")
        db.add(q)
        db.commit()
        assert q.question_type == "technical"

    def test_question_type_validator_rejects_invalid(self, db):
        with pytest.raises(ValueError):
            self._valid(question_type="invalid")


class TestQuestionHistoryModel:
    def test_action_validator_normalizes(self, db):
        entry = QuestionHistory(user_id=1, question_id=1, action="VIEWED")
        db.add(entry)
        db.commit()
        assert entry.action == "viewed"

    def test_action_validator_rejects_invalid(self, db):
        with pytest.raises(ValueError):
            QuestionHistory(user_id=1, action="invalid")


class TestInterviewSessionModel:
    def test_create_session(self, db):
        user = User(email="iv@example.com", hashed_password="x")
        db.add(user)
        db.commit()
        session = InterviewSession(
            user_id=user.id,
            job_title="SWE",
            session_type="technical",
            difficulty=3,
            target_difficulty=3,
            max_turns=7,
            status="active",
        )
        db.add(session)
        db.commit()
        assert session.id is not None
        assert session.status == "active"


class TestAnswerEvaluationModel:
    def test_create_evaluation(self, db):
        user = User(email="ev@example.com", hashed_password="x")
        db.add(user)
        db.commit()
        session = InterviewSession(
            user_id=user.id,
            job_title="SWE",
            session_type="technical",
            difficulty=3,
            target_difficulty=3,
            max_turns=7,
            status="active",
        )
        db.add(session)
        db.commit()
        evaluation = AnswerEvaluation(
            session_id=session.id,
            user_id=user.id,
            overall_score=7.5,
            technical_score=8.0,
            communication_score=7.0,
            completeness_score=7.5,
            feedback={"strengths": ["clear"], "gaps": [], "tips": []},
            next_action="follow_up",
        )
        db.add(evaluation)
        db.commit()
        assert evaluation.id is not None
        assert evaluation.overall_score == 7.5
