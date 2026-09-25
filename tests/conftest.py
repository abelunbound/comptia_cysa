"""pytest configuration: isolated CI Postgres, never staging Cloud SQL."""

import os
import sys
from pathlib import Path

import pytest

workspace_root = Path(__file__).parent.parent
sys.path.insert(0, str(workspace_root))

DEFAULT_TEST_DATABASE_URL = (
    "postgresql+psycopg2://cysa_test:cysa_test@127.0.0.1:5432/cysa_test"
)
# Always isolate tests — do not inherit a developer's staging DATABASE_URL.
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or DEFAULT_TEST_DATABASE_URL
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-client")

from auth import db  # noqa: E402
from tests.pg_seed import ensure_schema_and_one_question  # noqa: E402

ensure_schema_and_one_question(os.environ["DATABASE_URL"])

# Fail DDL that is waiting on another session instead of blocking the job.
TEST_ENGINE_OPTIONS = {
    "pool_pre_ping": True,
    "connect_args": {"options": "-c lock_timeout=5s"},
}


def reset_schema():
    """Drop tables only after releasing this test's session connection."""
    db.session.remove()
    db.drop_all()


@pytest.fixture
def dash_app():
    """Import the Dash app only when a test needs it, after reseeding questions."""
    ensure_schema_and_one_question(os.environ["DATABASE_URL"])
    from app import app as dash_application

    return dash_application
