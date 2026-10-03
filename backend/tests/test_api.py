"""End-to-end API tests for auth and admin routes via TestClient."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app


@pytest.fixture()
def client():
    """TestClient backed by a shared in-memory SQLite database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
    session.close()
    engine.dispose()


def register(client, email, password="password123"):
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": password},
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


class TestAuthFlow:
    def test_register_first_user_returns_admin_token(self, client):
        data = register(client, "first@example.com")
        assert data["user"]["role"] == "admin"
        assert "token" in data

    def test_me_requires_token(self, client):
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_me_returns_profile(self, client):
        data = register(client, "user@example.com")
        response = client.get("/api/auth/me", headers=auth_headers(data["token"]))
        assert response.status_code == 200
        assert response.json()["email"] == "user@example.com"

    def test_logout_revokes_token(self, client):
        data = register(client, "user@example.com")
        response = client.post("/api/auth/logout", headers=auth_headers(data["token"]))
        assert response.status_code == 204
        response = client.get("/api/auth/me", headers=auth_headers(data["token"]))
        assert response.status_code == 401

    def test_second_user_is_not_admin(self, client):
        register(client, "first@example.com")
        data = register(client, "second@example.com")
        assert data["user"]["role"] == "user"


class TestAdminFlow:
    def test_admin_stats_requires_auth(self, client):
        response = client.get("/api/admin/stats")
        assert response.status_code == 401

    def test_admin_stats_requires_admin_role(self, client):
        register(client, "first@example.com")
        regular = register(client, "regular@example.com")
        response = client.get("/api/admin/stats", headers=auth_headers(regular["token"]))
        assert response.status_code == 403

    def test_admin_can_read_stats(self, client):
        admin = register(client, "first@example.com")
        response = client.get("/api/admin/stats", headers=auth_headers(admin["token"]))
        assert response.status_code == 200
        body = response.json()
        assert body["total_users"] == 1
        assert body["admin_count"] == 1

    def test_admin_can_list_and_promote_users(self, client):
        admin = register(client, "first@example.com")
        regular = register(client, "regular@example.com")

        listing = client.get("/api/admin/users", headers=auth_headers(admin["token"]))
        assert listing.status_code == 200
        assert len(listing.json()) == 2

        promoted = client.patch(
            f"/api/admin/users/{regular['user']['id']}",
            json={"role": "admin"},
            headers=auth_headers(admin["token"]),
        )
        assert promoted.status_code == 200
        assert promoted.json()["role"] == "admin"

        # The promoted user can now access admin endpoints.
        response = client.get("/api/admin/stats", headers=auth_headers(regular["token"]))
        assert response.status_code == 200

    def test_admin_cannot_demote_self(self, client):
        admin = register(client, "first@example.com")
        response = client.patch(
            f"/api/admin/users/{admin['user']['id']}",
            json={"role": "user"},
            headers=auth_headers(admin["token"]),
        )
        assert response.status_code == 400

    def test_admin_cannot_delete_self(self, client):
        admin = register(client, "first@example.com")
        response = client.delete(
            f"/api/admin/users/{admin['user']['id']}",
            headers=auth_headers(admin["token"]),
        )
        assert response.status_code == 400

    def test_admin_audit_history(self, client):
        admin = register(client, "first@example.com")
        response = client.get("/api/admin/history", headers=auth_headers(admin["token"]))
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_admin_flagged_questions(self, client):
        admin = register(client, "first@example.com")
        response = client.get(
            "/api/admin/questions/flagged",
            headers=auth_headers(admin["token"]),
        )
        assert response.status_code == 200
        assert response.json() == []
