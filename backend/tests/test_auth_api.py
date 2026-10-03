"""Additional tests for auth routes and dependencies."""

import asyncio
import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from deps import get_optional_user
from main import app
from models import UserSession
from services import auth_service


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


class TestAuthRoutes:
    def test_register_requires_valid_email(self, client):
        response = client.post(
            "/api/auth/register",
            json={"email": "short", "password": "password123"},
        )
        assert response.status_code == 422

    def test_register_requires_long_password(self, client):
        response = client.post(
            "/api/auth/register",
            json={"email": "user@example.com", "password": "short"},
        )
        assert response.status_code == 422

    def test_register_duplicate_email(self, client):
        register(client)
        response = client.post(
            "/api/auth/register",
            json={"email": "user@example.com", "password": "password123"},
        )
        assert response.status_code == 409

    def test_login_success(self, client):
        register(client)
        response = client.post(
            "/api/auth/login",
            json={"email": "user@example.com", "password": "password123"},
        )
        assert response.status_code == 200
        assert "token" in response.json()

    def test_login_wrong_password(self, client):
        register(client)
        response = client.post(
            "/api/auth/login",
            json={"email": "user@example.com", "password": "wrong"},
        )
        assert response.status_code == 401

    def test_login_unknown_user(self, client):
        response = client.post(
            "/api/auth/login",
            json={"email": "ghost@example.com", "password": "password123"},
        )
        assert response.status_code == 401

    def test_logout_revokes_token(self, client):
        user = register(client)
        headers = auth_headers(user["token"])
        assert client.get("/api/auth/me", headers=headers).status_code == 200
        response = client.post("/api/auth/logout", headers=headers)
        assert response.status_code == 204
        assert client.get("/api/auth/me", headers=headers).status_code == 401

    def test_logout_without_token(self, client):
        register(client)
        # No Authorization header: dependency rejects before logout runs.
        response = client.post("/api/auth/logout")
        assert response.status_code == 401

    def test_history_endpoint(self, client, db_session):
        user = register(client)
        headers = auth_headers(user["token"])
        client.post(
            "/api/questions/",
            json={
                "job_title": "SWE",
                "question_text": "Explain how the reactor pattern handles concurrency?",
                "question_type": "technical",
            },
            headers=headers,
        )
        response = client.get("/api/auth/history", headers=headers)
        assert response.status_code == 200
        actions = [h["action"] for h in response.json()]
        assert "created" in actions

    def test_history_endpoint_with_action_filter(self, client, db_session):
        user = register(client)
        headers = auth_headers(user["token"])
        client.post(
            "/api/questions/",
            json={
                "job_title": "SWE",
                "question_text": "Explain how the reactor pattern handles concurrency?",
                "question_type": "technical",
            },
            headers=headers,
        )
        response = client.get("/api/auth/history", params={"action": "created"}, headers=headers)
        assert response.status_code == 200
        assert all(h["action"] == "created" for h in response.json())

    def test_history_endpoint_limit(self, client, db_session):
        user = register(client)
        headers = auth_headers(user["token"])
        for _ in range(3):
            client.post(
                "/api/questions/",
                json={
                    "job_title": "SWE",
                    "question_text": "Explain how the reactor pattern handles concurrency?",
                    "question_type": "technical",
                },
                headers=headers,
            )
        response = client.get("/api/auth/history", params={"limit": 2}, headers=headers)
        assert response.status_code == 200
        assert len(response.json()) == 2


class TestAuthServiceEdgeCases:
    @pytest.fixture()
    def db(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()
        engine.dispose()

    def test_expired_session_rejected(self, db):
        user = auth_service.create_user(db, email="user@example.com", password="password123")
        token = auth_service.create_session(db, user.id)
        # Force expiration.
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        session_row = db.query(UserSession).filter(UserSession.token_hash == token_hash).first()
        session_row.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db.commit()
        assert auth_service.get_user_from_token(db, token) is None

    def test_unknown_token_rejected(self, db):
        assert auth_service.get_user_from_token(db, "nonexistent-token") is None

    def test_empty_token_rejected(self, db):
        assert auth_service.get_user_from_token(db, "") is None

    def test_revoke_unknown_session(self, db):
        assert auth_service.revoke_session(db, "nonexistent") is False

    def test_revoke_all_sessions_count(self, db):
        user = auth_service.create_user(db, email="user@example.com", password="password123")
        auth_service.create_session(db, user.id)
        auth_service.create_session(db, user.id)
        assert auth_service.revoke_all_sessions(db, user.id) == 2

    def test_set_user_role_missing_user(self, db):
        assert auth_service.set_user_role(db, 99999, "admin") is None

    def test_set_user_active_missing_user(self, db):
        assert auth_service.set_user_active(db, 99999, False) is None

    def test_delete_user_missing(self, db):
        assert auth_service.delete_user(db, 99999) is False

    def test_password_hash_roundtrip(self):
        hashed = auth_service._hash_password("password123")
        assert auth_service._verify_password("password123", hashed) is True
        assert auth_service._verify_password("wrong", hashed) is False

    def test_verify_password_malformed_hash(self):
        assert auth_service._verify_password("password123", "garbage") is False
        assert auth_service._verify_password("password123", "pbkdf2_sha256$notanumber$salt$hash") is False
        assert auth_service._verify_password("password123", "bcrypt$10$salt$hash") is False

    def test_create_user_with_explicit_role(self, db):
        auth_service.create_user(db, email="admin@example.com", password="password123")
        user = auth_service.create_user(db, email="staff@example.com", password="password123", role="admin")
        assert user.role == "admin"

    def test_authenticate_missing_user(self, db):
        assert auth_service.authenticate_user(db, email="ghost@example.com", password="x") is None


class TestOptionalUserDependency:
    def test_no_header_returns_none(self):
        assert asyncio.run(get_optional_user(authorization=None)) is None

    def test_malformed_header_returns_none(self):
        assert asyncio.run(get_optional_user(authorization="Basic abc")) is None

    def test_invalid_token_returns_none(self, db_session):
        assert asyncio.run(get_optional_user(authorization="Bearer invalid", db=db_session)) is None

    def test_get_current_user_malformed_header(self):
        from deps import get_current_user

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(get_current_user(authorization="Basic abc"))
        assert exc_info.value.status_code == 401
