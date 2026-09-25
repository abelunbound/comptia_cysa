"""Exam setup + question-by-question exam-taking page ('/')."""

from datetime import datetime

import dash
from dash import ALL, Input, Output, State, dcc, html
from flask_login import current_user

from attempts import (
    abandon_attempt,
    complete_attempt,
    get_in_progress_attempt,
    public_exam_session,
    save_selected_option,
    set_resume_index,
    start_attempt,
)
from auth import ExamAttempt
from components.shell import shell
from components.ui import (
    ACCENT_COLOR,
    ACCENT_LIGHT,
    CORRECT_COLOR,
    DISABLED_BUTTON_STYLE,
    INCORRECT_COLOR,
    HEADING_COLOR,
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


def _option_card_style(letter, selected_letter, correct_letter=None, graded=False):
    """Highlight selection immediately. Correctness only in practice after Grade Now."""
    base = {
        "border": "1px solid #d1d5db",
        "borderRadius": "8px",
        "padding": "14px 16px",
        "cursor": "default" if graded else "pointer",
        "backgroundColor": "white",
        "fontSize": "14px",
        "userSelect": "none",
    }
    if graded and correct_letter:
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


def layout(**kwargs):
    """Layout function: check auth and return full UI or empty (Flask handles redirect)."""
    if not current_user.is_authenticated:
        return shell(html.Div())  # Flask before_request redirects; this won't paint
    
    return shell(_exam_ui())


def _exam_ui():
    """Return the full exam UI (intro banner + setup/exam sections)."""
    return html.Div(
        [
            html.Div(id="exam-page-ready"),
            html.Div(id="exam-persist-ack", style={"display": "none"}),
            dcc.Store(id="pending-start-mode", data=ExamAttempt.MODE_EXAM),
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
                            html.Div(
                                id="replace-confirm-panel",
                                style={"display": "none", "marginBottom": "12px"},
                                children=[
                                    html.P(
                                        "You have an exam in progress. Start a new one and "
                                        "abandon the current attempt?",
                                        style={"marginBottom": "8px"},
                                    ),
                                    html.Button(
                                        "Abandon and start new",
                                        id="replace-confirm-btn",
                                        n_clicks=0,
                                        style={**PRIMARY_BUTTON_STYLE, "marginRight": "8px"},
                                    ),
                                    html.Button(
                                        "Keep current exam",
                                        id="replace-cancel-btn",
                                        n_clicks=0,
                                        style=SECONDARY_BUTTON_STYLE,
                                    ),
                                ],
                            ),
                            html.Div(
                                style={"display": "flex", "gap": "12px", "flexWrap": "wrap"},
                                children=[
                                    html.Button(
                                        "Exam Mode",
                                        id="exam-mode-btn",
                                        n_clicks=0,
                                        style=PRIMARY_BUTTON_STYLE,
                                    ),
                                    html.Button(
                                        "Practice Mode",
                                        id="practice-mode-btn",
                                        n_clicks=0,
                                        style=SECONDARY_BUTTON_STYLE,
                                    ),
                                ],
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
                                            html.Button(
                                                "Quit Exam",
                                                id="quit-exam-btn",
                                                n_clicks=0,
                                                style=SECONDARY_BUTTON_STYLE,
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
                            html.Div(
                                id="quit-confirm-panel",
                                style={"display": "none", "marginTop": "16px"},
                                children=[
                                    html.P(
                                        "Quit this exam? Your in-progress attempt will be abandoned.",
                                        style={"marginBottom": "8px"},
                                    ),
                                    html.Button(
                                        "Abandon exam",
                                        id="quit-confirm-btn",
                                        n_clicks=0,
                                        style={**PRIMARY_BUTTON_STYLE, "marginRight": "8px"},
                                    ),
                                    html.Button(
                                        "Keep exam",
                                        id="quit-cancel-btn",
                                        n_clicks=0,
                                        style=SECONDARY_BUTTON_STYLE,
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ]
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


def _requested_mode(triggered_id=None, stored_mode=None):
    if triggered_id == "practice-mode-btn" or stored_mode == ExamAttempt.MODE_PRACTICE:
        return ExamAttempt.MODE_PRACTICE
    return ExamAttempt.MODE_EXAM


def _create_exam_session(domain, subsection, mode):
    """Start a new attempt for current_user. Caller must have abandoned any prior row."""
    pool = df[(df["Domain"] == domain) & (df["Sub-Section"] == subsection)]
    if pool.empty:
        return None, "No questions found for this Domain / Sub-Section yet."
    if "id" not in pool.columns:
        return None, "Question bank is missing ids. Re-seed questions."
    sampled = pool.sample(frac=1)
    question_ids = [int(qid) for qid in sampled["id"].tolist()]
    attempt = start_attempt(current_user.id, domain, subsection, question_ids, mode=mode)
    session = public_exam_session(current_user.id, attempt)
    if not session:
        return None, "Could not start the exam. Try again."
    return session, ""


HIDDEN = {"display": "none"}
REPLACE_PANEL_STYLE = {"display": "block", "marginBottom": "12px"}
QUIT_PANEL_STYLE = {"display": "block", "marginTop": "16px"}


@dash.callback(
    Output("exam-session-store", "data"),
    Output("setup-error-msg", "children"),
    Output("replace-confirm-panel", "style"),
    Output("pending-start-mode", "data"),
    Input("exam-mode-btn", "n_clicks"),
    Input("practice-mode-btn", "n_clicks"),
    State("domain-dropdown", "value"),
    State("subsection-dropdown", "value"),
    prevent_initial_call=True,
)
def start_exam(_exam_clicks, _practice_clicks, domain, subsection):
    """Create a Postgres attempt, or ask to abandon the current in-progress one."""
    mode = _requested_mode(dash.ctx.triggered_id)
    if not current_user.is_authenticated:
        return dash.no_update, "Please log in.", HIDDEN, mode
    if not domain or not subsection:
        return dash.no_update, "Please select a Domain and Sub-Section first.", HIDDEN, mode
    if get_in_progress_attempt(current_user.id):
        return dash.no_update, "", REPLACE_PANEL_STYLE, mode
    session, error = _create_exam_session(domain, subsection, mode)
    if error:
        return dash.no_update, error, HIDDEN, mode
    return session, "", HIDDEN, mode


@dash.callback(
    Output("exam-session-store", "data", allow_duplicate=True),
    Output("setup-error-msg", "children", allow_duplicate=True),
    Output("replace-confirm-panel", "style", allow_duplicate=True),
    Input("replace-confirm-btn", "n_clicks"),
    Input("replace-cancel-btn", "n_clicks"),
    State("domain-dropdown", "value"),
    State("subsection-dropdown", "value"),
    State("pending-start-mode", "data"),
    prevent_initial_call=True,
)
def confirm_replace_start(_confirm, _cancel, domain, subsection, pending_mode):
    """Abandon the in-progress row only after the user confirms a new start."""
    if not current_user.is_authenticated:
        return dash.no_update, dash.no_update, HIDDEN
    if dash.ctx.triggered_id == "replace-cancel-btn":
        session = public_exam_session(current_user.id)
        return session or dash.no_update, "", HIDDEN
    if not domain or not subsection:
        return dash.no_update, "Please select a Domain and Sub-Section first.", HIDDEN
    abandon_attempt(current_user.id)
    session, error = _create_exam_session(
        domain, subsection, _requested_mode(stored_mode=pending_mode)
    )
    if error:
        return dash.no_update, error, HIDDEN
    return session, "", HIDDEN


@dash.callback(
    Output("quit-confirm-panel", "style"),
    Input("quit-exam-btn", "n_clicks"),
    Input("quit-cancel-btn", "n_clicks"),
    prevent_initial_call=True,
)
def toggle_quit_confirm(_quit, _cancel):
    if dash.ctx.triggered_id == "quit-exam-btn":
        return QUIT_PANEL_STYLE
    return HIDDEN


@dash.callback(
    Output("exam-session-store", "data", allow_duplicate=True),
    Output("quit-confirm-panel", "style", allow_duplicate=True),
    Input("quit-confirm-btn", "n_clicks"),
    State("exam-session-store", "data"),
    prevent_initial_call=True,
)
def confirm_quit(_n_clicks, data):
    """Abandon the current attempt after an explicit Quit confirm."""
    if not current_user.is_authenticated:
        return dash.no_update, HIDDEN
    attempt_id = (data or {}).get("attempt_id")
    abandoned = abandon_attempt(current_user.id, attempt_id)
    if abandoned is None:
        return dash.no_update, HIDDEN
    return None, HIDDEN


dash.clientside_callback(
    """
    function(a, b, c, d, data) {
        if (!data || !data.questions) {
            return window.dash_clientside.no_update;
        }
        const ctx = dash_clientside.callback_context;
        if (!ctx.triggered || !ctx.triggered.length || !ctx.triggered[0].value) {
            return window.dash_clientside.no_update;
        }
        const map = {
            "option-card-A": "A",
            "option-card-B": "B",
            "option-card-C": "C",
            "option-card-D": "D"
        };
        const letter = map[ctx.triggered_id];
        if (!letter) {
            return window.dash_clientside.no_update;
        }
        const idx = data.current_index || 0;
        const graded = data.graded || {};
        if (graded[String(idx)]) {
            return window.dash_clientside.no_update;
        }
        const answers = Object.assign({}, data.answers || {});
        answers[String(idx)] = letter;
        return Object.assign({}, data, {answers: answers});
    }
    """,
    Output("exam-session-store", "data", allow_duplicate=True),
    Input(OPTION_CARD_IDS["A"], "n_clicks"),
    Input(OPTION_CARD_IDS["B"], "n_clicks"),
    Input(OPTION_CARD_IDS["C"], "n_clicks"),
    Input(OPTION_CARD_IDS["D"], "n_clicks"),
    State("exam-session-store", "data"),
    prevent_initial_call=True,
)


@dash.callback(
    Output("exam-persist-ack", "children"),
    Input(OPTION_CARD_IDS["A"], "n_clicks"),
    Input(OPTION_CARD_IDS["B"], "n_clicks"),
    Input(OPTION_CARD_IDS["C"], "n_clicks"),
    Input(OPTION_CARD_IDS["D"], "n_clicks"),
    State("exam-session-store", "data"),
    prevent_initial_call=True,
)
def persist_selected_option(_a, _b, _c, _d, data):
    """Thin DB write. UI already updated from the clientside store patch."""
    if not current_user.is_authenticated or not data or not data.get("questions"):
        return dash.no_update
    idx = data.get("current_index", 0)
    questions = data["questions"]
    if idx < 0 or idx >= len(questions):
        return dash.no_update
    if (data.get("graded") or {}).get(str(idx)):
        return dash.no_update
    id_to_letter = {v: k for k, v in OPTION_CARD_IDS.items()}
    letter = id_to_letter.get(dash.ctx.triggered_id)
    if not letter:
        return dash.no_update
    save_selected_option(
        current_user.id,
        data.get("attempt_id"),
        questions[idx].get("id"),
        letter,
    )
    return ""


@dash.callback(
    Output("exam-session-store", "data", allow_duplicate=True),
    Input("grade-btn", "n_clicks"),
    State("exam-session-store", "data"),
    prevent_initial_call=True,
)
def grade_current_question(_n_clicks, data):
    """Practice only: reveal after an option is selected. No DB score write."""
    if not data or data.get("mode") != ExamAttempt.MODE_PRACTICE:
        return dash.no_update
    idx = data.get("current_index", 0)
    if str(idx) not in (data.get("answers") or {}):
        return dash.no_update
    graded = dict(data.get("graded") or {})
    graded[str(idx)] = True
    return {**data, "graded": graded}


dash.clientside_callback(
    """
    function(prevClicks, nextClicks, data) {
        if (!data || !data.questions) {
            return window.dash_clientside.no_update;
        }
        const ctx = dash_clientside.callback_context;
        if (!ctx.triggered || !ctx.triggered.length || !ctx.triggered[0].value) {
            return window.dash_clientside.no_update;
        }
        const total = data.questions.length;
        let idx = data.current_index || 0;
        if (ctx.triggered_id === "prev-btn") {
            idx = Math.max(0, idx - 1);
        } else if (ctx.triggered_id === "next-btn") {
            idx = Math.min(total - 1, idx + 1);
        } else {
            return window.dash_clientside.no_update;
        }
        return Object.assign({}, data, {current_index: idx});
    }
    """,
    Output("exam-session-store", "data", allow_duplicate=True),
    Input("prev-btn", "n_clicks"),
    Input("next-btn", "n_clicks"),
    State("exam-session-store", "data"),
    prevent_initial_call=True,
)


@dash.callback(
    Output("exam-persist-ack", "children", allow_duplicate=True),
    Input("prev-btn", "n_clicks"),
    Input("next-btn", "n_clicks"),
    State("exam-session-store", "data"),
    prevent_initial_call=True,
)
def persist_resume_index(_prev_clicks, _next_clicks, data):
    if not current_user.is_authenticated or not data or not data.get("questions"):
        return dash.no_update
    total = len(data["questions"])
    idx = data.get("current_index", 0)
    if dash.ctx.triggered_id == "prev-btn":
        idx = max(0, idx - 1)
    elif dash.ctx.triggered_id == "next-btn":
        idx = min(total - 1, idx + 1)
    set_resume_index(current_user.id, data.get("attempt_id"), idx)
    return ""


@dash.callback(
    Output("exam-session-store", "data", allow_duplicate=True),
    Output("exam-persist-ack", "children", allow_duplicate=True),
    Input({"type": "page-btn", "index": ALL}, "n_clicks"),
    State("exam-session-store", "data"),
    prevent_initial_call=True,
)
def jump_to_question(_all_clicks, data):
    """Jump locally, then persist the cursor. Do not reload questions."""
    if not data or not data.get("questions"):
        return dash.no_update, dash.no_update

    triggered = dash.ctx.triggered[0] if dash.ctx.triggered else None
    if not triggered or not triggered.get("value"):
        return dash.no_update, dash.no_update

    triggered_id = dash.ctx.triggered_id
    if not triggered_id or "index" not in triggered_id:
        return dash.no_update, dash.no_update

    total = len(data["questions"])
    idx = max(0, min(triggered_id["index"], total - 1))
    patched = {**data, "current_index": idx}
    if current_user.is_authenticated:
        set_resume_index(current_user.id, data.get("attempt_id"), idx)
    return patched, ""


@dash.callback(
    Output("exam-timer-label", "children"),
    Input("exam-timer-interval", "n_intervals"),
    State("exam-session-store", "data"),
    prevent_initial_call=True,
)
def update_timer(_n_intervals, data):
    """Show how long the candidate has spent on the current exam attempt."""
    if not data or not data.get("questions"):
        return ""

    started_at = data.get("started_at")
    if not started_at:
        return ""

    try:
        started_dt = datetime.fromisoformat(started_at)
    except ValueError:
        return ""

    elapsed_seconds = max(0, int((datetime.utcnow() - started_dt).total_seconds()))
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
    prevent_initial_call=True,
)
def render_exam(data):
    """Show the setup form or the current exam question, based on session state."""
    if not data or not data.get("questions"):
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
    row = questions[idx]
    is_practice = data.get("mode") == ExamAttempt.MODE_PRACTICE
    is_graded = is_practice and bool((data.get("graded") or {}).get(str(idx)))
    selected_letter = answers.get(str(idx))
    correct_letter = (
        str(row.get("Correct Answer") or "").strip().upper() if is_practice else ""
    )

    option_updates = []
    for letter in OPTION_LETTERS:
        content = html.Span(
            [html.Strong(f"{letter}. "), row[f"Option {letter}"]]
        )
        style = _option_card_style(letter, selected_letter, correct_letter, is_graded)
        option_updates.extend([content, style])

    if is_practice and is_graded:
        is_correct = selected_letter == correct_letter
        result_text = (
            "Correct!"
            if is_correct
            else f"Incorrect \u2014 the correct answer was {correct_letter}."
        )
        result_color = CORRECT_COLOR if is_correct else INCORRECT_COLOR
        explanation_children = html.Div(
            [
                html.Div(result_text, style={"fontWeight": "bold", "color": result_color}),
                html.Div(
                    row.get("Explanation") or "",
                    style={"marginTop": "6px", "color": "#374151"},
                ),
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
    elif is_practice:
        explanation_children = ""
        explanation_style = {"gridColumn": "1", "gridRow": "4", "display": "none"}
        grade_btn_label = "Grade Now"
        grade_btn_disabled = selected_letter is None
        grade_btn_style = (
            DISABLED_BUTTON_STYLE if selected_letter is None else SECONDARY_BUTTON_STYLE
        )
    else:
        explanation_children = ""
        explanation_style = {"gridColumn": "1", "gridRow": "4", "display": "none"}
        grade_btn_label = "Grade Now"
        grade_btn_disabled = True
        grade_btn_style = DISABLED_BUTTON_STYLE

    # Progress ring counts answers saved so far, not correctness.
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
    Input("exam-page-ready", "id"),
    prevent_initial_call="initial_duplicate",
)
def hydrate_in_progress(_ready):
    """Reload the in-progress attempt from Postgres after refresh / reconnect."""
    if not current_user.is_authenticated:
        return dash.no_update
    return public_exam_session(current_user.id)


@dash.callback(
    Output("exam-session-store", "data", allow_duplicate=True),
    Output("_pages_location", "pathname"),
    Input("submit-exam-btn", "n_clicks"),
    State("exam-session-store", "data"),
    prevent_initial_call=True,
)
def submit_exam(_n_clicks, data):
    """Complete the attempt from DB answers and redirect. Ignore client scores."""
    if not current_user.is_authenticated or not data:
        return dash.no_update, dash.no_update

    completed = complete_attempt(current_user.id, data.get("attempt_id"))
    if not completed:
        return dash.no_update, dash.no_update
    return None, "/results"
