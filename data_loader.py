"""Question data source.

load_questions() is the single seam between the app and its data source.

M2+: when DATABASE_URL points at PostgreSQL, questions are loaded from the
`questions` table (ORM / parameterized SQL). CSV is not required at Cloud Run
runtime. Locally (no Postgres URL), the CSV path + hardcoded fallback remain.
"""

import logging
import os

import pandas as pd
from sqlalchemy import create_engine, text

from fallback_data import FALLBACK_QUESTIONS

CSV_PATH = "cysa_plus_questions.csv"

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

logger = logging.getLogger(__name__)

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


def _fallback_df() -> pd.DataFrame:
    logger.warning("Falling back to hardcoded question set.")
    return pd.DataFrame(FALLBACK_QUESTIONS)


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


def _uses_postgres() -> bool:
    url = (os.environ.get("DATABASE_URL") or "").strip().lower()
    return url.startswith("postgresql")


def _load_from_postgres() -> pd.DataFrame:
    """Load questions from Postgres via DATABASE_URL (Cloud SQL in prod)."""
    database_url = os.environ["DATABASE_URL"]
    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            df = pd.read_sql(_DB_SELECT, conn)
    except Exception as exc:  # noqa: BLE001 — fall back for resilience
        logger.error("Could not load questions from Postgres: %s", exc)
        return _fallback_df()

    df = _normalize_df(df)
    if df.empty:
        logger.warning("Postgres questions table empty or malformed; using fallback.")
        return _fallback_df()
    return df


def _load_from_csv() -> pd.DataFrame:
    try:
        df = pd.read_csv(CSV_PATH)
    except (FileNotFoundError, pd.errors.EmptyDataError, pd.errors.ParserError) as exc:
        logger.warning("Could not read %s: %s", CSV_PATH, exc)
        return _fallback_df()

    df = _normalize_df(df)
    if df.empty:
        logger.warning(
            "%s is empty or missing required columns %s.", CSV_PATH, REQUIRED_COLUMNS
        )
        return _fallback_df()
    return df


def load_questions() -> pd.DataFrame:
    """Load quiz questions from Postgres (M2+) or CSV/fallback (local)."""
    if _uses_postgres():
        return _load_from_postgres()
    return _load_from_csv()
