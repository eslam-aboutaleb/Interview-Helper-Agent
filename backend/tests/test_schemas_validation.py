"""Tests for Pydantic schema validation."""

import pytest
from pydantic import ValidationError

from schemas import (
    AdminUserUpdate,
    Question,
    QuestionCreate,
    QuestionGenerateRequest,
    QuestionSetCreate,
    QuestionUpdate,
    UserCreate,
    UserLogin,
    UserRatingCreate,
)


class TestQuestionBase:
    def test_valid_question(self):
        q = QuestionCreate(
            job_title="SWE",
            question_text="Explain how a hash table works?",
            question_type="TECHNICAL",
        )
        assert q.question_type == "technical"

    def test_empty_job_title(self):
        with pytest.raises(ValidationError):
            QuestionCreate(job_title="  ", question_text="Explain how a hash table works?")

    def test_short_job_title(self):
        with pytest.raises(ValidationError):
            QuestionCreate(job_title="A", question_text="Explain how a hash table works?")

    def test_long_job_title(self):
        with pytest.raises(ValidationError):
            QuestionCreate(job_title="A" * 101, question_text="Explain how a hash table works?")

    def test_job_title_invalid_characters(self):
        with pytest.raises(ValidationError):
            QuestionCreate(job_title="SWE!", question_text="Explain how a hash table works?")

    def test_job_title_allows_special(self):
        q = QuestionCreate(
            job_title="C++ Developer",
            question_text="Explain how a hash table works?",
            question_type="technical",
        )
        assert q.job_title == "C++ Developer"

    def test_empty_question_text(self):
        with pytest.raises(ValidationError):
            QuestionCreate(job_title="SWE", question_text="  ")

    def test_short_question_text(self):
        with pytest.raises(ValidationError):
            QuestionCreate(job_title="SWE", question_text="too short")

    def test_long_question_text(self):
        with pytest.raises(ValidationError):
            QuestionCreate(job_title="SWE", question_text="x" * 2001)

    def test_invalid_question_type(self):
        with pytest.raises(ValidationError):
            QuestionCreate(
                job_title="SWE",
                question_text="Explain how a hash table works?",
                question_type="invalid",
            )

    def test_difficulty_bounds(self):
        with pytest.raises(ValidationError):
            QuestionCreate(
                job_title="SWE",
                question_text="Explain how a hash table works?",
                difficulty=0,
            )
        with pytest.raises(ValidationError):
            QuestionCreate(
                job_title="SWE",
                question_text="Explain how a hash table works?",
                difficulty=6,
            )

    def test_tags_cleaned(self):
        q = QuestionCreate(
            job_title="SWE",
            question_text="Explain how a hash table works?",
            question_type="technical",
            tags="  python ,  algorithms  ",
        )
        assert q.tags == "python,algorithms"

    def test_tags_blank_becomes_none(self):
        q = QuestionCreate(
            job_title="SWE",
            question_text="Explain how a hash table works?",
            question_type="technical",
            tags="   ",
        )
        assert q.tags is None

    def test_tags_invalid_characters(self):
        with pytest.raises(ValidationError):
            QuestionCreate(
                job_title="SWE",
                question_text="Explain how a hash table works?",
                tags="python, bad-tag!",
            )

    def test_tags_too_long(self):
        with pytest.raises(ValidationError):
            QuestionCreate(
                job_title="SWE",
                question_text="Explain how a hash table works?",
                question_type="technical",
                tags="a" * 501,
            )


class TestQuestionUpdate:
    def test_partial_update(self):
        u = QuestionUpdate(difficulty=4)
        assert u.model_dump(exclude_unset=True) == {"difficulty": 4}

    def test_update_tags_invalid(self):
        with pytest.raises(ValidationError):
            QuestionUpdate(tags="bad tag!")


class TestQuestionGenerateRequest:
    def test_defaults(self):
        req = QuestionGenerateRequest(job_title="SWE")
        assert req.count == 5
        assert req.question_type == "mixed"

    def test_count_too_low(self):
        with pytest.raises(ValidationError):
            QuestionGenerateRequest(job_title="SWE", count=0)

    def test_count_too_high(self):
        with pytest.raises(ValidationError):
            QuestionGenerateRequest(job_title="SWE", count=101)

    def test_question_type_normalized(self):
        req = QuestionGenerateRequest(job_title="SWE", question_type="TECHNICAL")
        assert req.question_type == "technical"

    def test_invalid_question_type(self):
        with pytest.raises(ValidationError):
            QuestionGenerateRequest(job_title="SWE", question_type="invalid")

    def test_job_title_trimmed(self):
        req = QuestionGenerateRequest(job_title="  SWE  ")
        assert req.job_title == "SWE"


class TestQuestionSetCreate:
    def test_valid_set(self):
        s = QuestionSetCreate(
            name="  System Design  ",
            description="  Core questions  ",
            job_title="SWE",
            question_ids=[1, 2, 3],
        )
        assert s.name == "System Design"
        assert s.description == "Core questions"

    def test_blank_description_becomes_none(self):
        s = QuestionSetCreate(name="Set", job_title="SWE", question_ids=[1], description="   ")
        assert s.description is None

    def test_empty_name(self):
        with pytest.raises(ValidationError):
            QuestionSetCreate(name="  ", job_title="SWE", question_ids=[1])

    def test_description_too_long(self):
        with pytest.raises(ValidationError):
            QuestionSetCreate(name="Set", job_title="SWE", question_ids=[1], description="x" * 1001)

    def test_empty_question_ids(self):
        with pytest.raises(ValidationError):
            QuestionSetCreate(name="Set", job_title="SWE", question_ids=[])

    def test_short_job_title(self):
        with pytest.raises(ValidationError):
            QuestionSetCreate(name="Set", job_title="A", question_ids=[1])


class TestUserRatingCreate:
    def test_rating_rounded(self):
        r = UserRatingCreate(question_id=1, rating=4.56)
        assert r.rating == 4.6

    def test_rating_too_low(self):
        with pytest.raises(ValidationError):
            UserRatingCreate(question_id=1, rating=0.5)

    def test_rating_too_high(self):
        with pytest.raises(ValidationError):
            UserRatingCreate(question_id=1, rating=5.5)

    def test_invalid_question_id(self):
        with pytest.raises(ValidationError):
            UserRatingCreate(question_id=0, rating=4.0)

    def test_blank_feedback_becomes_none(self):
        r = UserRatingCreate(question_id=1, rating=4.0, feedback="   ")
        assert r.feedback is None

    def test_feedback_too_long(self):
        with pytest.raises(ValidationError):
            UserRatingCreate(question_id=1, rating=4.0, feedback="x" * 1001)


class TestUserSchemas:
    def test_user_create_email_normalized(self):
        u = UserCreate(email="  User@Example.COM  ", password="password123")
        assert u.email == "user@example.com"

    def test_user_create_email_without_at(self):
        with pytest.raises(ValidationError):
            UserCreate(email="not-an-email", password="password123")

    def test_user_create_short_password(self):
        with pytest.raises(ValidationError):
            UserCreate(email="user@example.com", password="short")

    def test_user_login_email_normalized(self):
        u = UserLogin(email="  User@Example.COM  ", password="password123")
        assert u.email == "user@example.com"


class TestAdminUserUpdate:
    def test_role_normalized(self):
        u = AdminUserUpdate(role="ADMIN")
        assert u.role == "admin"

    def test_invalid_role(self):
        with pytest.raises(ValidationError):
            AdminUserUpdate(role="root")

    def test_none_role_ok(self):
        assert AdminUserUpdate().role is None


class TestQuestionResponseSchema:
    def test_question_schema_from_attributes(self):
        from datetime import datetime

        q = Question.model_validate(
            {
                "id": 1,
                "job_title": "SWE",
                "question_text": "Explain how a hash table works?",
                "question_type": "technical",
                "difficulty": 3,
                "created_at": datetime.now(),
            }
        )
        assert q.id == 1
        assert q.job_title == "SWE"
