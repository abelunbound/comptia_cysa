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

3. **(Optional) Configure database URL** for production. By default, the app
   uses SQLite (`instance/users.db`) for local development. For Cloud Run
   with Cloud SQL, set:
   ```bash
   export DATABASE_URL='postgresql://user:password@host/dbname'
   ```

### Creating the First User

After starting the app, visit `http://127.0.0.1:8050/signup` to create your
first user account. You'll need:
- A valid email address
- A password of at least 8 characters

Once signed up, you'll be automatically logged in and redirected to the exam
page.

## Run

```bash
python app.py
```

Then open the URL printed in the terminal (typically `http://127.0.0.1:8050`).

**Note**: You must be logged in to access the exam. If not logged in, you'll
be redirected to `/login`.

## Running Tests

To run the test suite locally:

```bash
# Install test dependencies
pip install pytest

# Run all tests
pytest -v tests/

# Run specific test file
pytest -v tests/test_auth.py
```

Tests cover:
- Auth module functions (user creation, password hashing, authentication)
- Flask `before_request` auth gate (protected route redirects)
- E2E smoke test (signup → logout → login → protected access)

**Note**: Tests use temporary SQLite databases and set `SECRET_KEY` automatically.

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
   **Sub-Section** (e.g. `1.1`), then click **Start Exam**.
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

Questions are loaded from `questions.csv` via `data_loader.load_questions()`.
The CSV must contain these columns:

```
Domain, Sub-Section, Subtopic, Question, Option A, Option B, Option C, Option D, Correct Answer, Explanation
```

`Correct Answer` should be the letter of the correct option (`A`, `B`, `C`,
or `D`).

### Fallback behavior

If `questions.csv` is missing, empty, or missing required columns,
`load_questions()` automatically falls back to the hardcoded questions in
`fallback_data.py` so the app always has something to serve. A warning is
logged to the console when this happens.

## Swapping in PostgreSQL later

`data_loader.load_questions()` is the only place that knows about the data
source. To move from CSV to PostgreSQL:

1. Add a DB driver to `requirements.txt` (e.g. `psycopg2-binary` or
   `SQLAlchemy`).
2. Replace the body of `load_questions()` with a query that returns a
   `pandas.DataFrame` with the same columns listed above, for example:

   ```python
   import sqlalchemy

   def load_questions() -> pd.DataFrame:
       engine = sqlalchemy.create_engine(DATABASE_URL)
       return pd.read_sql("SELECT * FROM questions", engine)
   ```

3. No changes are needed anywhere else in the app -- pages only ever
   consume the DataFrame returned by `load_questions()`.

## Session state

Two `dcc.Store(storage_type="session")` components hold state across page
navigation (they clear when the browser tab closes -- nothing is persisted
to disk beyond the question bank itself):

- `exam-session-store`: the exam currently in progress or just completed
- `exam-history-store`: every attempt completed so far this browser session

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
├── data_loader.py           # load_questions() -> DataFrame, CSV with fallback
├── fallback_data.py         # hardcoded fallback question records
├── questions.csv            # sample question bank
├── requirements.txt
└── README.md
```

## Out of scope (possible future additions)

- Per-question or total exam timers
- Persisting exam history beyond the current browser session (e.g. to a
  database) so progress survives a restart
- A functional (non-mockup), multi-user Admin Dashboard backed by real data
- Live PostgreSQL connection (only the `load_questions()` seam is prepared for it)
