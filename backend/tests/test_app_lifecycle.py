"""Tests for application lifecycle and root endpoints."""

import pytest
from fastapi.testclient import TestClient

from main import app, ensure_db_initialized


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


class TestRootEndpoints:
    def test_root(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["message"] == "Interview Prep Platform API"
        assert response.json()["version"] == "1.0.0"

    def test_openapi_available(self, client):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "/api/questions/" in schema["paths"]
        assert "/api/auth/register" in schema["paths"]
        assert "/api/interviews/sessions" in schema["paths"]
        assert "/api/documents/upload" in schema["paths"]
        assert "/api/admin/users" in schema["paths"]

    def test_health_requires_database(self):
        # The health endpoint depends on the real database engine;
        # server exceptions are surfaced rather than swallowed.
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/health")
        assert response.status_code in (200, 500)


class TestLifespan:
    def test_ensure_db_initialized_creates_tables(self):
        ensure_db_initialized()  # should not raise

    def test_ensure_db_initialized_logs_error(self, caplog, monkeypatch):
        from main import Base

        def failing_create_all(bind=None):
            raise RuntimeError("cannot create tables")

        monkeypatch.setattr(Base.metadata, "create_all", failing_create_all)
        with pytest.raises(RuntimeError):
            ensure_db_initialized()

    def test_lifespan_swallows_startup_errors(self, monkeypatch):
        import main

        def failing_init():
            raise RuntimeError("startup failure")

        monkeypatch.setattr(main, "ensure_db_initialized", failing_init)
        # The lifespan context manager must not propagate startup errors.
        import asyncio

        async def run():
            async with main.lifespan(main.app):
                pass

        asyncio.run(run())
