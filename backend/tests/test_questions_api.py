"""End-to-end tests for the questions router, including error paths."""

import csv
import io
import json
from datetime import datetime

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app
from routes import questions as questions_routes
from services.gemini_service import GeminiServiceError


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
    yield TestClient(app)
    app.dependency_overrides.clear()


class FakeGeminiService:
    """Deterministic stand-in for the Gemini service."""

    def __init__(self, questions=None, error=None):
        self.questions = questions or []
        self.error = error

    def generate_questions(self, job_title, count=5, question_type="mixed"):
        if self.error:
            raise self.error
        return self.questions[:count]


@pytest.fixture()
def gemini_override(monkeypatch):
    """Point the lazy Gemini singleton at a controllable fake."""
    fake = FakeGeminiService()
    monkeypatch.setattr(questions_routes, "_gemini_service", fake)
    return fake


def register(client, email="user@example.com", password="password123"):
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": password},
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


class TestGenerateQuestions:
    def test_generate_success(self, client, gemini_override):
        gemini_override.questions = [
            {
                "job_title": "SWE",
                "question_text": "How does a hash table work?",
                "question_type": "technical",
                "difficulty": 3,
                "tags": "data-structures",
            }
        ]
        response = client.post(
            "/api/questions/generate",
            json={"job_title": "SWE", "count": 1, "question_type": "technical"},
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data) == 1
        assert data[0]["question_text"] == "How does a hash table work?"

    def test_generate_with_user_records_history(self, client, gemini_override, db_session):
        gemini_override.questions = [
            {
                "job_title": "SWE",
                "question_text": "Explain indexing in databases?",
                "question_type": "technical",
                "difficulty": 2,
                "tags": "databases",
            }
        ]
        user = register(client)
        response = client.post(
            "/api/questions/generate",
            json={"job_title": "SWE", "count": 1},
            headers=auth_headers(user["token"]),
        )
        assert response.status_code == 201
        history = db_session.execute(
            __import__("sqlalchemy").text("SELECT action FROM question_history WHERE user_id = :uid"),
            {"uid": user["user"]["id"]},
        ).fetchall()
        assert ("generated",) in history

    def test_generate_empty_job_title(self, client, gemini_override):
        # Pydantic rejects the blank job title before the handler runs.
        response = client.post(
            "/api/questions/generate",
            json={"job_title": "   ", "count": 1},
        )
        assert response.status_code == 422

    def test_generate_count_out_of_range(self, client, gemini_override):
        response = client.post(
            "/api/questions/generate",
            json={"job_title": "SWE", "count": 0},
        )
        assert response.status_code == 422
        response = client.post(
            "/api/questions/generate",
            json={"job_title": "SWE", "count": 101},
        )
        assert response.status_code == 422

    def test_generate_service_returns_nothing(self, client, gemini_override):
        gemini_override.questions = []
        response = client.post(
            "/api/questions/generate",
            json={"job_title": "SWE", "count": 1},
        )
        assert response.status_code == 503

    def test_generate_gemini_error(self, client, gemini_override):
        gemini_override.error = GeminiServiceError("provider down")
        response = client.post(
            "/api/questions/generate",
            json={"job_title": "SWE", "count": 1},
        )
        assert response.status_code == 503
        assert "AI service unavailable" in response.json()["detail"]

    def test_generate_value_error(self, client, gemini_override, monkeypatch):
        def bad_generate(self, job_title, count=5, question_type="mixed"):
            raise ValueError("bad input")

        monkeypatch.setattr(FakeGeminiService, "generate_questions", bad_generate)
        response = client.post(
            "/api/questions/generate",
            json={"job_title": "SWE", "count": 1},
        )
        assert response.status_code == 400

    def test_generate_unexpected_error(self, client, gemini_override, monkeypatch):
        def bad_generate(self, job_title, count=5, question_type="mixed"):
            raise RuntimeError("boom")

        monkeypatch.setattr(FakeGeminiService, "generate_questions", bad_generate)
        response = client.post(
            "/api/questions/generate",
            json={"job_title": "SWE", "count": 1},
        )
        assert response.status_code == 500

    def test_get_gemini_service_lazy_singleton(self, monkeypatch):
        monkeypatch.setattr(questions_routes, "_gemini_service", None)
        service = questions_routes.get_gemini_service()
        assert questions_routes._gemini_service is service
        assert questions_routes.get_gemini_service() is service


class TestListQuestions:
    def _seed(self, db_session):
        from models import Question

        for i, (title, qtype, flagged) in enumerate(
            [("SWE", "technical", False), ("PM", "behavioral", True), ("SWE", "mixed", False)]
        ):
            db_session.add(
                Question(
                    job_title=title,
                    question_text=f"Question number {i} about the role?",
                    question_type=qtype,
                    difficulty=3,
                    is_flagged=flagged,
                )
            )
        db_session.commit()

    def test_list_all(self, client, db_session):
        self._seed(db_session)
        response = client.get("/api/questions/")
        assert response.status_code == 200
        assert len(response.json()) == 3

    def test_filter_by_job_title(self, client, db_session):
        self._seed(db_session)
        response = client.get("/api/questions/", params={"job_title": "swe"})
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_filter_by_type(self, client, db_session):
        self._seed(db_session)
        response = client.get("/api/questions/", params={"question_type": "behavioral"})
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_filter_invalid_type(self, client, db_session):
        self._seed(db_session)
        response = client.get("/api/questions/", params={"question_type": "invalid"})
        assert response.status_code == 400

    def test_flagged_only(self, client, db_session):
        self._seed(db_session)
        response = client.get("/api/questions/", params={"flagged_only": "true"})
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_pagination(self, client, db_session):
        self._seed(db_session)
        response = client.get("/api/questions/", params={"skip": 1, "limit": 1})
        assert response.status_code == 200
        assert len(response.json()) == 1


class TestQuestionCRUD:
    def _create(self, client, text="What is a binary search tree?"):
        response = client.post(
            "/api/questions/",
            json={
                "job_title": "SWE",
                "question_text": text,
                "question_type": "technical",
                "difficulty": 3,
            },
        )
        assert response.status_code == 201, response.text
        return response.json()

    def test_create_and_get(self, client):
        question = self._create(client)
        response = client.get(f"/api/questions/{question['id']}")
        assert response.status_code == 200
        assert response.json()["id"] == question["id"]

    def test_create_with_user_tracks_history(self, client, db_session):
        user = register(client)
        response = client.post(
            "/api/questions/",
            json={
                "job_title": "SWE",
                "question_text": "Explain REST constraints in detail?",
                "question_type": "technical",
            },
            headers=auth_headers(user["token"]),
        )
        assert response.status_code == 201
        from models import QuestionHistory

        entries = db_session.query(QuestionHistory).all()
        assert any(e.action == "created" for e in entries)

    def test_create_empty_text(self, client):
        response = client.post(
            "/api/questions/",
            json={"job_title": "SWE", "question_text": "  ", "question_type": "technical"},
        )
        assert response.status_code == 422

    def test_create_invalid_type(self, client):
        response = client.post(
            "/api/questions/",
            json={
                "job_title": "SWE",
                "question_text": "Explain REST constraints in detail?",
                "question_type": "invalid",
            },
        )
        assert response.status_code == 422

    def test_create_invalid_difficulty(self, client):
        response = client.post(
            "/api/questions/",
            json={
                "job_title": "SWE",
                "question_text": "Explain REST constraints in detail?",
                "question_type": "technical",
                "difficulty": 9,
            },
        )
        assert response.status_code == 422

    def test_get_not_found(self, client):
        response = client.get("/api/questions/99999")
        assert response.status_code == 404

    def test_get_invalid_id(self, client):
        response = client.get("/api/questions/0")
        assert response.status_code == 400

    def test_get_tracks_view_for_user(self, client, db_session):
        user = register(client)
        question = self._create(client)
        response = client.get(f"/api/questions/{question['id']}", headers=auth_headers(user["token"]))
        assert response.status_code == 200
        from models import QuestionHistory

        entries = db_session.query(QuestionHistory).all()
        assert any(e.action == "viewed" for e in entries)

    def test_update(self, client):
        question = self._create(client)
        response = client.put(
            f"/api/questions/{question['id']}",
            json={"difficulty": 5, "is_flagged": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["difficulty"] == 5
        assert data["is_flagged"] is True

    def test_update_flag_tracks_history(self, client, db_session):
        user = register(client)
        question = self._create(client)
        response = client.put(
            f"/api/questions/{question['id']}",
            json={"is_flagged": True},
            headers=auth_headers(user["token"]),
        )
        assert response.status_code == 200
        from models import QuestionHistory

        entries = db_session.query(QuestionHistory).all()
        assert any(e.action == "flagged" for e in entries)

    def test_update_not_found(self, client):
        response = client.put("/api/questions/99999", json={"difficulty": 4})
        assert response.status_code == 404

    def test_update_invalid_id(self, client):
        response = client.put("/api/questions/-1", json={"difficulty": 4})
        assert response.status_code == 400

    def test_update_invalid_difficulty(self, client):
        question = self._create(client)
        response = client.put(f"/api/questions/{question['id']}", json={"difficulty": 10})
        assert response.status_code == 422

    def test_delete(self, client):
        question = self._create(client)
        response = client.delete(f"/api/questions/{question['id']}")
        assert response.status_code == 204
        assert client.get(f"/api/questions/{question['id']}").status_code == 404

    def test_delete_with_user_tracks_history(self, client, db_session):
        user = register(client)
        question = self._create(client)
        response = client.delete(f"/api/questions/{question['id']}", headers=auth_headers(user["token"]))
        assert response.status_code == 204
        from models import QuestionHistory

        entries = db_session.query(QuestionHistory).all()
        assert any(e.action == "deleted" for e in entries)

    def test_delete_not_found(self, client):
        response = client.delete("/api/questions/99999")
        assert response.status_code == 404

    def test_delete_invalid_id(self, client):
        response = client.delete("/api/questions/0")
        assert response.status_code == 400


class TestQuestionSets:
    def test_create_set(self, client):
        q1 = client.post(
            "/api/questions/",
            json={
                "job_title": "SWE",
                "question_text": "What is polymorphism in OOP design?",
                "question_type": "technical",
            },
        ).json()
        q2 = client.post(
            "/api/questions/",
            json={
                "job_title": "SWE",
                "question_text": "How do you design a URL shortener system?",
                "question_type": "technical",
            },
        ).json()
        response = client.post(
            "/api/questions/sets",
            json={
                "name": "System Design",
                "description": "Core system design questions",
                "job_title": "SWE",
                "question_ids": [q1["id"], q2["id"]],
            },
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["name"] == "System Design"

    def test_create_set_empty_name(self, client):
        response = client.post(
            "/api/questions/sets",
            json={"name": "  ", "job_title": "SWE", "question_ids": [1]},
        )
        assert response.status_code == 422

    def test_create_set_empty_job_title(self, client):
        response = client.post(
            "/api/questions/sets",
            json={"name": "Set", "job_title": "  ", "question_ids": [1]},
        )
        assert response.status_code == 422

    def test_create_set_empty_ids(self, client):
        response = client.post(
            "/api/questions/sets",
            json={"name": "Set", "job_title": "SWE", "question_ids": []},
        )
        assert response.status_code == 422

    def test_create_set_missing_question(self, client):
        response = client.post(
            "/api/questions/sets",
            json={"name": "Set", "job_title": "SWE", "question_ids": [99999]},
        )
        assert response.status_code == 404

    def test_list_sets(self, client):
        response = client.get("/api/questions/sets/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestRateQuestion:
    def _create(self, client):
        return client.post(
            "/api/questions/",
            json={
                "job_title": "SWE",
                "question_text": "What is the CAP theorem in distributed systems?",
                "question_type": "technical",
            },
        ).json()

    def test_rate_success(self, client):
        question = self._create(client)
        response = client.post(
            "/api/questions/rate",
            json={"question_id": question["id"], "rating": 4.5, "feedback": "Great question"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["rating"] == 4.5

    def test_rate_with_user_tracks_history(self, client, db_session):
        user = register(client)
        question = self._create(client)
        response = client.post(
            "/api/questions/rate",
            json={"question_id": question["id"], "rating": 3.0},
            headers=auth_headers(user["token"]),
        )
        assert response.status_code == 201
        from models import QuestionHistory

        entries = db_session.query(QuestionHistory).all()
        assert any(e.action == "rated" for e in entries)

    def test_rate_question_not_found(self, client):
        response = client.post(
            "/api/questions/rate",
            json={"question_id": 99999, "rating": 4.0},
        )
        assert response.status_code == 404

    def test_rate_out_of_range(self, client):
        question = self._create(client)
        response = client.post(
            "/api/questions/rate",
            json={"question_id": question["id"], "rating": 6.0},
        )
        assert response.status_code == 422


class TestJobTitles:
    def test_job_titles(self, client, db_session):
        from models import Question

        db_session.add(
            Question(
                job_title="SWE",
                question_text="Explain the SOLID principles in software design?",
                question_type="technical",
            )
        )
        db_session.add(
            Question(
                job_title="PM",
                question_text="How do you prioritize a product roadmap backlog?",
                question_type="behavioral",
            )
        )
        db_session.commit()
        response = client.get("/api/questions/job-titles/")
        assert response.status_code == 200
        assert set(response.json()) == {"SWE", "PM"}


class TestCompanyMode:
    """Company tagging, filtering and the ``/companies/`` lookup endpoint."""

    @staticmethod
    def _seed(db_session, *, text, company=None, job_title="SWE", question_type="technical"):
        from models import Question

        question = Question(
            job_title=job_title,
            question_text=text,
            question_type=question_type,
            company=company,
        )
        db_session.add(question)
        db_session.commit()
        db_session.refresh(question)
        return question

    # -- create / update ------------------------------------------------
    def test_create_question_with_company(self, client):
        response = client.post(
            "/api/questions/",
            json={
                "job_title": "SWE",
                "question_text": "Explain how a B-tree index is organized?",
                "question_type": "technical",
                "company": "Acme Corp",
            },
        )
        assert response.status_code == 201, response.text
        assert response.json()["company"] == "Acme Corp"

    def test_create_question_without_company(self, client):
        response = client.post(
            "/api/questions/",
            json={
                "job_title": "SWE",
                "question_text": "Explain how a hash table works?",
                "question_type": "technical",
            },
        )
        assert response.status_code == 201
        assert response.json()["company"] is None

    def test_blank_company_is_normalized_to_null(self, client):
        response = client.post(
            "/api/questions/",
            json={
                "job_title": "SWE",
                "question_text": "Explain how a heap is laid out in memory?",
                "question_type": "technical",
                "company": "   ",
            },
        )
        assert response.status_code == 201
        assert response.json()["company"] is None

    def test_company_is_trimmed(self, client):
        response = client.post(
            "/api/questions/",
            json={
                "job_title": "SWE",
                "question_text": "Describe how you would shard a database?",
                "question_type": "technical",
                "company": "  Globex  ",
            },
        )
        assert response.status_code == 201
        assert response.json()["company"] == "Globex"

    def test_company_longer_than_100_is_rejected(self, client):
        response = client.post(
            "/api/questions/",
            json={
                "job_title": "SWE",
                "question_text": "Explain how a hash table works?",
                "question_type": "technical",
                "company": "c" * 101,
            },
        )
        assert response.status_code == 422

    def test_update_company(self, client, db_session):
        question = self._seed(db_session, text="Explain how a trie is structured?")
        response = client.put(f"/api/questions/{question.id}", json={"company": "Initech"})
        assert response.status_code == 200
        assert response.json()["company"] == "Initech"

    def test_update_company_to_blank_clears_it(self, client, db_session):
        question = self._seed(db_session, text="Explain how a trie is structured?", company="Initech")
        response = client.put(f"/api/questions/{question.id}", json={"company": "  "})
        assert response.status_code == 200
        assert response.json()["company"] is None

    def test_update_without_company_keeps_the_value(self, client, db_session):
        question = self._seed(db_session, text="Explain how a trie is structured?", company="Initech")
        response = client.put(f"/api/questions/{question.id}", json={"difficulty": 4})
        assert response.status_code == 200
        assert response.json()["company"] == "Initech"

    def test_model_validates_company(self, client, db_session):
        """The model guard runs when Pydantic validation is bypassed."""
        from models import Question

        stored = self._seed(db_session, text="Explain how a trie is structured?", company="  Initech  ")
        assert stored.company == "Initech"

        blank = Question(
            job_title="SWE",
            question_text="Explain how a graph is stored?",
            question_type="technical",
            company="   ",
        )
        assert blank.company is None

        with pytest.raises(ValueError):
            Question(
                job_title="SWE",
                question_text="Explain how a graph is stored?",
                question_type="technical",
                company="c" * 101,
            )

    # -- filtering ------------------------------------------------------
    def test_filter_by_company(self, client, db_session):
        self._seed(db_session, text="Explain the Acme deployment pipeline?", company="Acme Corp")
        self._seed(db_session, text="Explain the Globex billing service?", company="Globex")

        response = client.get("/api/questions/", params={"company": "Acme Corp"})
        assert response.status_code == 200
        payload = response.json()
        assert [item["company"] for item in payload] == ["Acme Corp"]

    def test_company_filter_is_case_insensitive_and_partial(self, client, db_session):
        self._seed(db_session, text="Explain the Acme deployment pipeline?", company="Acme Corp")
        self._seed(db_session, text="Explain the Globex billing service?", company="Globex")

        response = client.get("/api/questions/", params={"company": "glob"})
        assert response.status_code == 200
        assert [item["company"] for item in response.json()] == ["Globex"]

    def test_company_filter_treats_wildcards_literally(self, client, db_session):
        self._seed(db_session, text="Explain the Acme deployment pipeline?", company="Acme Corp")
        self._seed(db_session, text="Explain the Initech rollout process?", company="Initech")

        response = client.get("/api/questions/", params={"company": "%"})
        assert response.status_code == 200
        assert response.json() == []

    def test_blank_company_filter_is_ignored(self, client, db_session):
        self._seed(db_session, text="Explain the Acme deployment pipeline?", company="Acme Corp")
        self._seed(db_session, text="Explain a generic distributed system?", company=None)

        response = client.get("/api/questions/", params={"company": "   "})
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_company_filter_combines_with_job_title(self, client, db_session):
        self._seed(db_session, text="Explain the Acme deployment pipeline?", company="Acme Corp", job_title="SWE")
        self._seed(
            db_session,
            text="Explain the Acme pricing strategy?",
            company="Acme Corp",
            job_title="PM",
            question_type="behavioral",
        )

        response = client.get("/api/questions/", params={"company": "Acme", "job_title": "PM"})
        assert response.status_code == 200
        assert [item["job_title"] for item in response.json()] == ["PM"]

    def test_export_filters_by_company(self, client, db_session):
        self._seed(db_session, text="Explain the Acme deployment pipeline?", company="Acme Corp")
        self._seed(db_session, text="Explain the Globex billing service?", company="Globex")

        response = client.get("/api/questions/export", params={"format": "json", "company": "Globex"})
        assert response.status_code == 200
        payload = json.loads(response.text)
        assert [item["company"] for item in payload] == ["Globex"]

    # -- /companies/ endpoint -------------------------------------------
    def test_companies_endpoint_returns_distinct_sorted_values(self, client, db_session):
        self._seed(db_session, text="Explain the Globex billing service?", company="Globex")
        self._seed(db_session, text="Explain the Acme deployment pipeline?", company="Acme Corp")
        self._seed(db_session, text="Explain another Globex service?", company="Globex")
        self._seed(db_session, text="Explain a generic distributed system?", company=None)

        response = client.get("/api/questions/companies/")
        assert response.status_code == 200
        assert response.json() == ["Acme Corp", "Globex"]

    def test_companies_endpoint_skips_empty_strings(self, client, db_session):
        self._seed(db_session, text="Explain the Acme deployment pipeline?", company="Acme Corp")
        # The model validator normalizes a blank company to NULL.
        self._seed(db_session, text="Explain a very generic system design?", company="   ")

        response = client.get("/api/questions/companies/")
        assert response.status_code == 200
        assert response.json() == ["Acme Corp"]

    def test_companies_endpoint_empty_bank(self, client):
        response = client.get("/api/questions/companies/")
        assert response.status_code == 200
        assert response.json() == []

    def test_companies_route_is_declared_before_the_dynamic_route(self, client, db_session):
        """``/{question_id}`` must not swallow the static ``/companies/`` path."""
        from routes.questions import router

        paths = [route.path for route in router.routes]
        assert paths.index("/companies/") < paths.index("/{question_id}")

        question = self._seed(db_session, text="Explain the Acme deployment pipeline?", company="Acme Corp")
        # The dynamic route still resolves real IDs.
        detail = client.get(f"/api/questions/{question.id}")
        assert detail.status_code == 200
        assert detail.json()["company"] == "Acme Corp"

        # A non-numeric segment under the static prefix stays a lookup, not a 422.
        listing = client.get("/api/questions/companies/")
        assert listing.status_code == 200
        assert listing.json() == ["Acme Corp"]

    def test_companies_endpoint_error_path(self, client, db_session, monkeypatch):
        def failing_query(*args, **kwargs):
            raise RuntimeError("connection lost")

        monkeypatch.setattr(db_session, "query", failing_query)
        response = client.get("/api/questions/companies/")
        assert response.status_code == 500

    # -- generate / import ----------------------------------------------
    def test_generate_tags_questions_with_company(self, client, gemini_override, db_session):
        gemini_override.questions = [
            {
                "job_title": "SWE",
                "question_text": "How does the Acme scheduler balance load?",
                "question_type": "technical",
                "difficulty": 3,
            }
        ]
        response = client.post(
            "/api/questions/generate",
            json={"job_title": "SWE", "count": 1, "company": "Acme Corp"},
        )
        assert response.status_code == 201
        assert response.json()[0]["company"] == "Acme Corp"

    def test_generate_without_company_leaves_it_null(self, client, gemini_override):
        gemini_override.questions = [
            {
                "job_title": "SWE",
                "question_text": "How does a scheduler balance load?",
                "question_type": "technical",
                "difficulty": 3,
            }
        ]
        response = client.post("/api/questions/generate", json={"job_title": "SWE", "count": 1})
        assert response.status_code == 201
        assert response.json()[0]["company"] is None

    def test_import_accepts_company(self, client):
        response = client.post(
            "/api/questions/import",
            json=[
                {
                    "job_title": "SWE",
                    "question_text": "Explain how the Acme scheduler works?",
                    "question_type": "technical",
                    "company": "Acme Corp",
                },
                {
                    "job_title": "SWE",
                    "question_text": "Explain the Globex billing flow?",
                    "question_type": "technical",
                    "company": "Globex",
                },
            ],
        )
        assert response.status_code == 200
        assert response.json()["imported"] == 2
        assert client.get("/api/questions/companies/").json() == ["Acme Corp", "Globex"]

    def test_company_longer_than_100_is_skipped_on_import(self, client):
        response = client.post(
            "/api/questions/import",
            json=[
                {
                    "job_title": "SWE",
                    "question_text": "Explain how the Acme scheduler works?",
                    "question_type": "technical",
                    "company": "c" * 101,
                }
            ],
        )
        assert response.status_code == 200
        assert response.json()["imported"] == 0
        assert response.json()["skipped"] == 1


class TestRouteLevelValidation:
    """Direct handler tests for the route-level 400 guards.

    Pydantic rejects most invalid payloads with 422 before the
    handlers run, so the handlers' own validation is exercised
    directly here with ``model_construct`` (which bypasses
    validation) to prove the defense-in-depth guards work.
    """

    @pytest.fixture()
    def handler_db(self, db_session):
        return db_session

    def test_generate_empty_job_title_guard(self, client, gemini_override, handler_db):
        import asyncio

        from routes.questions import generate_questions
        from schemas import QuestionGenerateRequest

        request = QuestionGenerateRequest.model_construct(job_title="   ", count=1, question_type="technical")
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                generate_questions(
                    request=request,
                    db=handler_db,
                    gemini_service=gemini_override,
                    current_user=None,
                )
            )
        assert exc_info.value.status_code == 400

    def test_generate_count_guard(self, client, gemini_override, handler_db):
        import asyncio

        from routes.questions import generate_questions
        from schemas import QuestionGenerateRequest

        request = QuestionGenerateRequest.model_construct(job_title="SWE", count=0, question_type="technical")
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                generate_questions(
                    request=request,
                    db=handler_db,
                    gemini_service=gemini_override,
                    current_user=None,
                )
            )
        assert exc_info.value.status_code == 400

    def test_create_empty_text_guard(self, client, handler_db):
        import asyncio

        from routes.questions import create_question
        from schemas import QuestionCreate

        question = QuestionCreate.model_construct(
            job_title="SWE",
            question_text="   ",
            question_type="technical",
        )
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(create_question(question=question, db=handler_db, current_user=None))
        assert exc_info.value.status_code == 400

    def test_create_invalid_type_guard(self, client, handler_db):
        import asyncio

        from routes.questions import create_question
        from schemas import QuestionCreate

        question = QuestionCreate.model_construct(
            job_title="SWE",
            question_text="Explain how a hash table works?",
            question_type="invalid",
        )
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(create_question(question=question, db=handler_db, current_user=None))
        assert exc_info.value.status_code == 400

    def test_create_invalid_difficulty_guard(self, client, handler_db):
        import asyncio

        from routes.questions import create_question
        from schemas import QuestionCreate

        question = QuestionCreate.model_construct(
            job_title="SWE",
            question_text="Explain how a hash table works?",
            question_type="technical",
            difficulty=9,
        )
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(create_question(question=question, db=handler_db, current_user=None))
        assert exc_info.value.status_code == 400

    def test_update_invalid_difficulty_guard(self, client, handler_db):
        import asyncio

        from models import Question
        from routes.questions import update_question
        from schemas import QuestionUpdate

        q = Question(
            job_title="SWE",
            question_text="Explain how a hash table works?",
            question_type="technical",
        )
        handler_db.add(q)
        handler_db.commit()
        handler_db.refresh(q)

        update = QuestionUpdate.model_construct(difficulty=10, is_flagged=None, tags=None)
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                update_question(
                    question_id=q.id,
                    question_update=update,
                    db=handler_db,
                    current_user=None,
                )
            )
        assert exc_info.value.status_code == 400

    def test_create_set_guards(self, client, handler_db):
        import asyncio

        from routes.questions import create_question_set
        from schemas import QuestionSetCreate

        empty_name = QuestionSetCreate.model_construct(name="   ", job_title="SWE", question_ids=[1], description=None)
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(create_question_set(question_set=empty_name, db=handler_db))
        assert exc_info.value.status_code == 400

        empty_title = QuestionSetCreate.model_construct(name="Set", job_title="  ", question_ids=[1], description=None)
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(create_question_set(question_set=empty_title, db=handler_db))
        assert exc_info.value.status_code == 400

        empty_ids = QuestionSetCreate.model_construct(name="Set", job_title="SWE", question_ids=[], description=None)
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(create_question_set(question_set=empty_ids, db=handler_db))
        assert exc_info.value.status_code == 400

    def test_rate_out_of_range_guard(self, client, handler_db):
        import asyncio

        from models import Question
        from routes.questions import rate_question
        from schemas import UserRatingCreate

        q = Question(
            job_title="SWE",
            question_text="Explain how a hash table works?",
            question_type="technical",
        )
        handler_db.add(q)
        handler_db.commit()
        handler_db.refresh(q)

        rating = UserRatingCreate.model_construct(question_id=q.id, rating=6.0, feedback=None)
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(rate_question(rating=rating, db=handler_db, current_user=None))
        assert exc_info.value.status_code == 400


class TestQuestionErrorPaths:
    """Cover the generic 500 handlers in the questions router."""

    def test_list_questions_db_error(self, client, db_session, monkeypatch):
        def failing_query(*args, **kwargs):
            raise RuntimeError("connection lost")

        monkeypatch.setattr(db_session, "query", failing_query)
        response = client.get("/api/questions/")
        assert response.status_code == 500

    def test_get_question_db_error(self, client, db_session, monkeypatch):
        def failing_query(*args, **kwargs):
            raise RuntimeError("connection lost")

        monkeypatch.setattr(db_session, "query", failing_query)
        response = client.get("/api/questions/1")
        assert response.status_code == 500

    def test_create_question_db_error(self, client, db_session, monkeypatch):
        def failing_add(obj):
            raise RuntimeError("insert failed")

        monkeypatch.setattr(db_session, "add", failing_add)
        response = client.post(
            "/api/questions/",
            json={
                "job_title": "SWE",
                "question_text": "Explain how a hash table works?",
                "question_type": "technical",
            },
        )
        assert response.status_code == 500

    def test_update_question_db_error(self, client, db_session, monkeypatch):
        from models import Question

        q = Question(
            job_title="SWE",
            question_text="Explain how a hash table works?",
            question_type="technical",
        )
        db_session.add(q)
        db_session.commit()
        db_session.refresh(q)

        def failing_commit():
            raise RuntimeError("commit failed")

        monkeypatch.setattr(db_session, "commit", failing_commit)
        response = client.put(f"/api/questions/{q.id}", json={"difficulty": 4})
        assert response.status_code == 500

    def test_delete_question_db_error(self, client, db_session, monkeypatch):
        from models import Question

        q = Question(
            job_title="SWE",
            question_text="Explain how a hash table works?",
            question_type="technical",
        )
        db_session.add(q)
        db_session.commit()
        db_session.refresh(q)

        def failing_delete(obj):
            raise RuntimeError("delete failed")

        monkeypatch.setattr(db_session, "delete", failing_delete)
        response = client.delete(f"/api/questions/{q.id}")
        assert response.status_code == 500

    def test_create_set_db_error(self, client, db_session, monkeypatch):
        from models import Question

        q = Question(
            job_title="SWE",
            question_text="Explain how a hash table works?",
            question_type="technical",
        )
        db_session.add(q)
        db_session.commit()

        def failing_add(obj):
            raise RuntimeError("insert failed")

        monkeypatch.setattr(db_session, "add", failing_add)
        response = client.post(
            "/api/questions/sets",
            json={
                "name": "Set",
                "job_title": "SWE",
                "question_ids": [q.id],
            },
        )
        assert response.status_code == 500

    def test_list_sets_db_error(self, client, db_session, monkeypatch):
        def failing_query(*args, **kwargs):
            raise RuntimeError("connection lost")

        monkeypatch.setattr(db_session, "query", failing_query)
        response = client.get("/api/questions/sets/")
        assert response.status_code == 500

    def test_rate_question_db_error(self, client, db_session, monkeypatch):
        from models import Question

        q = Question(
            job_title="SWE",
            question_text="Explain how a hash table works?",
            question_type="technical",
        )
        db_session.add(q)
        db_session.commit()
        db_session.refresh(q)

        def failing_add(obj):
            raise RuntimeError("insert failed")

        monkeypatch.setattr(db_session, "add", failing_add)
        response = client.post(
            "/api/questions/rate",
            json={"question_id": q.id, "rating": 4.0},
        )
        assert response.status_code == 500

    def test_job_titles_db_error(self, client, db_session, monkeypatch):
        def failing_query(*args, **kwargs):
            raise RuntimeError("connection lost")

        monkeypatch.setattr(db_session, "query", failing_query)
        response = client.get("/api/questions/job-titles/")
        assert response.status_code == 500

    def test_create_question_value_error(self, client, db_session):
        """Question model validators raise ValueError for short text."""
        import asyncio

        from routes.questions import create_question
        from schemas import QuestionCreate

        # model_construct bypasses pydantic so the SQLAlchemy
        # @validates hook fires inside the handler.
        question = QuestionCreate.model_construct(
            job_title="SWE",
            question_text="short",
            question_type="technical",
        )
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(create_question(question=question, db=db_session, current_user=None))
        assert exc_info.value.status_code == 400

    def test_create_set_value_error(self, client, db_session):
        """QuestionSet model validators raise ValueError for long names."""
        import asyncio

        from models import Question
        from routes.questions import create_question_set
        from schemas import QuestionSetCreate

        q = Question(
            job_title="SWE",
            question_text="Explain how a hash table works?",
            question_type="technical",
        )
        db_session.add(q)
        db_session.commit()
        db_session.refresh(q)

        question_set = QuestionSetCreate.model_construct(
            name="x" * 201,
            job_title="SWE",
            question_ids=[q.id],
            description=None,
        )
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(create_question_set(question_set=question_set, db=db_session))
        assert exc_info.value.status_code == 400


class TestSearchQuestions:
    """``q`` full-text search on the questions list endpoint."""

    def _seed(self, db_session):
        from models import Question

        rows = [
            ("SWE", "How does a hash table work under collisions?", "technical", "data-structures"),
            ("PM", "Tell me about a roadmap prioritization tradeoff", "behavioral", "leadership"),
            ("Data Engineer", "Explain vector indexing in a columnar store", "technical", "databases,indexing"),
        ]
        for job_title, text, qtype, tags in rows:
            db_session.add(
                Question(
                    job_title=job_title,
                    question_text=text,
                    question_type=qtype,
                    difficulty=3,
                    tags=tags,
                )
            )
        db_session.commit()

    def test_search_hits_question_text(self, client, db_session):
        self._seed(db_session)
        response = client.get("/api/questions/", params={"q": "hash table"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert "hash table" in data[0]["question_text"]

    def test_search_is_case_insensitive(self, client, db_session):
        self._seed(db_session)
        response = client.get("/api/questions/", params={"q": "ROADMAP"})
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_search_matches_job_title(self, client, db_session):
        self._seed(db_session)
        response = client.get("/api/questions/", params={"q": "Data Engineer"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["job_title"] == "Data Engineer"

    def test_search_matches_tags(self, client, db_session):
        self._seed(db_session)
        response = client.get("/api/questions/", params={"q": "indexing"})
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_search_miss_returns_empty_list(self, client, db_session):
        self._seed(db_session)
        response = client.get("/api/questions/", params={"q": "kubernetes"})
        assert response.status_code == 200
        assert response.json() == []

    def test_search_blank_returns_normal_list(self, client, db_session):
        self._seed(db_session)
        for blank in ("", "   "):
            response = client.get("/api/questions/", params={"q": blank})
            assert response.status_code == 200
            assert len(response.json()) == 3

    def test_search_special_characters(self, client, db_session):
        from models import Question

        db_session.add(
            Question(
                job_title="SWE",
                question_text="Explain 100% coverage tooling and C++ builds",
                question_type="technical",
            )
        )
        db_session.commit()
        for term in ("100%", "C++", "coverage tooling and", "Explain 100%"):
            response = client.get("/api/questions/", params={"q": term})
            assert response.status_code == 200, term
            assert len(response.json()) == 1, term

    def test_search_like_wildcards_are_escaped(self, client, db_session):
        """A bare wildcard must be matched literally, not expanded."""
        self._seed(db_session)
        for term in ("%", "_"):
            response = client.get("/api/questions/", params={"q": term})
            assert response.status_code == 200
            assert response.json() == []

    def test_search_sql_injection_is_safe(self, client, db_session):
        self._seed(db_session)
        payload = "'; DROP TABLE questions;--"
        response = client.get("/api/questions/", params={"q": payload})
        assert response.status_code == 200
        assert response.json() == []
        # The table must still exist and hold the seeded rows.
        assert len(client.get("/api/questions/").json()) == 3

    def test_search_sql_injection_variants_are_safe(self, client, db_session):
        self._seed(db_session)
        for payload in ("' OR 1=1--", '" OR ""="', "1; DELETE FROM questions"):
            response = client.get("/api/questions/", params={"q": payload})
            assert response.status_code == 200, payload
        assert len(client.get("/api/questions/").json()) == 3

    def test_search_combined_with_other_filters(self, client, db_session):
        self._seed(db_session)
        response = client.get("/api/questions/", params={"q": "a", "question_type": "behavioral"})
        assert response.status_code == 200
        data = response.json()
        assert [item["question_type"] for item in data] == ["behavioral"]

        response = client.get("/api/questions/", params={"q": "a", "job_title": "PM"})
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_search_rejects_invalid_type_still_400(self, client, db_session):
        self._seed(db_session)
        response = client.get("/api/questions/", params={"q": "hash", "question_type": "invalid"})
        assert response.status_code == 400

    def test_search_rejects_overlong_term(self, client, db_session):
        self._seed(db_session)
        response = client.get("/api/questions/", params={"q": "x" * 201})
        assert response.status_code == 422

    def test_search_ordered_by_created_at_desc(self, client, db_session):
        from models import Question

        stamps = [
            datetime(2026, 1, 1, 12, 0, 0),
            datetime(2026, 1, 2, 12, 0, 0),
            datetime(2026, 1, 3, 12, 0, 0),
        ]
        for index, stamp in enumerate(stamps):
            db_session.add(
                Question(
                    job_title="SWE",
                    question_text=f"Ordering probe number {index}",
                    question_type="technical",
                    created_at=stamp,
                )
            )
        db_session.commit()
        response = client.get("/api/questions/", params={"q": "ordering probe"})
        assert response.status_code == 200
        assert [item["created_at"][:10] for item in response.json()] == [
            "2026-01-03",
            "2026-01-02",
            "2026-01-01",
        ]

    def test_search_db_error(self, client, db_session, monkeypatch):
        def failing_query(*args, **kwargs):
            raise RuntimeError("connection lost")

        monkeypatch.setattr(db_session, "query", failing_query)
        response = client.get("/api/questions/", params={"q": "hash"})
        assert response.status_code == 500


class TestSearchDialectSelection:
    """The dialect branch must be resolved at query time, not import time."""

    def test_postgres_uses_tsvector_and_websearch_to_tsquery(self):
        criterion, rank = questions_routes.build_search_filter("postgresql", "hash table")
        assert rank is not None
        sql = str(criterion.compile(dialect=postgresql.dialect()))
        assert "to_tsvector(" in sql
        assert "websearch_to_tsquery(" in sql
        assert "ts_rank(" in str(rank.compile(dialect=postgresql.dialect()))
        for column in ("question_text", "job_title", "tags"):
            assert column in sql

    def test_postgres_parameterizes_the_search_term(self):
        criterion, _ = questions_routes.build_search_filter("postgresql", "'; DROP TABLE questions;--")
        compiled = criterion.compile(dialect=postgresql.dialect())
        assert "DROP TABLE" not in str(compiled)
        assert any("DROP TABLE questions;--" in value for value in compiled.params.values())

    def test_postgres_orders_by_relevance(self, db_session):
        from models import Question

        query, rank = questions_routes.apply_question_filters(
            db_session.query(Question), dialect_name="postgresql", q="hash"
        )
        assert rank is not None
        sql = str(query.statement.compile(dialect=postgresql.dialect()))
        assert "ORDER BY ts_rank(" in sql
        assert "created_at DESC" in sql

    def test_sqlite_falls_back_to_ilike_without_rank(self, db_session):
        from models import Question

        criterion, rank = questions_routes.build_search_filter("sqlite", "hash")
        assert rank is None
        # SQLAlchemy renders ILIKE as lower(col) LIKE lower(?) on SQLite.
        sql = str(criterion.compile(dialect=sqlite.dialect())).lower()
        assert " like " in sql
        assert "lower(questions.question_text)" in sql
        assert "to_tsvector" not in sql
        for column in ("question_text", "job_title", "tags"):
            assert column in sql

        query, rank = questions_routes.apply_question_filters(
            db_session.query(Question), dialect_name="sqlite", q="hash"
        )
        assert rank is None
        sql = str(query.statement.compile(dialect=sqlite.dialect()))
        assert "ts_rank" not in sql
        assert "ORDER BY questions.created_at DESC" in sql

    def test_sqlite_parameterizes_the_search_term(self):
        criterion, _ = questions_routes.build_search_filter("sqlite", "'; DROP TABLE questions;--")
        compiled = criterion.compile(dialect=sqlite.dialect())
        assert "DROP TABLE" not in str(compiled)
        values = list(compiled.params.values())
        assert values == ["%'; DROP TABLE questions;--%"] * 3


class TestExportQuestions:
    def _seed(self, db_session):
        from models import Question

        db_session.add(
            Question(
                job_title="SWE",
                question_text="How does a hash table work under collisions?",
                question_type="technical",
                difficulty=3,
                tags="data-structures",
            )
        )
        db_session.add(
            Question(
                job_title="PM",
                question_text="Tell me about a roadmap prioritization tradeoff",
                question_type="behavioral",
                difficulty=2,
                is_flagged=True,
            )
        )
        db_session.commit()

    def _csv_rows(self, response):
        return list(csv.reader(io.StringIO(response.text)))

    def test_export_json_returns_valid_array(self, client, db_session):
        self._seed(db_session)
        response = client.get("/api/questions/export", params={"format": "json"})
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        assert response.headers["content-disposition"] == 'attachment; filename="questions.json"'
        payload = json.loads(response.text)
        assert len(payload) == 2
        assert {item["job_title"] for item in payload} == {"SWE", "PM"}
        assert {"id", "job_title", "question_text", "question_type", "created_at"} <= set(payload[0])

    def test_export_json_is_the_default_format(self, client, db_session):
        self._seed(db_session)
        response = client.get("/api/questions/export")
        assert response.status_code == 200
        assert len(json.loads(response.text)) == 2

    def test_export_json_empty_bank(self, client):
        response = client.get("/api/questions/export", params={"format": "json"})
        assert response.status_code == 200
        assert json.loads(response.text) == []

    def test_export_csv_header_and_rows(self, client, db_session):
        self._seed(db_session)
        response = client.get("/api/questions/export", params={"format": "csv"})
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert response.headers["content-disposition"] == 'attachment; filename="questions.csv"'
        rows = self._csv_rows(response)
        assert rows[0] == [
            "id",
            "job_title",
            "question_text",
            "question_type",
            "difficulty",
            "is_flagged",
            "tags",
            "created_at",
        ]
        assert len(rows) == 3
        assert {row[1] for row in rows[1:]} == {"SWE", "PM"}

    def test_export_csv_empty_bank_emits_header_only(self, client):
        response = client.get("/api/questions/export", params={"format": "csv"})
        assert response.status_code == 200
        rows = self._csv_rows(response)
        assert len(rows) == 1
        assert rows[0][0] == "id"

    def test_export_csv_quotes_embedded_delimiters(self, client, db_session):
        from models import Question

        db_session.add(
            Question(
                job_title="SWE",
                question_text='Explain "caching", in depth, please',
                question_type="technical",
            )
        )
        db_session.commit()
        response = client.get("/api/questions/export", params={"format": "csv"})
        assert response.status_code == 200
        rows = self._csv_rows(response)
        assert rows[1][2] == 'Explain "caching", in depth, please'

    def test_export_csv_sanitizes_formula_injection(self, client, db_session):
        from models import Question

        for text in (
            "=SUM(A1:A9) what is the total",
            "+1234 injection payload here",
            "-1234 injection payload here",
            "@SUM(A1:A9) injection payload",
        ):
            db_session.add(Question(job_title="SWE", question_text=text, question_type="technical"))
        db_session.commit()

        response = client.get("/api/questions/export", params={"format": "csv"})
        assert response.status_code == 200
        rows = self._csv_rows(response)
        exported = [row[2] for row in rows[1:]]
        assert len(exported) == 4
        for cell in exported:
            assert cell.startswith("'"), cell
        # Every exported cell still round-trips through a CSV reader.
        assert "'=SUM(A1:A9) what is the total" in exported

    def test_export_respects_search_and_type_filters(self, client, db_session):
        self._seed(db_session)
        response = client.get("/api/questions/export", params={"format": "json", "q": "roadmap"})
        payload = json.loads(response.text)
        assert [item["job_title"] for item in payload] == ["PM"]

        response = client.get("/api/questions/export", params={"format": "json", "question_type": "technical"})
        assert len(json.loads(response.text)) == 1

        response = client.get("/api/questions/export", params={"format": "csv", "flagged_only": "true"})
        rows = self._csv_rows(response)
        assert len(rows) == 2

    def test_export_invalid_format(self, client):
        response = client.get("/api/questions/export", params={"format": "xml"})
        assert response.status_code == 400
        assert "json" in response.json()["detail"]

    def test_export_invalid_question_type(self, client):
        response = client.get("/api/questions/export", params={"format": "json", "question_type": "invalid"})
        assert response.status_code == 400

    def test_export_db_error(self, client, db_session, monkeypatch):
        def failing_query(*args, **kwargs):
            raise RuntimeError("connection lost")

        monkeypatch.setattr(db_session, "query", failing_query)
        assert client.get("/api/questions/export").status_code == 500

    def test_export_route_is_not_shadowed_by_dynamic_route(self, client):
        """``/export`` must resolve before ``/{question_id}`` in the router."""
        paths = [route.path for route in questions_routes.router.routes]
        assert paths.index("/export") < paths.index("/{question_id}")
        response = client.get("/api/questions/export", params={"format": "json"})
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestImportQuestions:
    VALID = {
        "job_title": "SWE",
        "question_text": "What is a binary search tree and when do you use it?",
        "question_type": "technical",
        "difficulty": 3,
        "tags": "data-structures",
    }

    def test_import_valid_payload(self, client, db_session):
        second = dict(self.VALID, question_text="Describe garbage collection in the JVM runtime")
        response = client.post("/api/questions/import", json=[self.VALID, second])
        assert response.status_code == 200
        assert response.json() == {"imported": 2, "skipped": 0, "errors": []}
        assert len(client.get("/api/questions/").json()) == 2

    def test_import_partial_invalid_payload(self, client, db_session):
        payload = [
            self.VALID,
            {"job_title": "SWE", "question_text": "short", "question_type": "technical"},
            {"job_title": "SWE", "question_text": "Which type is invalid here?", "question_type": "invalid"},
            {"question_text": "Missing the required job title field"},
            "not-an-object",
        ]
        response = client.post("/api/questions/import", json=payload)
        assert response.status_code == 200
        summary = response.json()
        assert summary["imported"] == 1
        assert summary["skipped"] == 4
        assert [item["index"] for item in summary["errors"]] == [1, 2, 3, 4]
        assert "question_text" in summary["errors"][0]["error"]
        assert "question_type" in summary["errors"][1]["error"]
        assert "job_title" in summary["errors"][2]["error"]
        assert summary["errors"][3]["error"] == "entry must be a JSON object"
        assert len(client.get("/api/questions/").json()) == 1

    def test_import_all_entries_invalid(self, client):
        payload = [{"job_title": "S", "question_text": "short", "question_type": "nope"}]
        response = client.post("/api/questions/import", json=payload)
        assert response.status_code == 200
        assert response.json()["imported"] == 0
        assert response.json()["skipped"] == 1

    def test_import_empty_payload(self, client):
        response = client.post("/api/questions/import", json=[])
        assert response.status_code == 400
        assert "at least one" in response.json()["detail"]

    def test_import_non_array_payload(self, client):
        response = client.post("/api/questions/import", json={"job_title": "SWE"})
        assert response.status_code == 422

    def test_import_assigns_user_and_records_history(self, client, db_session):
        user = register(client)
        response = client.post(
            "/api/questions/import",
            json=[self.VALID],
            headers=auth_headers(user["token"]),
        )
        assert response.status_code == 200
        from models import Question, QuestionHistory

        question = db_session.query(Question).one()
        assert question.user_id == user["user"]["id"]
        entries = db_session.query(QuestionHistory).all()
        assert any(e.action == "created" and e.context["source"] == "import" for e in entries)

    def test_import_isolates_database_failure_per_entry(self, client, db_session, monkeypatch):
        real_flush = db_session.flush
        calls = {"count": 0}

        def flaky_flush(*args, **kwargs):
            calls["count"] += 1
            if calls["count"] == 1:
                raise IntegrityError("INSERT", {}, Exception("duplicate key value"))
            return real_flush(*args, **kwargs)

        monkeypatch.setattr(db_session, "flush", flaky_flush)
        second = dict(self.VALID, question_text="Describe garbage collection in the JVM runtime")
        response = client.post("/api/questions/import", json=[self.VALID, second])
        assert response.status_code == 200
        summary = response.json()
        assert summary["imported"] == 1
        assert summary["skipped"] == 1
        assert "duplicate key value" in summary["errors"][0]["error"]
        # Only the healthy entry reached the database.
        assert len(client.get("/api/questions/").json()) == 1

    def test_import_commit_failure_returns_500(self, client, db_session, monkeypatch):
        def failing_commit():
            raise RuntimeError("commit failed")

        monkeypatch.setattr(db_session, "commit", failing_commit)
        response = client.post("/api/questions/import", json=[self.VALID])
        assert response.status_code == 500

    def test_import_route_is_not_shadowed_by_dynamic_route(self, client):
        paths = [route.path for route in questions_routes.router.routes]
        assert paths.index("/import") < paths.index("/{question_id}")
        response = client.post("/api/questions/import", json=[self.VALID])
        assert response.status_code == 200
        assert response.json()["imported"] == 1


class TestImportExportHelpers:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("=SUM(A1:A9)", "'=SUM(A1:A9)"),
            ("+1", "'+1"),
            ("-1", "'-1"),
            ("@cmd", "'@cmd"),
            ("\tleading tab", "'\tleading tab"),
            ("\rleading cr", "'\rleading cr"),
            ("plain", "plain"),
            ("", ""),
            (None, ""),
            (3, "3"),
        ],
    )
    def test_sanitize_csv_cell(self, value, expected):
        assert questions_routes.sanitize_csv_cell(value) == expected

    @pytest.mark.parametrize(
        "term,expected",
        [
            ("plain", "plain"),
            ("100%", "100\\%"),
            ("a_b", "a\\_b"),
            ("c:\\path", "c:\\\\path"),
        ],
    )
    def test_escape_like(self, term, expected):
        assert questions_routes.escape_like(term) == expected

    def test_format_validation_error_readable(self):
        from pydantic import BaseModel, ValidationError

        class Sample(BaseModel):
            job_title: str

        with pytest.raises(ValidationError) as exc_info:
            Sample.model_validate({"job_title": 5})
        message = questions_routes.format_validation_error(exc_info.value)
        assert "job_title" in message

    def test_questions_json_chunks_is_a_single_document(self, db_session):
        from models import Question

        db_session.add(
            Question(
                job_title="SWE",
                question_text="What is a binary search tree and when to use it?",
                question_type="technical",
            )
        )
        db_session.commit()
        chunks = list(questions_routes.questions_json_chunks([db_session.query(Question).one()]))
        assert chunks[0] == "["
        assert chunks[-1] == "]"
        assert len(json.loads("".join(chunks))) == 1
        assert list(questions_routes.questions_json_chunks([])) == ["[", "]"]

    def test_questions_csv_document_quotes_and_sanitizes(self, db_session):
        from models import Question

        db_session.add(
            Question(
                job_title="SWE",
                question_text='=1+1, "why"',
                question_type="technical",
            )
        )
        db_session.commit()
        document = questions_routes.questions_csv_document([db_session.query(Question).one()])
        rows = list(csv.reader(io.StringIO(document)))
        assert rows[0][0] == "id"
        assert rows[1][2] == '\'=1+1, "why"'
        assert questions_routes.questions_csv_document([]).count("\n") == 1
