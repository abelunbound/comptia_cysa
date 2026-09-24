# Deploying to Google Cloud Run

This app is deployed as a container on **Google Cloud Run**. This doc covers
the one-time setup that's already been done, and the simple steps to
redeploy after future changes.

## Current deployment

| | |
|---|---|
| **Project** | `cybersecuritylab-509321` |
| **Region** | `us-central1` |
| **Service name** | `cysa-exam-app` |
| **Service URL** | https://cysa-exam-app-104739181475.us-central1.run.app |
| **Access** | Public (requires user authentication after M1) |

## Milestone 1 redeployment

**Fast path (recommended):** from a machine logged into GCP project
`cybersecuritylab-509321`, at the repo root:

```bash
git checkout main && git pull
chmod +x scripts/redeploy-cloud-run.sh
./scripts/redeploy-cloud-run.sh
```

That script enables Secret Manager if needed, creates/reuses
`cysa-exam-secret-key`, grants the Cloud Run runtime SA access, deploys with
`--update-secrets=SECRET_KEY=…`, and prints a quick `/` → `/login` check.

Manual steps below match what the script does.

**M1 constraints**

- Mount `SECRET_KEY` from **Secret Manager** (`--update-secrets`). Prefer this
  over plaintext `--set-env-vars` (avoids shell history / accidental commits).
- `DATABASE_URL` is **required** (PostgreSQL). Do not omit it — there is no
  SQLite fallback. Staging mounts Secret Manager `cysa-exam-database-url`.
- Leave `SESSION_COOKIE_SECURE` **unset** so cookies stay Secure on HTTPS.
- After the revision is Serving, ping Delivery with the live URL for auth smoke.

### Manual steps

1. Pull `main` and cd to the repo root:

```bash
git checkout main && git pull
```

2. Enable Secret Manager if needed (one-time):

```bash
gcloud services enable secretmanager.googleapis.com --project=cybersecuritylab-509321
```

3. Create the secret (skip if `cysa-exam-secret-key` already exists):

```bash
python -c 'import secrets; print(secrets.token_hex(32), end="")' | \
  gcloud secrets create cysa-exam-secret-key --data-file=- --project=cybersecuritylab-509321
```

4. Grant the Cloud Run runtime service account access:

```bash
PROJECT_NUMBER=$(gcloud projects describe cybersecuritylab-509321 --format='value(projectNumber)')
gcloud secrets add-iam-policy-binding cysa-exam-secret-key \
  --project=cybersecuritylab-509321 \
  --role=roles/secretmanager.secretAccessor \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
```

5. Redeploy with `SECRET_KEY` from Secret Manager only:

```bash
gcloud run deploy cysa-exam-app \
  --source . \
  --region us-central1 \
  --project cybersecuritylab-509321 \
  --allow-unauthenticated \
  --update-secrets=SECRET_KEY=cysa-exam-secret-key:latest
```

6. When the new revision is Serving, paste the Service URL in the team room
   and ask Delivery to run the live auth smoke.

Stable URL (unchanged between deploys):
https://cysa-exam-app-104739181475.us-central1.run.app

### Milestone 2 (Cloud SQL + `DATABASE_URL`)

Questions and auth users share one Postgres database on the existing
`bankpassport` instance. See `docs/database.md` and `docs/M2-CLOUD-SQL.md`.

**Fast path** (from `feat/m2-cloud-sql-postgres` or `main` after merge):

```bash
chmod +x scripts/redeploy-cloud-run.sh
./scripts/redeploy-cloud-run.sh
```

That mounts **both** secrets and attaches Cloud SQL:

- `SECRET_KEY` ← Secret Manager `cysa-exam-secret-key`
- `DATABASE_URL` ← Secret Manager `cysa-exam-database-url`
- `--add-cloudsql-instances=bankpassport-be:us-central1:bankpassport`

Do **not** pass `DATABASE_URL` with `--set-env-vars`.

**Seed questions** (one-time or after CSV changes), via Cloud SQL Auth Proxy:

```bash
cloud-sql-proxy bankpassport-be:us-central1:bankpassport --port=5432
# other terminal, password from your password manager — not committed
export DATABASE_URL="postgresql+psycopg2://cysa_app:${DB_PASSWORD}@127.0.0.1:5432/cybersecuritylab"
python scripts/seed_questions.py
```

`load_questions()` always reads the `questions` table. CSV is seed-only
(`scripts/seed_questions.py`) and is not copied into the Cloud Run image.

## Required Environment Variables

### SECRET_KEY (required)

Flask session secret. The app fails to start if this is missing.

**Preferred (M1+):** mount from Secret Manager via `--update-secrets` — see
[Milestone 1 redeployment](#milestone-1-redeployment) / `scripts/redeploy-cloud-run.sh`.

Generate a value with:

```bash
python -c 'import secrets; print(secrets.token_hex(32))'
```

Weaker alternative (lands in shell history; avoid for the real key):

```bash
gcloud run services update cysa-exam-app \
  --region us-central1 \
  --project cybersecuritylab-509321 \
  --set-env-vars SECRET_KEY='your-generated-secret-key-here'
```

### DATABASE_URL (required)

SQLAlchemy URL for Postgres. **Required** everywhere the app starts (local,
tests, Cloud Run). Missing or SQLite URLs crash at startup.

| | |
|---|---|
| Secret | `cysa-exam-database-url` in `cybersecuritylab-509321` |
| Cloud Run env | `DATABASE_URL` mounted with `--update-secrets` |
| Shape (Cloud Run / Unix socket) | `postgresql+psycopg2://cysa_app:${DB_PASSWORD}@/cybersecuritylab?host=/cloudsql/bankpassport-be:us-central1:bankpassport` |
| Shape (local Auth Proxy) | `postgresql+psycopg2://cysa_app:${DB_PASSWORD}@127.0.0.1:5432/cybersecuritylab` |

Percent-encode `${DB_PASSWORD}` if it contains reserved URL characters.

```bash
# already applied on cysa-exam-app; re-apply after secret rotation:
gcloud run services update cysa-exam-app \
  --region us-central1 \
  --project cybersecuritylab-509321 \
  --add-cloudsql-instances=bankpassport-be:us-central1:bankpassport \
  --update-secrets=DATABASE_URL=cysa-exam-database-url:latest
```

Never put a real password in this file or in `--set-env-vars`.

**Security Notes**:
- Never commit `SECRET_KEY` or `DATABASE_URL` to the repository. Prefer Secret
  Manager mounts on Cloud Run; local `.env` must stay in `.gitignore`.
- Do **not** set `SESSION_COOKIE_SECURE=false` on Cloud Run (HTTPS). That flag
  is for local HTTP only.
- **Production must never run with debug=True**: The Dockerfile uses gunicorn,
  which serves the Flask `server` directly and never enables debug mode. This
  ensures `SESSION_COOKIE_SECURE=True` by default (HTTPS-only session cookies).
  The `debug=True` in `app.py`'s `if __name__ == "__main__"` block only affects
  local `python app.py` development runs and is never executed in production.

## How it's built

- **`Dockerfile`** builds a `python:3.12-slim` image, installs
  `requirements.txt`, copies the app, and runs it with `gunicorn` (a
  production WSGI server) instead of the Dash/Flask dev server:
  ```
  gunicorn --bind 0.0.0.0:${PORT} --workers 2 --threads 4 --timeout 0 app:server
  ```
  Cloud Run injects the `$PORT` env var (defaults to `8080`) and expects the
  container to listen on it. `app.py` already exposes the underlying Flask
  app as `server = app.server`, which is what `app:server` in that command
  refers to.
- **`.dockerignore`** keeps the image lean (excludes `venv/`, `__pycache__/`,
  `.git/`, etc).
- **State**: exam UI session data lives in the browser via
  `dcc.Store(storage_type="session")`. Auth users and questions live in
  Cloud SQL Postgres (`cybersecuritylab`).
- **Question bank**: seeded into `questions` via `scripts/seed_questions.py`.
  The CSV is not in the container image. Re-seed through the Auth Proxy after
  CSV edits; no rebuild required for data-only changes.

## Redeploying after a code change (routine)

For routine code-only updates **after** M1 secrets are already mounted, prefer
`./scripts/redeploy-cloud-run.sh` (keeps the Secret Manager mount) or from
the project root:

```bash
gcloud run deploy cysa-exam-app \
  --source . \
  --region us-central1 \
  --project cybersecuritylab-509321 \
  --allow-unauthenticated
```

This uses Cloud Build to build the `Dockerfile` remotely (no local Docker
install required), pushes the image to Artifact Registry, and rolls out a
new Cloud Run revision with zero downtime. It typically takes 1-3 minutes.

The service stays publicly accessible (no Cloud Run IAM auth); users must
still sign up / log in to use exams. The **Service URL** does not change
between deploys.

If `SECRET_KEY` is not yet mounted, follow [Milestone 1 redeployment](#milestone-1-redeployment)
instead of this shorter command.

## Verifying a deployment

```bash
curl -sI https://cysa-exam-app-104739181475.us-central1.run.app/ | head -5
```

Unauthenticated `/` should redirect to `/login` (typically HTTP 302). You can
also check recent revisions and traffic split with:

```bash
gcloud run revisions list --service cysa-exam-app --region us-central1 \
  --project cybersecuritylab-509321
```

Live auth smoke (signup → exam paints → shell Logout → re-login → protected
redirects) is owned by Delivery after each M1+ ship.

## Rolling back

If a deploy introduces a regression, route traffic back to the previous
(known-good) revision:

```bash
gcloud run revisions list --service cysa-exam-app --region us-central1 \
  --project cybersecuritylab-509321   # find the previous revision name

gcloud run services update-traffic cysa-exam-app --region us-central1 \
  --project cybersecuritylab-509321 \
  --to-revisions PREVIOUS_REVISION_NAME=100
```

## One-time project setup (already done for this project)

If you ever deploy to a **new/different** GCP project, you'll need to redo
these steps first (all one-time, per-project):

1. **Enable billing** on the project — Cloud Run/Cloud Build require it.
   Via console: `https://console.cloud.google.com/billing/linkedaccount?project=YOUR_PROJECT_ID`

2. **Enable the required APIs:**
   ```bash
   gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
     artifactregistry.googleapis.com secretmanager.googleapis.com \
     --project YOUR_PROJECT_ID
   ```

3. **Grant IAM roles to the default Compute service account.** On a
   freshly billing-enabled project, `gcloud run deploy --source .` can fail
   with `PERMISSION_DENIED ... default service account is missing required
   IAM permissions`. Fix it with (replace `PROJECT_NUMBER`, found via
   `gcloud projects describe YOUR_PROJECT_ID --format='value(projectNumber)'`):
   ```bash
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
     --role="roles/storage.objectViewer"

   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
     --role="roles/cloudbuild.builds.builder"
   ```

4. Then follow [Milestone 1 redeployment](#milestone-1-redeployment) (or the
   routine redeploy section once secrets are mounted), swapping in the new
   project ID (and region if desired).

## Troubleshooting

- **`Billing account ... is not found`** when enabling services → billing
  isn't linked to the project yet. See step 1 above.
- **`PERMISSION_DENIED: ... default service account is missing required IAM
  permissions`** during `gcloud run deploy --source .` → see step 3 above.
- **Container fails to start / SECRET_KEY required** → Secret Manager mount
  missing; re-run `./scripts/redeploy-cloud-run.sh`.
- **App loads but data looks stale** → re-seed Postgres
  (`python scripts/seed_questions.py` via Auth Proxy). CSV is not in the image.
- **Container fails to start / DATABASE_URL required** → Secret Manager mount
  missing or SQLite URL; remount `cysa-exam-database-url`.
- **Local sanity check before deploying** — Auth Proxy + Postgres URL required:
  ```bash
  export SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')
  export SESSION_COOKIE_SECURE=false
  export DATABASE_URL='postgresql+psycopg2://cysa_app:<PASSWORD>@127.0.0.1:5432/cybersecuritylab'
  pip install gunicorn
  PORT=8081 gunicorn --bind 0.0.0.0:8081 app:server
  curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8081/
  ```
