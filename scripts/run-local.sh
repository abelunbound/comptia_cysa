#!/usr/bin/env bash
# Start the Dash app against Cloud SQL via Auth Proxy (no SQLite).
# If 127.0.0.1:5432 is closed, starts cloud-sql-proxy in the background here.
# Usage (from repo root):
#   export DATABASE_URL='postgresql+psycopg2://cysa_app:<PASSWORD>@127.0.0.1:5432/cybersecuritylab'
#   ./scripts/run-local.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -x "$ROOT/venv/bin/python3" ]]; then
  APP_PYTHON="$ROOT/venv/bin/python3"
else
  APP_PYTHON="$(command -v python3)"
fi
echo "Using ${APP_PYTHON}"

CLOUD_SQL_INSTANCE="${CLOUD_SQL_INSTANCE:-bankpassport-be:us-central1:bankpassport}"
PROXY_PORT=5432
PROXY_LOG="${TMPDIR:-/tmp}/cysa-sql-proxy.log"

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "error: DATABASE_URL is required (PostgreSQL)." >&2
  echo "  cloud-sql-proxy ${CLOUD_SQL_INSTANCE} --port=${PROXY_PORT}" >&2
  echo "  export DATABASE_URL='postgresql+psycopg2://cysa_app:<PASSWORD>@127.0.0.1:${PROXY_PORT}/cybersecuritylab'" >&2
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

port_open() {
  "${APP_PYTHON}" -c 'import socket; s=socket.create_connection(("127.0.0.1", '"${PROXY_PORT}"'), 1); s.close()' 2>/dev/null
}

find_cloud_sql_proxy() {
  if [[ -n "${CLOUD_SQL_PROXY:-}" && -x "${CLOUD_SQL_PROXY}" ]]; then
    printf '%s' "${CLOUD_SQL_PROXY}"
    return 0
  fi
  local candidate
  for candidate in /tmp/cloud-sql-proxy "${HOME}/bin/cloud-sql-proxy"; do
    if [[ -x "$candidate" ]]; then
      printf '%s' "$candidate"
      return 0
    fi
  done
  if command -v cloud-sql-proxy >/dev/null 2>&1; then
    command -v cloud-sql-proxy
    return 0
  fi
  return 1
}

start_auth_proxy() {
  local proxy
  if ! proxy="$(find_cloud_sql_proxy)"; then
    echo "error: nothing is listening on 127.0.0.1:${PROXY_PORT} and cloud-sql-proxy was not found." >&2
    echo "Install it, then re-run, or start it yourself:" >&2
    echo "  /tmp/cloud-sql-proxy ${CLOUD_SQL_INSTANCE} --port=${PROXY_PORT}" >&2
    exit 1
  fi

  echo "Starting Cloud SQL Auth Proxy (${CLOUD_SQL_INSTANCE} → 127.0.0.1:${PROXY_PORT})"
  echo "Proxy log: ${PROXY_LOG}"
  nohup "$proxy" "${CLOUD_SQL_INSTANCE}" --port="${PROXY_PORT}" >"${PROXY_LOG}" 2>&1 &

  local i
  for i in $(seq 1 25); do
    if port_open; then
      return 0
    fi
    sleep 0.4
  done

  echo "error: Auth Proxy started but 127.0.0.1:${PROXY_PORT} never opened." >&2
  echo "Check gcloud auth and ${PROXY_LOG}" >&2
  exit 1
}

if ! port_open; then
  start_auth_proxy
fi

if ! "${APP_PYTHON}" -c "
import os
from sqlalchemy import create_engine, text
engine = create_engine(os.environ['DATABASE_URL'], pool_pre_ping=True)
with engine.connect() as conn:
    conn.execute(text('SELECT 1'))
engine.dispose()
" 2>/dev/null; then
  echo "error: 127.0.0.1:${PROXY_PORT} accepted TCP but Postgres closed the handshake." >&2
  echo "Something else may be on that port, or the Auth Proxy is stale. Do not kill blindly." >&2
  echo "If you are sure it is a dead proxy:" >&2
  echo "  kill \$(lsof -t -iTCP:${PROXY_PORT} -sTCP:LISTEN)" >&2
  echo "  ${CLOUD_SQL_PROXY:-cloud-sql-proxy} ${CLOUD_SQL_INSTANCE} --port=${PROXY_PORT}" >&2
  echo "Log if this script started the proxy: ${PROXY_LOG}" >&2
  exit 1
fi

export SESSION_COOKIE_SECURE="${SESSION_COOKIE_SECURE:-false}"
if [[ -z "${SECRET_KEY:-}" ]]; then
  SECRET_KEY="$("${APP_PYTHON}" -c 'import secrets; print(secrets.token_hex(32))')"
  export SECRET_KEY
fi

exec "${APP_PYTHON}" app.py
