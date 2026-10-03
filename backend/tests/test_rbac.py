"""Tests for role-based access control and user management."""

import asyncio

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import User
from services import auth_service
from deps import get_current_admin_user


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


class TestRoleBootstrap:
    def test_first_user_becomes_admin(self, db):
        user = auth_service.create_user(db, email="first@example.com", password="password123")
        assert user.role == "admin"
        assert user.is_admin is True

    def test_subsequent_users_are_regular(self, db):
        auth_service.create_user(db, email="first@example.com", password="password123")
        user = auth_service.create_user(db, email="second@example.com", password="password123")
        assert user.role == "user"
        assert user.is_admin is False

    def test_invalid_role_rejected(self, db):
        auth_service.create_user(db, email="first@example.com", password="password123")
        with pytest.raises(ValueError):
            auth_service.create_user(
                db,
                email="second@example.com",
                password="password123",
                role="superuser",
            )

    def test_duplicate_email_rejected(self, db):
        auth_service.create_user(db, email="first@example.com", password="password123")
        with pytest.raises(ValueError):
            auth_service.create_user(db, email="first@example.com", password="password123")


class TestAuthentication:
    def test_login_updates_last_login(self, db):
        auth_service.create_user(db, email="user@example.com", password="password123")
        user = auth_service.authenticate_user(db, email="user@example.com", password="password123")
        assert user is not None
        assert user.last_login_at is not None

    def test_wrong_password_rejected(self, db):
        auth_service.create_user(db, email="user@example.com", password="password123")
        user = auth_service.authenticate_user(db, email="user@example.com", password="wrong")
        assert user is None

    def test_inactive_user_cannot_login(self, db):
        auth_service.create_user(db, email="user@example.com", password="password123")
        auth_service.set_user_active(db, 1, False)
        user = auth_service.authenticate_user(db, email="user@example.com", password="password123")
        assert user is None


class TestSessionLifecycle:
    def test_token_roundtrip(self, db):
        user = auth_service.create_user(db, email="user@example.com", password="password123")
        token = auth_service.create_session(db, user.id)
        resolved = auth_service.get_user_from_token(db, token)
        assert resolved is not None
        assert resolved.id == user.id

    def test_logout_revokes_token(self, db):
        user = auth_service.create_user(db, email="user@example.com", password="password123")
        token = auth_service.create_session(db, user.id)
        assert auth_service.revoke_session(db, token) is True
        assert auth_service.get_user_from_token(db, token) is None

    def test_deactivation_revokes_all_sessions(self, db):
        user = auth_service.create_user(db, email="user@example.com", password="password123")
        token_a = auth_service.create_session(db, user.id)
        token_b = auth_service.create_session(db, user.id)
        auth_service.set_user_active(db, user.id, False)
        assert auth_service.get_user_from_token(db, token_a) is None
        assert auth_service.get_user_from_token(db, token_b) is None


class TestUserManagement:
    def test_set_user_role(self, db):
        user = auth_service.create_user(db, email="user@example.com", password="password123")
        updated = auth_service.set_user_role(db, user.id, "admin")
        assert updated.role == "admin"

    def test_set_user_role_invalid(self, db):
        user = auth_service.create_user(db, email="user@example.com", password="password123")
        with pytest.raises(ValueError):
            auth_service.set_user_role(db, user.id, "root")

    def test_delete_user(self, db):
        user = auth_service.create_user(db, email="user@example.com", password="password123")
        token = auth_service.create_session(db, user.id)
        assert auth_service.delete_user(db, user.id) is True
        assert auth_service.get_user_from_token(db, token) is None
        assert db.query(User).filter(User.id == user.id).first() is None


class TestAdminDependency:
    def test_admin_user_passes(self):
        admin = User(email="admin@example.com", hashed_password="x", role="admin")
        assert asyncio.run(get_current_admin_user(user=admin)) is admin

    def test_regular_user_forbidden(self):
        regular = User(email="user@example.com", hashed_password="x", role="user")
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(get_current_admin_user(user=regular))
        assert exc_info.value.status_code == 403
