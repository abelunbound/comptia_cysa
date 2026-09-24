"""Session-scoped live Dash/Flask server for Playwright smoke tests."""

import os
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DEFAULT_TEST_DATABASE_URL = (
    "postgresql+psycopg2://cysa_test:cysa_test@127.0.0.1:5432/cysa_test"
)


def _test_database_url():
    return os.environ.get("TEST_DATABASE_URL") or DEFAULT_TEST_DATABASE_URL


def _free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="session")
def live_server():
    """Start gunicorn on isolated CI Postgres (not staging Cloud SQL)."""
    from tests.pg_seed import ensure_schema_and_one_question

    database_url = _test_database_url()
    os.environ["DATABASE_URL"] = database_url
    ensure_schema_and_one_question(database_url)

    port = _free_port()
    env = os.environ.copy()
    env["SECRET_KEY"] = os.environ.get("SECRET_KEY") or "e2e-playwright-secret-key"
    env["DATABASE_URL"] = database_url
    env["SESSION_COOKIE_SECURE"] = "false"
    env.pop("FLASK_DEBUG", None)

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "gunicorn",
            "--bind",
            f"127.0.0.1:{port}",
            "--workers",
            "1",
            "--timeout",
            "60",
            "app:server",
        ],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    deadline = time.time() + 30
    while time.time() < deadline:
        if proc.poll() is not None:
            output = proc.stdout.read().decode("utf-8", errors="replace") if proc.stdout else ""
            raise RuntimeError(f"gunicorn exited {proc.returncode}: {output}")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                break
        except OSError:
            time.sleep(0.2)
    else:
        proc.kill()
        output = proc.stdout.read().decode("utf-8", errors="replace") if proc.stdout else ""
        raise RuntimeError(f"gunicorn did not bind to {port}: {output}")

    yield {
        "base_url": f"http://127.0.0.1:{port}",
        "email": f"e2e-{uuid.uuid4().hex[:8]}@example.com",
        "password": "E2ePass123",
    }

    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
