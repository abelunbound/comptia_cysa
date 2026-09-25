"""CySA+ Domain Practice Exam - a multi-page Dash app.

Pages (see pages/):
- /        exam setup (Domain/Sub-Section) + question-by-question exam taking
- /results overall performance donut chart + this session's attempt history
- /review  per-question breakdown of a completed attempt
- /admin   static admin dashboard mockup, reached via the profile icon

exam-session-store holds a client-safe copy of the in-progress exam (no
correct answers). Postgres is the source of truth for answers, score, and
completed history.
"""

import os

import load_env  # noqa: F401 — local .env; does not override Cloud Run / CI env

import dash
from dash import Dash, dcc, html
from flask import Flask, has_request_context, redirect, render_template, request
from flask_login import LoginManager, current_user, login_user, logout_user
from flask_wtf.csrf import CSRFProtect

from auth import User, authenticate_user, create_user, db, get_database_url, init_auth

# Create Flask first and wire Flask-Login BEFORE Dash imports pages.
# Dash(use_pages=True) loads pages/*/layout functions that call current_user;
# if LoginManager is not on the server yet, that raises:
#   AttributeError: 'Flask' object has no attribute 'login_manager'
server = Flask(__name__)

secret_key = os.environ.get("SECRET_KEY")
if not secret_key:
    raise RuntimeError(
        "SECRET_KEY environment variable is required. "
        "Generate one with: python -c 'import secrets; print(secrets.token_hex(32))'"
    )

server.config["SECRET_KEY"] = secret_key
server.config["SQLALCHEMY_DATABASE_URI"] = get_database_url()
server.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# Cloud SQL / Auth Proxy drop idle sockets; ping before reuse so
# Flask-Login user_loader does not 500 the Dash page callback.
server.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

# SESSION_COOKIE_SECURE defaults to True (HTTPS-only) for production.
# For local HTTP testing (http://127.0.0.1:8050), set SESSION_COOKIE_SECURE=false.
secure_cookie_env = os.environ.get("SESSION_COOKIE_SECURE")
if secure_cookie_env is not None:
    server.config["SESSION_COOKIE_SECURE"] = secure_cookie_env.lower() in ("true", "1", "yes")
else:
    is_dev = (
        os.environ.get("FLASK_DEBUG") == "1"
        or os.environ.get("ENV") == "development"
    )
    server.config["SESSION_COOKIE_SECURE"] = not is_dev

server.config["SESSION_COOKIE_HTTPONLY"] = True
server.config["SESSION_COOKIE_SAMESITE"] = "Lax"
server.config["PERMANENT_SESSION_LIFETIME"] = 86400  # 1 day in seconds

init_auth(server)

login_manager = LoginManager()
login_manager.init_app(server)
login_manager.login_view = "/login"


@login_manager.user_loader
def load_user(user_id):
    """Load user from database by ID for Flask-Login session management."""
    return db.session.get(User, int(user_id))


# CSRF: Flask forms only, not Dash AJAX endpoints
server.config["WTF_CSRF_CHECK_DEFAULT"] = False
csrf = CSRFProtect(server)


def csrf_protect():
    """Protect Flask form routes with CSRF, but not Dash endpoints."""
    if request.path.startswith("/_dash"):
        return
    if request.method == "GET":
        return
    csrf.protect()


server.before_request(csrf_protect)


@server.route("/signup", methods=["GET", "POST"])
def signup():
    """Sign up page with email/password form."""
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user, error = create_user(email, password)
        if error:
            return render_template("signup.html", error=error)

        login_user(user)
        return redirect("/")

    return render_template("signup.html")


@server.route("/login", methods=["GET", "POST"])
def login():
    """Log in page with email/password form."""
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user = authenticate_user(email, password)
        if not user:
            return render_template("login.html", error="Invalid email or password.")

        login_user(user)
        return redirect("/")

    return render_template("login.html")


@server.route("/logout")
def logout():
    """Log out and redirect to login page."""
    logout_user()
    return redirect("/login")


@server.before_request
def require_login():
    """Redirect unauthenticated users to /login for protected routes.

    Protected routes: /, /results, /review, /admin
    Public routes: /login, /signup, /logout, /assets/*, /_dash-*, /_reload-hash
    """
    if request.path in ("/login", "/signup", "/logout"):
        return None

    if request.path.startswith(("/_dash-", "/assets/", "/_reload-hash")):
        return None

    if not current_user.is_authenticated:
        return redirect("/login")

    return None


# Dash mounts on the already-configured Flask server (pages can safely use current_user)
app = Dash(
    __name__,
    server=server,
    use_pages=True,
    suppress_callback_exceptions=True,
)
app.title = "CySA+ Domain Practice Exam"

def serve_layout():
    """Seed the store from Postgres so resume paints on the first layout."""
    session = None
    if has_request_context() and current_user.is_authenticated:
        from attempts import public_exam_session

        session = public_exam_session(current_user.id)
    return html.Div(
        [
            dcc.Store(id="exam-session-store", storage_type="session", data=session),
            dash.page_container,
        ]
    )


app.layout = serve_layout

if __name__ == "__main__":
    # Local development only: debug=True enables auto-reload and detailed errors.
    # Production (Cloud Run) uses gunicorn via Dockerfile and never executes this block.
    app.run(debug=True)
