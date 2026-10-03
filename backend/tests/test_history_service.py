"""Tests for the history tracking service."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import QuestionHistory
from services.history_service import get_user_history, record_action


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


class TestRecordAction:
    def test_record_valid_action(self, db):
        entry = record_action(db, action="viewed", user_id=1, question_id=5)
        assert entry is not None
        assert entry.action == "viewed"
        assert entry.user_id == 1
        assert entry.question_id == 5

    def test_record_action_with_context(self, db):
        entry = record_action(db, action="generated", user_id=1, context={"job_title": "SWE", "count": 3})
        assert entry.context == {"job_title": "SWE", "count": 3}

    def test_record_invalid_action_returns_none(self, db):
        assert record_action(db, action="invalid_action") is None
        assert db.query(QuestionHistory).count() == 0

    def test_record_action_failure_returns_none(self, db, monkeypatch):
        def failing_add(obj):
            raise RuntimeError("db broken")

        monkeypatch.setattr(db, "add", failing_add)
        assert record_action(db, action="viewed") is None

    def test_record_action_anonymous(self, db):
        entry = record_action(db, action="viewed")
        assert entry is not None
        assert entry.user_id is None


class TestGetUserHistory:
    def _seed(self, db):
        for action in ("viewed", "created", "viewed", "rated"):
            record_action(db, action=action, user_id=1)
        record_action(db, action="viewed", user_id=2)

    def test_get_history_all(self, db):
        self._seed(db)
        history = get_user_history(db, user_id=1)
        assert len(history) == 4

    def test_get_history_filter_by_action(self, db):
        self._seed(db)
        history = get_user_history(db, user_id=1, action="created")
        assert len(history) == 1
        assert history[0].action == "created"

    def test_get_history_limit(self, db):
        self._seed(db)
        history = get_user_history(db, user_id=1, limit=2)
        assert len(history) == 2

    def test_get_history_contains_all_actions(self, db):
        self._seed(db)
        history = get_user_history(db, user_id=1)
        actions = {h.action for h in history}
        assert actions == {"viewed", "created", "rated"}

    def test_get_history_other_user_excluded(self, db):
        self._seed(db)
        history = get_user_history(db, user_id=2)
        assert len(history) == 1
