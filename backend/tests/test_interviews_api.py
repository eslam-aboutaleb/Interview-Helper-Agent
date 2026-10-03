"""Tests for the mock interview routes."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app
from models import User
from routes import interviews as interviews_routes
from services.evaluation_service import EvaluationService
from services.interview_service import InterviewService, InterviewServiceError


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    # Use a deterministic interview service with no LLM.
    interviews_routes._interview_service = InterviewService(
        gemini_service=None,
        evaluation_service=EvaluationService(gemini_service=None),
    )
    yield TestClient(app)
    app.dependency_overrides.clear()
    interviews_routes._interview_service = None


def register(client, email="user@example.com", password="password123"):
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": password},
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


class TestInterviewRoutes:
    def test_start_interview(self, client):
        user = register(client)
        response = client.post(
            "/api/interviews/sessions",
            json={"job_title": "SWE", "session_type": "technical", "difficulty": 3, "max_turns": 3},
            headers=auth_headers(user["token"]),
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["status"] == "active"
        assert data["job_title"] == "SWE"

    def test_start_interview_requires_auth(self, client):
        response = client.post(
            "/api/interviews/sessions",
            json={"job_title": "SWE"},
        )
        assert response.status_code == 401

    def test_list_interviews(self, client):
        user = register(client)
        headers = auth_headers(user["token"])
        client.post("/api/interviews/sessions", json={"job_title": "SWE"}, headers=headers)
        client.post("/api/interviews/sessions", json={"job_title": "PM"}, headers=headers)
        response = client.get("/api/interviews/sessions", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_get_interview(self, client):
        user = register(client)
        headers = auth_headers(user["token"])
        created = client.post("/api/interviews/sessions", json={"job_title": "SWE"}, headers=headers).json()
        response = client.get(f"/api/interviews/sessions/{created['id']}", headers=headers)
        assert response.status_code == 200
        assert response.json()["id"] == created["id"]

    def test_get_interview_not_found(self, client):
        user = register(client)
        response = client.get("/api/interviews/sessions/99999", headers=auth_headers(user["token"]))
        assert response.status_code == 404

    def test_get_interview_messages(self, client):
        user = register(client)
        headers = auth_headers(user["token"])
        created = client.post("/api/interviews/sessions", json={"job_title": "SWE"}, headers=headers).json()
        response = client.get(f"/api/interviews/sessions/{created['id']}/messages", headers=headers)
        assert response.status_code == 200
        messages = response.json()
        assert len(messages) == 1
        assert messages[0]["role"] == "interviewer"

    def test_get_interview_evaluations(self, client):
        user = register(client)
        headers = auth_headers(user["token"])
        created = client.post(
            "/api/interviews/sessions",
            json={"job_title": "SWE", "max_turns": 1},
            headers=headers,
        ).json()
        client.post(
            f"/api/interviews/sessions/{created['id']}/answer",
            json={"answer": "I would use Redis with a token bucket because it handles bursts well."},
            headers=headers,
        )
        response = client.get(f"/api/interviews/sessions/{created['id']}/evaluations", headers=headers)
        assert response.status_code == 200
        evaluations = response.json()
        assert len(evaluations) == 1
        assert "overall_score" in evaluations[0]

    def test_submit_answer(self, client):
        user = register(client)
        headers = auth_headers(user["token"])
        created = client.post(
            "/api/interviews/sessions",
            json={"job_title": "SWE", "max_turns": 3},
            headers=headers,
        ).json()
        response = client.post(
            f"/api/interviews/sessions/{created['id']}/answer",
            json={"answer": "I would use a token bucket algorithm with Redis."},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["completed"] is False
        assert "next_question" in data
        assert "evaluation" in data

    def test_submit_answer_completes_session(self, client):
        user = register(client)
        headers = auth_headers(user["token"])
        created = client.post(
            "/api/interviews/sessions",
            json={"job_title": "SWE", "max_turns": 1},
            headers=headers,
        ).json()
        response = client.post(
            f"/api/interviews/sessions/{created['id']}/answer",
            json={"answer": "A reasonable answer with because and therefore."},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["completed"] is True
        assert "summary" in data

    def test_submit_answer_to_other_users_session(self, client):
        owner = register(client, email="owner@example.com")
        other = register(client, email="other@example.com")
        created = client.post(
            "/api/interviews/sessions",
            json={"job_title": "SWE"},
            headers=auth_headers(owner["token"]),
        ).json()
        response = client.post(
            f"/api/interviews/sessions/{created['id']}/answer",
            json={"answer": "Trying to answer someone else's session."},
            headers=auth_headers(other["token"]),
        )
        assert response.status_code == 404

    def test_submit_answer_twice_on_completed_session(self, client):
        user = register(client)
        headers = auth_headers(user["token"])
        created = client.post(
            "/api/interviews/sessions",
            json={"job_title": "SWE", "max_turns": 1},
            headers=headers,
        ).json()
        client.post(
            f"/api/interviews/sessions/{created['id']}/answer",
            json={"answer": "First answer."},
            headers=headers,
        )
        response = client.post(
            f"/api/interviews/sessions/{created['id']}/answer",
            json={"answer": "Second answer."},
            headers=headers,
        )
        assert response.status_code == 404

    def test_model_answer_without_llm(self, client):
        user = register(client)
        response = client.post(
            "/api/interviews/model-answer",
            json={"question": "Explain how HTTPS works?", "question_type": "technical"},
            headers=auth_headers(user["token"]),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["question"] == "Explain how HTTPS works?"
        assert data["model_answer"] is None

    def test_model_answer_requires_auth(self, client):
        response = client.post(
            "/api/interviews/model-answer",
            json={"question": "Explain how HTTPS works?"},
        )
        assert response.status_code == 401


class TestInterviewServiceErrors:
    def test_submit_answer_missing_session(self, db_session):
        service = InterviewService(gemini_service=None)
        with pytest.raises(InterviewServiceError):
            service.submit_answer(db_session, 99999, 1, "answer")

    def test_submit_answer_completed_session(self, db_session, client):
        user = User(email="test@example.com", hashed_password="x")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        service = InterviewService(gemini_service=None)
        session = service.start_session(db_session, user_id=user.id, job_title="SWE", max_turns=1)
        service.submit_answer(db_session, session.id, user.id, "answer")
        with pytest.raises(InterviewServiceError):
            service.submit_answer(db_session, session.id, user.id, "another answer")

    def test_fallback_question_from_bank(self, db_session):
        from models import Question

        db_session.add(
            Question(
                job_title="SWE",
                question_text="Explain how the reactor pattern handles concurrent connections?",
                question_type="technical",
            )
        )
        db_session.commit()
        service = InterviewService(gemini_service=None)
        session = service.start_session(db_session, user_id=1, job_title="SWE")
        messages = session.messages
        assert messages[0].content == "Explain how the reactor pattern handles concurrent connections?"

    def test_fallback_question_generic(self, db_session):
        service = InterviewService(gemini_service=None)
        session = service.start_session(db_session, user_id=1, job_title="Astrophysicist")
        assert "Astrophysicist" in session.messages[0].content

    def test_llm_question_generation(self, db_session):
        class FakeGemini:
            def generate_content(self, prompt):
                return "Explain how Raft achieves consensus in distributed systems?"

        service = InterviewService(gemini_service=FakeGemini())
        session = service.start_session(db_session, user_id=1, job_title="SWE")
        assert session.messages[0].content == "Explain how Raft achieves consensus in distributed systems?"

    def test_llm_question_generation_falls_back_on_error(self, db_session):
        class BrokenGemini:
            def generate_content(self, prompt):
                raise RuntimeError("provider down")

        service = InterviewService(gemini_service=BrokenGemini())
        session = service.start_session(db_session, user_id=1, job_title="SWE")
        assert "SWE" in session.messages[0].content

    def test_build_summary_empty(self, db_session):
        service = InterviewService(gemini_service=None)
        session = service.start_session(db_session, user_id=1, job_title="SWE", max_turns=1)
        # No evaluations yet: summary reports zeros.
        summary = service._build_summary(db_session, session)
        assert summary["overall_average"] == 0.0
        assert summary["turns"] == 0

    def test_max_turns_clamped(self, db_session):
        service = InterviewService(gemini_service=None)
        session = service.start_session(db_session, user_id=1, job_title="SWE", max_turns=999)
        assert session.max_turns == 20
        session2 = service.start_session(db_session, user_id=1, job_title="SWE", max_turns=0)
        assert session2.max_turns == 1

    def test_list_sessions_respects_limit(self, db_session):
        service = InterviewService(gemini_service=None)
        for _ in range(3):
            service.start_session(db_session, user_id=1, job_title="SWE", max_turns=1)
        assert len(service.list_sessions(db_session, 1, limit=2)) == 2
