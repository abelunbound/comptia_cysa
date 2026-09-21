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
| **Access** | Public / unauthenticated |

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
- **State**: all exam/session data lives in the browser via
  `dcc.Store(storage_type="session")` — nothing is persisted server-side.
  This means the app is fully stateless, which is a great fit for Cloud
  Run's autoscaling (including scale-to-zero when idle, so it costs ~nothing
  when nobody's using it).
- **Question bank**: `cysa_plus_questions.csv` is baked into the container
  image at build time. If you edit the CSV, you must redeploy (rebuild) for
  the change to go live — it's not read from a live/mounted file.

## Redeploying after a code change

This is the only command you need for routine updates. Run it from the
project root (where the `Dockerfile` lives):

```bash
gcloud run deploy cysa-exam-app \
  --source . \
  --region us-central1 \
  --project cybersecuritylab-509321
```

This uses Cloud Build to build the `Dockerfile` remotely (no local Docker
install required), pushes the image to Artifact Registry, and rolls out a
new Cloud Run revision with zero downtime. It typically takes 1-3 minutes.

To also make sure it stays publicly accessible (this flag is idempotent —
safe to include every time, but not required after the first deploy):

```bash
gcloud run deploy cysa-exam-app \
  --source . \
  --region us-central1 \
  --project cybersecuritylab-509321 \
  --allow-unauthenticated
```

After it finishes, it prints the same stable **Service URL** shown above —
that URL doesn't change between deploys.

## Verifying a deployment

```bash
curl -s -o /dev/null -w "HTTP %{http_code}\n" \
  https://cysa-exam-app-104739181475.us-central1.run.app/
```

Should print `HTTP 200`. You can also check recent revisions and traffic
split with:

```bash
gcloud run revisions list --service cysa-exam-app --region us-central1 \
  --project cybersecuritylab-509321
```

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
     artifactregistry.googleapis.com --project YOUR_PROJECT_ID
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

4. Then run the same `gcloud run deploy` command from the "Redeploying"
   section above, swapping in the new project ID (and region if desired).

## Troubleshooting

- **`Billing account ... is not found`** when enabling services → billing
  isn't linked to the project yet. See step 1 above.
- **`PERMISSION_DENIED: ... default service account is missing required IAM
  permissions`** during `gcloud run deploy --source .` → see step 3 above.
- **App loads but data looks stale** → the CSV is baked into the image;
  redeploy after editing `cysa_plus_questions.csv` or `questions.csv`.
- **Local sanity check before deploying** — you can verify the production
  entrypoint works without touching Cloud Run at all:
  ```bash
  pip install gunicorn
  PORT=8081 gunicorn --bind 0.0.0.0:8081 app:server
  curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8081/
  ```
