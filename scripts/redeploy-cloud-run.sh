#!/usr/bin/env bash
# M2 Cloud Run redeploy for cysa-exam-app.
# Mounts SECRET_KEY + DATABASE_URL from Secret Manager, attaches Cloud SQL.
# Does NOT set SESSION_COOKIE_SECURE (leave Secure cookies on for HTTPS).
#
# Prerequisites:
#   - Shared Cloud SQL instance bankpassport RUNNABLE (project bankpassport-be)
#   - DB cybersecuritylab + user cysa_app created
#   - Secret cysa-exam-database-url holding the Unix-socket SQLAlchemy URL
#   - Questions seeded (python scripts/seed_questions.py via Auth Proxy)
#   - See docs/database.md and scripts/setup-cross-projects-db.sh
#
# Usage (from repo root, after: git checkout main && git pull):
#   ./scripts/redeploy-cloud-run.sh
#
# Requires: gcloud (logged into project cybersecuritylab-509321), python3, curl.

set -euo pipefail

PROJECT="cybersecuritylab-509321"
REGION="us-central1"
SERVICE="cysa-exam-app"
CLOUDSQL_OWNER_PROJECT="bankpassport-be"
CLOUDSQL_CONNECTION="bankpassport-be:us-central1:bankpassport"
SECRET_KEY_NAME="cysa-exam-secret-key"
DATABASE_URL_SECRET="cysa-exam-database-url"
DB_NAME="cybersecuritylab"
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
echo "==> Cloud SQL: $CLOUDSQL_CONNECTION"
echo

echo "==> Enabling APIs (safe if already on)"
gcloud services enable secretmanager.googleapis.com sqladmin.googleapis.com \
  --project="$PROJECT" >/dev/null

if gcloud secrets describe "$SECRET_KEY_NAME" --project="$PROJECT" >/dev/null 2>&1; then
  echo "==> Secret $SECRET_KEY_NAME already exists (reusing)"
else
  echo "==> Creating Secret Manager secret $SECRET_KEY_NAME"
  python3 -c 'import secrets; print(secrets.token_hex(32), end="")' | \
    gcloud secrets create "$SECRET_KEY_NAME" --data-file=- --project="$PROJECT"
fi

if ! gcloud secrets describe "$DATABASE_URL_SECRET" --project="$PROJECT" >/dev/null 2>&1; then
  echo "error: secret $DATABASE_URL_SECRET missing." >&2
  echo "Create it with the Unix-socket URL, e.g.:" >&2
  echo "  postgresql+psycopg2://cysa_app:APP_PASSWORD@/${DB_NAME}?host=/cloudsql/${CLOUDSQL_CONNECTION}" >&2
  echo "  echo -n 'URL' | gcloud secrets create ${DATABASE_URL_SECRET} --data-file=- --project=${PROJECT}" >&2
  exit 1
fi
echo "==> Secret $DATABASE_URL_SECRET present"

PROJECT_NUMBER="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"
RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "==> IAM: Secret Accessor + Cloud SQL Client for $RUNTIME_SA"
for SECRET in "$SECRET_KEY_NAME" "$DATABASE_URL_SECRET"; do
  gcloud secrets add-iam-policy-binding "$SECRET" \
    --project="$PROJECT" \
    --role=roles/secretmanager.secretAccessor \
    --member="serviceAccount:${RUNTIME_SA}" \
    --quiet >/dev/null || true
done

# Cloud SQL Client must be on the *instance* project (bankpassport-be), not
# the Cloud Run project. setup-cross-projects-db.sh grants this as the owner;
# this is a no-op if the current account cannot bind IAM there.
gcloud projects add-iam-policy-binding "$CLOUDSQL_OWNER_PROJECT" \
  --member="serviceAccount:${RUNTIME_SA}" \
  --role=roles/cloudsql.client \
  --quiet >/dev/null || true

echo "==> Deploying $SERVICE (SECRET_KEY + DATABASE_URL secrets, Cloud SQL attached)"
gcloud run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  --project "$PROJECT" \
  --allow-unauthenticated \
  --add-cloudsql-instances="$CLOUDSQL_CONNECTION" \
  --update-secrets="SECRET_KEY=${SECRET_KEY_NAME}:latest,DATABASE_URL=${DATABASE_URL_SECRET}:latest"

echo
echo "==> Quick check (expect HTTP 302 to /login)"
LOCATION="$(curl -sI "$SERVICE_URL/" | tr -d '\r' | awk 'tolower($1)=="location:"{print $2; exit}')"
STATUS="$(curl -sI "$SERVICE_URL/" | tr -d '\r' | awk 'NR==1{print $2; exit}')"
echo "    GET / -> HTTP ${STATUS:-?}  Location: ${LOCATION:-(none)}"

if [[ "${STATUS:-}" == "302" ]] || [[ "${LOCATION:-}" == *"/login"* ]]; then
  echo "==> Looks good. Ping Cyber Platform Delivery for live smoke."
else
  echo "==> WARNING: expected 302 → /login. Check revisions / logs before calling Delivery." >&2
fi

echo
echo "Service URL: $SERVICE_URL"
