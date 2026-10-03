"""End-to-end tests for the questions router, including error paths."""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
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
