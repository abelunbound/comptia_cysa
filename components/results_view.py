"""Shared Exam Results body used by `/results` and `/admin/results`."""

import plotly.graph_objects as go
from dash import dcc, html

from attempts import get_in_progress_attempt, list_completed_summaries
from components.ui import (
    ACCENT_COLOR,
    CARD_STYLE,
    CORRECT_COLOR,
    INCORRECT_COLOR,
    NEUTRAL_COLOR,
    PAGE_CARD_STYLE,
    PRIMARY_BUTTON_STYLE,
    progress_bar,
)


def _link_button(label, href, style=PRIMARY_BUTTON_STYLE):
    return dcc.Link(
        label,
        href=href,
        style={**style, "display": "inline-block", "textDecoration": "none"},
    )


def _resume_exam_button():
    """Return to `/`; exam layout hydrates the in-progress attempt from Postgres."""
    return _link_button("Resume Exam", "/")


def empty_results_state(can_resume=False):
    actions = [_resume_exam_button()] if can_resume else []
    actions.append(_link_button("Start an Exam", "/"))
    return html.Div(
        [
            html.H1("Exam Results"),
            html.P("You haven't completed an exam yet."),
            html.Div(
                actions,
                style={"display": "flex", "gap": "12px", "flexWrap": "wrap"},
            ),
        ]
    )


def _action_buttons_row(featured, can_resume=False):
    """Row 1: Resume (if in progress) / Review current attempt / Take Another Exam."""
    children = []
    if can_resume:
        children.append(_resume_exam_button())
    children.extend(
        [
            _link_button("Review current attempt", f"/review?attempt={featured['id']}"),
            _link_button("Take Another Exam", "/"),
        ]
    )
    return html.Div(
        style={
            "display": "flex",
            "gap": "12px",
            "flexWrap": "wrap",
            "marginBottom": "24px",
        },
        children=children,
    )


def results_page_children(user_id):
    """Exam Results body scoped to user_id (Postgres only)."""
    history = list_completed_summaries(user_id)
    can_resume = get_in_progress_attempt(user_id) is not None
    if not history:
        return empty_results_state(can_resume)

    featured = history[-1]
    return html.Div(
        [
            html.H1("Exam Results", style={"marginBottom": "20px"}),
            html.Div(
                style=PAGE_CARD_STYLE,
                children=[
                    _action_buttons_row(featured, can_resume),
                    html.Div(_performance_card(featured), style={"marginBottom": "24px"}),
                    _progress_section(history),
                ],
            ),
        ]
    )


def _performance_card(attempt):
    """Row 2: percentage + donut for the featured completed attempt."""
    total = attempt["total"]
    score = attempt["score"]
    answered = len(attempt["answers"])
    unanswered = max(0, total - answered)
    wrong = max(0, total - score - unanswered)
    percent = round((score / total) * 100) if total else 0
    color = CORRECT_COLOR if percent >= 70 else ("#d97706" if percent >= 40 else INCORRECT_COLOR)

    fig = go.Figure(
        data=[
            go.Pie(
                labels=["Correct answer", "Wrong answer", "Unanswered"],
                values=[score, wrong, unanswered],
                hole=0.6,
                marker={"colors": [CORRECT_COLOR, INCORRECT_COLOR, NEUTRAL_COLOR]},
                textinfo="percent",
                sort=False,
            )
        ]
    )
    fig.update_layout(
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        showlegend=True,
        legend={"orientation": "h", "y": -0.1},
        height=340,
        width=340,
    )

    return html.Div(
        style={**CARD_STYLE},
        children=[
            html.H3("Overall Performance", style={"marginTop": 0, "marginBottom": "20px"}),
            html.Div(
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "center",
                    "gap": "24px",
                    "flexWrap": "wrap",
                },
                children=[
                    html.Div(
                        style={
                            "flex": "1 1 200px",
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "flex-start",
                        },
                        children=html.Div(
                            f"{percent}%",
                            style={"fontSize": "128px", "fontWeight": "bold", "color": color},
                        ),
                    ),
                    html.Div(
                        style={"flex": "0 0 auto"},
                        children=dcc.Graph(figure=fig, config={"displayModeBar": False}),
                    ),
                ],
            ),
        ],
    )


def _attempt_tile(attempt):
    """A compact card for the 'Your Progress' grid (3 per row)."""
    total = attempt["total"]
    score = attempt["score"]
    percent = round((score / total) * 100) if total else 0
    return html.Div(
        style={**CARD_STYLE, "padding": "16px"},
        children=[
            html.Strong(
                f"{attempt['domain']} \u2014 {attempt['subsection']}",
                style={"fontSize": "13px"},
            ),
            html.Div(
                attempt["submitted_at"],
                style={"fontSize": "12px", "color": "#9ca3af", "marginBottom": "8px"},
            ),
            html.Div(
                f"{score}/{total} ({percent}%)",
                style={"fontWeight": "bold", "marginBottom": "6px"},
            ),
            progress_bar(percent, color=CORRECT_COLOR if percent >= 70 else "#d97706"),
            dcc.Link(
                "Review",
                href=f"/review?attempt={attempt['id']}",
                style={
                    "fontSize": "13px",
                    "color": ACCENT_COLOR,
                    "display": "inline-block",
                    "marginTop": "8px",
                },
            ),
        ],
    )


def _progress_section(history):
    """Row 3: Your Progress — 3-column grid of completed attempts."""
    return html.Div(
        style={**CARD_STYLE},
        children=[
            html.Div(
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "baseline",
                    "marginBottom": "16px",
                },
                children=[
                    html.H3("Your Progress", style={"marginTop": 0}),
                    html.Span(
                        f"Total Test Attempted: {len(history)}",
                        style={"color": "#6b7280", "fontSize": "13px"},
                    ),
                ],
            ),
            html.Div(
                style={
                    "display": "grid",
                    "gridTemplateColumns": "repeat(3, 1fr)",
                    "gap": "16px",
                },
                children=[_attempt_tile(a) for a in reversed(history)],
            ),
        ],
    )
