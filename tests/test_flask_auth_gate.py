"""Integration tests for Flask before_request auth gate and protected routes."""

import os
import tempfile
import uuid

import pytest
from flask_login import login_user

from app import app as dash_app
from auth import User, create_user, db


@pytest.fixture
def client():
    """Create test client with temporary database."""
    # Set required env var
    os.environ["SECRET_KEY"] = "test-secret-key-for-client"
    
    # Use temporary database with unique name
    db_fd, db_path = tempfile.mkstemp(suffix=f"_{uuid.uuid4().hex}.db")
    dash_app.server.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    dash_app.server.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    dash_app.server.config["TESTING"] = True
    dash_app.server.config["WTF_CSRF_ENABLED"] = False  # Disable CSRF for tests
    
    # Recreate all tables for this test
    with dash_app.server.app_context():
        db.drop_all()
        db.create_all()
    
    with dash_app.server.test_client() as client:
        yield client
    
    # Cleanup
    with dash_app.server.app_context():
        db.drop_all()
    os.close(db_fd)
    os.unlink(db_path)


def test_unauthenticated_root_redirects_to_login(client):
    """Unauthenticated GET / redirects to /login (302)."""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert response.location == "/login"


def test_unauthenticated_results_redirects_to_login(client):
    """Unauthenticated GET /results redirects to /login (302)."""
    response = client.get("/results", follow_redirects=False)
    assert response.status_code == 302
    assert response.location == "/login"


def test_unauthenticated_admin_redirects_to_login(client):
    """Unauthenticated GET /admin redirects to /login (302)."""
    response = client.get("/admin", follow_redirects=False)
    assert response.status_code == 302
    assert response.location == "/login"


def test_unauthenticated_review_redirects_to_login(client):
    """Unauthenticated GET /review redirects to /login (302)."""
    response = client.get("/review", follow_redirects=False)
    assert response.status_code == 302
    assert response.location == "/login"


def test_login_page_accessible_without_auth(client):
    """GET /login is accessible without authentication (200)."""
    response = client.get("/login", follow_redirects=False)
    assert response.status_code == 200


def test_signup_page_accessible_without_auth(client):
    """GET /signup is accessible without authentication (200)."""
    response = client.get("/signup", follow_redirects=False)
    assert response.status_code == 200


def test_authenticated_user_can_access_protected_routes(client):
    """Authenticated session can GET protected routes with 200."""
    with dash_app.server.app_context():
        # Create test user
        user, error = create_user("authuser@example.com", "TestPassword123")
        assert error is None, f"Failed to create user: {error}"
        user_id = user.id
    
    # Simulate login
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True
    
    # Now authenticated requests should succeed
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 200
    
    response = client.get("/results", follow_redirects=False)
    assert response.status_code == 200
    
    response = client.get("/admin", follow_redirects=False)
    assert response.status_code == 200


def test_logout_clears_session(client):
    """After logout, protected routes redirect again."""
    with dash_app.server.app_context():
        # Create and login user
        user, error = create_user("logoutuser@example.com", "TestPassword123")
        assert error is None, f"Failed to create user: {error}"
        user_id = user.id
    
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True
    
    # Verify authenticated access works
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 200
    
    # Clear session manually (simulating logout)
    # Note: The /logout page uses clientside callback which doesn't execute in test client
    with client.session_transaction() as sess:
        sess.clear()
    
    # After logout, protected routes should redirect
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert response.location == "/login"
