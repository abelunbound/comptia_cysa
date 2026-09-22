"""Authentication module: User model, database setup, and auth utilities.

M2: one SQLAlchemy database for auth users and exam questions.
- Local/tests: SQLite (instance/users.db) when DATABASE_URL is unset.
- Cloud Run: PostgreSQL via DATABASE_URL (Cloud SQL Unix socket).
Passwords are hashed with bcrypt (never reversible).
"""

import os
from datetime import datetime

import bcrypt
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model, UserMixin):
    """User account for authentication and session management."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def set_password(self, password):
        """Hash and store a password using bcrypt."""
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def check_password(self, password):
        """Verify a password against the stored bcrypt hash."""
        return bcrypt.checkpw(
            password.encode("utf-8"), self.password_hash.encode("utf-8")
        )

    def __repr__(self):
        return f"<User {self.email}>"


class Question(db.Model):
    """Exam question row (seeded once from CSV; runtime reads via load_questions)."""

    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)
    domain = db.Column(db.String(200), nullable=False, index=True)
    sub_section = db.Column(db.String(100), nullable=False, index=True)
    subtopic = db.Column(db.String(300), nullable=False, default="")
    question = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.Text, nullable=False, default="")
    option_b = db.Column(db.Text, nullable=False, default="")
    option_c = db.Column(db.Text, nullable=False, default="")
    option_d = db.Column(db.Text, nullable=False, default="")
    correct_answer = db.Column(db.String(8), nullable=False)
    explanation = db.Column(db.Text, nullable=False, default="")

    def __repr__(self):
        return f"<Question {self.id} {self.domain}/{self.sub_section}>"


def get_database_url():
    """Return DATABASE_URL from env if set, else SQLite for local dev.

    Cloud Run (M2+) must set DATABASE_URL to the Cloud SQL Postgres URL
    (Unix socket host=/cloudsql/PROJECT:REGION:INSTANCE). Local/tests may
    omit it and use SQLite under instance/users.db.
    """
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        return database_url
    instance_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance")
    os.makedirs(instance_dir, exist_ok=True)
    return f"sqlite:///{os.path.join(instance_dir, 'users.db')}"


def init_auth(app):
    """Initialize database and create tables if needed.

    Call this once during app initialization (after app.config is set).
    """
    db.init_app(app)
    with app.app_context():
        db.create_all()


def create_user(email, password):
    """Create a new user account with hashed password.

    Returns (user, None) on success or (None, error_message) on failure.
    """
    if not email or "@" not in email:
        return None, "Invalid email address."
    if not password or len(password) < 8:
        return None, "Password must be at least 8 characters."

    existing = User.query.filter_by(email=email).first()
    if existing:
        return None, "An account with this email already exists."

    user = User(email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user, None


def authenticate_user(email, password):
    """Verify email and password credentials.

    Returns the User object on success, or None on failure.
    """
    user = User.query.filter_by(email=email).first()
    if user and user.is_active and user.check_password(password):
        return user
    return None
