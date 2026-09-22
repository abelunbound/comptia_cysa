# Milestone 2 — Cloud SQL Postgres

M2 puts **auth users and exam questions** on one Cloud SQL Postgres database.
Cloud Run requires `DATABASE_URL` (Secret Manager) and a Cloud SQL connection.
See also `scripts/redeploy-cloud-run.sh`.

| | |
|---|---|
| **Instance** | `cysa-exam-sql` |
| **Connection name** | `cybersecuritylab-509321:us-central1:cysa-exam-sql` |
| **Database** | `cysa_exam` |
| **App user** | `cysa_app` (least privilege — not the `postgres` superuser) |
| **Secrets** | `cysa-exam-secret-key`, `cysa-exam-database-url` |

## One-time: create instance + DB + user

```bash
export CLOUDSQL_ROOT_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
export CLOUDSQL_APP_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
# Save both passwords securely (password manager). Do not commit them.

gcloud sql instances create cysa-exam-sql \
  --project=cybersecuritylab-509321 \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --storage-size=10 \
  --storage-auto-increase \
  --availability-type=ZONAL \
  --root-password="$CLOUDSQL_ROOT_PASSWORD"

gcloud sql databases create cysa_exam --instance=cysa-exam-sql --project=cybersecuritylab-509321
gcloud sql users create cysa_app --instance=cysa-exam-sql --project=cybersecuritylab-509321 \
  --password="$CLOUDSQL_APP_PASSWORD"
```

## One-time: DATABASE_URL secret (Unix socket for Cloud Run)

```bash
CONN=cybersecuritylab-509321:us-central1:cysa-exam-sql
URL="postgresql+psycopg2://cysa_app:${CLOUDSQL_APP_PASSWORD}@/cysa_exam?host=/cloudsql/${CONN}"
echo -n "$URL" | gcloud secrets create cysa-exam-database-url --data-file=- --project=cybersecuritylab-509321
```

## One-time: seed questions (Cloud SQL Auth Proxy)

```bash
# Terminal A
cloud-sql-proxy cybersecuritylab-509321:us-central1:cysa-exam-sql --port=5432

# Terminal B (repo root)
export DATABASE_URL="postgresql+psycopg2://cysa_app:${CLOUDSQL_APP_PASSWORD}@127.0.0.1:5432/cysa_exam"
pip install -r requirements.txt
python scripts/seed_questions.py
```

CSV is used **only** for this seed. Cloud Run runtime loads questions via
`load_questions()` from Postgres (no CSV dependency).

## Redeploy (M2)

```bash
git checkout main && git pull
chmod +x scripts/redeploy-cloud-run.sh
./scripts/redeploy-cloud-run.sh
```

Mounts `SECRET_KEY` + `DATABASE_URL`, attaches `--add-cloudsql-instances`,
leaves `SESSION_COOKIE_SECURE` unset.
