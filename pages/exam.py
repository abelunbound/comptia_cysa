"""Exam setup + question-by-question exam-taking page ('/')."""

import uuid
from datetime import datetime

import dash
from dash import ALL, Input, Output, State, dcc, html

from components.shell import shell
from components.ui import (
    ACCENT_COLOR,
    ACCENT_LIGHT,
    CORRECT_COLOR,
    DISABLED_BUTTON_STYLE,
    HEADING_COLOR,
    INCORRECT_COLOR,
    INTRO_CARD_STYLE,
    OPTION_LETTERS,
    PAGE_CARD_STYLE,
    PRIMARY_BUTTON_STYLE,
    SECONDARY_BUTTON_STYLE,
    SUBTEXT_COLOR,
    score_ring_figure,
)
from data_loader import load_questions

dash.register_page(__name__, path="/", name="Exam")

df = load_questions()

domain_options = [{"label": d, "value": d} for d in sorted(df["Domain"].unique())]

OPTION_CARD_IDS = {letter: f"option-card-{letter}" for letter in OPTION_LETTERS}

EMPTY_RING_FIGURE = score_ring_figure(0, 1)


def _option_card_style(letter, selected_letter, correct_letter, graded):
    base = {
        "border": "1px solid #d1d5db",
        "borderRadius": "8px",
        "padding": "14px 16px",
        "cursor": "default" if graded else "pointer",
        "backgroundColor": "white",
        "fontSize": "14px",
        "userSelect": "none",
    }
    if graded:
        if letter == correct_letter:
            return {
                **base,
                "backgroundColor": "#dcfce7",
                "border": f"2px solid {CORRECT_COLOR}",
                "fontWeight": "bold",
            }
        if letter == selected_letter:
            return {
                **base,
                "backgroundColor": "#fee2e2",
                "border": f"2px solid {INCORRECT_COLOR}",
                "fontWeight": "bold",
            }
        return {**base, "opacity": 0.55}

    if letter == selected_letter:
        return {**base, "border": f"2px solid {ACCENT_COLOR}", "backgroundColor": ACCENT_LIGHT}
    return base


def _page_buttons(total, current_idx):
    buttons = []
    for i in range(total):
        is_current = i == current_idx
        buttons.append(
            html.Button(
                str(i + 1),
                id={"type": "page-btn", "index": i},
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
                    "flexShrink": "0",
                },
            )
        )
    return buttons


layout = shell(
    html.Div(
        [
            html.Div(
                style={**INTRO_CARD_STYLE, "marginBottom": "28px"},
                children=html.Div(
                    style={
                        "display": "grid",
                        "gridTemplateColumns": "7fr 3fr",
                        "columnGap": "24px",
                        "alignItems": "center",
                    },
                    children=[
                        html.Div(
                            [
                                html.H1(
                                    "CySA+ V4 (New Version)",
                                    style={"margin": 0, "color": HEADING_COLOR},
                                ),
                                html.P(
                                    "CompTIA Cybersecurity Analyst (CySA+) is a cybersecurity "
                                    "certification that validates your ability to detect, "
                                    "analyze, and respond to threats in security operations and "
                                    "vulnerability management roles. It focuses on incident "
                                    "detection, response, and continuous monitoring in modern "
                                    "environments, while managing vulnerabilities and "
                                    "effectively communicating critical risks.",
                                    style={
                                        "color": SUBTEXT_COLOR,
                                        "marginTop": "12px",
                                        "maxWidth": "760px",
                                    },
                                ),
                            ],
                            style={"gridColumn": "1"},
                        ),
                        html.Img(
                            src=dash.get_asset_url("cysa_logo.webp"),
                            style={
                                "gridColumn": "2",
                                "justifySelf": "center",
                                "width": "120px",
                                "height": "auto",
                            },
                        ),
                    ],
                ),
            ),
            html.Div(
                style=PAGE_CARD_STYLE,
                children=[
                    html.Div(
                        id="setup-section",
                        children=[
                            html.Div(
                                style={"display": "flex", "gap": "16px", "marginBottom": "16px"},
                                children=[
                                    html.Div(
                                        style={"flex": 1},
                                        children=[
                                            html.Label("Select Domain"),
                                            dcc.Dropdown(
                                                id="domain-dropdown",
                                                options=domain_options,
                                                placeholder="Select a domain...",
                                            ),
                                        ],
                                    ),
                                    html.Div(
                                        style={"flex": 1},
                                        children=[
                                            html.Label("Select Sub-Section"),
                                            dcc.Dropdown(
                                                id="subsection-dropdown",
                                                options=[],
                                                placeholder="Select a sub-section...",
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            html.Div(
                                id="setup-error-msg",
                                style={"color": "#b45309", "marginBottom": "12px"},
                            ),
                            html.Button(
                                "Start Exam",
                                id="start-exam-btn",
                                n_clicks=0,
                                style=PRIMARY_BUTTON_STYLE,
                            ),
                        ],
                    ),
                    html.Div(
                        id="exam-section",
                        style={"display": "none"},
                        children=[
                            html.Div(
                                style={
                                    "display": "grid",
                                    "gridTemplateColumns": "7fr 3fr",
                                    "columnGap": "24px",
                                    "alignItems": "center",
                                    "marginBottom": "20px",
                                },
                                children=[
                                    html.Div(
                                        id="exam-progress-label",
                                        style={
                                            "gridColumn": "1",
                                            "color": "#6b7280",
                                            "fontSize": "13px",
                                        },
                                    ),
                                    html.Div(
                                        id="exam-timer-label",
                                        style={
                                            "gridColumn": "2",
                                            "justifySelf": "center",
                                            "color": "#6b7280",
                                            "fontSize": "13px",
                                            "fontWeight": "bold",
                                        },
                                    ),
                                ],
                            ),
                            dcc.Interval(
                                id="exam-timer-interval", interval=1000, n_intervals=0
                            ),
                            html.Div(
                                style={
                                    "display": "grid",
                                    "gridTemplateColumns": "7fr 3fr",
                                    "columnGap": "24px",
                                },
                                children=[
                                    html.Div(
                                        id="exam-subtopic-label",
                                        style={
                                            "gridColumn": "1",
                                            "gridRow": "1",
                                            "color": "#6b7280",
                                            "fontSize": "13px",
                                            "marginBottom": "8px",
                                        },
                                    ),
                                    html.Div(
                                        id="exam-question-text",
                                        style={
                                            "gridColumn": "1",
                                            "gridRow": "2",
                                            "fontWeight": "bold",
                                            "marginBottom": "20px",
                                        },
                                    ),
                                    html.Div(
                                        id="exam-options-grid",
                                        style={
                                            "gridColumn": "1",
                                            "gridRow": "3",
                                            "alignSelf": "start",
                                            "display": "grid",
                                            "gridTemplateColumns": "1fr 1fr",
                                            "gap": "12px",
                                        },
                                        children=[
                                            html.Div(id=OPTION_CARD_IDS[letter], n_clicks=0)
                                            for letter in OPTION_LETTERS
                                        ],
                                    ),
                                    html.Div(
                                        style={
                                            "gridColumn": "2",
                                            "gridRow": "3 / span 2",
                                            "alignSelf": "start",
                                            "justifySelf": "center",
                                        },
                                        children=dcc.Graph(
                                            id="score-ring",
                                            figure=EMPTY_RING_FIGURE,
                                            config={
                                                "displayModeBar": False,
                                                "staticPlot": True,
                                            },
                                            style={"width": "180px", "height": "180px"},
                                        ),
                                    ),
                                    html.Div(
                                        id="explanation-panel",
                                        style={
                                            "gridColumn": "1",
                                            "gridRow": "4",
                                            "display": "none",
                                            "marginTop": "20px",
                                        },
                                    ),
                                ],
                            ),
                            html.Div(
                                style={
                                    "display": "flex",
                                    "alignItems": "flex-start",
                                    "marginTop": "20px",
                                    "gap": "16px",
                                },
                                children=[
                                    html.Div(
                                        style={
                                            "display": "flex",
                                            "flexDirection": "column",
                                            "gap": "8px",
                                            "flexShrink": "0",
                                        },
                                        children=[
                                            html.Button(
                                                "Grade Now",
                                                id="grade-btn",
                                                n_clicks=0,
                                                style=SECONDARY_BUTTON_STYLE,
                                            ),
                                            html.Button(
                                                "Prev",
                                                id="prev-btn",
                                                n_clicks=0,
                                                style=SECONDARY_BUTTON_STYLE,
                                            ),
                                            html.Button(
                                                "Next",
                                                id="next-btn",
                                                n_clicks=0,
                                                style=SECONDARY_BUTTON_STYLE,
                                            ),
                                            html.Button(
                                                "Submit Exam",
                                                id="submit-exam-btn",
                                                n_clicks=0,
                                                style=PRIMARY_BUTTON_STYLE,
                                            ),
                                        ],
                                    ),
                                    html.Div(
                                        id="page-number-buttons",
                                        style={
                                            "display": "flex",
                                            "flexWrap": "wrap",
                                            "gap": "8px",
                                            "flex": "1",
                                            "alignContent": "flex-start",
                                        },
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ]
    )
)


@dash.callback(
    Output("subsection-dropdown", "options"),
    Output("subsection-dropdown", "value"),
    Input("domain-dropdown", "value"),
)
def update_subsections(selected_domain):
    """Populate the Sub-Section dropdown based on the chosen Domain."""
    if not selected_domain:
        return [], None
    subsections = sorted(df.loc[df["Domain"] == selected_domain, "Sub-Section"].unique())
    return [{"label": sub, "value": sub} for sub in subsections], None


@dash.callback(
    Output("exam-session-store", "data"),
    Output("setup-error-msg", "children"),
    Input("start-exam-btn", "n_clicks"),
    State("domain-dropdown", "value"),
    State("subsection-dropdown", "value"),
    prevent_initial_call=True,
)
def start_exam(_n_clicks, domain, subsection):
    """Build a new exam session from every question matching Domain + Sub-Section."""
    if not domain or not subsection:
        return dash.no_update, "Please select a Domain and Sub-Section first."

    pool = df[(df["Domain"] == domain) & (df["Sub-Section"] == subsection)]
    if pool.empty:
        return dash.no_update, "No questions found for this Domain / Sub-Section yet."

    questions = pool.sample(frac=1).to_dict("records")
    session = {
        "id": str(uuid.uuid4())[:8],
        "domain": domain,
        "subsection": subsection,
        "questions": questions,
        "answers": {},
        "graded": {},
        "current_index": 0,
        "submitted": False,
        "started_at": datetime.now().isoformat(timespec="seconds"),
    }
    return session, ""


@dash.callback(
    Output("exam-session-store", "data", allow_duplicate=True),
    Input(OPTION_CARD_IDS["A"], "n_clicks"),
    Input(OPTION_CARD_IDS["B"], "n_clicks"),
    Input(OPTION_CARD_IDS["C"], "n_clicks"),
    Input(OPTION_CARD_IDS["D"], "n_clicks"),
    State("exam-session-store", "data"),
    prevent_initial_call=True,
)
def select_option(_a, _b, _c, _d, data):
    """Record the clicked option as the answer for the current question."""
    if not data or not data.get("questions"):
        return dash.no_update

    idx = data.get("current_index", 0)
    if data.get("graded", {}).get(str(idx)):
        return dash.no_update  # locked once graded

    id_to_letter = {v: k for k, v in OPTION_CARD_IDS.items()}
    letter = id_to_letter.get(dash.ctx.triggered_id)
    if not letter:
        return dash.no_update

    answers = dict(data.get("answers", {}))
    answers[str(idx)] = letter
    return {**data, "answers": answers}


@dash.callback(
    Output("exam-session-store", "data", allow_duplicate=True),
    Input("grade-btn", "n_clicks"),
    State("exam-session-store", "data"),
    prevent_initial_call=True,
)
def grade_current_question(_n_clicks, data):
    """Lock in the current answer and reveal correctness + explanation."""
    if not data or not data.get("questions"):
        return dash.no_update

    idx = data.get("current_index", 0)
    if str(idx) not in data.get("answers", {}):
        return dash.no_update

    graded = dict(data.get("graded", {}))
    graded[str(idx)] = True
    return {**data, "graded": graded}


@dash.callback(
    Output("exam-session-store", "data", allow_duplicate=True),
    Input("prev-btn", "n_clicks"),
    Input("next-btn", "n_clicks"),
    State("exam-session-store", "data"),
    prevent_initial_call=True,
)
def navigate_question(_prev_clicks, _next_clicks, data):
    """Move to the previous/next question."""
    if not data or not data.get("questions"):
        return dash.no_update

    total = len(data["questions"])
    idx = data.get("current_index", 0)
    triggered_id = dash.ctx.triggered_id
    if triggered_id == "prev-btn":
        idx = max(0, idx - 1)
    elif triggered_id == "next-btn":
        idx = min(total - 1, idx + 1)

    return {**data, "current_index": idx}


@dash.callback(
    Output("exam-session-store", "data", allow_duplicate=True),
    Input({"type": "page-btn", "index": ALL}, "n_clicks"),
    State("exam-session-store", "data"),
    prevent_initial_call=True,
)
def jump_to_question(_all_clicks, data):
    """Jump directly to the clicked question number."""
    if not data or not data.get("questions"):
        return dash.no_update

    # The page-number buttons are recreated from scratch on every render_exam
    # call (see _page_buttons), so this pattern-matching ALL input also fires
    # whenever a button is freshly (re)mounted with n_clicks=0 -- not just on
    # a genuine click. Ignore those "phantom" triggers so navigating away
    # from question 1 doesn't get silently reverted back to it.
    triggered = dash.ctx.triggered[0] if dash.ctx.triggered else None
    if not triggered or not triggered.get("value"):
        return dash.no_update

    triggered_id = dash.ctx.triggered_id
    if not triggered_id or "index" not in triggered_id:
        return dash.no_update

    total = len(data["questions"])
    idx = max(0, min(triggered_id["index"], total - 1))
    return {**data, "current_index": idx}


@dash.callback(
    Output("exam-timer-label", "children"),
    Input("exam-timer-interval", "n_intervals"),
    State("exam-session-store", "data"),
)
def update_timer(_n_intervals, data):
    """Show how long the candidate has spent on the current exam attempt."""
    if not data or not data.get("questions") or data.get("submitted"):
        return ""

    started_at = data.get("started_at")
    if not started_at:
        return ""

    try:
        started_dt = datetime.fromisoformat(started_at)
    except ValueError:
        return ""

    elapsed_seconds = max(0, int((datetime.now() - started_dt).total_seconds()))
    hours, remainder = divmod(elapsed_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"Time: {hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"Time: {minutes:02d}:{seconds:02d}"


@dash.callback(
    Output("setup-section", "style"),
    Output("exam-section", "style"),
    Output("exam-progress-label", "children"),
    Output("exam-subtopic-label", "children"),
    Output("exam-question-text", "children"),
    Output(OPTION_CARD_IDS["A"], "children"),
    Output(OPTION_CARD_IDS["A"], "style"),
    Output(OPTION_CARD_IDS["B"], "children"),
    Output(OPTION_CARD_IDS["B"], "style"),
    Output(OPTION_CARD_IDS["C"], "children"),
    Output(OPTION_CARD_IDS["C"], "style"),
    Output(OPTION_CARD_IDS["D"], "children"),
    Output(OPTION_CARD_IDS["D"], "style"),
    Output("explanation-panel", "children"),
    Output("explanation-panel", "style"),
    Output("grade-btn", "children"),
    Output("grade-btn", "disabled"),
    Output("grade-btn", "style"),
    Output("prev-btn", "disabled"),
    Output("next-btn", "disabled"),
    Output("score-ring", "figure"),
    Output("page-number-buttons", "children"),
    Input("exam-session-store", "data"),
)
def render_exam(data):
    """Show the setup form or the current exam question, based on session state."""
    if not data or not data.get("questions") or data.get("submitted"):
        empty_option_updates = []
        for letter in OPTION_LETTERS:
            empty_option_updates.extend([f"{letter}.", {"display": "none"}])
        return (
            {"display": "block"},
            {"display": "none"},
            "",
            "",
            "",
            *empty_option_updates,
            "",
            {"gridColumn": "1", "gridRow": "4", "display": "none"},
            "Grade Now",
            True,
            SECONDARY_BUTTON_STYLE,
            True,
            True,
            EMPTY_RING_FIGURE,
            [],
        )

    questions = data["questions"]
    total = len(questions)
    idx = max(0, min(data.get("current_index", 0), total - 1))
    answers = data.get("answers", {})
    graded = data.get("graded", {})
    row = questions[idx]

    selected_letter = answers.get(str(idx))
    is_graded = bool(graded.get(str(idx)))
    correct_letter = str(row["Correct Answer"]).strip().upper()

    option_updates = []
    for letter in OPTION_LETTERS:
        content = html.Span(
            [html.Strong(f"{letter}. "), row[f"Option {letter}"]]
        )
        style = _option_card_style(letter, selected_letter, correct_letter, is_graded)
        option_updates.extend([content, style])

    if is_graded:
        is_correct = selected_letter == correct_letter
        result_text = "Correct!" if is_correct else f"Incorrect \u2014 the correct answer was {correct_letter}."
        result_color = CORRECT_COLOR if is_correct else INCORRECT_COLOR
        explanation_children = html.Div(
            [
                html.Div(result_text, style={"fontWeight": "bold", "color": result_color}),
                html.Div(row["Explanation"], style={"marginTop": "6px", "color": "#374151"}),
            ]
        )
        explanation_style = {
            "gridColumn": "1",
            "gridRow": "4",
            "display": "block",
            "marginTop": "20px",
            "padding": "14px",
            "minHeight": "120px",
            "boxSizing": "border-box",
            "backgroundColor": "#f9fafb",
            "borderRadius": "8px",
        }
        grade_btn_label = "See Explanation"
        grade_btn_disabled = True
        grade_btn_style = DISABLED_BUTTON_STYLE
    else:
        explanation_children = ""
        explanation_style = {"gridColumn": "1", "gridRow": "4", "display": "none"}
        grade_btn_label = "Grade Now"
        grade_btn_disabled = selected_letter is None
        grade_btn_style = DISABLED_BUTTON_STYLE if selected_letter is None else SECONDARY_BUTTON_STYLE

    # This ring tracks progress through the exam (questions answered so far),
    # not correctness -- it updates the moment an option is selected, with no
    # extra change needed on "Grade Now". The correct-vs-incorrect breakdown
    # is shown separately on the results page.
    answered_so_far = sum(1 for i in range(total) if answers.get(str(i)))
    ring_figure = score_ring_figure(answered_so_far, total)

    return (
        {"display": "none"},
        {"display": "block"},
        f"Question {idx + 1} of {total}",
        f"Topic: {row['Subtopic']}",
        row["Question"],
        *option_updates,
        explanation_children,
        explanation_style,
        grade_btn_label,
        grade_btn_disabled,
        grade_btn_style,
        idx == 0,
        idx == total - 1,
        ring_figure,
        _page_buttons(total, idx),
    )


@dash.callback(
    Output("exam-session-store", "data", allow_duplicate=True),
    Output("exam-history-store", "data"),
    Output("_pages_location", "pathname"),
    Input("submit-exam-btn", "n_clicks"),
    State("exam-session-store", "data"),
    State("exam-history-store", "data"),
    prevent_initial_call=True,
)
def submit_exam(_n_clicks, data, history):
    """Grade the exam, record it in history, and redirect to the results page."""
    if not data or not data.get("questions"):
        return dash.no_update, dash.no_update, dash.no_update

    questions = data["questions"]
    total = len(questions)
    answers = data.get("answers", {})

    score = sum(
        1
        for i, question in enumerate(questions)
        if str(answers.get(str(i), "")).strip().upper()
        == str(question["Correct Answer"]).strip().upper()
    )

    attempt = {
        "id": data.get("id") or str(uuid.uuid4())[:8],
        "domain": data["domain"],
        "subsection": data["subsection"],
        "questions": questions,
        "answers": answers,
        "score": score,
        "total": total,
        "started_at": data.get("started_at"),
        "submitted_at": datetime.now().isoformat(timespec="seconds"),
    }

    history = list(history or [])
    history.append(attempt)

    submitted_session = {**data, "submitted": True}

    return submitted_session, history, "/results"
