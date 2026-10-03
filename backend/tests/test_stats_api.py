"""Tests for the stats endpoint."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app
from models import Question, QuestionSet


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


class TestStats:
    def test_stats_empty(self, client):
        response = client.get("/api/stats/")
        assert response.status_code == 200
        data = response.json()
        assert data["total_questions"] == 0
        assert data["questions_by_type"] == {}
        assert data["questions_by_job_title"] == {}
        assert data["average_difficulty"] == 0.0
        assert data["flagged_questions"] == 0
        assert data["total_question_sets"] == 0

    def test_stats_with_data(self, client, db_session):
        db_session.add_all(
            [
                Question(
                    job_title="SWE",
                    question_text="Explain how the reactor pattern handles concurrency?",
                    question_type="technical",
                    difficulty=4,
                    is_flagged=False,
                ),
                Question(
                    job_title="SWE",
                    question_text="Tell me about a time you led a team through a conflict?",
                    question_type="behavioral",
                    difficulty=2,
                    is_flagged=True,
                ),
                Question(
                    job_title="PM",
                    question_text="How do you prioritize competing roadmap priorities?",
                    question_type="behavioral",
                    difficulty=3,
                    is_flagged=False,
                ),
            ]
        )
        db_session.add(
            QuestionSet(
                name="System Design",
                job_title="SWE",
                question_ids="[1, 2]",
            )
        )
        db_session.commit()

        response = client.get("/api/stats/")
        assert response.status_code == 200
        data = response.json()
        assert data["total_questions"] == 3
        assert data["questions_by_type"] == {"technical": 1, "behavioral": 2}
        assert data["questions_by_job_title"] == {"SWE": 2, "PM": 1}
        assert data["average_difficulty"] == pytest.approx(3.0)
        assert data["flagged_questions"] == 1
        assert data["total_question_sets"] == 1

    def test_stats_query_error(self, client, db_session, monkeypatch):
        def failing_query(*args, **kwargs):
            raise RuntimeError("connection lost")

        monkeypatch.setattr(db_session, "query", failing_query)
        response = client.get("/api/stats/")
        assert response.status_code == 500
