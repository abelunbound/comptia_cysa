"""Exam Results body: Resume Exam only when an attempt is in progress."""

from dash import dcc

from attempts import complete_attempt, save_selected_option, start_attempt
from components.results_view import results_page_children
from tests.test_attempts import _question, _user, app_context  # noqa: F401


def _link_labels(node):
    labels = []
    if isinstance(node, dcc.Link):
        labels.append(node.children)
    children = getattr(node, "children", None)
    if children is None:
        return labels
    if not isinstance(children, (list, tuple)):
        children = [children]
    for child in children:
        labels.extend(_link_labels(child))
    return labels


def test_resume_hidden_after_submit_only(app_context):
    user = _user()
    question = _question("B")
    attempt = start_attempt(user.id, "Dom", "Sub", [question.id])
    save_selected_option(user.id, attempt.id, question.id, "B")
    complete_attempt(user.id, attempt.id)

    labels = _link_labels(results_page_children(user.id))
    assert "Resume Exam" not in labels
    assert "Review current attempt" in labels
    assert "Take Another Exam" in labels


def test_resume_shown_with_in_progress_and_history(app_context):
    user = _user()
    question = _question("B")
    first = start_attempt(user.id, "Dom", "Sub", [question.id])
    save_selected_option(user.id, first.id, question.id, "B")
    complete_attempt(user.id, first.id)
    start_attempt(user.id, "Dom", "Sub", [question.id])

    labels = _link_labels(results_page_children(user.id))
    assert "Resume Exam" in labels
    assert "Review current attempt" in labels


def test_empty_state_resume_when_only_in_progress(app_context):
    user = _user()
    question = _question()
    start_attempt(user.id, "Dom", "Sub", [question.id])

    labels = _link_labels(results_page_children(user.id))
    assert "Resume Exam" in labels
    assert "Start an Exam" in labels
