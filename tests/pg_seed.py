"""Minimal question row so exam.py can import against CI Postgres."""

from sqlalchemy import create_engine, func, select

from auth import Question, db

QUESTION_VALUES = {
    "domain": "1.0 Security Operations",
    "sub_section": "1.1 Explain concepts",
    "subtopic": "Logging Concepts",
    "question": "What is ingestion?",
    "option_a": "A",
    "option_b": "B",
    "option_c": "C",
    "option_d": "D",
    "correct_answer": "B",
    "explanation": "Because.",
}


def ensure_schema_and_one_question(database_url: str) -> None:
    """Create tables and insert one question if the table is empty."""
    engine = create_engine(database_url)
    db.metadata.create_all(engine)
    with engine.begin() as conn:
        count = conn.execute(select(func.count()).select_from(Question.__table__)).scalar()
        if not count:
            conn.execute(Question.__table__.insert().values(**QUESTION_VALUES))
    engine.dispose()
