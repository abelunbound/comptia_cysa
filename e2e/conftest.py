"""Session-scoped live Dash/Flask server for Playwright smoke tests."""

import os
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="session")
def live_server():
    """Start gunicorn on a free port with a throwaway SQLite database."""
    port = _free_port()
    db_path = Path(tempfile.gettempdir()) / f"cysa_e2e_{uuid.uuid4().hex}.db"
    env = os.environ.copy()
    env["SECRET_KEY"] = os.environ.get("SECRET_KEY") or "e2e-playwright-secret-key"
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
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
    db_path.unlink(missing_ok=True)
