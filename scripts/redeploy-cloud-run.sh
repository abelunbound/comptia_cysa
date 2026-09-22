#!/usr/bin/env bash
# M1 Cloud Run redeploy for cysa-exam-app.
# Mounts SECRET_KEY from Secret Manager. Does NOT set DATABASE_URL or
# SESSION_COOKIE_SECURE (leave Secure cookies on for HTTPS).
#
# Usage (from repo root, after: git checkout main && git pull):
#   ./scripts/redeploy-cloud-run.sh
#
# Requires: gcloud (logged into project cybersecuritylab-509321), python3.

set -euo pipefail

PROJECT="cybersecuritylab-509321"
REGION="us-central1"
SERVICE="cysa-exam-app"
SECRET_NAME="cysa-exam-secret-key"
SERVICE_URL="https://cysa-exam-app-104739181475.us-central1.run.app"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f Dockerfile ]]; then
  echo "error: run this from the comptia_cysa repo (Dockerfile missing)." >&2
  exit 1
fi

if ! command -v gcloud >/dev/null 2>&1; then
  echo "error: gcloud not found. Install Google Cloud SDK and log in." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "error: python3 not found (needed to generate SECRET_KEY once)." >&2
  exit 1
fi

echo "==> Repo: $ROOT"
echo "==> git HEAD: $(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
echo "==> Project: $PROJECT  Service: $SERVICE  Region: $REGION"
echo

echo "==> Enabling Secret Manager API (safe if already on)"
gcloud services enable secretmanager.googleapis.com --project="$PROJECT" >/dev/null

if gcloud secrets describe "$SECRET_NAME" --project="$PROJECT" >/dev/null 2>&1; then
  echo "==> Secret $SECRET_NAME already exists (reusing)"
else
  echo "==> Creating Secret Manager secret $SECRET_NAME"
  python3 -c 'import secrets; print(secrets.token_hex(32), end="")' | \
    gcloud secrets create "$SECRET_NAME" --data-file=- --project="$PROJECT"
fi

PROJECT_NUMBER="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"
RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "==> Ensuring $RUNTIME_SA can access $SECRET_NAME"
gcloud secrets add-iam-policy-binding "$SECRET_NAME" \
  --project="$PROJECT" \
  --role=roles/secretmanager.secretAccessor \
  --member="serviceAccount:${RUNTIME_SA}" \
  --quiet >/dev/null || true

echo "==> Deploying $SERVICE from source (SECRET_KEY from Secret Manager only)"
gcloud run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  --project "$PROJECT" \
  --allow-unauthenticated \
  --update-secrets="SECRET_KEY=${SECRET_NAME}:latest"

echo
echo "==> Quick check (expect HTTP 302 to /login)"
HTTP_CODE="$(curl -s -o /dev/null -w '%{http_code}' -L --max-redirs 0 "$SERVICE_URL/" || true)"
# curl -L --max-redirs 0 still follows? Use -sI instead
LOCATION="$(curl -sI "$SERVICE_URL/" | tr -d '\r' | awk 'tolower($1)=="location:"{print $2; exit}')"
STATUS="$(curl -sI "$SERVICE_URL/" | tr -d '\r' | awk 'NR==1{print $2; exit}')"
echo "    GET / -> HTTP ${STATUS:-?}  Location: ${LOCATION:-(none)}"

if [[ "${STATUS:-}" == "302" ]] || [[ "${LOCATION:-}" == *"/login"* ]]; then
  echo "==> Looks good. Ping Cyber Platform Delivery for live auth smoke."
else
  echo "==> WARNING: expected 302 → /login. Check revisions / logs before calling Delivery." >&2
fi

echo
echo "Service URL: $SERVICE_URL"
