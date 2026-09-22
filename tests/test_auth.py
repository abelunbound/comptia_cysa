"""Unit tests for auth.py: user creation, password hashing, authentication."""

import os
import tempfile

import bcrypt
import pytest
from flask import Flask

from auth import User, authenticate_user, create_user, db, init_auth


@pytest.fixture
def test_app():
    """Create a test Flask app with temporary SQLite database."""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret-key"
    
    # Use temporary database
    db_fd, db_path = tempfile.mkstemp()
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["TESTING"] = True
    
    init_auth(app)
    
    yield app
    
    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def app_context(test_app):
    """Provide Flask app context for database operations."""
    with test_app.app_context():
        yield test_app


def test_create_user_with_bcrypt_hash(app_context):
    """Signup creates user with bcrypt-hashed password, not plaintext."""
    email = "test@example.com"
    password = "SecurePass123"
    
    user, error = create_user(email, password)
    
    assert error is None
    assert user is not None
    assert user.email == email
    
    # Verify password is hashed (not plaintext)
    assert user.password_hash != password
    
    # Verify it's a valid bcrypt hash
    assert user.password_hash.startswith("$2")  # bcrypt hashes start with $2
    
    # Verify we can check the password with bcrypt.checkpw
    assert bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8'))
    
    # Verify wrong password fails
    assert not bcrypt.checkpw("WrongPass".encode('utf-8'), user.password_hash.encode('utf-8'))


def test_create_user_validates_email(app_context):
    """User creation fails with invalid email."""
    user, error = create_user("", "password123")
    assert user is None
    assert "Invalid email" in error
    
    user, error = create_user("notemail", "password123")
    assert user is None
    assert "Invalid email" in error


def test_create_user_validates_password(app_context):
    """User creation fails with short password."""
    user, error = create_user("test@example.com", "short")
    assert user is None
    assert "at least 8 characters" in error


def test_create_user_prevents_duplicates(app_context):
    """User creation fails for duplicate email."""
    email = "duplicate@example.com"
    create_user(email, "password123")
    
    user, error = create_user(email, "password456")
    assert user is None
    assert "already exists" in error


def test_authenticate_user_succeeds_with_correct_password(app_context):
    """Login succeeds with correct password."""
    email = "login@example.com"
    password = "CorrectPassword123"
    
    create_user(email, password)
    
    user = authenticate_user(email, password)
    assert user is not None
    assert user.email == email


def test_authenticate_user_fails_with_wrong_password(app_context):
    """Login fails with wrong password."""
    email = "wrongpass@example.com"
    password = "CorrectPassword123"
    
    create_user(email, password)
    
    user = authenticate_user(email, "WrongPassword")
    assert user is None


def test_authenticate_user_fails_with_nonexistent_user(app_context):
    """Login fails for non-existent user."""
    user = authenticate_user("nonexistent@example.com", "password")
    assert user is None


def test_user_check_password_method(app_context):
    """User.check_password() correctly verifies passwords."""
    email = "checkpw@example.com"
    password = "TestPassword123"
    
    user, _ = create_user(email, password)
    
    assert user.check_password(password) is True
    assert user.check_password("WrongPassword") is False
