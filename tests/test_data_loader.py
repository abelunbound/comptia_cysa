"""Tests for load_questions data seam (CSV local path)."""

from data_loader import REQUIRED_COLUMNS, load_questions


def test_load_questions_csv_has_required_columns(monkeypatch):
    """Without DATABASE_URL, load_questions uses CSV/fallback with required cols."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    df = load_questions()
    assert not df.empty
    assert REQUIRED_COLUMNS.issubset(set(df.columns))


def test_load_questions_postgres_flag(monkeypatch):
    """_uses_postgres is driven by DATABASE_URL scheme only."""
    from data_loader import _uses_postgres

    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert _uses_postgres() is False
    monkeypatch.setenv("DATABASE_URL", "sqlite:///tmp.db")
    assert _uses_postgres() is False
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg2://u:p@/db?host=/cloudsql/x:y:z",
    )
    assert _uses_postgres() is True
