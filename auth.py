"""Authentication module: User model, database setup, and auth utilities.

Users, questions, and exam attempts share one PostgreSQL database (DATABASE_URL required).
SQLite is not supported. Passwords are hashed with bcrypt (never reversible).
"""

import os
from datetime import datetime

import bcrypt
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Index, text

db = SQLAlchemy()


class User(db.Model, UserMixin):
    """User account for authentication and session management."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    attempts = db.relationship(
        "ExamAttempt",
        back_populates="user",
        cascade="all, delete-orphan",
    )

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


class ExamAttempt(db.Model):
    """One exam sitting for a logged-in user. Score is server-set on complete."""

    __tablename__ = "exam_attempts"

    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_ABANDONED = "abandoned"
    MODE_EXAM = "exam"
    MODE_PRACTICE = "practice"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = db.Column(db.String(20), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    score_correct = db.Column(db.Integer, nullable=True)
    score_total = db.Column(db.Integer, nullable=True)
    current_index = db.Column(db.Integer, nullable=False, default=0)
    domain = db.Column(db.String(200), nullable=False, default="", server_default="")
    subsection = db.Column(db.String(100), nullable=False, default="", server_default="")
    question_ids = db.Column(db.JSON, nullable=False, default=list, server_default=text("'[]'"))
    mode = db.Column(
        db.String(20),
        nullable=False,
        default="exam",
        server_default="exam",
    )

    user = db.relationship("User", back_populates="attempts")
    answers = db.relationship(
        "AttemptAnswer",
        back_populates="attempt",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index(
            "uq_exam_attempts_one_in_progress_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'in_progress'"),
        ),
    )

    def __repr__(self):
        return f"<ExamAttempt {self.id} user={self.user_id} {self.status}>"


class AttemptAnswer(db.Model):
    """User's selected option for one question on an attempt. No grade columns."""

    __tablename__ = "attempt_answers"

    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(
        db.Integer,
        db.ForeignKey("exam_attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id = db.Column(
        db.Integer,
        db.ForeignKey("questions.id"),
        nullable=False,
    )
    selected_option = db.Column(db.String(8), nullable=False)
    answered_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    attempt = db.relationship("ExamAttempt", back_populates="answers")

    __table_args__ = (
        db.UniqueConstraint(
            "attempt_id",
            "question_id",
            name="uq_attempt_answers_attempt_question",
        ),
    )

    def __repr__(self):
        return f"<AttemptAnswer attempt={self.attempt_id} q={self.question_id}>"


def get_database_url():
    """Return DATABASE_URL. Postgres only — never SQLite.

    Local (Auth Proxy): postgresql+psycopg2://cysa_app:...@127.0.0.1:5432/cybersecuritylab
    Staging (Cloud Run): Unix-socket URL from Secret Manager cysa-exam-database-url
    Tests/CI: ephemeral Postgres via TEST_DATABASE_URL (see tests/conftest.py)
    """
    database_url = (os.environ.get("DATABASE_URL") or "").strip()
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is required (PostgreSQL). "
            "Local: start Cloud SQL Auth Proxy, then set "
            "postgresql+psycopg2://cysa_app:<PASSWORD>@127.0.0.1:5432/cybersecuritylab. "
            "Staging: mount Secret Manager cysa-exam-database-url."
        )
    lowered = database_url.lower()
    if lowered.startswith("sqlite"):
        raise RuntimeError(
            "SQLite is not supported. Set DATABASE_URL to a postgresql:// "
            "or postgresql+psycopg2:// URL."
        )
    if not lowered.startswith("postgresql"):
        raise RuntimeError(
            "DATABASE_URL must be a postgresql:// or postgresql+psycopg2:// URL."
        )
    return database_url


def _ensure_exam_attempt_columns():
    """Add M3 columns if create_all already ran against an older exam_attempts table."""
    statements = (
        "ALTER TABLE exam_attempts ADD COLUMN IF NOT EXISTS domain VARCHAR(200) NOT NULL DEFAULT ''",
        "ALTER TABLE exam_attempts ADD COLUMN IF NOT EXISTS subsection VARCHAR(100) NOT NULL DEFAULT ''",
        "ALTER TABLE exam_attempts ADD COLUMN IF NOT EXISTS question_ids JSON NOT NULL DEFAULT '[]'",
        "ALTER TABLE exam_attempts ADD COLUMN IF NOT EXISTS mode VARCHAR(20) NOT NULL DEFAULT 'exam'",
    )
    with db.engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


def init_auth(app):
    """Initialize database and create tables if needed.

    Call this once during app initialization (after app.config is set).
    """
    db.init_app(app)
    with app.app_context():
        db.create_all()
        _ensure_exam_attempt_columns()


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
