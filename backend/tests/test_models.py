"""Tests for SQLAlchemy model validators and properties."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import (
    AnswerEvaluation,
    InterviewMessage,
    InterviewSession,
    Question,
    QuestionHistory,
    QuestionSet,
    User,
    UserDocument,
    UserRating,
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


class TestModelReprMethods:
    """Cover the __repr__ method of every model."""

    def test_user_session_repr(self):
        s = UserSession(
            user_id=1,
            token_hash="hash",
            expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
        )
        assert "UserSession" in repr(s)

    def test_user_document_repr(self):
        d = UserDocument(user_id=1, document_type="resume", content_text="text")
        assert "UserDocument" in repr(d)

    def test_interview_session_repr(self):
        s = InterviewSession(
            user_id=1,
            job_title="SWE",
            session_type="technical",
            difficulty=3,
            target_difficulty=3,
            max_turns=7,
            status="active",
        )
        assert "InterviewSession" in repr(s)

    def test_interview_message_repr(self):
        m = InterviewMessage(session_id=1, role="interviewer", content="hello")
        assert "InterviewMessage" in repr(m)

    def test_answer_evaluation_repr(self):
        e = AnswerEvaluation(session_id=1, user_id=1, overall_score=8.0)
        assert "AnswerEvaluation" in repr(e)

    def test_question_history_repr(self):
        h = QuestionHistory(user_id=1, action="viewed")
        assert "QuestionHistory" in repr(h)

    def test_question_repr(self):
        q = Question(
            job_title="SWE",
            question_text="Explain how a hash table works?",
            question_type="technical",
        )
        assert "Question" in repr(q)

    def test_question_set_repr(self):
        qs = QuestionSet(name="Core set", job_title="SWE", question_ids="[1, 2]")
        assert "QuestionSet" in repr(qs)

    def test_user_rating_repr(self):
        r = UserRating(question_id=1, rating=4.5)
        assert "UserRating" in repr(r)


class TestQuestionValidatorBranches:
    def _valid(self, **overrides):
        data = dict(
            job_title="SWE",
            question_text="Explain how a hash table works?",
            question_type="technical",
        )
        data.update(overrides)
        return Question(**data)

    def test_job_title_too_long(self):
        with pytest.raises(ValueError):
            self._valid(job_title="A" * 101)

    def test_job_title_invalid_characters(self):
        with pytest.raises(ValueError):
            self._valid(job_title="SWE!!!")

    def test_question_text_too_long(self):
        with pytest.raises(ValueError):
            self._valid(question_text="A" * 2001)

    def test_difficulty_none_defaults_to_one(self):
        q = self._valid(difficulty=None)
        assert q.difficulty == 1

    def test_difficulty_out_of_range(self):
        with pytest.raises(ValueError):
            self._valid(difficulty=6)

    def test_tags_blank_returns_none(self):
        q = self._valid(tags="   ")
        assert q.tags is None

    def test_tags_too_long(self):
        with pytest.raises(ValueError):
            self._valid(tags="A" * 501)

    def test_tags_invalid_format(self):
        with pytest.raises(ValueError):
            self._valid(tags="bad!!!tag")


class TestQuestionSetValidatorBranches:
    def _valid(self, **overrides):
        data = dict(name="Core set", job_title="SWE", question_ids="[1, 2]")
        data.update(overrides)
        return QuestionSet(**data)

    def test_name_empty(self):
        with pytest.raises(ValueError):
            self._valid(name="   ")

    def test_description_blank_returns_none(self):
        qs = self._valid(description="   ")
        assert qs.description is None

    def test_description_too_long(self):
        with pytest.raises(ValueError):
            self._valid(description="A" * 1001)

    def test_job_title_empty(self):
        with pytest.raises(ValueError):
            self._valid(job_title="  ")

    def test_job_title_short(self):
        with pytest.raises(ValueError):
            self._valid(job_title="A")

    def test_job_title_too_long(self):
        with pytest.raises(ValueError):
            self._valid(job_title="A" * 101)

    def test_question_ids_empty(self):
        with pytest.raises(ValueError):
            self._valid(question_ids="  ")

    def test_question_ids_invalid_json(self):
        with pytest.raises(ValueError):
            self._valid(question_ids="not-json")


class TestUserRatingValidatorBranches:
    def test_question_id_null(self):
        with pytest.raises(ValueError):
            UserRating(question_id=None, rating=4.0)

    def test_question_id_non_positive(self):
        with pytest.raises(ValueError):
            UserRating(question_id=0, rating=4.0)

    def test_rating_null(self):
        with pytest.raises(ValueError):
            UserRating(question_id=1, rating=None)

    def test_rating_out_of_range(self):
        with pytest.raises(ValueError):
            UserRating(question_id=1, rating=5.5)

    def test_feedback_blank_returns_none(self):
        r = UserRating(question_id=1, rating=4.0, feedback="   ")
        assert r.feedback is None

    def test_feedback_too_long(self):
        with pytest.raises(ValueError):
            UserRating(question_id=1, rating=4.0, feedback="A" * 1001)
