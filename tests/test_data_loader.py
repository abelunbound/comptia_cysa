"""Tests for load_questions data seam (CSV local path + Postgres contract)."""

import pandas as pd

from data_loader import REQUIRED_COLUMNS, load_questions

# Columns the exam UI reads (pages/exam.py). Must stay stable if the source
# switches from CSV to the questions table.
EXAM_UI_COLUMNS = {
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


def test_load_questions_csv_has_required_columns(monkeypatch):
    """Without DATABASE_URL, load_questions uses CSV/fallback with required cols."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    df = load_questions()
    assert not df.empty
    assert REQUIRED_COLUMNS.issubset(set(df.columns))
    assert EXAM_UI_COLUMNS.issubset(set(df.columns))


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


def test_load_questions_postgres_keeps_exam_dataframe_contract(monkeypatch):
    """Postgres path aliases snake_case columns to the exam UI CSV names."""
    db_rows = pd.DataFrame(
        [
            {
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
    assert EXAM_UI_COLUMNS.issubset(set(df.columns))
    # Exam start_exam filters on these two columns then to_dict("records").
    pool = df[
        (df["Domain"] == "1.0 Security Operations")
        & (df["Sub-Section"] == "1.1 Explain concepts")
    ]
    record = pool.to_dict("records")[0]
    assert record["Option B"] == "B"
    assert record["Question"] == "What is ingestion?"
