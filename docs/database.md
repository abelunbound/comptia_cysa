# Database architecture

Auth users and exam questions share **one** Cloud SQL Postgres database.
Cloud Run never stores credentials in source. This page is architecture,
grants, and secret *shape* only — no passwords and no filled-in URLs.

## Layout

| Piece | Value |
|---|---|
| App / Cloud Run project | `cybersecuritylab-509321` |
| Cloud Run service | `cysa-exam-app` (`us-central1`) |
| Cloud SQL project | `bankpassport-be` |
| Instance | `bankpassport` |
| Connection name | `bankpassport-be:us-central1:bankpassport` |
| Database | `cybersecuritylab` |
| App role | `cysa_app` (not `postgres`) |
| Tables | `users`, `questions` (same `DATABASE_URL`) |

Runtime path: Cloud Run `--add-cloudsql-instances` → Unix socket
`/cloudsql/bankpassport-be:us-central1:bankpassport`.

Local seed path: Cloud SQL Auth Proxy on `127.0.0.1:5432` (no
`0.0.0.0/0` authorized networks).

Do not create `cysa-exam-sql` or database `cysa_exam`. Those names were
placeholders in the first M2 draft.

## Secrets (app project)

| Secret | Purpose |
|---|---|
| `cysa-exam-secret-key` | Flask `SECRET_KEY` |
| `cysa-exam-database-url` | SQLAlchemy `DATABASE_URL` |

`DATABASE_URL` shape for Cloud Run (password is an env/placeholder, never
committed):

```
postgresql+psycopg2://cysa_app:${DB_PASSWORD}@/cybersecuritylab?host=/cloudsql/bankpassport-be:us-central1:bankpassport
```

Percent-encode `${DB_PASSWORD}` if it contains reserved URL characters.

Mount on Cloud Run with `--update-secrets`, never `--set-env-vars`.

## IAM grants

Cloud Run runtime SA
(`PROJECT_NUMBER-compute@developer.gserviceaccount.com`, currently
`104739181475-compute@developer.gserviceaccount.com`):

| Binding | Where |
|---|---|
| `roles/secretmanager.secretAccessor` on both secrets above | `cybersecuritylab-509321` |
| `roles/cloudsql.client` | `bankpassport-be` (instance project) |

`cysa_app` database grants (apply as `postgres` after tables exist):

```sql
GRANT CONNECT ON DATABASE cybersecuritylab TO cysa_app;
GRANT USAGE ON SCHEMA public TO cysa_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE users, questions TO cysa_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO cysa_app;
```

## Ops scripts

| Script | Role |
|---|---|
| `scripts/setup-cross-projects-db.sh` | Cross-account user/IAM/secret/Cloud Run attach. Reads `DB_PASSWORD` from the environment or a prompt. |
| `scripts/rotate-cysa-app-password.sh` | Rotate `cysa_app`, add a new secret version, refresh Cloud Run. Interactive password prompt. |
| `scripts/redeploy-cloud-run.sh` | Rebuild/deploy the app with both secrets + the bankpassport connection. |
| `scripts/seed_questions.py` | CSV → `questions` via Auth Proxy. Ops only; not used at runtime. Does not touch `users`. |
| `scripts/run-local.sh` | Local Dash against Auth Proxy Postgres. Requires `DATABASE_URL`. |

See `docs/M2-CLOUD-SQL.md` for the M2 runbook.
