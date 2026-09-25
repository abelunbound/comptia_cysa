"""Admin Dashboard ('/admin'): profile-icon home.

The four large numbers, time chart, latest-performance donut, and
browse-results table are live and scoped to current_user.

SECURITY NOTE: any logged-in user can open this page. Metrics never include
another user's attempts. Role-based admin access is a later milestone.
"""

import dash
import plotly.graph_objects as go
from dash import Input, Output, State, dcc, html
from flask_login import current_user

from components.admin_chrome import admin_chrome
from attempts import (
    CHART_ATTEMPT_SLOTS,
    PASS_PERCENT,
    RESULTS_PAGE_SIZE,
    dashboard_metrics,
    dashboard_results_page,
    latest_exam_percent,
    recent_attempt_durations,
    time_target_baseline,
)

DONUT_LABEL_COLOR = "#4338ca"

dash.register_page(__name__, path="/admin", name="Admin")


def layout(**kwargs):
    """Layout function: check auth and return admin dashboard or empty (Flask handles redirect)."""
    if not current_user.is_authenticated:
        return html.Div()
    
    return _admin_dashboard()


def _stat_cards(metrics):
    return [
        {
            "label": "Highest score",
            "value": f"{metrics['highest_score']}%",
            "sub": "Best completed exam",
        },
        {
            "label": "Total attempts",
            "value": str(metrics["total_attempts"]),
            "sub": "Completed exams",
        },
        {
            "label": "Pass rate",
            "value": f"{metrics['pass_rate']}%",
            "sub": f"Share of exams at {PASS_PERCENT}% or above",
        },
        {
            "label": "Average score",
            "value": f"{metrics['average_score']}%",
            "sub": "Mean of completed exam percents",
        },
    ]


def _stat_card(card):
    return html.Div(
        style={
            "flex": 1,
            "backgroundColor": "white",
            "border": "1px solid #e5e7eb",
            "borderRadius": "10px",
            "padding": "18px",
        },
        children=[
            html.Div(card["label"], style={"color": "#6b7280", "fontSize": "13px"}),
            html.Div(
                card["value"],
                style={"fontSize": "26px", "fontWeight": "bold", "margin": "6px 0"},
            ),
            html.Div(card["sub"], style={"color": "#16a34a", "fontSize": "12px"}),
        ],
    )


def _exam_taken_chart(durations):
    """Target area (80→50 min) plus this user's Start→Submit times."""
    slots = list(range(1, CHART_ATTEMPT_SLOTS + 1))
    baseline = time_target_baseline()
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=slots,
            y=baseline,
            name="Target",
            mode="lines+markers",
            line={"color": "#6366f1", "width": 2},
            marker={"size": 8},
            fill="tozeroy",
            fillcolor="rgba(99, 102, 241, 0.12)",
        )
    )
    if durations:
        fig.add_trace(
            go.Scatter(
                x=list(range(1, len(durations) + 1)),
                y=durations,
                name="Your time",
                mode="lines+markers",
                line={"color": "#0f766e", "width": 2},
                marker={"size": 8},
            )
        )
    fig.update_layout(
        title="Time per attempt vs target",
        xaxis={
            "title": "Attempt",
            "range": [0.5, CHART_ATTEMPT_SLOTS + 0.5],
            "dtick": 1,
            "tickmode": "linear",
        },
        yaxis={"title": "Minutes", "range": [0, 120], "dtick": 20},
        margin={"l": 48, "r": 10, "t": 40, "b": 40},
        height=300,
        plot_bgcolor="white",
        legend={"orientation": "h", "y": -0.2},
    )
    return dcc.Graph(figure=fig, config={"displayModeBar": False})


def _latest_performance_chart(percent):
    """Donut of the latest exam vs 100%. Center label only; no slice text or legend."""
    scored = 0 if percent is None else max(0, min(100, percent))
    remainder = 100 - scored
    fig = go.Figure(
        data=[
            go.Pie(
                values=[scored, remainder],
                hole=0.72,
                sort=False,
                direction="clockwise",
                rotation=90,
                textinfo="none",
                hoverinfo="skip",
                marker={"colors": ["#6366f1", "#eef2ff"]},
            )
        ]
    )
    fig.update_layout(
        showlegend=False,
        margin={"l": 10, "r": 10, "t": 8, "b": 8},
        height=260,
        paper_bgcolor="white",
        annotations=[
            {
                "text": f"{scored}%",
                "x": 0.5,
                "y": 0.5,
                "xref": "paper",
                "yref": "paper",
                "showarrow": False,
                "font": {"size": 36, "color": DONUT_LABEL_COLOR, "family": "Arial, sans-serif"},
            }
        ],
    )
    return dcc.Graph(figure=fig, config={"displayModeBar": False})


_TH_STYLE = {
    "textAlign": "left",
    "padding": "10px 8px",
    "backgroundColor": DONUT_LABEL_COLOR,
    "color": "#ffffff",
    "fontWeight": "600",
    "border": "none",
}
_TD_STYLE = {
    "padding": "10px 8px",
    "borderBottom": "1px solid #f3f4f6",
    "color": "#111827",
}


def _results_table(rows):
    header = html.Tr(
        [
            html.Th("Subsection", style=_TH_STYLE),
            html.Th("Your Score", style=_TH_STYLE),
            html.Th("Attempts", style=_TH_STYLE),
            html.Th("Date", style=_TH_STYLE),
        ]
    )
    if not rows:
        body = [
            html.Tr(
                [
                    html.Td(
                        "No completed exams yet.",
                        colSpan=4,
                        style={**_TD_STYLE, "color": "#6b7280"},
                    )
                ]
            )
        ]
    else:
        body = [
            html.Tr(
                [
                    html.Td(row["subsection"], style=_TD_STYLE),
                    html.Td(row["score"], style=_TD_STYLE),
                    html.Td(str(row["attempts"]), style=_TD_STYLE),
                    html.Td(row["date"], style=_TD_STYLE),
                ]
            )
            for row in rows
        ]
    return html.Table(
        [html.Thead(header), html.Tbody(body)],
        style={
            "width": "100%",
            "borderCollapse": "collapse",
            "fontSize": "14px",
            "overflow": "hidden",
            "borderRadius": "6px",
        },
    )


_PAGER_BUTTON = {
    "padding": "6px 12px",
    "border": "1px solid #d1d5db",
    "borderRadius": "6px",
    "backgroundColor": "white",
    "cursor": "pointer",
    "fontSize": "13px",
}


def _pager(meta, page, pages, total):
    if total <= RESULTS_PAGE_SIZE:
        style = {"display": "none"}
    else:
        style = {
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "flex-end",
            "gap": "12px",
            "marginTop": "12px",
        }
    return html.Div(
        style=style,
        children=[
            html.Button(
                "Previous",
                id="browse-results-prev",
                n_clicks=0,
                disabled=page <= 1,
                style=_PAGER_BUTTON,
            ),
            html.Span(meta, id="browse-results-meta", style={"fontSize": "13px", "color": "#6b7280"}),
            html.Button(
                "Next",
                id="browse-results-next",
                n_clicks=0,
                disabled=page >= pages,
                style=_PAGER_BUTTON,
            ),
        ],
    )


def _browse_results_block():
    payload = dashboard_results_page(current_user.id, page=1)
    return html.Div(
        [
            html.H3("Browse Mock Exam Results", style={"marginTop": 0}),
            html.Div(id="browse-results-ready"),
            dcc.Store(id="browse-results-page", data=1),
            html.Div(_results_table(payload["rows"]), id="browse-results-table"),
            _pager(
                _page_meta(payload),
                payload["page"],
                payload["pages"],
                payload["total"],
            ),
        ]
    )


def _page_meta(payload):
    total = payload["total"]
    if not total:
        return ""
    page = payload["page"]
    size = RESULTS_PAGE_SIZE
    start = (page - 1) * size + 1
    end = min(page * size, total)
    return f"{start}–{end} of {total}"


def _is_real_click():
    triggered = dash.ctx.triggered[0] if dash.ctx.triggered else None
    return bool(triggered and triggered.get("value"))


@dash.callback(
    Output("browse-results-table", "children"),
    Output("browse-results-meta", "children"),
    Output("browse-results-prev", "disabled"),
    Output("browse-results-next", "disabled"),
    Output("browse-results-page", "data"),
    Input("browse-results-ready", "id"),
    Input("browse-results-prev", "n_clicks"),
    Input("browse-results-next", "n_clicks"),
    State("browse-results-page", "data"),
)
def paginate_browse_results(_ready, _prev, _next, page):
    if not current_user.is_authenticated:
        return _results_table([]), "", True, True, 1

    page = page or 1
    triggered = dash.ctx.triggered_id
    if triggered == "browse-results-next" and _is_real_click():
        page += 1
    elif triggered == "browse-results-prev" and _is_real_click():
        page -= 1

    payload = dashboard_results_page(current_user.id, page=page)
    return (
        _results_table(payload["rows"]),
        _page_meta(payload),
        payload["page"] <= 1,
        payload["page"] >= payload["pages"] or payload["total"] == 0,
        payload["page"],
    )


def _admin_dashboard():
    """Return the admin dashboard UI."""
    metrics = dashboard_metrics(current_user.id)
    durations = recent_attempt_durations(current_user.id)
    latest_percent = latest_exam_percent(current_user.id)
    return admin_chrome(
        [
            html.Div(
                [
                    html.H2("Good Morning", style={"margin": 0}),
                    html.P(
                        "Large numbers are from your completed exams.",
                        style={"color": "#6b7280"},
                    ),
                ],
                style={"marginBottom": "24px"},
            ),
            html.Div(
                style={"display": "flex", "gap": "16px", "marginBottom": "24px"},
                children=[_stat_card(card) for card in _stat_cards(metrics)],
            ),
            html.Div(
                style={"display": "flex", "gap": "16px", "marginBottom": "24px"},
                children=[
                    html.Div(
                        _exam_taken_chart(durations),
                        style={
                            "flex": 3,
                            "backgroundColor": "white",
                            "border": "1px solid #e5e7eb",
                            "borderRadius": "10px",
                            "padding": "12px",
                        },
                    ),
                    html.Div(
                        [
                            html.H3(
                                "Latest Performance",
                                style={
                                    "margin": "4px 0 0 4px",
                                    "fontSize": "16px",
                                    "fontWeight": "normal",
                                    "color": "#374151",
                                },
                            ),
                            _latest_performance_chart(latest_percent),
                        ],
                        style={
                            "flex": 2,
                            "backgroundColor": "white",
                            "border": "1px solid #e5e7eb",
                            "borderRadius": "10px",
                            "padding": "12px",
                        },
                    ),
                ],
            ),
            html.Div(
                style={
                    "backgroundColor": "white",
                    "border": "1px solid #e5e7eb",
                    "borderRadius": "10px",
                    "padding": "20px",
                },
                children=_browse_results_block(),
            ),
        ],
        active="Dashboard",
    )
