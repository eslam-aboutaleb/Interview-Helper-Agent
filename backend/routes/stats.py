from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import AnswerEvaluation, Question, QuestionSet, User
from schemas import StatsResponse

router = APIRouter()

# Window sizes for the dashboard time series. The series are dense
# (zero-filled) so the charts never have to interpolate missing buckets.
SIGNUP_WINDOW_DAYS = 7
EVALUATION_WINDOW_DAYS = 7
TREND_WINDOW_WEEKS = 8
DIFFICULTY_LEVELS = (1, 2, 3, 4, 5)


def _day_bucket(column, dialect_name: str):
    """Day bucket expression for ``column`` on the given dialect.

    PostgreSQL truncates with ``date_trunc``; SQLite has no ``date_trunc``
    and uses ``strftime`` instead. The dialect is inspected per request so the
    same code path serves both the Postgres deployment and the SQLite tests.
    """
    if dialect_name.startswith("postgres"):
        return func.date_trunc("day", column)
    return func.strftime("%Y-%m-%d", column)


def _week_bucket(column, dialect_name: str):
    """Monday-anchored week bucket expression for ``column``.

    ``date_trunc('week', ...)`` yields the Monday of the ISO week on
    PostgreSQL. SQLite expresses the same thing with the ``weekday 0``
    modifier (advance to Sunday) followed by ``-6 days`` (back to Monday).
    """
    if dialect_name.startswith("postgres"):
        return func.date_trunc("week", column)
    return func.date(column, "weekday 0", "-6 days")


def _iso_date(value) -> str:
    """Normalize a bucket key to a ``YYYY-MM-DD`` string.

    ``date_trunc`` returns ``timestamptz`` on PostgreSQL while SQLite returns
    text, so both have to collapse to the same JSON representation.
    """
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)[:10]


def _utc_midnight(day: date) -> datetime:
    """Start of ``day`` in UTC, used as a bucketing cutoff."""
    return datetime(day.year, day.month, day.day, tzinfo=timezone.utc)


def _recent_days(today: date, days: int) -> List[str]:
    """The last ``days`` calendar days ending on ``today``, oldest first."""
    return [(today - timedelta(days=offset)).isoformat() for offset in range(days - 1, -1, -1)]


def _recent_week_starts(today: date, weeks: int) -> List[str]:
    """The last ``weeks`` Monday-anchored ISO weeks, oldest first."""
    current_monday = today - timedelta(days=today.weekday())
    return [(current_monday - timedelta(days=7 * offset)).isoformat() for offset in range(weeks - 1, -1, -1)]


def _counts_by_bucket(db: Session, model, timestamp_column, bucket, cutoff: datetime) -> Dict[str, int]:
    """Group ``model`` rows by ``bucket`` and return ``YYYY-MM-DD`` -> count."""
    rows = (
        db.query(bucket.label("bucket"), func.count(model.id)).filter(timestamp_column >= cutoff).group_by(bucket).all()
    )
    return {_iso_date(key): int(count) for key, count in rows}


def _scores_by_bucket(db: Session, bucket, cutoff: datetime) -> Dict[str, Tuple[Optional[float], int]]:
    """Group evaluations by ``bucket`` into ``YYYY-MM-DD`` -> (mean score, count).

    The mean is ``None`` for buckets that produced no rows and is rounded to
    two decimals so the JSON payload stays stable.
    """
    rows = (
        db.query(
            bucket.label("bucket"),
            func.avg(AnswerEvaluation.overall_score),
            func.count(AnswerEvaluation.id),
        )
        .filter(AnswerEvaluation.created_at >= cutoff)
        .group_by(bucket)
        .all()
    )
    return {
        _iso_date(key): (round(float(average), 2) if average is not None else None, int(count))
        for key, average, count in rows
    }


def _score_series(keys: List[str], rows: Dict[str, Tuple[Optional[float], int]], key_name: str) -> List[dict]:
    """Build a dense score series over ``keys``, filling gaps with zero counts."""
    series = []
    for key in keys:
        average_score, count = rows.get(key, (None, 0))
        series.append({key_name: key, "average_score": average_score, "count": count})
    return series


@router.get("/", response_model=StatsResponse, status_code=status.HTTP_200_OK)
async def get_stats(db: Session = Depends(get_db)):
    """Get comprehensive platform statistics

    Retrieves aggregated statistics including total questions, breakdown by type and job title,
    average difficulty, flagged questions count, and total question sets, plus the time series
    that back the dashboard charts: daily signups, daily evaluations, the question difficulty
    distribution and the weekly average score trend.

    Args:
        db: Database session dependency

    Returns:
        StatsResponse object containing all platform statistics

    Raises:
        HTTPException 500: If database query or aggregation fails
    """
    try:
        dialect_name = db.bind.dialect.name
        today = datetime.now(timezone.utc).date()

        # Total questions
        total_questions = db.query(func.count(Question.id)).scalar() or 0

        # Questions by type
        type_stats = db.query(Question.question_type, func.count(Question.id)).group_by(Question.question_type).all()

        questions_by_type = {type_name: count for type_name, count in type_stats if type_name}

        # Questions by job title
        job_stats = db.query(Question.job_title, func.count(Question.id)).group_by(Question.job_title).all()

        questions_by_job_title = {job_title: count for job_title, count in job_stats if job_title}

        # Average difficulty
        avg_difficulty = db.query(func.avg(Question.difficulty)).scalar() or 0.0

        # Flagged questions
        flagged_count = db.query(func.count(Question.id)).filter(Question.is_flagged).scalar() or 0

        # Total question sets
        total_sets = db.query(func.count(QuestionSet.id)).scalar() or 0

        # Daily signups over the last 7 days
        signup_cutoff = _utc_midnight(today - timedelta(days=SIGNUP_WINDOW_DAYS - 1))
        signup_rows = _counts_by_bucket(
            db, User, User.created_at, _day_bucket(User.created_at, dialect_name), signup_cutoff
        )
        signups_last_7_days = [
            {"date": day, "count": signup_rows.get(day, 0)} for day in _recent_days(today, SIGNUP_WINDOW_DAYS)
        ]

        # Daily evaluation volume and mean overall score over the last 7 days
        evaluation_cutoff = _utc_midnight(today - timedelta(days=EVALUATION_WINDOW_DAYS - 1))
        evaluation_day_rows = _scores_by_bucket(
            db, _day_bucket(AnswerEvaluation.created_at, dialect_name), evaluation_cutoff
        )
        evaluations_last_7_days = _score_series(
            _recent_days(today, EVALUATION_WINDOW_DAYS), evaluation_day_rows, "date"
        )

        # Question count per difficulty level, always one entry per level 1-5
        difficulty_rows = dict(
            db.query(Question.difficulty, func.count(Question.id)).group_by(Question.difficulty).all()
        )
        difficulty_distribution = [
            {"difficulty": level, "count": int(difficulty_rows.get(level, 0))} for level in DIFFICULTY_LEVELS
        ]

        # Weekly mean overall score over the last 8 ISO weeks. Weeks without
        # evaluations keep a null score so the chart can show the gap, and the
        # whole series is dropped when the window holds no evaluations at all.
        week_keys = _recent_week_starts(today, TREND_WINDOW_WEEKS)
        trend_cutoff = _utc_midnight(date.fromisoformat(week_keys[0]))
        trend_rows = _scores_by_bucket(db, _week_bucket(AnswerEvaluation.created_at, dialect_name), trend_cutoff)
        average_score_trend = _score_series(week_keys, trend_rows, "week_start")
        if not any(point["count"] for point in average_score_trend):
            average_score_trend = []

        return StatsResponse(
            total_questions=total_questions,
            questions_by_type=questions_by_type,
            questions_by_job_title=questions_by_job_title,
            average_difficulty=float(avg_difficulty),
            flagged_questions=flagged_count,
            total_question_sets=total_sets,
            signups_last_7_days=signups_last_7_days,
            evaluations_last_7_days=evaluations_last_7_days,
            difficulty_distribution=difficulty_distribution,
            average_score_trend=average_score_trend,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to retrieve statistics: {str(e)}"
        )
