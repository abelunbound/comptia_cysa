"""CySA+ Domain Practice Exam - a multi-page Dash app.

Pages (see pages/):
- /        exam setup (Domain/Sub-Section) + question-by-question exam taking
- /results overall performance donut chart + this session's attempt history
- /review  per-question breakdown of a completed attempt
- /admin   static admin dashboard mockup, reached via the profile icon

Session-scoped state lives in two dcc.Store components below (outside the
page container so they survive navigation between pages, but reset when the
browser tab closes):

- exam-session-store: the exam currently in progress or just completed
- exam-history-store: every attempt completed so far this session
"""

import os

import dash
from dash import Dash, dcc, html
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

from auth import User, get_database_url, init_auth

app = Dash(__name__, use_pages=True, suppress_callback_exceptions=True)
app.title = "CySA+ Domain Practice Exam"
server = app.server

# Flask server configuration for secure sessions and authentication
secret_key = os.environ.get("SECRET_KEY")
if not secret_key:
    raise RuntimeError(
        "SECRET_KEY environment variable is required. "
        "Generate one with: python -c 'import secrets; print(secrets.token_hex(32))'"
    )

server.config["SECRET_KEY"] = secret_key
server.config["SQLALCHEMY_DATABASE_URI"] = get_database_url()
server.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Security: SESSION_COOKIE_SECURE must be True in production to enforce HTTPS-only
# cookies. Flask's server.debug is False by default when served via gunicorn (Cloud
# Run), ensuring secure cookies are enabled. The debug=True in __main__ below only
# affects local `python app.py` dev runs.
server.config["SESSION_COOKIE_HTTPONLY"] = True
server.config["SESSION_COOKIE_SECURE"] = not server.debug
server.config["SESSION_COOKIE_SAMESITE"] = "Lax"
server.config["PERMANENT_SESSION_LIFETIME"] = 86400  # 1 day in seconds

# Initialize authentication
init_auth(server)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(server)
login_manager.login_view = "/login"


@login_manager.user_loader
def load_user(user_id):
    """Load user from database by ID for Flask-Login session management."""
    return User.query.get(int(user_id))


# CSRF protection for state-changing requests
csrf = CSRFProtect(server)

app.layout = html.Div(
    [
        dcc.Store(id="exam-session-store", storage_type="session"),
        dcc.Store(id="exam-history-store", storage_type="session"),
        dash.page_container,
    ]
)

if __name__ == "__main__":
    # Local development only: debug=True enables auto-reload and detailed errors.
    # IMPORTANT: Production (Cloud Run) uses gunicorn via Dockerfile, which never
    # executes this block and keeps debug=False, ensuring SESSION_COOKIE_SECURE=True.
    app.run(debug=True)
