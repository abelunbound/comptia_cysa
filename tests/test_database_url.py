"""Fail-fast: get_database_url never returns SQLite."""

import pytest

from auth import get_database_url


def test_get_database_url_requires_env(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL is required"):
        get_database_url()


def test_get_database_url_rejects_sqlite(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///instance/users.db")
    with pytest.raises(RuntimeError, match="SQLite is not supported"):
        get_database_url()


def test_get_database_url_rejects_non_postgres(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "mysql://u:p@localhost/db")
    with pytest.raises(RuntimeError, match="postgresql"):
        get_database_url()


def test_get_database_url_accepts_postgres(monkeypatch):
    url = "postgresql+psycopg2://cysa_app:x@127.0.0.1:5432/cybersecuritylab"
    monkeypatch.setenv("DATABASE_URL", url)
    assert get_database_url() == url
    assert not get_database_url().lower().startswith("sqlite")
