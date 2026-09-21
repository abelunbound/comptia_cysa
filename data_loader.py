"""Question data source.

load_questions() is the single seam between the app and its data source.
Today it reads from a local CSV file and falls back to a hardcoded set of
questions if the CSV is missing, empty, or malformed. When you're ready to
move to PostgreSQL, replace the body of load_questions() with a query
(e.g. via SQLAlchemy/psycopg) that returns a DataFrame with the same
columns -- no other part of the app needs to change.
"""

import logging

import pandas as pd

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


def _fallback_df() -> pd.DataFrame:
    logger.warning("Falling back to hardcoded question set.")
    return pd.DataFrame(FALLBACK_QUESTIONS)


def load_questions() -> pd.DataFrame:
    """Load quiz questions, falling back to hardcoded data on any problem."""
    try:
        df = pd.read_csv(CSV_PATH)
    except (FileNotFoundError, pd.errors.EmptyDataError, pd.errors.ParserError) as exc:
        logger.warning("Could not read %s: %s", CSV_PATH, exc)
        return _fallback_df()

    df.columns = [str(col).strip() for col in df.columns]

    if df.empty or not REQUIRED_COLUMNS.issubset(set(df.columns)):
        logger.warning(
            "%s is empty or missing required columns %s.", CSV_PATH, REQUIRED_COLUMNS
        )
        return _fallback_df()

    # Drop rows that are missing critical fields (e.g. blank lines).
    df = df.dropna(subset=["Question", "Correct Answer"])
    if df.empty:
        return _fallback_df()

    for col in ["Domain", "Sub-Section", "Correct Answer"]:
        df[col] = df[col].astype(str).str.strip()

    return df.reset_index(drop=True)
