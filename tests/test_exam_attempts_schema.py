"""M3 #16: exam_attempts / attempt_answers schema, constraints, AuthZ stubs."""

from datetime import datetime

import os

import pytest
from flask import Flask
from sqlalchemy.exc import IntegrityError

from attempts import (
    get_attempt_for_user,
    get_in_progress_attempt,
    list_answers_for_user_attempt,
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


def _question():
    question = Question(**QUESTION_VALUES)
    db.session.add(question)
    db.session.commit()
    return question


def _in_progress(user_id, current_index=0):
    attempt = ExamAttempt(
        user_id=user_id,
        status=ExamAttempt.STATUS_IN_PROGRESS,
        started_at=datetime.utcnow(),
        current_index=current_index,
    )
    db.session.add(attempt)
    db.session.commit()
    return attempt


def test_create_all_defines_attempt_tables(app_context):
    assert "exam_attempts" in db.metadata.tables
    assert "attempt_answers" in db.metadata.tables
    attempt_cols = set(ExamAttempt.__table__.columns.keys())
    answer_cols = set(AttemptAnswer.__table__.columns.keys())
    assert attempt_cols == {
        "id",
        "user_id",
        "status",
        "started_at",
        "completed_at",
        "score_correct",
        "score_total",
        "current_index",
        "domain",
        "subsection",
        "question_ids",
        "mode",
    }
    assert answer_cols == {
        "id",
        "attempt_id",
        "question_id",
        "selected_option",
        "answered_at",
    }
    assert "is_correct" not in answer_cols


def test_one_in_progress_attempt_per_user(app_context):
    user = _user()
    _in_progress(user.id)
    db.session.add(
        ExamAttempt(
            user_id=user.id,
            status=ExamAttempt.STATUS_IN_PROGRESS,
            started_at=datetime.utcnow(),
        )
    )
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_completed_attempts_not_limited_to_one(app_context):
    user = _user()
    for _ in range(2):
        db.session.add(
            ExamAttempt(
                user_id=user.id,
                status=ExamAttempt.STATUS_COMPLETED,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                score_correct=1,
                score_total=1,
            )
        )
    db.session.commit()
    assert ExamAttempt.query.filter_by(user_id=user.id).count() == 2


def test_unique_answer_per_question_on_attempt(app_context):
    user = _user()
    question = _question()
    attempt = _in_progress(user.id)
    db.session.add(
        AttemptAnswer(
            attempt_id=attempt.id,
            question_id=question.id,
            selected_option="A",
        )
    )
    db.session.commit()
    db.session.add(
        AttemptAnswer(
            attempt_id=attempt.id,
            question_id=question.id,
            selected_option="B",
        )
    )
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_get_attempt_for_user_rejects_other_users_id(app_context):
    owner = _user("owner@example.com")
    other = _user("other@example.com")
    attempt = _in_progress(owner.id)
    assert get_attempt_for_user(attempt.id, owner.id).id == attempt.id
    assert get_attempt_for_user(attempt.id, other.id) is None


def test_get_in_progress_and_answers_are_user_scoped(app_context):
    owner = _user("owner@example.com")
    other = _user("other@example.com")
    question = _question()
    attempt = _in_progress(owner.id)
    db.session.add(
        AttemptAnswer(
            attempt_id=attempt.id,
            question_id=question.id,
            selected_option="C",
        )
    )
    db.session.commit()

    assert get_in_progress_attempt(owner.id).id == attempt.id
    assert get_in_progress_attempt(other.id) is None
    assert len(list_answers_for_user_attempt(attempt.id, owner.id)) == 1
    assert list_answers_for_user_attempt(attempt.id, other.id) == []


def test_deleting_user_cascades_attempts_and_answers(app_context):
    user = _user()
    question = _question()
    attempt = _in_progress(user.id)
    db.session.add(
        AttemptAnswer(
            attempt_id=attempt.id,
            question_id=question.id,
            selected_option="D",
        )
    )
    db.session.commit()

    db.session.delete(user)
    db.session.commit()

    assert ExamAttempt.query.count() == 0
    assert AttemptAnswer.query.count() == 0
    assert Question.query.count() == 1
