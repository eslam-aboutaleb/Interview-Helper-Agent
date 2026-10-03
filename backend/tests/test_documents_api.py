"""Tests for document upload and analysis routes."""

import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app
from services import document_service


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


class TestUploadDocument:
    def test_upload_txt_resume(self, client):
        user = register(client)
        content = b"Jane Doe, Python developer with 5 years of experience in FastAPI and React."
        response = client.post(
            "/api/documents/upload?document_type=resume",
            files={"file": ("resume.txt", io.BytesIO(content), "text/plain")},
            headers=auth_headers(user["token"]),
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["document_type"] == "resume"
        assert data["filename"] == "resume.txt"
        assert data["parsed_metadata"]["years_of_experience"] == 5

    def test_upload_txt_jd(self, client):
        user = register(client)
        content = b"We need a Go developer with Kubernetes and Terraform experience."
        response = client.post(
            "/api/documents/upload?document_type=jd",
            files={"file": ("jd.txt", io.BytesIO(content), "text/plain")},
            headers=auth_headers(user["token"]),
        )
        assert response.status_code == 201
        assert response.json()["document_type"] == "jd"

    def test_upload_requires_auth(self, client):
        response = client.post(
            "/api/documents/upload?document_type=resume",
            files={"file": ("resume.txt", io.BytesIO(b"content"), "text/plain")},
        )
        assert response.status_code == 401

    def test_upload_empty_file(self, client):
        user = register(client)
        response = client.post(
            "/api/documents/upload?document_type=resume",
            files={"file": ("resume.txt", io.BytesIO(b""), "text/plain")},
            headers=auth_headers(user["token"]),
        )
        assert response.status_code == 400

    def test_upload_file_too_large(self, client):
        user = register(client)
        # One byte over the 10MB backend limit.
        content = b"x" * (10 * 1024 * 1024 + 1)
        response = client.post(
            "/api/documents/upload?document_type=resume",
            files={"file": ("big.txt", io.BytesIO(content), "text/plain")},
            headers=auth_headers(user["token"]),
        )
        assert response.status_code == 413

    def test_upload_unextractable_pdf(self, client):
        user = register(client)
        # Not a real PDF: PyPDF2 will fail to parse it.
        response = client.post(
            "/api/documents/upload?document_type=resume",
            files={"file": ("resume.pdf", io.BytesIO(b"not a pdf"), "application/pdf")},
            headers=auth_headers(user["token"]),
        )
        assert response.status_code == 422

    def test_upload_invalid_document_type(self, client):
        user = register(client)
        response = client.post(
            "/api/documents/upload?document_type=other",
            files={"file": ("f.txt", io.BytesIO(b"content"), "text/plain")},
            headers=auth_headers(user["token"]),
        )
        assert response.status_code == 422


class TestListDocuments:
    def test_list_documents(self, client):
        user = register(client)
        headers = auth_headers(user["token"])
        client.post(
            "/api/documents/upload?document_type=resume",
            files={"file": ("r.txt", io.BytesIO(b"Python developer with 3 years of experience."), "text/plain")},
            headers=headers,
        )
        client.post(
            "/api/documents/upload?document_type=jd",
            files={"file": ("j.txt", io.BytesIO(b"Requires Java and Spring Boot skills."), "text/plain")},
            headers=headers,
        )
        response = client.get("/api/documents/", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_list_documents_filter(self, client):
        user = register(client)
        headers = auth_headers(user["token"])
        client.post(
            "/api/documents/upload?document_type=resume",
            files={"file": ("r.txt", io.BytesIO(b"Python developer with 3 years of experience."), "text/plain")},
            headers=headers,
        )
        client.post(
            "/api/documents/upload?document_type=jd",
            files={"file": ("j.txt", io.BytesIO(b"Requires Java and Spring Boot skills."), "text/plain")},
            headers=headers,
        )
        response = client.get("/api/documents/", params={"document_type": "jd"}, headers=headers)
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["document_type"] == "jd"

    def test_list_documents_requires_auth(self, client):
        response = client.get("/api/documents/")
        assert response.status_code == 401


class TestDeleteDocument:
    def test_delete_document(self, client):
        user = register(client)
        headers = auth_headers(user["token"])
        created = client.post(
            "/api/documents/upload?document_type=resume",
            files={"file": ("r.txt", io.BytesIO(b"Python developer with 3 years of experience."), "text/plain")},
            headers=headers,
        ).json()
        response = client.delete(f"/api/documents/{created['id']}", headers=headers)
        assert response.status_code == 204
        remaining = client.get("/api/documents/", headers=headers).json()
        assert len(remaining) == 0

    def test_delete_not_found(self, client):
        user = register(client)
        response = client.delete("/api/documents/99999", headers=auth_headers(user["token"]))
        assert response.status_code == 404

    def test_delete_other_users_document(self, client):
        owner = register(client, email="owner@example.com")
        other = register(client, email="other@example.com")
        created = client.post(
            "/api/documents/upload?document_type=resume",
            files={"file": ("r.txt", io.BytesIO(b"Python developer with 3 years of experience."), "text/plain")},
            headers=auth_headers(owner["token"]),
        ).json()
        response = client.delete(f"/api/documents/{created['id']}", headers=auth_headers(other["token"]))
        assert response.status_code == 404


class TestSkillGap:
    def test_compute_skill_gap(self, client):
        user = register(client)
        headers = auth_headers(user["token"])
        resume = client.post(
            "/api/documents/upload?document_type=resume",
            files={
                "file": (
                    "r.txt",
                    io.BytesIO(b"Python developer with 3 years of experience in React and PostgreSQL."),
                    "text/plain",
                )
            },
            headers=headers,
        ).json()
        jd = client.post(
            "/api/documents/upload?document_type=jd",
            files={
                "file": (
                    "j.txt",
                    io.BytesIO(b"Requires Python, React, PostgreSQL, and Go with Docker."),
                    "text/plain",
                )
            },
            headers=headers,
        ).json()
        response = client.post(
            "/api/documents/skill-gap",
            params={"resume_id": resume["id"], "jd_id": jd["id"]},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "go" in data["missing_skills"]
        assert "python" in data["matched_skills"]
        assert 0 <= data["match_percentage"] <= 100
        assert "summary" in data

    def test_skill_gap_missing_document(self, client):
        user = register(client)
        response = client.post(
            "/api/documents/skill-gap",
            params={"resume_id": 999, "jd_id": 998},
            headers=auth_headers(user["token"]),
        )
        assert response.status_code == 404

    def test_skill_gap_requires_auth(self, client):
        response = client.post("/api/documents/skill-gap", params={"resume_id": 1, "jd_id": 2})
        assert response.status_code == 401


class TestDocumentServiceUnit:
    def test_extract_text_txt(self):
        assert document_service.extract_text("f.txt", b"hello world") == "hello world"

    def test_extract_text_docx_without_library(self):
        # A fake .docx payload: python-docx is not installed in the test
        # environment, so extraction degrades to an empty string.
        assert document_service.extract_text("f.docx", b"not really a docx") == ""

    def test_extract_text_pdf_without_library(self):
        assert document_service.extract_text("f.pdf", b"not really a pdf") == ""

    def test_extract_email(self):
        assert document_service._extract_email("Contact me at jane@example.com please") == "jane@example.com"
        assert document_service._extract_email("no email here") is None

    def test_parse_resume_email(self):
        meta = document_service.parse_resume("Reach me at bob@example.com for 2 years of experience.")
        assert meta["email"] == "bob@example.com"
        assert meta["word_count"] > 0

    def test_parse_job_description_word_count(self):
        meta = document_service.parse_job_description("We need Python and Go skills.")
        assert meta["word_count"] == 6

    def test_skill_gap_empty_jd(self):
        gap = document_service.compute_skill_gap({"skills": {}}, {"required_skills": {}})
        assert gap["match_percentage"] == 0.0
        assert gap["matched_skills"] == []
        assert gap["missing_skills"] == []
        assert gap["extra_skills"] == []

    def test_skill_gap_extra_skills(self):
        resume = {"skills": {"languages": ["python", "rust"]}}
        jd = {"required_skills": {"languages": ["python"]}}
        gap = document_service.compute_skill_gap(resume, jd)
        assert gap["extra_skills"] == ["rust"]
        assert gap["match_percentage"] == 100.0
