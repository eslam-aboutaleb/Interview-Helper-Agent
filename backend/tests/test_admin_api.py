"""Tests for admin routes via TestClient."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app
from models import Question, QuestionHistory


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


def register(client, email="user@example.com", password="password123"):
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": password},
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


class TestAdminUsers:
    def test_list_users_requires_admin(self, client):
        admin = register(client, email="admin@example.com")
        register(client, email="regular@example.com")
        response = client.get("/api/admin/users", headers=auth_headers(admin["token"]))
        assert response.status_code == 200
        # A regular user must not access admin endpoints.
        regular = client.post(
            "/api/auth/login",
            json={"email": "regular@example.com", "password": "password123"},
        ).json()
        response = client.get("/api/admin/users", headers=auth_headers(regular["token"]))
        assert response.status_code == 403

    def test_list_users(self, client):
        admin = register(client, email="admin@example.com")
        register(client, email="one@example.com")
        register(client, email="two@example.com")
        response = client.get("/api/admin/users", headers=auth_headers(admin["token"]))
        assert response.status_code == 200
        assert len(response.json()) == 3

    def test_list_users_role_filter(self, client):
        admin = register(client, email="admin@example.com")
        register(client, email="one@example.com")
        response = client.get("/api/admin/users", params={"role": "admin"}, headers=auth_headers(admin["token"]))
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_list_users_invalid_role(self, client):
        admin = register(client, email="admin@example.com")
        response = client.get("/api/admin/users", params={"role": "root"}, headers=auth_headers(admin["token"]))
        assert response.status_code == 400

    def test_update_user_role(self, client):
        admin = register(client, email="admin@example.com")
        user = register(client, email="one@example.com")
        response = client.patch(
            f"/api/admin/users/{user['user']['id']}",
            json={"role": "admin"},
            headers=auth_headers(admin["token"]),
        )
        assert response.status_code == 200
        assert response.json()["role"] == "admin"

    def test_update_user_active(self, client):
        admin = register(client, email="admin@example.com")
        user = register(client, email="one@example.com")
        response = client.patch(
            f"/api/admin/users/{user['user']['id']}",
            json={"is_active": False},
            headers=auth_headers(admin["token"]),
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is False

    def test_admin_cannot_demote_self(self, client):
        admin = register(client, email="admin@example.com")
        response = client.patch(
            f"/api/admin/users/{admin['user']['id']}",
            json={"role": "user"},
            headers=auth_headers(admin["token"]),
        )
        assert response.status_code == 400

    def test_admin_cannot_deactivate_self(self, client):
        admin = register(client, email="admin@example.com")
        response = client.patch(
            f"/api/admin/users/{admin['user']['id']}",
            json={"is_active": False},
            headers=auth_headers(admin["token"]),
        )
        assert response.status_code == 400

    def test_update_user_not_found(self, client):
        admin = register(client, email="admin@example.com")
        response = client.patch("/api/admin/users/99999", json={"role": "user"}, headers=auth_headers(admin["token"]))
        assert response.status_code == 404

    def test_update_user_invalid_id(self, client):
        admin = register(client, email="admin@example.com")
        response = client.patch("/api/admin/users/0", json={"role": "user"}, headers=auth_headers(admin["token"]))
        assert response.status_code == 400

    def test_delete_user(self, client):
        admin = register(client, email="admin@example.com")
        user = register(client, email="one@example.com")
        response = client.delete(f"/api/admin/users/{user['user']['id']}", headers=auth_headers(admin["token"]))
        assert response.status_code == 204

    def test_admin_cannot_delete_self(self, client):
        admin = register(client, email="admin@example.com")
        response = client.delete(f"/api/admin/users/{admin['user']['id']}", headers=auth_headers(admin["token"]))
        assert response.status_code == 400

    def test_delete_user_not_found(self, client):
        admin = register(client, email="admin@example.com")
        response = client.delete("/api/admin/users/99999", headers=auth_headers(admin["token"]))
        assert response.status_code == 404

    def test_delete_user_invalid_id(self, client):
        admin = register(client, email="admin@example.com")
        response = client.delete("/api/admin/users/-1", headers=auth_headers(admin["token"]))
        assert response.status_code == 400


class TestAdminStats:
    def test_platform_stats(self, client, db_session):
        admin = register(client, email="admin@example.com")
        db_session.add(
            Question(
                job_title="SWE",
                question_text="Explain how the reactor pattern handles concurrency?",
                question_type="technical",
                is_flagged=True,
            )
        )
        db_session.commit()
        response = client.get("/api/admin/stats", headers=auth_headers(admin["token"]))
        assert response.status_code == 200
        data = response.json()
        assert data["total_users"] == 1
        assert data["active_users"] == 1
        assert data["admin_count"] == 1
        assert data["total_questions"] == 1
        assert data["flagged_questions"] == 1
        assert data["total_documents"] == 0
        assert data["total_interview_sessions"] == 0
        assert data["completed_sessions"] == 0
        assert data["total_evaluations"] == 0
        assert data["average_score"] is None
        assert data["recent_users"] == 1

    def test_platform_stats_requires_admin(self, client):
        register(client, email="admin@example.com")
        register(client, email="regular@example.com")
        regular = client.post(
            "/api/auth/login",
            json={"email": "regular@example.com", "password": "password123"},
        ).json()
        response = client.get("/api/admin/stats", headers=auth_headers(regular["token"]))
        assert response.status_code == 403


class TestAdminHistory:
    def test_audit_history(self, client, db_session):
        admin = register(client, email="admin@example.com")
        db_session.add(QuestionHistory(user_id=admin["user"]["id"], action="viewed", question_id=1))
        db_session.commit()
        response = client.get("/api/admin/history", headers=auth_headers(admin["token"]))
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_audit_history_filters(self, client, db_session):
        admin = register(client, email="admin@example.com")
        db_session.add(QuestionHistory(user_id=admin["user"]["id"], action="viewed"))
        db_session.add(QuestionHistory(user_id=admin["user"]["id"], action="created"))
        db_session.commit()
        response = client.get("/api/admin/history", params={"action": "created"}, headers=auth_headers(admin["token"]))
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["action"] == "created"

    def test_audit_history_user_filter(self, client, db_session):
        admin = register(client, email="admin@example.com")
        db_session.add(QuestionHistory(user_id=admin["user"]["id"], action="viewed"))
        db_session.add(QuestionHistory(user_id=999, action="viewed"))
        db_session.commit()
        response = client.get(
            "/api/admin/history",
            params={"user_id": admin["user"]["id"]},
            headers=auth_headers(admin["token"]),
        )
        assert response.status_code == 200
        assert len(response.json()) == 1


class TestAdminQuestions:
    def test_flagged_questions(self, client, db_session):
        admin = register(client, email="admin@example.com")
        db_session.add(
            Question(
                job_title="SWE",
                question_text="Explain how the reactor pattern handles concurrency?",
                question_type="technical",
                is_flagged=True,
            )
        )
        db_session.add(
            Question(
                job_title="SWE",
                question_text="Explain how the actor model handles concurrency?",
                question_type="technical",
                is_flagged=False,
            )
        )
        db_session.commit()
        response = client.get("/api/admin/questions/flagged", headers=auth_headers(admin["token"]))
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_delete_any_question(self, client, db_session):
        admin = register(client, email="admin@example.com")
        q = Question(
            job_title="SWE",
            question_text="Explain how the reactor pattern handles concurrency?",
            question_type="technical",
        )
        db_session.add(q)
        db_session.commit()
        db_session.refresh(q)
        response = client.delete(f"/api/admin/questions/{q.id}", headers=auth_headers(admin["token"]))
        assert response.status_code == 204
        assert db_session.query(Question).filter(Question.id == q.id).first() is None

    def test_delete_any_question_not_found(self, client):
        admin = register(client, email="admin@example.com")
        response = client.delete("/api/admin/questions/99999", headers=auth_headers(admin["token"]))
        assert response.status_code == 404

    def test_delete_any_question_invalid_id(self, client):
        admin = register(client, email="admin@example.com")
        response = client.delete("/api/admin/questions/0", headers=auth_headers(admin["token"]))
        assert response.status_code == 400
