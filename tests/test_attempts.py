"""M3 #17: persist answers, server-side score, AuthZ, answer secrecy."""

from datetime import datetime, timedelta

import os

import pytest
from flask import Flask

from attempts import (
    abandon_attempt,
    complete_attempt,
    dashboard_metrics,
    dashboard_results_page,
    dashboard_results_rows,
    get_in_progress_attempt,
    latest_exam_percent,
    list_completed_summaries,
    public_exam_session,
    recent_attempt_durations,
    review_payload,
    save_selected_option,
    start_attempt,
    time_target_baseline,
)
from auth import AttemptAnswer, ExamAttempt, Question, create_user, db, init_auth
from tests.conftest import TEST_ENGINE_OPTIONS, reset_schema
from tests.pg_seed import QUESTION_VALUES


@pytest.fixture
def app_context():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = TEST_ENGINE_OPTIONS
    app.config["TESTING"] = True

    init_auth(app)
    with app.app_context():
        reset_schema()
        db.create_all()
        try:
            yield app
        finally:
            reset_schema()
            db.engine.dispose()


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


def test_dashboard_metrics_empty_and_scoped(app_context):
    owner = _user("owner@example.com")
    other = _user("other@example.com")
    question = _question("B")
    other_attempt = start_attempt(other.id, "Dom", "Sub", [question.id])
    save_selected_option(other.id, other_attempt.id, question.id, "B")
    complete_attempt(other.id, other_attempt.id)

    empty = dashboard_metrics(owner.id)
    assert empty == {
        "highest_score": 0,
        "total_attempts": 0,
        "pass_rate": 0,
        "average_score": 0,
    }

    first = start_attempt(owner.id, "Dom", "Sub", [question.id])
    save_selected_option(owner.id, first.id, question.id, "B")
    complete_attempt(owner.id, first.id)
    abandoned = start_attempt(owner.id, "Dom", "Sub", [question.id])
    abandon_attempt(owner.id, abandoned.id)
    second = start_attempt(owner.id, "Dom", "Sub", [question.id])
    complete_attempt(owner.id, second.id)

    metrics = dashboard_metrics(owner.id)
    assert metrics["total_attempts"] == 2
    assert metrics["highest_score"] == 100
    assert metrics["average_score"] == 50
    assert metrics["pass_rate"] == 50
    assert dashboard_metrics(other.id)["total_attempts"] == 1


def test_time_target_baseline_runs_80_to_50_over_ten_slots():
    baseline = time_target_baseline()
    assert len(baseline) == 10
    assert baseline[0] == 80
    assert baseline[-1] == 50
    assert baseline == sorted(baseline, reverse=True)


def test_recent_attempt_durations_uses_submit_delta_and_last_ten(app_context):
    owner = _user("owner@example.com")
    other = _user("other@example.com")
    question = _question()
    origin = datetime(2026, 1, 1, 12, 0, 0)

    other_row = start_attempt(other.id, "Dom", "Sub", [question.id])
    complete_attempt(other.id, other_row.id)
    other_row.started_at = origin
    other_row.completed_at = origin + timedelta(minutes=99)
    db.session.commit()

    abandoned = start_attempt(owner.id, "Dom", "Sub", [question.id])
    abandon_attempt(owner.id, abandoned.id)

    for index in range(11):
        row = start_attempt(owner.id, "Dom", "Sub", [question.id])
        complete_attempt(owner.id, row.id)
        row.started_at = origin + timedelta(days=index)
        row.completed_at = row.started_at + timedelta(minutes=10 + index)
        db.session.commit()

    minutes = recent_attempt_durations(owner.id)
    assert minutes == [11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0]
    assert recent_attempt_durations(other.id) == [99.0]


def test_latest_exam_percent_is_most_recent_completed(app_context):
    owner = _user("owner@example.com")
    other = _user("other@example.com")
    question = _question("B")
    assert latest_exam_percent(owner.id) is None

    other_row = start_attempt(other.id, "Dom", "Sub", [question.id])
    save_selected_option(other.id, other_row.id, question.id, "B")
    complete_attempt(other.id, other_row.id)

    first = start_attempt(owner.id, "Dom", "Sub", [question.id])
    save_selected_option(owner.id, first.id, question.id, "B")
    complete_attempt(owner.id, first.id)
    second = start_attempt(owner.id, "Dom", "Sub", [question.id])
    complete_attempt(owner.id, second.id)

    assert latest_exam_percent(owner.id) == 0
    assert latest_exam_percent(other.id) == 100


def test_dashboard_results_rows_are_user_scoped_newest_first(app_context):
    owner = _user("owner@example.com")
    other = _user("other@example.com")
    question = _question("B")
    origin = datetime(2026, 1, 20, 12, 0, 0)

    other_row = start_attempt(other.id, "Dom", "1.1 Explain concepts", [question.id])
    save_selected_option(other.id, other_row.id, question.id, "B")
    complete_attempt(other.id, other_row.id)

    first = start_attempt(owner.id, "Dom", "1.1 Explain concepts", [question.id])
    save_selected_option(owner.id, first.id, question.id, "B")
    complete_attempt(owner.id, first.id)
    first.completed_at = origin
    db.session.commit()

    abandoned = start_attempt(owner.id, "Dom", "1.1 Explain concepts", [question.id])
    abandon_attempt(owner.id, abandoned.id)

    second = start_attempt(owner.id, "Dom", "1.2 Analyze indicators", [question.id])
    complete_attempt(owner.id, second.id)
    second.completed_at = origin + timedelta(days=1)
    db.session.commit()

    third = start_attempt(owner.id, "Dom", "1.1 Explain concepts", [question.id])
    save_selected_option(owner.id, third.id, question.id, "B")
    complete_attempt(owner.id, third.id)
    third.completed_at = origin + timedelta(days=2)
    db.session.commit()

    assert dashboard_results_rows(owner.id) == [
        {
            "subsection": "1.1 Explain concepts",
            "score": "100%",
            "attempts": 2,
            "date": "Jan 22, 2026",
        },
        {
            "subsection": "1.2 Analyze indicators",
            "score": "0%",
            "attempts": 1,
            "date": "Jan 21, 2026",
        },
        {
            "subsection": "1.1 Explain concepts",
            "score": "100%",
            "attempts": 1,
            "date": "Jan 20, 2026",
        },
    ]
    other_rows = dashboard_results_rows(other.id)
    assert len(other_rows) == 1
    assert other_rows[0]["subsection"] == "1.1 Explain concepts"
    assert dashboard_results_rows(_user("empty@example.com").id) == []


def test_dashboard_results_page_is_five_newest(app_context):
    user = _user("paged@example.com")
    question = _question()
    origin = datetime(2026, 1, 1, 12, 0, 0)
    for index in range(6):
        row = start_attempt(user.id, "Dom", "Sub", [question.id])
        complete_attempt(user.id, row.id)
        row.completed_at = origin + timedelta(days=index)
        db.session.commit()

    first = dashboard_results_page(user.id, page=1)
    assert first["total"] == 6
    assert first["pages"] == 2
    assert first["page"] == 1
    assert len(first["rows"]) == 5
    assert first["rows"][0]["date"] == "Jan 6, 2026"

    second = dashboard_results_page(user.id, page=2)
    assert second["page"] == 2
    assert len(second["rows"]) == 1
    assert second["rows"][0]["date"] == "Jan 1, 2026"

    clamped = dashboard_results_page(user.id, page=99)
    assert clamped["page"] == 2
