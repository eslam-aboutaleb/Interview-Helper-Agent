"""Alembic environment configuration.

This module reuses the application's engine (from ``database.py``) so
migrations and the running app always share a single connection-config
path. The ``sqlalchemy.url`` in ``alembic.ini`` is intentionally ignored
— the engine is authoritative.
"""

from alembic import context

from database import engine
from models import Base

# Import every model module so all mapped tables are registered on
# Base.metadata before autogenerate compares the schema.
import models  # noqa: F401

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL to stdout)."""
    url = engine.url.render_as_string(hide_password=False)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (live DB connection)."""
    # Reuse the application engine directly instead of building a second
    # engine from alembic.ini's sqlalchemy.url.
    connectable = engine

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
