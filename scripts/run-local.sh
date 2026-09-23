#!/usr/bin/env bash
# Start the Dash app against Cloud SQL via Auth Proxy (no SQLite).
# Usage (from repo root):
#   export DATABASE_URL='postgresql+psycopg2://cysa_app:<PASSWORD>@127.0.0.1:5432/cybersecuritylab'
#   ./scripts/run-local.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "error: DATABASE_URL is required (PostgreSQL)." >&2
  echo "  cloud-sql-proxy bankpassport-be:us-central1:bankpassport --port=5432" >&2
  echo "  export DATABASE_URL='postgresql+psycopg2://cysa_app:<PASSWORD>@127.0.0.1:5432/cybersecuritylab'" >&2
  exit 1
fi

lowered="$(printf '%s' "$DATABASE_URL" | tr '[:upper:]' '[:lower:]')"
if [[ "$lowered" == sqlite* ]]; then
  echo "error: SQLite is not supported." >&2
  exit 1
fi
if [[ "$lowered" != postgresql* ]]; then
  echo "error: DATABASE_URL must be postgresql:// or postgresql+psycopg2://." >&2
  exit 1
fi

if ! python3 -c 'import socket; s=socket.create_connection(("127.0.0.1", 5432), 1); s.close()' 2>/dev/null; then
  echo "error: nothing is listening on 127.0.0.1:5432." >&2
  echo "Start the Auth Proxy in another terminal:" >&2
  echo "  /tmp/cloud-sql-proxy bankpassport-be:us-central1:bankpassport --port=5432" >&2
  echo "  # or: \$HOME/bin/cloud-sql-proxy bankpassport-be:us-central1:bankpassport --port=5432" >&2
  exit 1
fi

if ! python3 -c "
import os
from sqlalchemy import create_engine, text
engine = create_engine(os.environ['DATABASE_URL'], pool_pre_ping=True)
with engine.connect() as conn:
    conn.execute(text('SELECT 1'))
engine.dispose()
" 2>/dev/null; then
  echo "error: 127.0.0.1:5432 accepted TCP but Postgres closed the handshake." >&2
  echo "The Auth Proxy is probably stale. In another terminal:" >&2
  echo "  kill \$(lsof -t -iTCP:5432 -sTCP:LISTEN)" >&2
  echo "  /tmp/cloud-sql-proxy bankpassport-be:us-central1:bankpassport --port=5432" >&2
  exit 1
fi

export SESSION_COOKIE_SECURE="${SESSION_COOKIE_SECURE:-false}"
if [[ -z "${SECRET_KEY:-}" ]]; then
  SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
  export SECRET_KEY
fi

exec python3 app.py
