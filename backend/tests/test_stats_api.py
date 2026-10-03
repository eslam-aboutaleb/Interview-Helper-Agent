"""Tests for the stats endpoint."""

from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app
from models import AnswerEvaluation, InterviewSession, Question, QuestionSet, User
from routes.stats import _day_bucket, _iso_date, _recent_days, _recent_week_starts, _week_bucket


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


def _today() -> date:
    """Current UTC date, matching the buckets the endpoint builds."""
    return datetime.now(timezone.utc).date()


def _expected_days(days: int):
    """Last ``days`` UTC calendar days ending today, oldest first."""
    today = _today()
    return [(today - timedelta(days=offset)).isoformat() for offset in range(days - 1, -1, -1)]


def _expected_week_starts(weeks: int):
    """Last ``weeks`` Monday-anchored ISO weeks, oldest first."""
    monday = _today() - timedelta(days=_today().weekday())
    return [(monday - timedelta(days=7 * offset)).isoformat() for offset in range(weeks - 1, -1, -1)]


def _at(day: date, hour: int = 12) -> datetime:
    """A UTC timestamp at ``hour`` on ``day``."""
    return datetime(day.year, day.month, day.day, hour, tzinfo=timezone.utc)


def _sql(expression, dialect) -> str:
    """Compile ``expression`` to SQL for ``dialect`` with inline literals."""
    return str(expression.compile(dialect=dialect, compile_kwargs={"literal_binds": True}))


class TestBucketingHelpers:
    """The bucket helpers branch on the dialect, so both branches are asserted here.

    The suite itself runs on SQLite; these checks compile against the PostgreSQL
    dialect without a server so the production SQL is still covered.
    """

    def test_day_bucket_uses_date_trunc_on_postgres(self):
        sql = _sql(_day_bucket(AnswerEvaluation.created_at, "postgresql"), postgresql.dialect())
        assert "date_trunc('day', answer_evaluations.created_at)" in sql

    def test_day_bucket_uses_strftime_on_sqlite(self):
        sql = _sql(_day_bucket(AnswerEvaluation.created_at, "sqlite"), sqlite.dialect())
        assert "strftime('%Y-%m-%d', answer_evaluations.created_at)" in sql

    def test_week_bucket_uses_date_trunc_on_postgres(self):
        sql = _sql(_week_bucket(AnswerEvaluation.created_at, "postgresql"), postgresql.dialect())
        assert "date_trunc('week', answer_evaluations.created_at)" in sql

    def test_week_bucket_monday_anchor_on_sqlite(self):
        sql = _sql(_week_bucket(AnswerEvaluation.created_at, "sqlite"), sqlite.dialect())
        assert "date(answer_evaluations.created_at, 'weekday 0', '-6 days')" in sql

    def test_day_bucket_treats_mysql_like_dialects_as_sqlite(self):
        sql = _sql(_day_bucket(User.created_at, "mysql"), sqlite.dialect())
        assert "strftime('%Y-%m-%d'" in sql


class TestIsoDate:
    def test_normalizes_datetime(self):
        # A PostgreSQL timestamptz bucket result.
        assert _iso_date(datetime(2026, 10, 3, 17, 45, tzinfo=timezone.utc)) == "2026-10-03"

    def test_normalizes_date(self):
        assert _iso_date(date(2026, 10, 3)) == "2026-10-03"

    def test_normalizes_sqlite_text(self):
        # SQLite returns the text form of the bucket expression.
        assert _iso_date("2026-10-03") == "2026-10-03"
        assert _iso_date("2026-10-03 00:00:00") == "2026-10-03"


class TestWindowHelpers:
    def test_recent_days_is_ascending_and_ends_today(self):
        today = date(2026, 10, 3)
        assert _recent_days(today, 7) == [
            "2026-09-27",
            "2026-09-28",
            "2026-09-29",
            "2026-09-30",
            "2026-10-01",
            "2026-10-02",
            "2026-10-03",
        ]

    def test_recent_week_starts_are_mondays_seven_days_apart(self):
        # 2026-10-03 is a Saturday, so the current week starts on 2026-09-28.
        assert _recent_week_starts(date(2026, 10, 3), 8) == [
            "2026-08-10",
            "2026-08-17",
            "2026-08-24",
            "2026-08-31",
            "2026-09-07",
            "2026-09-14",
            "2026-09-21",
            "2026-09-28",
        ]

    def test_recent_week_starts_when_today_is_monday(self):
        assert _recent_week_starts(date(2026, 9, 28), 2) == ["2026-09-21", "2026-09-28"]


def _add_user(db, email: str, created_at: datetime) -> User:
    user = User(email=email, hashed_password="x", created_at=created_at)
    db.add(user)
    db.commit()
    return user


def _add_evaluation(db, user: User, session: InterviewSession, score: float, created_at: datetime):
    evaluation = AnswerEvaluation(
        session_id=session.id,
        user_id=user.id,
        overall_score=score,
        technical_score=score,
        communication_score=score,
        completeness_score=score,
        created_at=created_at,
    )
    db.add(evaluation)
    db.commit()
    return evaluation


def _add_question(db, difficulty: int, index: int = 0):
    db.add(
        Question(
            job_title="SWE",
            question_text=f"Explain a concurrency primitive in detail #{index}",
            question_type="technical",
            difficulty=difficulty,
        )
    )
    db.commit()


class TestStats:
    def test_stats_empty(self, client):
        response = client.get("/api/stats/")
        assert response.status_code == 200
        data = response.json()
        assert data["total_questions"] == 0
        assert data["questions_by_type"] == {}
        assert data["questions_by_job_title"] == {}
        assert data["average_difficulty"] == 0.0
        assert data["flagged_questions"] == 0
        assert data["total_question_sets"] == 0

    def test_stats_with_data(self, client, db_session):
        db_session.add_all(
            [
                Question(
                    job_title="SWE",
                    question_text="Explain how the reactor pattern handles concurrency?",
                    question_type="technical",
                    difficulty=4,
                    is_flagged=False,
                ),
                Question(
                    job_title="SWE",
                    question_text="Tell me about a time you led a team through a conflict?",
                    question_type="behavioral",
                    difficulty=2,
                    is_flagged=True,
                ),
                Question(
                    job_title="PM",
                    question_text="How do you prioritize competing roadmap priorities?",
                    question_type="behavioral",
                    difficulty=3,
                    is_flagged=False,
                ),
            ]
        )
        db_session.add(
            QuestionSet(
                name="System Design",
                job_title="SWE",
                question_ids="[1, 2]",
            )
        )
        db_session.commit()

        response = client.get("/api/stats/")
        assert response.status_code == 200
        data = response.json()
        assert data["total_questions"] == 3
        assert data["questions_by_type"] == {"technical": 1, "behavioral": 2}
        assert data["questions_by_job_title"] == {"SWE": 2, "PM": 1}
        assert data["average_difficulty"] == pytest.approx(3.0)
        assert data["flagged_questions"] == 1
        assert data["total_question_sets"] == 1

        # The difficulty distribution always reports all five levels.
        assert data["difficulty_distribution"] == [
            {"difficulty": 1, "count": 0},
            {"difficulty": 2, "count": 1},
            {"difficulty": 3, "count": 1},
            {"difficulty": 4, "count": 1},
            {"difficulty": 5, "count": 0},
        ]

    def test_stats_query_error(self, client, db_session, monkeypatch):
        def failing_query(*args, **kwargs):
            raise RuntimeError("connection lost")

        monkeypatch.setattr(db_session, "query", failing_query)
        response = client.get("/api/stats/")
        assert response.status_code == 500


class TestStatsEmptySeries:
    """An empty database must still return well formed, zero-filled series."""

    def test_daily_series_are_zero_filled(self, client):
        response = client.get("/api/stats/")
        assert response.status_code == 200
        data = response.json()

        expected_days = _expected_days(7)
        assert [point["date"] for point in data["signups_last_7_days"]] == expected_days
        assert [point["count"] for point in data["signups_last_7_days"]] == [0] * 7

        assert [point["date"] for point in data["evaluations_last_7_days"]] == expected_days
        assert [point["count"] for point in data["evaluations_last_7_days"]] == [0] * 7
        assert [point["average_score"] for point in data["evaluations_last_7_days"]] == [None] * 7

    def test_difficulty_distribution_covers_every_level(self, client):
        data = client.get("/api/stats/").json()
        assert data["difficulty_distribution"] == [{"difficulty": level, "count": 0} for level in range(1, 6)]

    def test_score_trend_is_empty_without_evaluations(self, client):
        data = client.get("/api/stats/").json()
        assert data["average_score_trend"] == []


class TestSignupsSeries:
    def test_buckets_daily_signups(self, client, db_session):
        today = _today()
        _add_user(db_session, "today-a@example.com", _at(today, 9))
        _add_user(db_session, "today-b@example.com", _at(today, 23))
        _add_user(db_session, "two-ago@example.com", _at(today - timedelta(days=2), 10))
        _add_user(db_session, "six-ago@example.com", _at(today - timedelta(days=6), 0))
        _add_user(db_session, "three-ago-b@example.com", _at(today - timedelta(days=3), 15))
        _add_user(db_session, "three-ago-a@example.com", _at(today - timedelta(days=3), 16))

        data = client.get("/api/stats/").json()
        counts = {point["date"]: point["count"] for point in data["signups_last_7_days"]}
        assert counts == {
            (today - timedelta(days=6)).isoformat(): 1,
            (today - timedelta(days=5)).isoformat(): 0,
            (today - timedelta(days=4)).isoformat(): 0,
            (today - timedelta(days=3)).isoformat(): 2,
            (today - timedelta(days=2)).isoformat(): 1,
            (today - timedelta(days=1)).isoformat(): 0,
            today.isoformat(): 2,
        }

    def test_signups_outside_window_are_excluded(self, client, db_session):
        today = _today()
        _add_user(db_session, "just-inside@example.com", _at(today - timedelta(days=6)))
        _add_user(db_session, "just-outside@example.com", _at(today - timedelta(days=7), 23))

        data = client.get("/api/stats/").json()
        counts = {point["date"]: point["count"] for point in data["signups_last_7_days"]}
        assert counts[(today - timedelta(days=6)).isoformat()] == 1
        assert sum(point["count"] for point in data["signups_last_7_days"]) == 1


class TestEvaluationsSeries:
    @pytest.fixture()
    def seeded(self, db_session):
        user = _add_user(db_session, "candidate@example.com", _at(_today()))
        session = InterviewSession(
            user_id=user.id,
            job_title="SWE",
            session_type="technical",
            difficulty=3,
            target_difficulty=3,
            max_turns=7,
            status="completed",
        )
        db_session.add(session)
        db_session.commit()
        return db_session, user, session

    def test_buckets_evaluations_with_mean_score(self, client, seeded):
        db_session, user, session = seeded
        today = _today()
        _add_evaluation(db_session, user, session, 6.0, _at(today, 10))
        _add_evaluation(db_session, user, session, 8.0, _at(today, 11))
        _add_evaluation(db_session, user, session, 5.0, _at(today - timedelta(days=3), 9))

        data = client.get("/api/stats/").json()
        by_date = {point["date"]: point for point in data["evaluations_last_7_days"]}
        assert by_date[today.isoformat()] == {"date": today.isoformat(), "average_score": 7.0, "count": 2}
        three_ago = (today - timedelta(days=3)).isoformat()
        assert by_date[three_ago] == {"date": three_ago, "average_score": 5.0, "count": 1}
        # Untouched days stay zero filled with a null mean.
        assert by_date[(today - timedelta(days=1)).isoformat()] == {
            "date": (today - timedelta(days=1)).isoformat(),
            "average_score": None,
            "count": 0,
        }

    def test_scores_are_rounded(self, client, seeded):
        db_session, user, session = seeded
        today = _today()
        _add_evaluation(db_session, user, session, 7.3333, _at(today, 10))
        _add_evaluation(db_session, user, session, 7.6666, _at(today, 11))

        data = client.get("/api/stats/").json()
        by_date = {point["date"]: point for point in data["evaluations_last_7_days"]}
        assert by_date[today.isoformat()]["average_score"] == 7.5

    def test_evaluations_outside_window_are_excluded(self, client, seeded):
        db_session, user, session = seeded
        today = _today()
        _add_evaluation(db_session, user, session, 9.0, _at(today - timedelta(days=7), 22))

        data = client.get("/api/stats/").json()
        assert sum(point["count"] for point in data["evaluations_last_7_days"]) == 0


class TestDifficultyDistribution:
    def test_counts_per_level(self, client, db_session):
        for index, difficulty in enumerate([1, 1, 2, 3, 5, 5, 5]):
            _add_question(db_session, difficulty, index=index)

        data = client.get("/api/stats/").json()
        assert data["difficulty_distribution"] == [
            {"difficulty": 1, "count": 2},
            {"difficulty": 2, "count": 1},
            {"difficulty": 3, "count": 1},
            {"difficulty": 4, "count": 0},
            {"difficulty": 5, "count": 3},
        ]


class TestScoreTrend:
    def test_weeks_are_monday_anchored_and_ascending(self, client):
        data = client.get("/api/stats/").json()
        # No evaluations at all, so the series is omitted entirely.
        assert data["average_score_trend"] == []

    def test_aggregates_per_iso_week(self, client, db_session):
        today = _today()
        monday = today - timedelta(days=today.weekday())
        user = _add_user(db_session, "trend@example.com", _at(today))
        session = InterviewSession(
            user_id=user.id,
            job_title="SWE",
            session_type="mixed",
            difficulty=3,
            target_difficulty=3,
            max_turns=7,
            status="completed",
        )
        db_session.add(session)
        db_session.commit()

        # Wednesday of the previous week: two evaluations averaging 7.0.
        previous_week = monday - timedelta(days=7)
        _add_evaluation(db_session, user, session, 6.0, _at(previous_week + timedelta(days=2), 10))
        _add_evaluation(db_session, user, session, 8.0, _at(previous_week + timedelta(days=2), 11))
        # One evaluation today, in the current week.
        _add_evaluation(db_session, user, session, 4.0, _at(today, 9))
        # One far outside the 8 week window.
        _add_evaluation(db_session, user, session, 2.0, _at(monday - timedelta(days=60), 9))

        data = client.get("/api/stats/").json()
        trend = data["average_score_trend"]

        assert len(trend) == 8
        assert [point["week_start"] for point in trend] == _expected_week_starts(8)
        assert trend[-1]["week_start"] == monday.isoformat()
        # Every week start is a Monday and consecutive weeks are 7 days apart.
        for point in trend:
            assert date.fromisoformat(point["week_start"]).weekday() == 0
        starts = [date.fromisoformat(point["week_start"]) for point in trend]
        assert all((later - earlier).days == 7 for earlier, later in zip(starts, starts[1:]))

        # The out-of-window evaluation is not counted anywhere.
        assert sum(point["count"] for point in trend) == 3
        assert trend[6] == {"week_start": previous_week.isoformat(), "average_score": 7.0, "count": 2}
        assert trend[7]["count"] == 1
        assert trend[7]["average_score"] == 4.0

        # Weeks without evaluations keep a null mean so the chart shows a gap.
        assert [(point["count"], point["average_score"]) for point in trend[:6]] == [(0, None)] * 6

    def test_evaluations_older_than_the_window_drop_the_series(self, client, db_session):
        today = _today()
        monday = today - timedelta(days=today.weekday())
        user = _add_user(db_session, "stale@example.com", _at(today))
        session = InterviewSession(
            user_id=user.id,
            job_title="SWE",
            session_type="mixed",
            difficulty=3,
            target_difficulty=3,
            max_turns=7,
            status="completed",
        )
        db_session.add(session)
        db_session.commit()
        # Older than the eight week window (which starts 49 days before this Monday).
        _add_evaluation(db_session, user, session, 8.5, _at(monday - timedelta(days=55), 9))

        data = client.get("/api/stats/").json()
        assert data["average_score_trend"] == []
