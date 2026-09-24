#!/usr/bin/env bash
# =============================================================================
# Cross-account Cloud SQL setup: reuse `bankpassport` instance (on your other
# Gmail account) as the database for cybersecuritylab-509321 (on abelakeni).
#
# HOW TO USE:
#   1. Fill in the CONFIG block below.
#   2. Run:  bash setup-cross-project-db.sh
#   3. The script will STOP and tell you when to `gcloud auth login` as your
#      other Gmail account, then again when to switch back to abelakeni.
#      Just follow the on-screen prompts — you don't need to edit anything
#      else once CONFIG is filled in.
# =============================================================================

set -euo pipefail

# ---------------------------- CONFIG -- FILL ME IN --------------------------
# Passwords: export DB_PASSWORD='...' or enter it at the prompt. Do not commit it.
OWNER_ACCOUNT="unboundpassport@gmail.com"     # the Gmail that owns bankpassport-be
APP_ACCOUNT="abelakeni@gmail.com"              # your current logged-in account (confirm with: gcloud config get-value account)

OWNER_PROJECT="bankpassport-be"
APP_PROJECT="cybersecuritylab-509321"

INSTANCE="bankpassport"
DB_NAME="cybersecuritylab"                     # already exists per your screenshot — leave as-is unless you want a fresh DB
DB_USER="cysa_app"
# Never hardcode a password. Set DB_PASSWORD in the environment, or you
# will be prompted. Generate with: openssl rand -base64 24

CLOUD_RUN_SERVICE="cysa-exam-app"
CLOUD_RUN_REGION="us-central1"
SECRET_NAME="cysa-exam-database-url"           # separate from cysa-exam-secret-key — do not reuse that one

RUNTIME_SA=""   # leave blank to auto-detect the default Compute SA later; set explicitly if Cloud Run uses a custom SA
# ------------------------------------------------------------------------------

pause() {
  echo ""
  echo "############################################################"
  echo "$1"
  echo "############################################################"
  read -rp "Press Enter once done... "
}

DB_PASSWORD="${DB_PASSWORD:-}"
if [ -z "$DB_PASSWORD" ]; then
  if [ ! -t 0 ]; then
    echo "DB_PASSWORD is unset and stdin is not a TTY. Export DB_PASSWORD and re-run." >&2
    exit 1
  fi
  read -rsp "Enter password for DB user ${DB_USER} (will not be echoed): " DB_PASSWORD
  echo
fi
if [ -z "$DB_PASSWORD" ]; then
  echo "DB_PASSWORD is required." >&2
  exit 1
fi
 
echo "=== STAGE 0: sanity check current account ==="
gcloud config get-value account
 
# =============================================================================
# STAGE 1 — runs as OWNER_ACCOUNT (your other Gmail). Sets up the instance side.
# =============================================================================
pause "STEP 1: Sign in as your OTHER Gmail account ($OWNER_ACCOUNT).
Run this now in another terminal tab OR let this script do it:
  gcloud auth login
Pick the account that owns bankpassport-be, then come back here."
 
gcloud config set account "$OWNER_ACCOUNT"
gcloud config set project "$OWNER_PROJECT"
 
echo "--- Getting instance connection name ---"
CONNECTION_NAME=$(gcloud sql instances describe "$INSTANCE" \
  --project="$OWNER_PROJECT" \
  --format='value(connectionName)')
echo "Connection name: $CONNECTION_NAME"
# shape looks like: bankpassport-be:REGION:bankpassport
 
REGION=$(echo "$CONNECTION_NAME" | cut -d: -f2)
echo "Region detected: $REGION"
 
echo "--- Creating least-privilege app DB user (if it doesn't already exist) ---"
gcloud sql users create "$DB_USER" \
  --instance="$INSTANCE" \
  --project="$OWNER_PROJECT" \
  --password="$DB_PASSWORD" \
  || echo "(user may already exist — that's fine, continuing)"
 
echo "--- Getting cybersecuritylab-509321's project number (needed for IAM grant) ---"
pause "STEP 2: We now need the PROJECT NUMBER of cybersecuritylab-509321.
Switching accounts temporarily to fetch it — you may be prompted again."
 
gcloud config set account "$APP_ACCOUNT"
APP_PROJECT_NUMBER=$(gcloud projects describe "$APP_PROJECT" --format='value(projectNumber)')
echo "App project number: $APP_PROJECT_NUMBER"
 
if [ -z "$RUNTIME_SA" ]; then
  RUNTIME_SA="${APP_PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
  echo "Using default Compute SA: $RUNTIME_SA"
  echo "(If your Cloud Run service uses a CUSTOM service account, stop and set RUNTIME_SA in the config block instead, then re-run.)"
fi
 
pause "STEP 3: Switching back to OWNER_ACCOUNT ($OWNER_ACCOUNT) to grant IAM access."
 
gcloud config set account "$OWNER_ACCOUNT"
gcloud config set project "$OWNER_PROJECT"
 
echo "--- Granting Cloud SQL Client role to Cloud Run's service account ---"
gcloud projects add-iam-policy-binding "$OWNER_PROJECT" \
  --member="serviceAccount:${RUNTIME_SA}" \
  --role="roles/cloudsql.client"
 
echo "--- Confirming Cloud SQL Admin API is enabled on owner project ---"
gcloud services enable sqladmin.googleapis.com --project="$OWNER_PROJECT"
 
echo ""
echo "Stage 1 complete. Instance side is ready."
echo "Connection name to remember: $CONNECTION_NAME"
 
# =============================================================================
# STAGE 2 — runs as APP_ACCOUNT (abelakeni). Sets up the app side.
# =============================================================================
pause "STEP 4: Switch back to abelakeni for the app-side setup."
 
gcloud config set account "$APP_ACCOUNT"
gcloud config set project "$APP_PROJECT"
 
echo "--- Ensuring Cloud SQL Admin API is enabled on the app project too ---"
gcloud services enable sqladmin.googleapis.com --project="$APP_PROJECT"
 
echo "--- Creating/updating the Secret Manager secret with the DB connection string ---"
ENCODED_PASSWORD=$(python3 -c "import urllib.parse, sys; print(urllib.parse.quote(sys.argv[1], safe=''))" "$DB_PASSWORD")
DB_URL="postgresql+psycopg2://${DB_USER}:${ENCODED_PASSWORD}@/${DB_NAME}?host=/cloudsql/${CONNECTION_NAME}"
 
if gcloud secrets describe "$SECRET_NAME" --project="$APP_PROJECT" >/dev/null 2>&1; then
  echo -n "$DB_URL" | gcloud secrets versions add "$SECRET_NAME" --project="$APP_PROJECT" --data-file=-
else
  echo -n "$DB_URL" | gcloud secrets create "$SECRET_NAME" --project="$APP_PROJECT" --data-file=-
fi
 
echo "--- Granting Cloud Run's service account access to read this secret ---"
gcloud secrets add-iam-policy-binding "$SECRET_NAME" \
  --project="$APP_PROJECT" \
  --role=roles/secretmanager.secretAccessor \
  --member="serviceAccount:${RUNTIME_SA}" \
  --quiet
 
echo "--- Updating Cloud Run service with the Cloud SQL connection attached ---"
echo "(config-only update — no source rebuild)"
gcloud run services update "$CLOUD_RUN_SERVICE" \
  --project="$APP_PROJECT" \
  --region="$CLOUD_RUN_REGION" \
  --add-cloudsql-instances="$CONNECTION_NAME" \
  --update-secrets="DATABASE_URL=${SECRET_NAME}:latest"
 
echo ""
echo "=============================================================="
echo "DONE. Summary:"
echo "  Instance connection name: $CONNECTION_NAME"
echo "  Database: $DB_NAME"
echo "  App DB user: $DB_USER"
echo "  Cloud Run SA granted cloudsql.client: $RUNTIME_SA"
echo "  Secret: $SECRET_NAME (in $APP_PROJECT)"
echo "=============================================================="
echo "Next: test your app's DB connectivity, then run your seed script"
echo "against this instance via the Cloud SQL Auth Proxy if needed."
 