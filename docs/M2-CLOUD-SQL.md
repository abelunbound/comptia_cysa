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

## Security constraints (required)

1. **No public `0.0.0.0/0` authorized networks.** Do not add `0.0.0.0/0` (or any
   broad CIDR) under Cloud SQL Connections. Prefer **no public IP** if your
   VPC setup allows; otherwise leave public IP with **empty** authorized
   networks and connect only via:
   - Cloud SQL Auth Proxy (local seed), and
   - Cloud Run `--add-cloudsql-instances` / Unix socket (runtime).
2. **Least-privilege `cysa_app`.** Create the DB objects as `postgres`, then
   grant `cysa_app` only table privileges on `users` and `questions` (see
   grants below). Never use the `postgres` superuser password in Cloud Run
   or in `DATABASE_URL`.
3. **`DATABASE_URL` only via Secret Manager** (`cysa-exam-database-url`). Never
   pass it with plaintext `--set-env-vars`.

## One-time: create instance + DB + user

```bash
export CLOUDSQL_ROOT_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
export CLOUDSQL_APP_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
# Save both passwords securely (password manager). Do not commit them.

# Create without opening the world. Do NOT run:
#   gcloud sql instances patch ... --authorized-networks=0.0.0.0/0
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

After first app connect / `db.create_all()` (or seed), grant least privilege
(as `postgres` via Auth Proxy):

```sql
GRANT CONNECT ON DATABASE cysa_exam TO cysa_app;
GRANT USAGE ON SCHEMA public TO cysa_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE users, questions TO cysa_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO cysa_app;
-- Optional: revoke anything broader if you created objects as postgres first
```

## One-time: DATABASE_URL secret (Unix socket for Cloud Run)

```bash
CONN=cybersecuritylab-509321:us-central1:cysa-exam-sql
URL="postgresql+psycopg2://cysa_app:${CLOUDSQL_APP_PASSWORD}@/cysa_exam?host=/cloudsql/${CONN}"
echo -n "$URL" | gcloud secrets create cysa-exam-database-url --data-file=- --project=cybersecuritylab-509321
```

## One-time: seed questions (Cloud SQL Auth Proxy)

```bash
# Terminal A — do not use a public authorized-network hole for this
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

Mounts `SECRET_KEY` + `DATABASE_URL` from Secret Manager only, attaches
`--add-cloudsql-instances`, leaves `SESSION_COOKIE_SECURE` unset.
