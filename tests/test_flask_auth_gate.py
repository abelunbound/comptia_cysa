"""Integration tests for Flask before_request auth gate and protected routes."""

import os

import pytest

from auth import create_user, db
from tests.conftest import reset_schema


@pytest.fixture
def client(dash_app):
    """Create test client on isolated CI Postgres."""
    os.environ["SECRET_KEY"] = "test-secret-key-for-client"
    dash_app.server.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]
    dash_app.server.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    dash_app.server.config["TESTING"] = True
    dash_app.server.config["WTF_CSRF_ENABLED"] = False

    with dash_app.server.app_context():
        reset_schema()
        db.create_all()

    with dash_app.server.test_client() as client:
        yield client

    with dash_app.server.app_context():
        reset_schema()


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


def test_unauthenticated_exams_redirects_to_login(client):
    response = client.get("/exams", follow_redirects=False)
    assert response.status_code == 302
    assert response.location == "/login"


def test_unauthenticated_admin_results_redirects_to_login(client):
    response = client.get("/admin/results", follow_redirects=False)
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


def test_signup_redirects_to_dashboard(client):
    response = client.post(
        "/signup",
        data={"email": "newuser@example.com", "password": "TestPassword123"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.location == "/admin"


def test_login_redirects_to_dashboard(client, dash_app):
    with dash_app.server.app_context():
        user, error = create_user("loginland@example.com", "TestPassword123")
        assert error is None, error

    response = client.post(
        "/login",
        data={"email": "loginland@example.com", "password": "TestPassword123"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.location == "/admin"


def test_authenticated_user_can_access_protected_routes(client, dash_app):
    """Authenticated session can GET protected routes with 200."""
    with dash_app.server.app_context():
        user, error = create_user("authuser@example.com", "TestPassword123")
        assert error is None, f"Failed to create user: {error}"
        user_id = user.id

    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True

    response = client.get("/", follow_redirects=False)
    assert response.status_code == 200

    response = client.get("/results", follow_redirects=False)
    assert response.status_code == 200

    response = client.get("/admin", follow_redirects=False)
    assert response.status_code == 200

    response = client.get("/exams", follow_redirects=False)
    assert response.status_code == 200

    response = client.get("/admin/results", follow_redirects=False)
    assert response.status_code == 200


def test_logout_clears_session(client, dash_app):
    """After logout, protected routes redirect again."""
    with dash_app.server.app_context():
        user, error = create_user("logoutuser@example.com", "TestPassword123")
        assert error is None, f"Failed to create user: {error}"
        user_id = user.id

    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True

    response = client.get("/", follow_redirects=False)
    assert response.status_code == 200

    with client.session_transaction() as sess:
        sess.clear()

    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert response.location == "/login"
