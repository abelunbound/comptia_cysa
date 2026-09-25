"""Tests for load_questions Postgres DataFrame contract."""

import pandas as pd
import pytest

from data_loader import REQUIRED_COLUMNS, load_questions

EXAM_UI_COLUMNS = {
    "id",
    "Domain",
    "Sub-Section",
    "Subtopic",
    "Question",
    "Option A",
    "Option B",
    "Option C",
    "Option D",
    "Correct Answer",
    "Explanation",
}


def test_load_questions_rejects_missing_or_sqlite_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="postgresql"):
        load_questions()
    monkeypatch.setenv("DATABASE_URL", "sqlite:///tmp.db")
    with pytest.raises(RuntimeError, match="postgresql"):
        load_questions()


def test_load_questions_raises_when_query_fails(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg2://u:p@127.0.0.1:1/missing",
    )
    with pytest.raises(RuntimeError, match="Could not load questions"):
        load_questions()


def test_load_questions_raises_when_table_empty(monkeypatch):
    empty = pd.DataFrame()

    class _FakeConn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class _FakeEngine:
        def connect(self):
            return _FakeConn()

    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg2://u:p@/cybersecuritylab?host=/cloudsql/x:y:z",
    )
    monkeypatch.setattr("data_loader.create_engine", lambda _url: _FakeEngine())
    monkeypatch.setattr("data_loader.pd.read_sql", lambda *_a, **_k: empty)
    with pytest.raises(RuntimeError, match="empty or malformed"):
        load_questions()


def test_load_questions_postgres_keeps_exam_dataframe_contract(monkeypatch):
    """Postgres path aliases snake_case columns to the exam UI names."""
    db_rows = pd.DataFrame(
        [
            {
                "id": 1,
                "Domain": "1.0 Security Operations",
                "Sub-Section": "1.1 Explain concepts",
                "Subtopic": "Logging Concepts",
                "Question": "What is ingestion?",
                "Option A": "A",
                "Option B": "B",
                "Option C": "C",
                "Option D": "D",
                "Correct Answer": "B",
                "Explanation": "Because.",
            }
        ]
    )

    class _FakeConn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class _FakeEngine:
        def connect(self):
            return _FakeConn()

    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg2://u:p@/cybersecuritylab?host=/cloudsql/x:y:z",
    )
    monkeypatch.setattr("data_loader.create_engine", lambda _url: _FakeEngine())
    monkeypatch.setattr("data_loader.pd.read_sql", lambda *_a, **_k: db_rows.copy())

    df = load_questions()
    assert list(df["Domain"]) == ["1.0 Security Operations"]
    assert list(df["Sub-Section"]) == ["1.1 Explain concepts"]
    assert list(df["Correct Answer"]) == ["B"]
    assert REQUIRED_COLUMNS.issubset(set(df.columns))
    assert EXAM_UI_COLUMNS.issubset(set(df.columns))
    pool = df[
        (df["Domain"] == "1.0 Security Operations")
        & (df["Sub-Section"] == "1.1 Explain concepts")
    ]
    record = pool.to_dict("records")[0]
    assert record["Option B"] == "B"
    assert record["Question"] == "What is ingestion?"
