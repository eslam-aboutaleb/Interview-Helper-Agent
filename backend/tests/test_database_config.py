"""Tests for database configuration and validation."""

import os
from unittest import mock

import pytest

import database
from database import (
    DatabaseConfigError,
    _get_database_url,
    _validate_database_url,
    _verify_database_connection,
    get_db,
)


class TestValidateDatabaseUrl:
    def test_missing_url_raises(self):
        with pytest.raises(DatabaseConfigError):
            _validate_database_url("")

    def test_unsupported_scheme(self):
        with pytest.raises(DatabaseConfigError):
            _validate_database_url("mongodb://localhost/db")

    def test_missing_host(self):
        with pytest.raises(DatabaseConfigError):
            _validate_database_url("postgresql:///dbname")

    def test_sqlite_without_host_ok(self):
        assert _validate_database_url("sqlite:///:memory:") == "sqlite:///:memory:"

    def test_valid_postgres_url(self):
        url = "postgresql://user:pass@localhost:5432/db"
        assert _validate_database_url(url) == url

    def test_mysql_scheme_accepted(self):
        url = "mysql://user:pass@localhost:3306/db"
        assert _validate_database_url(url) == url

    def test_invalid_url_format(self):
        with mock.patch("database.urlparse", side_effect=ValueError("bad")):
            with pytest.raises(DatabaseConfigError):
                _validate_database_url("not a url")

    def test_production_rejects_default_credentials(self):
        with mock.patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            with pytest.raises(DatabaseConfigError):
                _validate_database_url("postgresql://postgres:password@localhost/db")

    def test_production_rejects_password_localhost(self):
        with mock.patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            with pytest.raises(DatabaseConfigError):
                _validate_database_url("postgresql://password@localhost/db")

    def test_development_warns_on_default_credentials(self, caplog):
        with mock.patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            _validate_database_url("postgresql://postgres:password@localhost/db")
            assert any("test credentials" in r.message for r in caplog.records)

    def test_missing_password_warns(self, caplog):
        with mock.patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            _validate_database_url("postgresql://user@localhost/db")
            assert any("does not contain a password" in r.message for r in caplog.records)


class TestGetDatabaseUrl:
    def test_env_var_missing(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ.pop("DATABASE_URL", None)
            with pytest.raises(DatabaseConfigError):
                _get_database_url()

    def test_env_var_present(self):
        with mock.patch.dict(os.environ, {"DATABASE_URL": "sqlite:///:memory:"}):
            assert _get_database_url() == "sqlite:///:memory:"


class TestVerifyConnection:
    def test_verify_success(self):
        assert _verify_database_connection() is True

    def test_verify_operational_error(self):
        with mock.patch("database.engine.connect", side_effect=database.exc.OperationalError("x", {}, Exception())):
            with pytest.raises(DatabaseConfigError):
                _verify_database_connection()

    def test_verify_argument_error(self):
        with mock.patch("database.engine.connect", side_effect=database.exc.ArgumentError("x")):
            with pytest.raises(DatabaseConfigError):
                _verify_database_connection()

    def test_verify_unexpected_error(self):
        with mock.patch("database.engine.connect", side_effect=RuntimeError("x")):
            with pytest.raises(DatabaseConfigError):
                _verify_database_connection()


class TestGetDb:
    def test_get_db_yields_session(self):
        gen = get_db()
        session = next(gen)
        assert session is not None
        gen.close()

    def test_get_db_rolls_back_on_sqlalchemy_error(self):
        gen = get_db()
        next(gen)
        with pytest.raises(database.exc.SQLAlchemyError):
            gen.throw(database.exc.SQLAlchemyError("boom"))

    def test_get_db_rolls_back_on_unexpected_error(self):
        gen = get_db()
        next(gen)
        with pytest.raises(RuntimeError):
            gen.throw(RuntimeError("boom"))


class TestEngineConfiguration:
    def test_sqlite_uses_null_pool(self):
        assert database._pool_class_for_url("sqlite:///:memory:") is database.NullPool

    def test_server_database_uses_queue_pool(self):
        url = "postgresql://user:pass@localhost:5432/db"
        assert database._pool_class_for_url(url) is database.QueuePool

    def test_engine_pool_matches_configured_url(self):
        expected = database._pool_class_for_url(database.DATABASE_URL)
        assert isinstance(database.engine.pool, expected)

    def test_session_local_configured(self):
        assert database.SessionLocal is not None
        assert database.Base is not None
