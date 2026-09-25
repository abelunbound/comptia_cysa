#!/usr/bin/env python3
"""One-shot seed: load cysa_plus_questions.csv into the questions table.

Usage (from repo root):

  export DATABASE_URL='postgresql+psycopg2://cysa_app:PASSWORD@/cybersecuritylab?host=/cloudsql/bankpassport-be:us-central1:bankpassport'
  # or local Cloud SQL Auth Proxy: postgresql+psycopg2://cysa_app:PASSWORD@127.0.0.1:5432/cybersecuritylab
  python scripts/seed_questions.py

Safe to re-run: clears existing questions rows then re-inserts from CSV.
Does not touch users, exam_attempts, or attempt_answers. Re-seed fails if
attempt_answers still reference questions.
"""

from __future__ import annotations

import os
import sys

import pandas as pd
from flask import Flask

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import load_env  # noqa: E402, F401 — local .env before DATABASE_URL is read
from auth import Question, db, get_database_url  # noqa: E402

CSV_PATH = os.path.join(ROOT, "cysa_plus_questions.csv")

COLUMN_MAP = {
    "Domain": "domain",
    "Sub-Section": "sub_section",
    "Subtopic": "subtopic",
    "Question": "question",
    "Option A": "option_a",
    "Option B": "option_b",
    "Option C": "option_c",
    "Option D": "option_d",
    "Correct Answer": "correct_answer",
    "Explanation": "explanation",
}


def main() -> int:
    if not os.environ.get("DATABASE_URL"):
        print("error: set DATABASE_URL to the target Postgres database.", file=sys.stderr)
        return 1
    if not os.path.isfile(CSV_PATH):
        print(f"error: missing {CSV_PATH}", file=sys.stderr)
        return 1

    df = pd.read_csv(CSV_PATH)
    df.columns = [str(c).strip() for c in df.columns]
    missing = [c for c in COLUMN_MAP if c not in df.columns]
    if missing:
        print(f"error: CSV missing columns: {missing}", file=sys.stderr)
        return 1

    df = df.dropna(subset=["Question", "Correct Answer"])
    for col in ["Domain", "Sub-Section", "Correct Answer"]:
        df[col] = df[col].astype(str).str.strip()

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = get_database_url()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    with app.app_context():
        db.create_all()
        deleted = Question.query.delete()
        db.session.commit()
        print(f"cleared {deleted} existing question row(s)")

        rows = []
        for _, record in df.iterrows():
            rows.append(
                Question(
                    domain=str(record["Domain"]),
                    sub_section=str(record["Sub-Section"]),
                    subtopic=str(record.get("Subtopic") or ""),
                    question=str(record["Question"]),
                    option_a=str(record.get("Option A") or ""),
                    option_b=str(record.get("Option B") or ""),
                    option_c=str(record.get("Option C") or ""),
                    option_d=str(record.get("Option D") or ""),
                    correct_answer=str(record["Correct Answer"]).strip().upper()[:8],
                    explanation=str(record.get("Explanation") or ""),
                )
            )
        db.session.bulk_save_objects(rows)
        db.session.commit()
        print(f"seeded {len(rows)} questions into {get_database_url().split('@')[-1]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
