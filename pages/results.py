"""Results page ('/results'): overall performance donut + session progress."""

import dash
import plotly.graph_objects as go
from dash import Input, Output, dcc, html
from flask_login import current_user

from components.shell import shell
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

dash.register_page(__name__, path="/results", name="Results")


def layout(**kwargs):
    """Layout function: check auth and return results or empty (Flask handles redirect)."""
    if not current_user.is_authenticated:
        return shell(html.Div())
    
    # Access exam history from dcc.Store - we need to handle this differently
    # Since we can't access stores in layout functions, return a container
    # that will be populated by a callback
    return shell(
        html.Div(
            [
                html.Div(id="results-page-ready"),
                html.Div(id="results-container"),
            ]
        )
    )


def _empty_state():
    return html.Div(
        [
            html.H1("Results"),
            html.P("You haven't completed an exam yet."),
            dcc.Link("Start an Exam", href="/", style=PRIMARY_BUTTON_STYLE),
        ]
    )


def _action_buttons_row(featured):
    """Row 1: Review current attempt / Take Another Exam."""
    return html.Div(
        style={
            "display": "flex",
            "gap": "12px",
            "flexWrap": "wrap",
            "marginBottom": "24px",
        },
        children=[
            dcc.Link(
                "Review current attempt",
                href=f"/review?attempt={featured['id']}",
                style={
                    **PRIMARY_BUTTON_STYLE,
                    "display": "inline-block",
                    "textDecoration": "none",
                },
            ),
            dcc.Link(
                "Take Another Exam",
                href="/",
                style={
                    **PRIMARY_BUTTON_STYLE,
                    "display": "inline-block",
                    "textDecoration": "none",
                },
            ),
        ],
    )


def _performance_card(attempt):
    """Row 2: 'Overall Performance' heading on top, then the percentage
    filling the left column and a large donut chart filling the right."""
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
    """Row 3: 'Your Progress' -- a 3-column grid of attempt tiles that wraps
    onto additional rows as more attempts are taken."""
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


@dash.callback(
    Output("results-container", "children"),
    Input("results-page-ready", "id"),
    Input("exam-history-store", "data"),
)
def render_results(_ready, history):
    """Render results on first paint and whenever session history changes."""
    if not history:
        return _empty_state()

    featured = history[-1]

    return html.Div(
        [
            html.H1("Exam Results", style={"marginBottom": "20px"}),
            html.Div(
                style=PAGE_CARD_STYLE,
                children=[
                    _action_buttons_row(featured),
                    html.Div(_performance_card(featured), style={"marginBottom": "24px"}),
                    _progress_section(history),
                ],
            ),
        ]
    )
