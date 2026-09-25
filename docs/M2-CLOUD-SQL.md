# Milestone 2 — Cloud SQL Postgres

M2 puts **auth users and exam questions** on one Cloud SQL Postgres database.
Cloud Run requires `DATABASE_URL` (Secret Manager) and a Cloud SQL connection.
See also `docs/database.md` and `scripts/redeploy-cloud-run.sh`.

Do **not** create a new instance named `cysa-exam-sql` or a database named
`cysa_exam`. Those were the original M2 placeholders. The live instance is
the existing shared `bankpassport` instance.

| | |
|---|---|
| **Instance** | `bankpassport` (project `bankpassport-be`) |
| **Connection name** | `bankpassport-be:us-central1:bankpassport` |
| **Database** | `cybersecuritylab` |
| **App user** | `cysa_app` (least privilege — not the `postgres` superuser) |
| **Secrets** | `cysa-exam-secret-key`, `cysa-exam-database-url` (in `cybersecuritylab-509321`) |

## Security constraints (required)

1. **No public `0.0.0.0/0` authorized networks.** Do not add `0.0.0.0/0` (or any
   broad CIDR) under Cloud SQL Connections. Prefer **no public IP** if your
   VPC setup allows; otherwise leave public IP with **empty** authorized
   networks and connect only via:
   - Cloud SQL Auth Proxy (local seed), and
   - Cloud Run `--add-cloudsql-instances` / Unix socket (runtime).
2. **Least-privilege `cysa_app`.** Create the DB objects as `postgres`, then
   grant `cysa_app` only table privileges on `users`, `questions`,
   `exam_attempts`, and `attempt_answers` (see grants below). Never use the
   `postgres` superuser password in Cloud Run
   or in `DATABASE_URL`.
3. **`DATABASE_URL` only via Secret Manager** (`cysa-exam-database-url`). Never
   pass it with plaintext `--set-env-vars`.

## One-time: instance side (already exists)

The instance, database, and `cysa_app` user already exist. Cross-project IAM
and the Secret Manager URL are applied by:

```bash
# From repo root. Prompts for DB_PASSWORD (or use export DB_PASSWORD=...).
# Do not put a password in the script or commit it.
bash scripts/setup-cross-projects-db.sh
```

To rotate the app-user password later: `bash scripts/rotate-cysa-app-password.sh`.

After first app connect / `db.create_all()` (or seed), grant least privilege
(as `postgres` via Auth Proxy):

```sql
GRANT CONNECT ON DATABASE cybersecuritylab TO cysa_app;
GRANT USAGE ON SCHEMA public TO cysa_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE users, questions, exam_attempts, attempt_answers TO cysa_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO cysa_app;
-- Optional: revoke anything broader if you created objects as postgres first
```

## One-time: DATABASE_URL secret (Unix socket for Cloud Run)

`setup-cross-projects-db.sh` writes this secret. Shape only (password from env):

```bash
CONN=bankpassport-be:us-central1:bankpassport
URL="postgresql+psycopg2://cysa_app:${DB_PASSWORD}@/cybersecuritylab?host=/cloudsql/${CONN}"
# echo -n "$URL" | gcloud secrets versions add cysa-exam-database-url --data-file=- \
#   --project=cybersecuritylab-509321
```

URL-encode `DB_PASSWORD` if it contains `@ : / ? # &`.

## One-time: seed questions (Cloud SQL Auth Proxy)

```bash
# Terminal A — do not use a public authorized-network hole for this
cloud-sql-proxy bankpassport-be:us-central1:bankpassport --port=5432

# Terminal B (repo root)
export DATABASE_URL="postgresql+psycopg2://cysa_app:${DB_PASSWORD}@127.0.0.1:5432/cybersecuritylab"
pip install -r requirements.txt
python scripts/seed_questions.py
```

CSV is used **only** for this seed. Runtime (`python app.py` and Cloud Run)
loads questions via `load_questions()` from Postgres only. SQLite is not
supported. Local app:

```bash
export DATABASE_URL="postgresql+psycopg2://cysa_app:${DB_PASSWORD}@127.0.0.1:5432/cybersecuritylab"
export SESSION_COOKIE_SECURE=false
./scripts/run-local.sh
```

Tests use an ephemeral `cysa_test` Postgres (CI service), not this database.

## Redeploy (M2)

```bash
git checkout feat/m2-cloud-sql-postgres && git pull
chmod +x scripts/redeploy-cloud-run.sh
./scripts/redeploy-cloud-run.sh
```

Mounts `SECRET_KEY` + `DATABASE_URL` from Secret Manager only, attaches
`--add-cloudsql-instances=bankpassport-be:us-central1:bankpassport`, leaves
`SESSION_COOKIE_SECURE` unset.
