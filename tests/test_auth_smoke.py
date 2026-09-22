"""E2E smoke test: signup → logout → login → protected page access."""

import os
import tempfile
import uuid

import pytest

from app import app as dash_app
from auth import User, authenticate_user, create_user, db


@pytest.fixture
def client():
    """Create test client with temporary database."""
    os.environ["SECRET_KEY"] = "test-secret-key-smoke"
    
    db_fd, db_path = tempfile.mkstemp(suffix=f"_{uuid.uuid4().hex}.db")
    dash_app.server.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    dash_app.server.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    dash_app.server.config["TESTING"] = True
    dash_app.server.config["WTF_CSRF_ENABLED"] = False
    
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


def test_smoke_signup_logout_login_protected_access(client):
    """E2E: signup → access protected → logout → login → access protected."""
    
    # Step 1: Verify signup page accessible
    response = client.get("/signup")
    assert response.status_code == 200
    
    # Step 2: Create user via auth helper (simulating signup)
    with dash_app.server.app_context():
        user, error = create_user("smoke@example.com", "SmokeTest123")
        assert error is None
        assert user is not None
        user_id = user.id  # Get ID inside app context
    
    # Step 3: Simulate login session
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True
    
    # Step 4: Verify authenticated user can access protected routes
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 200, "Authenticated user should access / (exam)"
    
    response = client.get("/results", follow_redirects=False)
    assert response.status_code == 200, "Authenticated user should access /results"
    
    response = client.get("/admin", follow_redirects=False)
    assert response.status_code == 200, "Authenticated user should access /admin"
    
    # Step 5: Logout
    response = client.get("/logout")
    assert response.status_code == 200
    
    # Clear session manually (clientside callback doesn't execute in test client)
    with client.session_transaction() as sess:
        sess.clear()
    
    # Step 6: Verify logged-out user redirected from protected routes
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert response.location == "/login", "Logged-out user should redirect to /login"
    
    # Step 7: Re-authenticate (simulating login)
    with dash_app.server.app_context():
        authenticated_user = authenticate_user("smoke@example.com", "SmokeTest123")
        assert authenticated_user is not None, "Login should succeed with correct password"
        reauth_user_id = authenticated_user.id
    
    with client.session_transaction() as sess:
        sess["_user_id"] = str(reauth_user_id)
        sess["_fresh"] = True
    
    # Step 8: Verify re-authenticated user can access protected routes again
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 200, "Re-authenticated user should access / (exam)"
    
    # Step 9: Verify wrong password fails
    with dash_app.server.app_context():
        failed_auth = authenticate_user("smoke@example.com", "WrongPassword")
        assert failed_auth is None, "Login should fail with wrong password"
