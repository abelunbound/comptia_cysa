"""M3 #17: persist answers, server-side score, AuthZ, answer secrecy."""

from datetime import datetime

import os

import pytest
from flask import Flask

from attempts import (
    abandon_attempt,
    complete_attempt,
    get_in_progress_attempt,
    list_completed_summaries,
    public_exam_session,
    review_payload,
    save_selected_option,
    start_attempt,
)
from auth import AttemptAnswer, ExamAttempt, Question, create_user, db, init_auth
from tests.pg_seed import QUESTION_VALUES


@pytest.fixture
def app_context():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["TESTING"] = True

    init_auth(app)
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.drop_all()


def _user(email="owner@example.com"):
    user, error = create_user(email, "password123")
    assert error is None
    return user


def _question(correct="B"):
    values = dict(QUESTION_VALUES)
    values["correct_answer"] = correct
    question = Question(**values)
    db.session.add(question)
    db.session.commit()
    return question


def test_start_persists_in_progress_and_reuses_existing(app_context):
    user = _user()
    question = _question()
    first = start_attempt(user.id, "Dom", "Sub", [question.id])
    second = start_attempt(user.id, "Other", "Other", [question.id])
    assert first.id == second.id
    assert get_in_progress_attempt(user.id).id == first.id
    assert ExamAttempt.query.filter_by(user_id=user.id).count() == 1


def test_save_answer_upserts_and_rejects_other_user(app_context):
    owner = _user("owner@example.com")
    other = _user("other@example.com")
    question = _question()
    attempt = start_attempt(owner.id, "Dom", "Sub", [question.id])

    assert save_selected_option(other.id, attempt.id, question.id, "A") is None
    assert save_selected_option(owner.id, attempt.id, question.id, "A") is not None
    assert save_selected_option(owner.id, attempt.id, question.id, "C") is not None
    rows = AttemptAnswer.query.filter_by(attempt_id=attempt.id).all()
    assert len(rows) == 1
    assert rows[0].selected_option == "C"


def test_complete_scores_from_db_not_client_payload(app_context):
    user = _user()
    question = _question("B")
    attempt = start_attempt(user.id, "Dom", "Sub", [question.id])
    save_selected_option(user.id, attempt.id, question.id, "B")

    completed = complete_attempt(user.id, attempt.id)
    assert completed.status == ExamAttempt.STATUS_COMPLETED
    assert completed.score_correct == 1
    assert completed.score_total == 1
    assert completed.completed_at is not None

    # Client cannot complete someone else's attempt or re-complete.
    assert complete_attempt(user.id, attempt.id) is None
    other = _user("other@example.com")
    assert complete_attempt(other.id, attempt.id) is None


def test_complete_wrong_answer_scores_zero(app_context):
    user = _user()
    question = _question("B")
    attempt = start_attempt(user.id, "Dom", "Sub", [question.id])
    save_selected_option(user.id, attempt.id, question.id, "A")
    completed = complete_attempt(user.id, attempt.id)
    assert completed.score_correct == 0
    assert completed.score_total == 1


def test_practice_and_exam_modes_score_the_same(app_context):
    user = _user()
    question = _question("B")
    exam = start_attempt(user.id, "Dom", "Sub", [question.id], mode=ExamAttempt.MODE_EXAM)
    save_selected_option(user.id, exam.id, question.id, "B")
    complete_attempt(user.id, exam.id)
    practice = start_attempt(
        user.id, "Dom", "Sub", [question.id], mode=ExamAttempt.MODE_PRACTICE
    )
    save_selected_option(user.id, practice.id, question.id, "B")
    complete_attempt(user.id, practice.id)
    summaries = list_completed_summaries(user.id)
    assert len(summaries) == 2
    assert {row["score"] for row in summaries} == {1}
    assert "mode" not in summaries[0]


def test_public_session_hides_answers_and_explanations(app_context):
    user = _user()
    question = _question("B")
    attempt = start_attempt(user.id, "Dom", "Sub", [question.id])
    save_selected_option(user.id, attempt.id, question.id, "A")
    session = public_exam_session(user.id, attempt)
    assert session["attempt_id"] == attempt.id
    assert session["answers"] == {"0": "A"}
    dumped = str(session)
    assert "Correct Answer" not in dumped
    assert "Explanation" not in dumped
    assert question.explanation not in dumped
    assert "Because." not in dumped
    assert session.get("mode") == ExamAttempt.MODE_EXAM
    assert review_payload(user.id, attempt.id) is None


def test_practice_session_includes_keys_for_grade_now(app_context):
    user = _user("practice@example.com")
    question = _question("B")
    attempt = start_attempt(
        user.id, "Dom", "Sub", [question.id], mode=ExamAttempt.MODE_PRACTICE
    )
    session = public_exam_session(user.id, attempt)
    assert session["mode"] == ExamAttempt.MODE_PRACTICE
    assert session["questions"][0]["Correct Answer"] == "B"
    assert session["questions"][0]["Explanation"] == "Because."


def test_results_and_review_only_after_complete(app_context):
    owner = _user("owner@example.com")
    other = _user("other@example.com")
    question = _question("B")
    attempt = start_attempt(owner.id, "Dom", "Sub", [question.id])
    save_selected_option(owner.id, attempt.id, question.id, "B")
    assert list_completed_summaries(owner.id) == []

    complete_attempt(owner.id, attempt.id)
    summaries = list_completed_summaries(owner.id)
    assert len(summaries) == 1
    assert summaries[0]["score"] == 1
    assert summaries[0]["total"] == 1
    assert list_completed_summaries(other.id) == []

    payload = review_payload(owner.id, attempt.id)
    assert payload["questions"][0]["Correct Answer"] == "B"
    assert payload["questions"][0]["Explanation"] == "Because."
    assert review_payload(other.id, attempt.id) is None


def test_complete_does_not_use_client_score_columns(app_context):
    user = _user()
    question = _question("B")
    attempt = start_attempt(user.id, "Dom", "Sub", [question.id])
    save_selected_option(user.id, attempt.id, question.id, "A")
    # Tamper with the row the way a client flag would hope to.
    attempt.score_correct = 99
    attempt.score_total = 99
    db.session.commit()

    completed = complete_attempt(user.id, attempt.id)
    assert completed.score_correct == 0
    assert completed.score_total == 1
    assert completed.status == ExamAttempt.STATUS_COMPLETED


def test_abandon_requires_owner_and_ends_in_progress(app_context):
    owner = _user("owner@example.com")
    other = _user("other@example.com")
    question = _question()
    attempt = start_attempt(owner.id, "Dom", "Sub", [question.id])
    save_selected_option(owner.id, attempt.id, question.id, "A")

    assert abandon_attempt(other.id, attempt.id) is None
    assert get_in_progress_attempt(owner.id).id == attempt.id

    abandoned = abandon_attempt(owner.id, attempt.id)
    assert abandoned.status == ExamAttempt.STATUS_ABANDONED
    assert abandoned.completed_at is not None
    assert abandoned.score_correct is None
    assert abandoned.score_total is None
    assert get_in_progress_attempt(owner.id) is None
    assert public_exam_session(owner.id) is None
    assert review_payload(owner.id, attempt.id) is None
    assert list_completed_summaries(owner.id) == []


def test_start_after_explicit_abandon_creates_new_attempt(app_context):
    user = _user()
    question = _question()
    first = start_attempt(user.id, "Dom", "Sub", [question.id])
    abandon_attempt(user.id)
    second = start_attempt(user.id, "Dom", "Sub", [question.id])
    assert second.id != first.id
    assert get_in_progress_attempt(user.id).id == second.id
    assert ExamAttempt.query.filter_by(
        user_id=user.id, status=ExamAttempt.STATUS_ABANDONED
    ).count() == 1


def test_unanswered_counts_as_incorrect(app_context):
    user = _user()
    question = _question("B")
    attempt = start_attempt(user.id, "Dom", "Sub", [question.id])
    completed = complete_attempt(user.id, attempt.id)
    assert completed.score_correct == 0
    assert completed.score_total == 1
    assert datetime.utcnow() >= completed.completed_at
