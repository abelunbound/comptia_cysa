# CySA+ Domain Practice Exam

A Dash app for practicing CompTIA CySA+ exam questions. Pick a Domain and
Sub-Section, take a full exam question-by-question, submit it, and review
your results with a per-question breakdown.

## Setup

```bash
python -m venv venv
source venv/bin/activate  # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Authentication Setup

The app requires authentication to access exam, results, review, and admin
pages. Set up authentication as follows:

1. **Generate a SECRET_KEY** for session security:
   ```bash
   python -c 'import secrets; print(secrets.token_hex(32))'
   ```

2. **Set the SECRET_KEY environment variable**:
   ```bash
   export SECRET_KEY='your-generated-secret-key-here'
   ```
   
   On Windows:
   ```cmd
   set SECRET_KEY=your-generated-secret-key-here
   ```

3. **For local HTTP development** (http://127.0.0.1:8050), set:
   ```bash
   export SESSION_COOKIE_SECURE=false
   ```
   
   **IMPORTANT**: Do NOT set `SESSION_COOKIE_SECURE=false` in production.
   Production (Cloud Run with HTTPS) should always use secure cookies (this is
   the default). Without this setting locally, your browser won't keep the
   session cookie over HTTP.

4. **PostgreSQL is required** (no SQLite). For local work against staging Cloud
   SQL, start the Auth Proxy, then:
   ```bash
   cloud-sql-proxy bankpassport-be:us-central1:bankpassport --port=5432
   export DATABASE_URL='postgresql+psycopg2://cysa_app:<PASSWORD>@127.0.0.1:5432/cybersecuritylab'
   ```
   URL-encode reserved characters in the password. Staging Cloud Run uses the
   Unix-socket URL in Secret Manager `cysa-exam-database-url`.

   Or: `./scripts/run-local.sh` after `DATABASE_URL` is set.

### Creating the First User

After starting the app, visit `http://127.0.0.1:8050/signup` to create your
first user account. You'll need:
- A valid email address
- A password of at least 8 characters

Once signed up, you'll be automatically logged in and redirected to the exam
page.

## Run

```bash
export SESSION_COOKIE_SECURE=false
python app.py
# or: ./scripts/run-local.sh
```

Then open the URL printed in the terminal (typically `http://127.0.0.1:8050`).
Signup on localhost writes to the same `users` table as staging.

**Note**: You must be logged in to access the exam. If not logged in, you'll
be redirected to `/login`.

## Running Tests

To run the test suite locally:

```bash
# Isolated Postgres (never staging Cloud SQL)
docker run -d --name cysa-test-pg -p 5432:5432 \
  -e POSTGRES_USER=cysa_test -e POSTGRES_PASSWORD=cysa_test \
  -e POSTGRES_DB=cysa_test postgres:16

export TEST_DATABASE_URL='postgresql+psycopg2://cysa_test:cysa_test@127.0.0.1:5432/cysa_test'
export SECRET_KEY=test-local-secret

pytest -v tests/
pytest -v e2e/ --browser chromium   # first time: playwright install chromium
```

`tests/` is Flask-client / unit. `e2e/` is Playwright (login → exam paints → Dash).
CI starts `postgres:16` as a service; it does not use the staging database.

## Security Notes

- **Production runs with debug=False**: The `debug=True` in `app.py` only applies
  to local `python app.py` development. Cloud Run uses gunicorn (see `Dockerfile`),
  which keeps debug disabled and ensures secure session cookies (HTTPS-only).
- **Rate limiting**: Not implemented in M1. Signup/login rate-limiting is parked
  as a follow-on security enhancement.
- **Admin access**: Currently accessible to any logged-in user. Role-based access
  control will be added in a future milestone.

## Deployment

The app is deployed to Google Cloud Run. See [DEPLOYMENT.md](DEPLOYMENT.md)
for the live URL, the redeploy command, and one-time setup/troubleshooting
notes.

## How it works

1. On the home page, select a **Domain** (e.g. `Security Operations`) and a
   **Sub-Section** (e.g. `1.1`), then click **Exam Mode** or **Practice Mode**.
2. The exam includes **every question** matching that Domain + Sub-Section,
   in a shuffled order. Navigate with **Prev** / **Next** -- your answers
   are remembered as you move back and forth.
3. Click **Submit Exam** at any point (unanswered questions count as
   unanswered, not correct).
4. You're taken to the **Results** page: an overall performance donut chart
   (Correct / Wrong / Unanswered) and a **Your Progress** panel listing
   every attempt you've made this session, each with its own **Review**
   link.
5. **Review** shows every question from that attempt, with your answer and
   the correct answer clearly marked, plus the explanation for each.
6. Click the profile icon in the right-hand panel (visible on every quiz
   page) to see a static preview of a future **Admin Dashboard**.

## Layout

Exam/Results/Review pages use a 75% (white, page content) / 25% (solid
brand-color panel with the title and profile icon) shell, defined once in
`components/shell.py`. The Admin Dashboard uses its own full-page layout.

## Data source

`data_loader.load_questions()` reads the Postgres `questions` table and
returns a DataFrame with these columns (exam UI contract):

```
Domain, Sub-Section, Subtopic, Question, Option A, Option B, Option C, Option D, Correct Answer, Explanation
```

CSV (`cysa_plus_questions.csv`) is used only by `scripts/seed_questions.py`.
It is not read at runtime and is excluded from the Cloud Run image. An empty
table or a failed query raises; there is no SQLite or hardcoded fallback.

## Session state

`exam-session-store` holds a client-safe view of an in-progress exam (no
correct answers). Answers, scores, and completed history live in Postgres
(`exam_attempts` / `attempt_answers`).

## Project structure

```
comptia_cysa/
├── app.py                 # App init (use_pages=True), root stores, page_container
├── pages/
│   ├── exam.py              # '/'        setup + exam-taking flow
│   ├── results.py           # '/results' donut chart + session progress
│   ├── review.py            # '/review'  per-question breakdown
│   └── admin.py              # '/admin'   static admin dashboard mockup
├── components/
│   ├── shell.py              # shared 75/25 layout + branding panel + profile icon
│   └── ui.py                 # shared buttons, progress bar, score header, option builder
├── data_loader.py           # load_questions() -> DataFrame from Postgres
├── cysa_plus_questions.csv  # seed input only (not used at runtime)
├── scripts/seed_questions.py
├── scripts/run-local.sh
├── requirements.txt
└── README.md
```

## Out of scope (possible future additions)

- Per-question or total exam timers
- Persisting exam history to Postgres beyond the current browser session
- A functional (non-mockup), multi-user Admin Dashboard backed by real data
