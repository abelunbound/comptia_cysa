"""Tests to ensure signup and login forms actually render (not blank pages)."""

import os
import tempfile
import uuid

import pytest

from app import app as dash_app
from auth import db


@pytest.fixture
def client():
    """Create test client with temporary database."""
    os.environ["SECRET_KEY"] = "test-secret-key-form-rendering"
    
    db_fd, db_path = tempfile.mkstemp(suffix=f"_{uuid.uuid4().hex}.db")
    dash_app.server.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    dash_app.server.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    dash_app.server.config["TESTING"] = True
    dash_app.server.config["WTF_CSRF_ENABLED"] = False
    
    with dash_app.server.app_context():
        db.drop_all()
        db.create_all()
    
    with dash_app.server.test_client() as client:
        yield client
    
    with dash_app.server.app_context():
        db.drop_all()
    os.close(db_fd)
    os.unlink(db_path)


def test_signup_page_renders_form_fields(client):
    """GET /signup returns 200 and HTML contains email + password input fields.
    
    This test must fail if the page is a blank Dash shell.
    """
    response = client.get("/signup")
    
    assert response.status_code == 200, "Signup page should return 200"
    
    # Verify response is HTML
    assert response.content_type.startswith("text/html"), "Response should be HTML"
    
    html = response.data.decode('utf-8')
    
    # Verify form has email input field
    assert 'type="email"' in html, "Signup form must contain email input field"
    
    # Verify form has password input field
    assert 'type="password"' in html, "Signup form must contain password input field"
    
    # Verify form has a submit control (button or input[type=submit])
    assert ('type="submit"' in html or '<button' in html), \
        "Signup form must contain submit button"
    
    # Verify form uses POST method
    assert 'method="POST"' in html or 'method="post"' in html, \
        "Signup form must use POST method"


def test_login_page_renders_form_fields(client):
    """GET /login returns 200 and HTML contains email + password input fields.
    
    This test must fail if the page is a blank Dash shell.
    """
    response = client.get("/login")
    
    assert response.status_code == 200, "Login page should return 200"
    
    # Verify response is HTML
    assert response.content_type.startswith("text/html"), "Response should be HTML"
    
    html = response.data.decode('utf-8')
    
    # Verify form has email input field
    assert 'type="email"' in html, "Login form must contain email input field"
    
    # Verify form has password input field
    assert 'type="password"' in html, "Login form must contain password input field"
    
    # Verify form has a submit control (button or input[type=submit])
    assert ('type="submit"' in html or '<button' in html), \
        "Login form must contain submit button"
    
    # Verify form uses POST method
    assert 'method="POST"' in html or 'method="post"' in html, \
        "Login form must use POST method"


def test_signup_form_includes_csrf_token(client):
    """Signup form includes CSRF token for security."""
    response = client.get("/signup")
    html = response.data.decode('utf-8')
    
    # Verify CSRF token is present
    assert 'name="csrf_token"' in html, "Signup form must include CSRF token"


def test_login_form_includes_csrf_token(client):
    """Login form includes CSRF token for security."""
    response = client.get("/login")
    html = response.data.decode('utf-8')
    
    # Verify CSRF token is present
    assert 'name="csrf_token"' in html, "Login form must include CSRF token"
