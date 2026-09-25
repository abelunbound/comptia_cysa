"""Review page ('/review?attempt=<id>'): per-question breakdown of an attempt."""

from datetime import datetime
from urllib.parse import parse_qs

import dash
from dash import ALL, Input, Output, State, dcc, html
from flask_login import current_user

from attempts import list_completed_summaries, review_payload
from components.shell import shell
from components.ui import (
    ACCENT_COLOR,
    CARD_STYLE,
    CORRECT_COLOR,
    DISABLED_BUTTON_STYLE,
    INCORRECT_COLOR,
    OPTION_LETTERS,
    PAGE_CARD_STYLE,
    PRIMARY_BUTTON_STYLE,
    SECONDARY_BUTTON_STYLE,
)

dash.register_page(__name__, path="/review", name="Review")

QUESTIONS_PER_PAGE = 10


def layout(**kwargs):
    """Layout function: check auth and return review UI or empty (Flask handles redirect)."""
    if not current_user.is_authenticated:
        return shell(html.Div())
    
    return shell(
        html.Div(
            [
                dcc.Store(id="review-page-store", data=0),
                html.Div(id="review-page-ready"),
                html.Div(id="review-container"),
            ]
        )
    )


def _empty_state():
    return html.Div(
        [
            html.H1("Review"),
            html.P("No completed exam to review yet."),
            dcc.Link("Start an Exam", href="/", style=PRIMARY_BUTTON_STYLE),
        ]
    )


def _current_attempt(user_id, search):
    """Load a completed attempt owned by user_id. Never an in-progress row."""
    params = parse_qs((search or "").lstrip("?"))
    attempt_id = params.get("attempt", [None])[0]
    if attempt_id is not None:
        payload = review_payload(user_id, attempt_id)
        if payload:
            return payload
    summaries = list_completed_summaries(user_id)
    if not summaries:
        return None
    return review_payload(user_id, summaries[-1]["id"])


def _total_pages(total_questions):
    return max(1, -(-total_questions // QUESTIONS_PER_PAGE))  # ceil division


def _format_duration(seconds):
    hours, remainder = divmod(max(0, int(seconds)), 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def _time_spent_header(attempt):
    """Title showing total time spent on the exam, in place of the score."""
    duration_label = "N/A"
    started_at = attempt.get("started_at")
    submitted_at = attempt.get("submitted_at")
    if started_at and submitted_at:
        try:
            started_dt = datetime.fromisoformat(started_at)
            submitted_dt = datetime.fromisoformat(submitted_at)
            elapsed = (submitted_dt - started_dt).total_seconds()
            duration_label = _format_duration(elapsed)
        except ValueError:
            duration_label = "N/A"

    return html.Div(
        style={
            "display": "flex",
            "justifyContent": "space-between",
            "alignItems": "baseline",
        },
        children=[
            html.H3("Time Spent", style={"margin": 0}),
            html.Span(
                f"Time: {duration_label}",
                style={"fontWeight": "bold", "color": ACCENT_COLOR, "fontSize": "18px"},
            ),
        ],
    )


def _option_row(letter, text, correct_letter, user_answer):
    is_correct = letter == correct_letter
    is_chosen = letter == user_answer
    if is_correct:
        bg, border, marker = "#dcfce7", CORRECT_COLOR, "\u2713"
    elif is_chosen:
        bg, border, marker = "#fee2e2", INCORRECT_COLOR, "\u2717"
    else:
        bg, border, marker = "#f9fafb", "#e5e7eb", ""

    return html.Div(
        style={
            "display": "flex",
            "justifyContent": "space-between",
            "padding": "10px 14px",
            "backgroundColor": bg,
            "border": f"1px solid {border}",
            "borderRadius": "6px",
            "marginBottom": "6px",
        },
        children=[
            html.Span(f"{letter}. {text}"),
            html.Span(marker, style={"fontWeight": "bold", "color": border}),
        ],
    )


def _question_block(index, question, user_answer):
    correct_letter = str(question["Correct Answer"]).strip().upper()

    header_children = [question["Question"]]
    if not user_answer:
        header_children.append(
            html.Span(
                "  Not answered",
                style={"color": "#b45309", "fontSize": "12px", "fontWeight": "normal"},
            )
        )

    return html.Div(
        style={**CARD_STYLE, "marginBottom": "16px"},
        children=[
            html.Div(
                f"Question {index + 1} \u2014 {question['Subtopic']}",
                style={"color": "#6b7280", "fontSize": "13px", "marginBottom": "4px"},
            ),
            html.Div(header_children, style={"fontWeight": "bold", "marginBottom": "12px"}),
            html.Div(
                [
                    _option_row(
                        letter, question[f"Option {letter}"], correct_letter, user_answer
                    )
                    for letter in OPTION_LETTERS
                ]
            ),
            html.Div(
                [html.Strong("Explanation: "), question["Explanation"]],
                style={"marginTop": "10px", "color": "#374151", "fontSize": "14px"},
            ),
        ],
    )


def _page_number_buttons(total_pages, current_page, position):
    buttons = []
    for i in range(total_pages):
        is_current = i == current_page
        buttons.append(
            html.Button(
                str(i + 1),
                id={"type": f"review-page-btn-{position}", "index": i},
                n_clicks=0,
                style={
                    "width": "36px",
                    "height": "36px",
                    "borderRadius": "6px",
                    "border": "1px solid #d1d5db",
                    "backgroundColor": ACCENT_COLOR if is_current else "white",
                    "color": "white" if is_current else "#111827",
                    "cursor": "pointer",
                    "fontWeight": "bold" if is_current else "normal",
                    "margin": "0 4px",
                },
            )
        )
    return buttons


def _pagination_nav(total_pages, current_page, position):
    """Build a Prev/page-numbers/Next row. `position` ("top"/"bottom") keeps
    the ids unique so the same controls can be shown in two places at once.
    """
    if total_pages <= 1:
        return None

    return html.Div(
        style={
            "display": "flex",
            "justifyContent": "center",
            "alignItems": "center",
        },
        children=[
            html.Button(
                "Prev",
                id=f"review-prev-btn-{position}",
                n_clicks=0,
                disabled=current_page == 0,
                style={
                    **(DISABLED_BUTTON_STYLE if current_page == 0 else SECONDARY_BUTTON_STYLE),
                    "marginRight": "8px",
                },
            ),
            html.Div(
                _page_number_buttons(total_pages, current_page, position),
                style={"display": "flex"},
            ),
            html.Button(
                "Next",
                id=f"review-next-btn-{position}",
                n_clicks=0,
                disabled=current_page == total_pages - 1,
                style={
                    **(
                        DISABLED_BUTTON_STYLE
                        if current_page == total_pages - 1
                        else SECONDARY_BUTTON_STYLE
                    ),
                    "marginLeft": "8px",
                },
            ),
        ],
    )


@dash.callback(
    Output("review-page-store", "data", allow_duplicate=True),
    Input("_pages_location", "pathname"),
    Input("_pages_location", "search"),
    prevent_initial_call=True,
)
def reset_review_page(pathname, _search):
    """Jump back to page 1 whenever a (possibly different) attempt is opened."""
    if pathname != "/review":
        return dash.no_update
    return 0


@dash.callback(
    Output("review-page-store", "data", allow_duplicate=True),
    Input("review-prev-btn-top", "n_clicks"),
    Input("review-next-btn-top", "n_clicks"),
    Input({"type": "review-page-btn-top", "index": ALL}, "n_clicks"),
    Input("review-prev-btn-bottom", "n_clicks"),
    Input("review-next-btn-bottom", "n_clicks"),
    Input({"type": "review-page-btn-bottom", "index": ALL}, "n_clicks"),
    State("review-page-store", "data"),
    State("_pages_location", "search"),
    prevent_initial_call=True,
)
def change_review_page(
    _prev_top,
    _next_top,
    _all_top,
    _prev_bottom,
    _next_bottom,
    _all_bottom,
    current_page,
    search,
):
    """Move between review pages via either the top or bottom Prev/Next/page-number controls."""
    # The page-number buttons are recreated from scratch on every render (see
    # _page_number_buttons), so this pattern-matching ALL input also fires
    # whenever a button is freshly (re)mounted with n_clicks=0 -- not just on
    # a genuine click. Ignore those "phantom" triggers.
    triggered = dash.ctx.triggered[0] if dash.ctx.triggered else None
    if not triggered or not triggered.get("value"):
        return dash.no_update

    if not current_user.is_authenticated:
        return dash.no_update

    attempt = _current_attempt(current_user.id, search)
    if not attempt:
        return dash.no_update

    total_pages = _total_pages(len(attempt["questions"]))
    current_page = current_page or 0

    triggered_id = dash.ctx.triggered_id
    if triggered_id in ("review-prev-btn-top", "review-prev-btn-bottom"):
        return max(0, current_page - 1)
    if triggered_id in ("review-next-btn-top", "review-next-btn-bottom"):
        return min(total_pages - 1, current_page + 1)
    if isinstance(triggered_id, dict) and triggered_id.get("type", "").startswith(
        "review-page-btn-"
    ):
        return max(0, min(triggered_id["index"], total_pages - 1))
    return dash.no_update


@dash.callback(
    Output("review-container", "children"),
    Input("review-page-ready", "id"),
    Input("_pages_location", "search"),
    Input("review-page-store", "data"),
)
def render_review(_ready, search, page):
    """Render review from a completed Postgres attempt owned by the user."""
    if not current_user.is_authenticated:
        return _empty_state()

    attempt = _current_attempt(current_user.id, search)
    if not attempt:
        return _empty_state()

    questions = attempt["questions"]
    answers = attempt["answers"]
    total_questions = len(questions)
    total_pages = _total_pages(total_questions)
    page = max(0, min(page or 0, total_pages - 1))

    start = page * QUESTIONS_PER_PAGE
    end = min(start + QUESTIONS_PER_PAGE, total_questions)
    blocks = [
        _question_block(i, q, answers.get(str(i)))
        for i, q in enumerate(questions)
        if start <= i < end
    ]

    body_children = [_time_spent_header(attempt)]
    if total_pages > 1:
        body_children.append(
            html.Div(
                f"Showing questions {start + 1}\u2013{end} of {total_questions}",
                style={"color": "#6b7280", "fontSize": "13px", "marginTop": "16px"},
            )
        )
    top_nav = _pagination_nav(total_pages, page, "top")
    if top_nav is not None:
        body_children.append(html.Div(top_nav, style={"marginTop": "16px"}))
    body_children.append(html.Div(blocks, style={"marginTop": "20px"}))
    bottom_nav = _pagination_nav(total_pages, page, "bottom")
    if bottom_nav is not None:
        body_children.append(html.Div(bottom_nav, style={"marginTop": "8px"}))

    return html.Div(
        [
            html.Div(
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "center",
                    "marginBottom": "8px",
                },
                children=[
                    html.H1("Review", style={"margin": 0}),
                    dcc.Link("Back to Results", href="/results", style=SECONDARY_BUTTON_STYLE),
                ],
            ),
            html.Div(
                f"{attempt['domain']} \u2014 {attempt['subsection']} \u00b7 "
                f"Attempted {attempt['submitted_at']}",
                style={"color": "#6b7280", "marginBottom": "16px"},
            ),
            html.Div(
                style=PAGE_CARD_STYLE,
                children=body_children,
            ),
        ]
    )
