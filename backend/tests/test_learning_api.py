"""Tests for the learning-plan endpoints and service (plan 08)."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app
from models import AnswerEvaluation, InterviewSession, Question, UserDocument
from routes import learning as learning_routes
from services import learning_plan as learning_plan_service
from services.llm_service import LLMServiceError


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
    # Default every test to the deterministic heuristic plan: the suite must
    # never reach a real provider.
    app.dependency_overrides[learning_routes.get_llm_service] = lambda: None
    yield TestClient(app)
    app.dependency_overrides.clear()


class FakeLLMService:
    """Stand-in for ``LLMService`` that replays a canned response."""

    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.prompts = []

    def complete(self, prompt, system=None, temperature=None, max_tokens=None):
        self.prompts.append(prompt)
        if self.error:
            raise self.error
        return self.response

    def is_configured(self):
        return True


def register(client, email="learner@example.com", password="password123"):
    response = client.post("/api/auth/register", json={"email": email, "password": password})
    assert response.status_code == 201, response.text
    return response.json()


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def seed_question(db, *, text, question_type="technical", tags=None, difficulty=3):
    question = Question(
        job_title="SWE",
        question_text=text,
        question_type=question_type,
        difficulty=difficulty,
        tags=tags,
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


def seed_evaluations(db, user_id, question_type, scores):
    """Insert ``scores`` evaluations for sessions of one question type."""
    question = seed_question(db, text=f"Sample question about {question_type} topics", question_type=question_type)
    session = InterviewSession(
        user_id=user_id,
        job_title="SWE",
        session_type=question_type,
        difficulty=3,
        target_difficulty=3,
        status="completed",
        current_turn=len(scores),
        max_turns=len(scores),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    for index, score in enumerate(scores, start=1):
        db.add(
            AnswerEvaluation(
                session_id=session.id,
                question_id=question.id,
                user_id=user_id,
                overall_score=score,
                technical_score=score,
                communication_score=score,
                completeness_score=score,
            )
        )
    db.commit()
    return question


def seed_documents(db, user_id, resume_meta, jd_meta):
    """Attach a resume and a job description with pre-parsed metadata."""
    resume = UserDocument(
        user_id=user_id,
        document_type="resume",
        filename="resume.txt",
        content_text="resume",
        parsed_metadata=resume_meta,
    )
    jd = UserDocument(
        user_id=user_id,
        document_type="jd",
        filename="jd.txt",
        content_text="job description",
        parsed_metadata=jd_meta,
    )
    db.add_all([resume, jd])
    db.commit()


class TestAuthentication:
    def test_get_plan_requires_auth(self, client):
        response = client.get("/api/learning/plan")
        assert response.status_code == 401

    def test_post_plan_requires_auth(self, client):
        response = client.post("/api/learning/plan")
        assert response.status_code == 401

    def test_invalid_token_is_rejected(self, client):
        response = client.get("/api/learning/plan", headers=auth_headers("not-a-real-token"))
        assert response.status_code == 401


class TestHeuristicPlan:
    def test_plan_from_weak_question_types(self, client, db_session):
        user = register(client)
        seed_evaluations(db_session, 1, "technical", [4.0, 6.0])
        seed_evaluations(db_session, 1, "behavioral", [9.0])

        response = client.get("/api/learning/plan", headers=auth_headers(user["token"]))
        assert response.status_code == 200
        body = response.json()
        assert body["source"] == "heuristic"
        topics = [item["topic"] for item in body["items"]]
        assert "Technical depth" in topics
        assert body["items"][0]["topic"] == "Technical depth"
        assert body["items"][0]["priority"] in {"high", "medium", "low"}
        assert body["items"][0]["estimated_hours"] > 0
        # The strong area is reported as a weak-question-type data point but
        # does not become a study item.
        assert "Behavioral storytelling" not in topics
        assert body["weak_question_types"] == [
            {"question_type": "technical", "average_score": 5.0, "sample_size": 2},
            {"question_type": "behavioral", "average_score": 9.0, "sample_size": 1},
        ]

    def test_plan_uses_latest_resume_and_jd(self, client, db_session):
        user = register(client)
        seed_documents(
            db_session,
            1,
            {"skills": {"languages": ["python"], "frameworks": [], "concepts": []}},
            {
                "required_skills": {
                    "languages": ["python", "go"],
                    "frameworks": ["react"],
                    "cloud_devops": ["kubernetes"],
                }
            },
        )

        response = client.get("/api/learning/plan", headers=auth_headers(user["token"]))
        assert response.status_code == 200
        body = response.json()
        assert body["skill_match_percentage"] == pytest.approx(25.0)
        assert body["missing_skills"] == ["go", "kubernetes", "react"]
        topics = [item["topic"] for item in body["items"]]
        # The first missing skill is the highest-priority item.
        assert topics[0] == "go"
        assert body["items"][0]["priority"] == "high"

    def test_plan_recommends_matching_questions(self, client, db_session):
        user = register(client)
        seed_question(db_session, text="Explain how we run services on Kubernetes", tags="kubernetes", difficulty=4)
        seed_question(db_session, text="What is a container runtime like docker?", tags="docker", difficulty=2)
        seed_documents(
            db_session,
            1,
            {"skills": {"languages": []}},
            {"required_skills": {"languages": ["kubernetes"]}},
        )

        response = client.get("/api/learning/plan", headers=auth_headers(user["token"]))
        body = response.json()
        kubernetes_item = next(item for item in body["items"] if item["topic"] == "kubernetes")
        assert kubernetes_item["recommended_question_ids"]
        assert body["items"] is not None
        # The docker question must not be attached to the kubernetes topic.
        assert len(kubernetes_item["recommended_question_ids"]) == 1

    def test_plan_is_scoped_to_the_authenticated_user(self, client, db_session):
        first = register(client, email="first@example.com")
        second = register(client, email="second@example.com")
        seed_evaluations(db_session, 1, "technical", [2.0])
        seed_evaluations(db_session, 2, "behavioral", [3.0])

        response = client.get("/api/learning/plan", headers=auth_headers(second["token"]))
        body = response.json()
        topics = [item["topic"] for item in body["items"]]
        assert topics == ["Behavioral storytelling"]
        assert first["token"] != second["token"]

    def test_plan_without_a_job_description_has_no_match_percentage(self, client, db_session):
        user = register(client)
        seed_evaluations(db_session, 1, "technical", [3.0])

        response = client.get("/api/learning/plan", headers=auth_headers(user["token"]))
        body = response.json()
        assert body["skill_match_percentage"] is None
        assert body["missing_skills"] == []

    def test_post_plan_regenerates(self, client, db_session):
        user = register(client)
        seed_evaluations(db_session, 1, "technical", [3.0])

        headers = auth_headers(user["token"])
        first = client.get("/api/learning/plan", headers=headers).json()
        second = client.post("/api/learning/plan", headers=headers).json()

        assert first["source"] == "heuristic"
        assert second["source"] == "heuristic"
        assert [item["topic"] for item in second["items"]] == [item["topic"] for item in first["items"]]
        assert second["generated_at"] >= first["generated_at"]

    def test_plan_skips_questions_from_other_types(self, client, db_session):
        user = register(client)
        behavioral_only = seed_question(db_session, text="Tell me about technical depth", question_type="behavioral")
        seed_evaluations(db_session, 1, "technical", [3.5])

        response = client.get("/api/learning/plan", headers=auth_headers(user["token"]))
        item = next(i for i in response.json()["items"] if i["topic"] == "Technical depth")
        assert behavioral_only.id not in item["recommended_question_ids"]


class TestEmptyData:
    def test_empty_plan_is_still_well_formed(self, client):
        user = register(client)
        response = client.get("/api/learning/plan", headers=auth_headers(user["token"]))
        assert response.status_code == 200
        body = response.json()
        assert body["items"] == []
        assert body["weak_question_types"] == []
        assert body["missing_skills"] == []
        assert body["source"] == "heuristic"
        assert body["summary"]

    def test_empty_plan_post(self, client):
        user = register(client)
        response = client.post("/api/learning/plan", headers=auth_headers(user["token"]))
        assert response.status_code == 200
        assert response.json()["items"] == []


class TestLLMPlan:
    LLM_PAYLOAD = """Here is your plan:
```json
{
  "summary": "Focus on distributed systems first.",
  "items": [
    {
      "topic": "Distributed systems",
      "reason": "Lowest scoring area.",
      "recommended_question_ids": [1],
      "priority": "high",
      "estimated_hours": 5
    }
  ]
}
```
"""

    def _override_llm(self, client, service):
        client.app.dependency_overrides[learning_routes.get_llm_service] = lambda: service
        return service

    def test_llm_plan_is_used_when_configured(self, client, db_session):
        user = register(client)
        seed_question(db_session, text="Explain consensus in distributed systems", tags="systems")
        fake = self._override_llm(client, FakeLLMService(response=self.LLM_PAYLOAD))

        response = client.get("/api/learning/plan", headers=auth_headers(user["token"]))
        assert response.status_code == 200
        body = response.json()
        assert body["source"] == "llm"
        assert body["summary"] == "Focus on distributed systems first."
        assert body["items"][0]["topic"] == "Distributed systems"
        assert body["items"][0]["recommended_question_ids"] == [1]
        assert len(fake.prompts) == 1
        assert "Signals collected from the platform" in fake.prompts[0]

    def test_llm_prompt_carries_the_signals(self, client, db_session):
        user = register(client)
        seed_question(db_session, text="Explain consensus in distributed systems")
        seed_evaluations(db_session, 1, "technical", [3.0])
        fake = self._override_llm(client, FakeLLMService(response=self.LLM_PAYLOAD))

        client.post("/api/learning/plan", headers=auth_headers(user["token"]))
        prompt = fake.prompts[0]
        assert "technical: average 3.0/10 over 1 answers" in prompt
        assert "Explain consensus in distributed systems" in prompt

    def test_unknown_question_ids_are_dropped(self, client, db_session):
        user = register(client)
        seed_question(db_session, text="Explain consensus in distributed systems")
        payload = (
            '{"summary": "ok", "items": [{"topic": "Systems", "reason": "why", '
            '"recommended_question_ids": [99999, 1], "priority": "high", "estimated_hours": 3}]}'
        )
        self._override_llm(client, FakeLLMService(response=payload))

        body = client.get("/api/learning/plan", headers=auth_headers(user["token"])).json()
        assert body["source"] == "llm"
        assert body["items"][0]["recommended_question_ids"] == [1]

    def test_invalid_json_falls_back_to_heuristic(self, client, db_session):
        user = register(client)
        seed_evaluations(db_session, 1, "technical", [3.0])
        self._override_llm(client, FakeLLMService(response="I am sorry, I cannot help with that."))

        body = client.get("/api/learning/plan", headers=auth_headers(user["token"])).json()
        assert body["source"] == "heuristic"
        assert body["items"][0]["topic"] == "Technical depth"

    def test_empty_item_list_falls_back_to_heuristic(self, client, db_session):
        user = register(client)
        seed_evaluations(db_session, 1, "technical", [3.0])
        self._override_llm(client, FakeLLMService(response='{"summary": "nothing", "items": []}'))

        body = client.get("/api/learning/plan", headers=auth_headers(user["token"])).json()
        assert body["source"] == "heuristic"

    def test_llm_error_falls_back_to_heuristic(self, client, db_session):
        user = register(client)
        seed_evaluations(db_session, 1, "technical", [3.0])
        self._override_llm(client, FakeLLMService(error=LLMServiceError("all providers failed")))

        body = client.post("/api/learning/plan", headers=auth_headers(user["token"])).json()
        assert body["source"] == "heuristic"
        assert body["items"][0]["topic"] == "Technical depth"

    def test_llm_plan_without_user_data_still_answers(self, client):
        user = register(client)
        payload = '{"summary": "Start anywhere", "items": [{"topic": "Anything", "reason": "start"}]}'
        self._override_llm(client, FakeLLMService(response=payload))

        body = client.get("/api/learning/plan", headers=auth_headers(user["token"])).json()
        assert body["source"] == "llm"
        assert body["items"][0]["estimated_hours"] == 2.5
        assert body["items"][0]["priority"] == "medium"


class TestServiceHelpers:
    def test_priority_boundaries(self):
        assert learning_plan_service._priority_for_score(2.0) == {
            "priority": "high",
            "estimated_hours": learning_plan_service.HOURS_FOR_HIGH_PRIORITY,
        }
        assert learning_plan_service._priority_for_score(5.0)["priority"] == "medium"
        assert learning_plan_service._priority_for_score(9.0)["priority"] == "low"
        # A score above the 0-10 scale cannot happen through the API, but the
        # helper still clamps rather than returning nothing.
        assert learning_plan_service._priority_for_score(11.0) == {
            "priority": "low",
            "estimated_hours": learning_plan_service.HOURS_FOR_LOW_PRIORITY,
        }
        # A type with no score data is treated as the weakest case.
        assert learning_plan_service._priority_for_score(None)["priority"] == "high"

    def test_find_questions_for_topic_matches_tags_and_text(self, db_session):
        by_tag = seed_question(db_session, text="Totally unrelated wording", tags="kafka,streaming")
        by_text = seed_question(db_session, text="How would you tune a kafka consumer?", tags=None)
        seed_question(db_session, text="Another unrelated topic entirely", tags="postgres")

        matches = learning_plan_service.find_questions_for_topic(db_session, "kafka")
        assert set(matches) == {by_tag.id, by_text.id}

    def test_find_questions_for_topic_ignores_blank_topic(self, db_session):
        seed_question(db_session, text="Some question", tags="kafka")
        assert learning_plan_service.find_questions_for_topic(db_session, "  ") == []

    def test_find_questions_for_topic_respects_the_limit(self, db_session):
        for index in range(learning_plan_service.MAX_QUESTIONS_PER_TOPIC + 3):
            seed_question(db_session, text=f"Kafka question number {index}", tags="kafka")

        assert len(learning_plan_service.find_questions_for_topic(db_session, "kafka")) == (
            learning_plan_service.MAX_QUESTIONS_PER_TOPIC
        )

    @pytest.mark.parametrize(
        "raw_items,expected",
        [
            ("not a list", []),
            (["string entry"], []),
            ([{"reason": "no topic"}], []),
            ([{"topic": "   "}], []),
        ],
    )
    def test_coerce_items_drops_malformed_entries(self, raw_items, expected):
        assert learning_plan_service._coerce_items(raw_items) == expected

    def test_coerce_items_clamps_and_defaults(self):
        items = learning_plan_service._coerce_items(
            [
                {
                    "topic": "Kubernetes",
                    "reason": "Needed",
                    "recommended_question_ids": ["1", None, "abc", 2],
                    "priority": "URGENT",
                    "estimated_hours": "not a number",
                },
                {
                    "topic": "x" * 400,
                    "reason": "y" * 900,
                    "estimated_hours": 999,
                },
            ]
        )
        first, second = items
        assert first["recommended_question_ids"] == [1, 2]
        assert first["priority"] == "medium"
        assert first["estimated_hours"] == learning_plan_service.HOURS_FOR_MEDIUM_PRIORITY
        assert len(second["topic"]) == 200
        assert len(second["reason"]) == 500
        assert second["estimated_hours"] == 40.0

    def test_coerce_items_caps_the_item_count(self):
        raw = [{"topic": f"Topic {index}"} for index in range(learning_plan_service.MAX_PLAN_ITEMS + 5)]
        assert len(learning_plan_service._coerce_items(raw)) == learning_plan_service.MAX_PLAN_ITEMS

    def test_coerce_items_handles_missing_list(self):
        assert learning_plan_service._coerce_items([{"topic": "A", "recommended_question_ids": "nope"}]) == [
            {
                "topic": "A",
                "reason": "",
                "recommended_question_ids": [],
                "priority": "medium",
                "estimated_hours": learning_plan_service.HOURS_FOR_MEDIUM_PRIORITY,
            }
        ]

    def test_drop_unknown_question_ids(self):
        items = [{"topic": "A", "recommended_question_ids": [1, 5, 9]}]
        library = [{"id": 1}, {"id": 9}]
        assert learning_plan_service._drop_unknown_question_ids(items, library)[0]["recommended_question_ids"] == [1, 9]

    def test_build_prompt_without_data(self):
        prompt = learning_plan_service.build_prompt({"skill_gap": {}, "weak_areas": [], "library": []})
        assert "unknown" in prompt
        assert "no mock-interview evaluations recorded yet" in prompt
        assert "the question library is empty" in prompt
        assert "none detected" in prompt

    def test_heuristic_plan_is_capped(self, db_session):
        missing = [f"skill{index}" for index in range(learning_plan_service.MAX_SKILL_TOPICS + 4)]
        signals = {
            "skill_gap": {"match_percentage": 10.0, "missing_skills": missing},
            "weak_areas": [],
            "library": [],
        }
        plan = learning_plan_service.build_heuristic_plan(db_session, signals)
        assert len(plan["items"]) <= learning_plan_service.MAX_PLAN_ITEMS
        assert plan["summary"]

    def test_build_llm_plan_rejects_non_dict_payload(self):
        assert learning_plan_service.build_llm_plan(FakeLLMService(response="[1, 2, 3]"), {}) is None

    def test_generate_learning_plan_never_calls_llm_when_unset(self, db_session, monkeypatch):
        seed_question(db_session, text="Explain garbage collection", question_type="technical")

        def explode(*args, **kwargs):
            raise AssertionError("the LLM must not be used when no service is passed")

        monkeypatch.setattr(learning_plan_service, "build_llm_plan", explode)
        plan = learning_plan_service.generate_learning_plan(db_session, 1, llm_service=None)
        assert plan["source"] == "heuristic"
        assert isinstance(plan["generated_at"], datetime)
        assert plan["generated_at"].tzinfo == timezone.utc


class TestRouteFailurePath:
    def test_generation_error_is_wrapped_in_500(self, client, monkeypatch):
        user = register(client)

        def boom(*args, **kwargs):
            raise RuntimeError("database exploded")

        monkeypatch.setattr(learning_routes, "generate_learning_plan", boom)
        response = client.get("/api/learning/plan", headers=auth_headers(user["token"]))
        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"

    def test_llm_dependency_returns_none_without_a_key(self, monkeypatch):
        monkeypatch.setattr(learning_routes, "_llm_service", None)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        assert learning_routes.get_llm_service() is None

    def test_llm_dependency_caches_a_configured_service(self, monkeypatch):
        monkeypatch.setattr(learning_routes, "_llm_service", None)
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")

        service = learning_routes.get_llm_service()
        assert service is not None
        assert learning_routes.get_llm_service() is service
