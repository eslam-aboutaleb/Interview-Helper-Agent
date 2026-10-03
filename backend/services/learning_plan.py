"""Personalized study plans built from skill gaps and weak evaluation areas.

The plan is generated LLM-first: when an LLM provider is configured the
collected signals (resume-vs-JD skill gaps, weakest question types, the
question library) are turned into a plan by the model. Without a key — or
when the model fails or returns unusable JSON — the same signals feed a
deterministic rule-based plan, so the endpoint always answers.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from models import AnswerEvaluation, InterviewSession, Question, UserDocument
from services import document_service
from services.llm_service import LLMService

logger = logging.getLogger(__name__)

# Maximum number of topics surfaced by the heuristic plan, so a user with a
# large skill gap still gets a plan they can realistically work through.
MAX_SKILL_TOPICS = 5
MAX_QUESTIONS_PER_TOPIC = 5
MAX_PLAN_ITEMS = 8

# An average score at or below this value marks a question type as weak.
WEAK_SCORE_THRESHOLD = 6.0

# Hours estimated per study item, derived from how weak the area is.
HOURS_FOR_HIGH_PRIORITY = 4.0
HOURS_FOR_MEDIUM_PRIORITY = 2.5
HOURS_FOR_LOW_PRIORITY = 1.5

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}

PRIORITY_BY_SCORE = (
    # (upper bound of the average score, priority, estimated hours)
    (4.0, "high", HOURS_FOR_HIGH_PRIORITY),
    (WEAK_SCORE_THRESHOLD, "medium", HOURS_FOR_MEDIUM_PRIORITY),
    (10.0, "low", HOURS_FOR_LOW_PRIORITY),
)

QUESTION_TYPE_LABELS = {
    "technical": "Technical depth",
    "behavioral": "Behavioral storytelling",
    "mixed": "Mixed interview practice",
}


def collect_signals(db: Session, user_id: int) -> Dict[str, Any]:
    """Gather the raw inputs a learning plan is built from.

    Args:
        db: Database session.
        user_id: The user the plan is generated for.

    Returns:
        A dict with the latest resume/JD skill gap (or empty lists), the
        per-question-type average evaluation scores, and the question
        library summaries available for recommendations.
    """
    latest_resume = (
        db.query(UserDocument)
        .filter(UserDocument.user_id == user_id, UserDocument.document_type == "resume")
        .order_by(UserDocument.created_at.desc(), UserDocument.id.desc())
        .first()
    )
    latest_jd = (
        db.query(UserDocument)
        .filter(UserDocument.user_id == user_id, UserDocument.document_type == "jd")
        .order_by(UserDocument.created_at.desc(), UserDocument.id.desc())
        .first()
    )

    skill_gap: Dict[str, Any] = {"match_percentage": None, "missing_skills": [], "matched_skills": []}
    if latest_resume is not None and latest_jd is not None:
        resume_meta = latest_resume.parsed_metadata or document_service.parse_resume(latest_resume.content_text)
        jd_meta = latest_jd.parsed_metadata or document_service.parse_job_description(latest_jd.content_text)
        skill_gap = document_service.compute_skill_gap(resume_meta, jd_meta)

    # Weakest question types: average the overall score of every evaluation
    # the user received, grouped by the type of the session the answers came
    # from (the session type is the question type the session asked).
    rows = (
        db.query(
            InterviewSession.session_type,
            func.avg(AnswerEvaluation.overall_score),
            func.count(AnswerEvaluation.id),
        )
        .join(AnswerEvaluation, AnswerEvaluation.session_id == InterviewSession.id)
        .filter(AnswerEvaluation.user_id == user_id)
        .group_by(InterviewSession.session_type)
        .all()
    )
    weak_areas = [
        {
            "question_type": question_type,
            "average_score": round(float(average), 2) if average is not None else None,
            "sample_size": int(count),
        }
        for question_type, average, count in rows
        if question_type
    ]
    weak_areas.sort(key=lambda area: (area["average_score"] if area["average_score"] is not None else 0.0))

    # A small sample of the library so the LLM can only recommend real IDs.
    library = (
        db.query(Question.id, Question.question_text, Question.question_type, Question.difficulty, Question.tags)
        .order_by(Question.id)
        .limit(50)
        .all()
    )
    library_summaries = [
        {
            "id": question_id,
            "question_text": question_text,
            "question_type": question_type,
            "difficulty": difficulty,
            "tags": tags,
        }
        for question_id, question_text, question_type, difficulty, tags in library
    ]

    return {
        "skill_gap": skill_gap,
        "weak_areas": weak_areas,
        "library": library_summaries,
    }


def _priority_for_score(average_score: Optional[float]) -> Dict[str, Any]:
    """Map an average evaluation score to a priority and an hour estimate."""
    score = average_score if average_score is not None else 0.0
    for upper_bound, priority, hours in PRIORITY_BY_SCORE:
        if score <= upper_bound:
            return {"priority": priority, "estimated_hours": hours}
    return {"priority": "low", "estimated_hours": HOURS_FOR_LOW_PRIORITY}


def find_questions_for_topic(db: Session, topic: str, question_type: Optional[str] = None) -> List[int]:
    """Return IDs of questions that mention ``topic`` (tag or question text).

    Args:
        db: Database session.
        topic: Skill or topic name, e.g. ``kubernetes``.
        question_type: Optional question type to restrict the search to.

    Returns:
        At most ``MAX_QUESTIONS_PER_TOPIC`` question IDs, lowest ID first so
        the result is deterministic.
    """
    cleaned = (topic or "").strip()
    if not cleaned:
        return []

    pattern = f"%{cleaned.lower()}%"
    query = db.query(Question.id).filter(
        or_(
            func.lower(Question.tags).like(pattern),
            func.lower(Question.question_text).like(pattern),
        )
    )
    if question_type:
        query = query.filter(Question.question_type == question_type)
    return [row[0] for row in query.order_by(Question.id).limit(MAX_QUESTIONS_PER_TOPIC).all()]


def build_heuristic_plan(db: Session, signals: Dict[str, Any]) -> Dict[str, Any]:
    """Build a deterministic, rule-based plan from the collected signals.

    Args:
        db: Database session, used to match library questions to topics.
        signals: Output of :func:`collect_signals`.

    Returns:
        A plan dict with the same shape as the LLM plan.
    """
    items: List[Dict[str, Any]] = []
    skill_gap = signals.get("skill_gap") or {}
    missing_skills = list(skill_gap.get("missing_skills") or [])

    for area in signals.get("weak_areas") or []:
        average_score = area.get("average_score")
        # Areas the user already scores well on are noise on a study plan.
        if average_score is not None and average_score > WEAK_SCORE_THRESHOLD:
            continue
        severity = _priority_for_score(average_score)
        question_type = area.get("question_type") or "mixed"
        label = QUESTION_TYPE_LABELS.get(question_type, question_type.title())
        score_text = "n/a" if average_score is None else f"{average_score}/10"
        items.append(
            {
                "topic": label,
                "reason": (
                    f"Your average score on {question_type} questions is {score_text} "
                    f"across {area.get('sample_size', 0)} evaluated answers."
                ),
                "recommended_question_ids": find_questions_for_topic(db, question_type, question_type),
                "priority": severity["priority"],
                "estimated_hours": severity["estimated_hours"],
            }
        )

    match_percentage = skill_gap.get("match_percentage")
    for index, skill in enumerate(missing_skills[:MAX_SKILL_TOPICS]):
        # Missing skills that the resume/JD gap flags are the highest-value
        # work, so they outrank the weaker question types.
        priority = "high" if index == 0 else "medium"
        reason = "Required by the job description but missing from your resume."
        if match_percentage is not None:
            reason = f"{reason} Overall skill match is {match_percentage}%."
        items.append(
            {
                "topic": skill,
                "reason": reason,
                "recommended_question_ids": find_questions_for_topic(db, skill),
                "priority": priority,
                "estimated_hours": HOURS_FOR_HIGH_PRIORITY if priority == "high" else HOURS_FOR_MEDIUM_PRIORITY,
            }
        )

    items.sort(key=lambda item: PRIORITY_ORDER.get(item["priority"], PRIORITY_ORDER["medium"]))
    items = items[:MAX_PLAN_ITEMS]

    if not items:
        summary = (
            "No study areas need work yet. Upload a resume and a job description, or run a mock "
            "interview, so the plan can be built from your skill gaps and evaluation scores."
        )
    else:
        summary = (
            f"Focus on {items[0]['topic']} first, then work through the remaining "
            f"{len(items) - 1} topic(s) in priority order."
        )

    return {
        "summary": summary,
        "items": items,
        "source": "heuristic",
        "skill_gap": skill_gap,
        "weak_areas": signals.get("weak_areas") or [],
    }


def build_prompt(signals: Dict[str, Any]) -> str:
    """Build the strict-JSON prompt describing the candidate's situation."""
    skill_gap = signals.get("skill_gap") or {}
    match_percentage = skill_gap.get("match_percentage")
    match_text = "unknown" if match_percentage is None else f"{match_percentage}%"
    weak_lines = (
        "\n".join(
            f"- {area['question_type']}: average {area['average_score']}/10 over {area['sample_size']} answers"
            for area in (signals.get("weak_areas") or [])
        )
        or "- no mock-interview evaluations recorded yet"
    )
    library_lines = (
        "\n".join(
            f"- id={entry['id']} [{entry['question_type']}/difficulty {entry['difficulty']}] {entry['question_text']}"
            for entry in (signals.get("library") or [])
        )
        or "- the question library is empty"
    )

    return f"""You are an interview coach building a study plan for a candidate.

Signals collected from the platform:
- Skill match against the job description: {match_text}
- Missing skills: {", ".join(skill_gap.get("missing_skills") or []) or "none detected"}
- Weakest question types:
{weak_lines}

Questions available in the library (recommend these IDs only):
{library_lines}

Produce at most {MAX_PLAN_ITEMS} study items, most important first. Base every item on
the signals above and only use question IDs that appear in the library.

Return ONLY a JSON object with this structure and no other text:
{{
  "summary": "one or two sentences describing the plan",
  "items": [
    {{
      "topic": "short topic name",
      "reason": "why this topic matters for this candidate",
      "recommended_question_ids": [<question id>, ...],
      "priority": "one of: high, medium, low",
      "estimated_hours": <number of hours>
    }}
  ]
}}
"""


def _coerce_items(raw_items: Any) -> List[Dict[str, Any]]:
    """Normalize the LLM's ``items`` list into plan items.

    Malformed entries are dropped rather than failing the whole plan: the
    endpoint must always answer with something usable.
    """
    if not isinstance(raw_items, list):
        return []

    items: List[Dict[str, Any]] = []
    for entry in raw_items:
        if not isinstance(entry, dict):
            continue
        topic = str(entry.get("topic") or "").strip()
        if not topic:
            continue

        question_ids = entry.get("recommended_question_ids")
        if not isinstance(question_ids, list):
            question_ids = []
        clean_ids: List[int] = []
        for value in question_ids:
            try:
                clean_ids.append(int(value))
            except (TypeError, ValueError):
                continue

        try:
            hours = float(entry.get("estimated_hours") or HOURS_FOR_MEDIUM_PRIORITY)
        except (TypeError, ValueError):
            hours = HOURS_FOR_MEDIUM_PRIORITY
        hours = round(min(max(hours, 0.5), 40.0), 1)

        priority = str(entry.get("priority") or "medium").strip().lower()
        if priority not in PRIORITY_ORDER:
            priority = "medium"

        items.append(
            {
                "topic": topic[:200],
                "reason": str(entry.get("reason") or "").strip()[:500],
                "recommended_question_ids": clean_ids,
                "priority": priority,
                "estimated_hours": hours,
            }
        )
    return items[:MAX_PLAN_ITEMS]


def _drop_unknown_question_ids(items: List[Dict[str, Any]], library: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Strip recommended IDs that are not in the question library."""
    known_ids = {entry["id"] for entry in library}
    for item in items:
        item["recommended_question_ids"] = [
            question_id for question_id in item["recommended_question_ids"] if question_id in known_ids
        ]
    return items


def build_llm_plan(llm_service: LLMService, signals: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Ask the LLM for a plan and normalize the response.

    Args:
        llm_service: A configured :class:`LLMService`.
        signals: Output of :func:`collect_signals`.

    Returns:
        The plan dict, or ``None`` when the model failed or returned nothing
        usable, in which case the caller falls back to the heuristic plan.
    """
    response = llm_service.complete(build_prompt(signals), temperature=0.4, max_tokens=2000)
    parsed = LLMService.parse_json(response)
    if not isinstance(parsed, dict):
        return None

    items = _coerce_items(parsed.get("items"))
    if not items:
        return None

    items = _drop_unknown_question_ids(items, signals.get("library") or [])
    summary = str(parsed.get("summary") or "").strip()

    return {
        "summary": summary[:500] or "Personalized learning plan.",
        "items": items,
        "source": "llm",
        "skill_gap": signals.get("skill_gap") or {},
        "weak_areas": signals.get("weak_areas") or [],
    }


def generate_learning_plan(db: Session, user_id: int, llm_service: Optional[LLMService] = None) -> Dict[str, Any]:
    """Generate a study plan for a user.

    Tries the LLM first when ``llm_service`` is provided, and always falls
    back to the deterministic heuristic plan when the LLM is unavailable or
    unusable.

    Args:
        db: Database session.
        user_id: The user the plan is generated for.
        llm_service: Optional configured LLM service.

    Returns:
        A plan dict with ``summary``, ``items``, ``source``, ``generated_at``,
        ``skill_match_percentage``, ``missing_skills`` and
        ``weak_question_types``.
    """
    signals = collect_signals(db, user_id)

    plan: Optional[Dict[str, Any]] = None
    if llm_service is not None:
        try:
            plan = build_llm_plan(llm_service, signals)
        except Exception as e:
            logger.warning(f"LLM learning plan failed, using heuristic plan: {e}")
            plan = None

    if plan is None:
        plan = build_heuristic_plan(db, signals)

    skill_gap = plan.get("skill_gap") or {}
    return {
        "summary": plan["summary"],
        "items": plan["items"],
        "source": plan["source"],
        "generated_at": datetime.now(timezone.utc),
        "skill_match_percentage": skill_gap.get("match_percentage"),
        "missing_skills": list(skill_gap.get("missing_skills") or []),
        "weak_question_types": list(plan.get("weak_areas") or []),
    }
