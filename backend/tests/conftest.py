"""Pytest configuration and shared fixtures."""

import os
import sys
from pathlib import Path

# Ensure the backend directory is importable when running `pytest`.
sys.path.insert(0, str(Path(__file__).parent.parent))

# Provide a default DATABASE_URL so importing `database` during test
# collection does not require a real PostgreSQL instance. Tests that need
# a real connection use their own in-memory SQLite engine.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("GEMINI_API_KEY", "test-key")
