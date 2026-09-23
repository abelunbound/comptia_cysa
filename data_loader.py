"""Question data source.

load_questions() is the single seam between the app and the questions table.
It always reads PostgreSQL via DATABASE_URL and returns a DataFrame with the
exam UI column names. CSV is seed-only (scripts/seed_questions.py), never
read at runtime.
"""

import os

import pandas as pd
from sqlalchemy import create_engine, text

REQUIRED_COLUMNS = {
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

_DB_SELECT = text(
    """
    SELECT
        domain AS "Domain",
        sub_section AS "Sub-Section",
        subtopic AS "Subtopic",
        question AS "Question",
        option_a AS "Option A",
        option_b AS "Option B",
        option_c AS "Option C",
        option_d AS "Option D",
        correct_answer AS "Correct Answer",
        explanation AS "Explanation"
    FROM questions
    """
)


def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(col).strip() for col in df.columns]
    if df.empty or not REQUIRED_COLUMNS.issubset(set(df.columns)):
        return pd.DataFrame()
    df = df.dropna(subset=["Question", "Correct Answer"])
    if df.empty:
        return df
    for col in ["Domain", "Sub-Section", "Correct Answer"]:
        df[col] = df[col].astype(str).str.strip()
    return df.reset_index(drop=True)


def load_questions() -> pd.DataFrame:
    """Load quiz questions from Postgres. Raises if URL/query/table is unusable."""
    database_url = (os.environ.get("DATABASE_URL") or "").strip()
    if not database_url.lower().startswith("postgresql"):
        raise RuntimeError(
            "DATABASE_URL must be a postgresql:// or postgresql+psycopg2:// URL "
            "to load questions. CSV is not used at runtime."
        )
    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            df = pd.read_sql(_DB_SELECT, conn)
    except Exception as exc:
        raise RuntimeError(f"Could not load questions from Postgres: {exc}") from exc

    df = _normalize_df(df)
    if df.empty:
        raise RuntimeError(
            "questions table is empty or malformed. "
            "Seed with: python scripts/seed_questions.py"
        )
    return df
