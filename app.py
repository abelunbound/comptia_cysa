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
from flask import redirect, request
from flask_login import LoginManager, current_user
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

# Security: SESSION_COOKIE_SECURE defaults to True (HTTPS-only) for production.
# For local HTTP testing (http://127.0.0.1:8050), set SESSION_COOKIE_SECURE=false.
# Production (Cloud Run) should always use Secure=True (HTTPS).
secure_cookie_env = os.environ.get("SESSION_COOKIE_SECURE")
if secure_cookie_env is not None:
    # Explicit env override
    server.config["SESSION_COOKIE_SECURE"] = secure_cookie_env.lower() in ("true", "1", "yes")
else:
    # Default: False for local dev (FLASK_DEBUG=1 or development), True for prod
    is_dev = (
        os.environ.get("FLASK_DEBUG") == "1" or
        os.environ.get("ENV") == "development"
    )
    server.config["SESSION_COOKIE_SECURE"] = not is_dev

server.config["SESSION_COOKIE_HTTPONLY"] = True
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


# Flask routes for authentication (plain HTML forms, not Dash pages)
from flask import render_template
from flask_login import login_user, logout_user

from auth import authenticate_user, create_user


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


# HTTP-level page-load protection: redirect unauthenticated users before any UI renders
@server.before_request
def require_login():
    """Redirect unauthenticated users to /login for protected routes.
    
    Protected routes: /, /results, /review, /admin
    Public routes: /login, /signup, /logout, /assets/*, /_dash-*, /_reload-hash
    """
    # Allow public authentication routes
    if request.path in ("/login", "/signup", "/logout"):
        return None
    
    # Allow Dash internal routes and static assets
    if request.path.startswith(("/_dash-", "/assets/", "/_reload-hash")):
        return None
    
    # Protect all other routes (/, /results, /review, /admin, etc.)
    if not current_user.is_authenticated:
        return redirect("/login")
    
    return None


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
