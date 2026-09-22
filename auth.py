"""Authentication module: User model, database setup, and auth utilities.

For M1, this supports SQLite for local development and optional DATABASE_URL for
Cloud Run with Cloud SQL. Passwords are hashed with bcrypt (never reversible).
"""

import os
from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

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
        """Hash and store a password using bcrypt (via werkzeug)."""
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256")

    def check_password(self, password):
        """Verify a password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.email}>"


def get_database_url():
    """Return DATABASE_URL from env if set, else SQLite for local dev.
    
    Cloud Run deployments should set DATABASE_URL to a Cloud SQL connection
    string. Local dev falls back to SQLite stored in instance/users.db.
    """
    return os.environ.get("DATABASE_URL", "sqlite:///instance/users.db")


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
