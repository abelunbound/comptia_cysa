#!/usr/bin/env bash
# Rotate the cysa_app Cloud SQL password, write a new DATABASE_URL secret
# version, and refresh the Cloud Run revision. Prompts for the new password.
# Does not print the password.
set -euo pipefail

OWNER_ACCOUNT="${OWNER_ACCOUNT:-unboundpassport@gmail.com}"
APP_ACCOUNT="${APP_ACCOUNT:-abelakeni@gmail.com}"
OWNER_PROJECT="${OWNER_PROJECT:-bankpassport-be}"
APP_PROJECT="${APP_PROJECT:-cybersecuritylab-509321}"
INSTANCE="${INSTANCE:-bankpassport}"
DB_NAME="${DB_NAME:-cybersecuritylab}"
DB_USER="${DB_USER:-cysa_app}"
CLOUD_RUN_SERVICE="${CLOUD_RUN_SERVICE:-cysa-exam-app}"
CLOUD_RUN_REGION="${CLOUD_RUN_REGION:-us-central1}"
SECRET_NAME="${SECRET_NAME:-cysa-exam-database-url}"

if [ ! -t 0 ]; then
  echo "This script must be run in an interactive terminal so it can prompt for the password." >&2
  exit 1
fi

read -rsp "Enter NEW password for Cloud SQL user ${DB_USER}: " DB_PASSWORD
echo
read -rsp "Confirm NEW password: " DB_PASSWORD_CONFIRM
echo
if [ -z "$DB_PASSWORD" ]; then
  echo "Password cannot be empty." >&2
  exit 1
fi
if [ "$DB_PASSWORD" != "$DB_PASSWORD_CONFIRM" ]; then
  echo "Passwords do not match." >&2
  exit 1
fi

ENCODED_PASSWORD=$(python3 -c "import urllib.parse, sys; print(urllib.parse.quote(sys.argv[1], safe=''))" "$DB_PASSWORD")

echo "=== Current gcloud account ==="
CURRENT_ACCOUNT=$(gcloud config get-value account)
echo "$CURRENT_ACCOUNT"

echo ""
echo "=== Stage 1: rotate Cloud SQL user password on ${OWNER_PROJECT}/${INSTANCE} ==="
echo "Switching to owner account ${OWNER_ACCOUNT} (you may be prompted to log in)."
gcloud config set account "$OWNER_ACCOUNT"
gcloud config set project "$OWNER_PROJECT"

gcloud sql users set-password "$DB_USER" \
  --instance="$INSTANCE" \
  --project="$OWNER_PROJECT" \
  --password="$DB_PASSWORD"

CONNECTION_NAME=$(gcloud sql instances describe "$INSTANCE" \
  --project="$OWNER_PROJECT" \
  --format='value(connectionName)')
echo "Connection name: $CONNECTION_NAME"

echo ""
echo "=== Stage 2: new Secret Manager version + Cloud Run refresh ==="
gcloud config set account "$APP_ACCOUNT"
gcloud config set project "$APP_PROJECT"

DB_URL="postgresql+psycopg2://${DB_USER}:${ENCODED_PASSWORD}@/${DB_NAME}?host=/cloudsql/${CONNECTION_NAME}"

if gcloud secrets describe "$SECRET_NAME" --project="$APP_PROJECT" >/dev/null 2>&1; then
  echo -n "$DB_URL" | gcloud secrets versions add "$SECRET_NAME" --project="$APP_PROJECT" --data-file=-
else
  echo -n "$DB_URL" | gcloud secrets create "$SECRET_NAME" --project="$APP_PROJECT" --data-file=-
fi

PROJECT_NUMBER=$(gcloud projects describe "$APP_PROJECT" --format='value(projectNumber)')
RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
gcloud secrets add-iam-policy-binding "$SECRET_NAME" \
  --project="$APP_PROJECT" \
  --role=roles/secretmanager.secretAccessor \
  --member="serviceAccount:${RUNTIME_SA}" \
  --quiet >/dev/null

gcloud run services update "$CLOUD_RUN_SERVICE" \
  --project="$APP_PROJECT" \
  --region="$CLOUD_RUN_REGION" \
  --add-cloudsql-instances="$CONNECTION_NAME" \
  --update-secrets="DATABASE_URL=${SECRET_NAME}:latest"

gcloud config set account "$CURRENT_ACCOUNT" >/dev/null || true

echo ""
echo "DONE. Cloud SQL password rotated, secret ${SECRET_NAME} updated, Cloud Run refreshed."
echo "The new password was not written to disk or printed."
