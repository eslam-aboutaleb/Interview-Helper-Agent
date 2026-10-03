"""Document ingestion: parse resumes and job descriptions into structured data."""

import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Curated skill dictionaries for rule-based extraction.
PROGRAMMING_LANGUAGES = {
    "python",
    "java",
    "javascript",
    "typescript",
    "c++",
    "c",
    "c#",
    "go",
    "rust",
    "ruby",
    "php",
    "swift",
    "kotlin",
    "scala",
    "r",
    "sql",
    "html",
    "css",
    "sass",
    "less",
}
FRAMEWORKS = {
    "react",
    "vue",
    "angular",
    "svelte",
    "django",
    "flask",
    "fastapi",
    "spring",
    "spring boot",
    "express",
    "next.js",
    "nuxt",
    "rails",
    "laravel",
    "asp.net",
    "tailwind",
    "node.js",
    "tensorflow",
    "pytorch",
    "pandas",
    "numpy",
    "scikit-learn",
    "keras",
}
CLOUD_DEVOPS = {
    "aws",
    "gcp",
    "azure",
    "docker",
    "kubernetes",
    "terraform",
    "ci/cd",
    "jenkins",
    "github actions",
    "gitlab ci",
    "linux",
}
DATABASES = {
    "postgresql",
    "mysql",
    "mongodb",
    "redis",
    "elasticsearch",
    "sqlite",
    "oracle",
    "dynamodb",
    "cassandra",
    "kafka",
}
CONCEPTS = {
    "system design",
    "microservices",
    "rest",
    "graphql",
    "api",
    "machine learning",
    "deep learning",
    "nlp",
    "computer vision",
    "data structures",
    "algorithms",
    "design patterns",
    "agile",
    "scrum",
    "testing",
    "tdd",
    "unit testing",
    "integration testing",
}


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF using PyPDF2 (best-effort)."""
    try:
        from io import BytesIO
        from PyPDF2 import PdfReader

        reader = PdfReader(BytesIO(file_bytes))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages)
    except ImportError:
        logger.warning("PyPDF2 not installed; cannot parse PDF")
        return ""
    except Exception as e:
        logger.error(f"PDF parsing failed: {e}")
        return ""


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from a DOCX using python-docx (best-effort)."""
    try:
        from io import BytesIO
        from docx import Document

        doc = Document(BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs)
    except ImportError:
        logger.warning("python-docx not installed; cannot parse DOCX")
        return ""
    except Exception as e:
        logger.error(f"DOCX parsing failed: {e}")
        return ""


def extract_text(filename: str, file_bytes: bytes) -> str:
    """Dispatch to the correct parser based on filename extension."""
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    if lower.endswith((".docx", ".doc")):
        return extract_text_from_docx(file_bytes)
    # Plain text / markdown
    return file_bytes.decode("utf-8", errors="replace")


def _find_skills(text: str, skill_set: set[str]) -> list[str]:
    lower = text.lower()
    return sorted({skill for skill in skill_set if skill in lower})


def extract_years_of_experience(text: str) -> Optional[int]:
    """Heuristically extract years of experience from text."""
    patterns = [
        r"(\d+)\+?\s*years?\s*(?:of\s*)?(?:experience|exp|at|in|with|working)",
        r"(\d+)\s*yrs?\b",
        r"(\d+)\+?\s*years?\b",
    ]
    best: Optional[int] = None
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            try:
                value = int(match.group(1))
                if best is None or value > best:
                    best = value
            except ValueError:
                continue
    return best


def parse_resume(text: str) -> dict[str, Any]:
    """Parse resume text into structured metadata."""
    return {
        "skills": {
            "languages": _find_skills(text, PROGRAMMING_LANGUAGES),
            "frameworks": _find_skills(text, FRAMEWORKS),
            "cloud_devops": _find_skills(text, CLOUD_DEVOPS),
            "databases": _find_skills(text, DATABASES),
            "concepts": _find_skills(text, CONCEPTS),
        },
        "years_of_experience": extract_years_of_experience(text),
        "word_count": len(text.split()),
        "email": _extract_email(text),
    }


def parse_job_description(text: str) -> dict[str, Any]:
    """Parse a job description into structured metadata."""
    return {
        "required_skills": {
            "languages": _find_skills(text, PROGRAMMING_LANGUAGES),
            "frameworks": _find_skills(text, FRAMEWORKS),
            "cloud_devops": _find_skills(text, CLOUD_DEVOPS),
            "databases": _find_skills(text, DATABASES),
            "concepts": _find_skills(text, CONCEPTS),
        },
        "word_count": len(text.split()),
    }


def _extract_email(text: str) -> Optional[str]:
    match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    return match.group(0) if match else None


def compute_skill_gap(resume_meta: dict[str, Any], jd_meta: dict[str, Any]) -> dict[str, Any]:
    """Compare resume skills against a job description and surface gaps."""
    resume_skills = _flatten_skills(resume_meta.get("skills", {}))
    jd_skills = _flatten_skills(jd_meta.get("required_skills", {}))

    matched = sorted(resume_skills & jd_skills)
    missing = sorted(jd_skills - resume_skills)
    extra = sorted(resume_skills - jd_skills)

    total = len(jd_skills) or 1
    match_pct = round(100 * len(matched) / total, 1)

    return {
        "match_percentage": match_pct,
        "matched_skills": matched,
        "missing_skills": missing,
        "extra_skills": extra,
        "summary": (
            f"Your resume matches {match_pct}% of the required skills. "
            f"Key gaps: {', '.join(missing[:8]) if missing else 'none'}."
        ),
    }


def _flatten_skills(skills: dict[str, list[str]]) -> set[str]:
    flat: set[str] = set()
    for values in skills.values():
        flat.update(values)
    return flat
