"""Tests for core services that do not require the LLM."""

from services.evaluation_service import EvaluationService
from services.document_service import (
    parse_resume,
    parse_job_description,
    compute_skill_gap,
    extract_years_of_experience,
)


class TestEvaluationService:
    def setup_method(self):
        self.service = EvaluationService(gemini_service=None)

    def test_evaluate_strong_answer(self):
        result = self.service.evaluate_answer(
            question="Design a rate limiter.",
            answer=(
                "I would use a token bucket algorithm. Because we need to handle "
                "bursts, a fixed window would cause problems at the boundaries. "
                "Specifically, I would use Redis with an atomic decrement. "
                "For example, each user gets 100 tokens per minute. "
                "As a result, we reduced latency by 40% in production."
            ),
            question_type="technical",
        )
        assert 0 <= result["overall"] <= 10
        assert "technical" in result
        assert "communication" in result
        assert "completeness" in result
        assert isinstance(result["strengths"], list)
        assert result["next_action"] in {"probe_deeper", "follow_up", "move_on", "redirect"}

    def test_evaluate_weak_answer(self):
        result = self.service.evaluate_answer(
            question="What is a closure?",
            answer="I don't know",
            question_type="technical",
        )
        assert result["overall"] < 5
        assert len(result["gaps"]) > 0

    def test_evaluate_behavioral_star(self):
        result = self.service.evaluate_answer(
            question="Tell me about a conflict.",
            answer=(
                "In my previous job there was a time I disagreed with a teammate. "
                "I was responsible for the API layer. I decided to set up a meeting "
                "and we aligned on the contract. As a result, we shipped on time."
            ),
            question_type="behavioral",
        )
        assert result["completeness"] >= 4

    def test_scores_are_clamped(self):
        result = self.service.evaluate_answer(
            question="Q",
            answer="word " * 500,
            question_type="technical",
        )
        for key in ("technical", "communication", "completeness", "overall"):
            assert 0 <= result[key] <= 10


class TestDocumentService:
    def test_parse_resume_extracts_skills(self):
        text = (
            "Senior Python developer with 5 years of experience building "
            "REST APIs with FastAPI, Django, React, PostgreSQL, Redis, "
            "Docker, Kubernetes, AWS, and machine learning with PyTorch."
        )
        meta = parse_resume(text)
        assert "python" in meta["skills"]["languages"]
        assert "fastapi" in meta["skills"]["frameworks"]
        assert "aws" in meta["skills"]["cloud_devops"]
        assert "postgresql" in meta["skills"]["databases"]
        assert meta["years_of_experience"] == 5

    def test_parse_job_description(self):
        meta = parse_job_description("We need Go, Kubernetes, Terraform, GraphQL, and Kafka experience.")
        assert "go" in meta["required_skills"]["languages"]
        assert "kubernetes" in meta["required_skills"]["cloud_devops"]
        assert "kafka" in meta["required_skills"]["databases"]

    def test_skill_gap(self):
        resume = parse_resume("I know Python, React, and PostgreSQL.")
        jd = parse_job_description("Requires Python, React, PostgreSQL, and Go.")
        gap = compute_skill_gap(resume, jd)
        assert gap["match_percentage"] > 0
        assert "go" in gap["missing_skills"]
        assert "python" in gap["matched_skills"]
        assert 0 <= gap["match_percentage"] <= 100

    def test_extract_years_of_experience(self):
        assert extract_years_of_experience("10 years of experience") == 10
        assert extract_years_of_experience("5 yrs") == 5
        assert extract_years_of_experience("no numbers here") is None

    def test_extract_years_picks_max(self):
        assert extract_years_of_experience("3 years at Google, 7 years at Meta") == 7
