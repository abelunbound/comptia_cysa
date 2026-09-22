"""Admin Dashboard ('/admin'): static UI mockup reached via the profile icon.

This page intentionally uses placeholder data throughout -- the app has no
multi-user backend yet, so nothing here is wired to real state. It exists to
demonstrate the target layout for a future, fully-functional admin area.

SECURITY NOTE (M1): Currently accessible to any logged-in user. Role-based access
control (admin vs. regular user) will be added in a future milestone. Residual
risk: authenticated users can view this mock dashboard, which contains no real data.
"""

import dash
import plotly.graph_objects as go
from dash import Input, Output, dcc, html
from flask_login import current_user

dash.register_page(__name__, path="/admin", name="Admin")

NAV_ITEMS = [
    ("Dashboard", True),
    ("Exams", False),
    ("Results Database", False),
    ("Certificates", False),
    ("Settings", False),
    ("Help", False),
]

STAT_CARDS = [
    {"label": "Need to Grade", "value": "87%", "sub": "Average grade this month"},
    {"label": "New Active Students", "value": "536", "sub": "+6.35% from last month"},
    {"label": "Questions", "value": "64", "sub": "+2.56% in the question bank"},
]


def _sidebar():
    nav_children = []
    for label, active in NAV_ITEMS:
        nav_children.append(
            html.Div(
                label,
                style={
                    "padding": "10px 16px",
                    "borderRadius": "6px",
                    "marginBottom": "4px",
                    "backgroundColor": "#eef2ff" if active else "transparent",
                    "color": "#4338ca" if active else "#374151",
                    "fontWeight": "600" if active else "normal",
                    "fontSize": "14px",
                },
            )
        )

    return html.Div(
        style={
            "flex": "0 0 220px",
            "maxWidth": "220px",
            "backgroundColor": "#ffffff",
            "borderRight": "1px solid #e5e7eb",
            "padding": "24px 12px",
            "boxSizing": "border-box",
            "display": "flex",
            "flexDirection": "column",
            "justifyContent": "space-between",
        },
        children=[
            html.Div(
                [
                    html.Div(
                        "CySA+ Admin",
                        style={
                            "fontWeight": "bold",
                            "fontSize": "18px",
                            "padding": "0 16px",
                            "marginBottom": "24px",
                        },
                    ),
                    html.Div(nav_children),
                ]
            ),
            dcc.Link(
                "\u2190 Back to Quiz",
                href="/",
                style={
                    "display": "block",
                    "padding": "10px 16px",
                    "color": "#2563eb",
                    "fontSize": "14px",
                    "textDecoration": "none",
                },
            ),
        ],
    )


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


def _exam_taken_chart():
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    values = [12, 14, 18, 22, 19, 24, 28, 26, 21, 17, 15, 13]

    fig = go.Figure(
        data=[
            go.Scatter(
                x=months,
                y=values,
                mode="lines+markers",
                line={"color": "#6366f1", "shape": "spline"},
                fill="tozeroy",
                fillcolor="rgba(99, 102, 241, 0.1)",
            )
        ]
    )
    fig.update_layout(
        title="Exam Taken Times",
        margin={"l": 30, "r": 10, "t": 40, "b": 30},
        height=300,
        plot_bgcolor="white",
    )
    return dcc.Graph(figure=fig, config={"displayModeBar": False})


def _average_results_chart():
    subjects = ["Economics", "Science", "English", "Mathematic"]
    easy = [20, 25, 22, 30]
    medium = [25, 20, 28, 25]
    hard = [15, 18, 12, 20]

    fig = go.Figure(
        data=[
            go.Bar(name="Easy questions", x=easy, y=subjects, orientation="h", marker_color="#a5b4fc"),
            go.Bar(name="Medium questions", x=medium, y=subjects, orientation="h", marker_color="#818cf8"),
            go.Bar(name="Hard questions", x=hard, y=subjects, orientation="h", marker_color="#4f46e5"),
        ]
    )
    fig.update_layout(
        title="Average Results For Test Questions",
        barmode="stack",
        margin={"l": 90, "r": 10, "t": 40, "b": 30},
        height=300,
        plot_bgcolor="white",
        legend={"orientation": "h", "y": -0.15},
    )
    return dcc.Graph(figure=fig, config={"displayModeBar": False})


RESULTS_TABLE_ROWS = [
    {"name": "Tahsan Khan", "score": "16.7%", "attempts": "1/2", "start_date": "Jan 20, 2026"},
    {"name": "Anwar Hussen", "score": "19.7%", "attempts": "2/2", "start_date": "Jan 20, 2026"},
    {"name": "Hasan Khan", "score": "13.7%", "attempts": "0/2", "start_date": "Jan 20, 2026"},
]


def _results_table():
    header = html.Tr(
        [
            html.Th("Name"),
            html.Th("Total Score"),
            html.Th("Attempts"),
            html.Th("Start Date"),
        ]
    )
    rows = [
        html.Tr(
            [
                html.Td(row["name"]),
                html.Td(row["score"]),
                html.Td(row["attempts"]),
                html.Td(row["start_date"]),
            ]
        )
        for row in RESULTS_TABLE_ROWS
    ]
    return html.Table(
        [html.Thead(header), html.Tbody(rows)],
        style={"width": "100%", "borderCollapse": "collapse", "fontSize": "14px"},
    )


layout = html.Div(id="admin-container")


@dash.callback(
    Output("admin-container", "children"),
    Input("_pages_location", "pathname"),
)
def render_admin(pathname):
    """Render admin dashboard if authenticated (Flask before_request handles redirect)."""
    if pathname != "/admin":
        return dash.no_update

    # Flask before_request already redirected unauthenticated users
    if not current_user.is_authenticated:
        return html.Div()

    return html.Div(
        style={"display": "flex", "minHeight": "100vh", "fontFamily": "Arial, sans-serif"},
        children=[
            _sidebar(),
            html.Div(
                style={"flex": 1, "padding": "32px", "backgroundColor": "#f9fafb"},
                children=[
                    html.Div(
                        [
                            html.H2("Good Morning", style={"margin": 0}),
                            html.P(
                                "This is a static preview of a future admin dashboard.",
                                style={"color": "#6b7280"},
                            ),
                        ],
                        style={"marginBottom": "24px"},
                    ),
                    html.Div(
                        style={"display": "flex", "gap": "16px", "marginBottom": "24px"},
                        children=[_stat_card(card) for card in STAT_CARDS],
                    ),
                    html.Div(
                        style={"display": "flex", "gap": "16px", "marginBottom": "24px"},
                        children=[
                            html.Div(
                                _exam_taken_chart(),
                                style={
                                    "flex": 3,
                                    "backgroundColor": "white",
                                    "border": "1px solid #e5e7eb",
                                    "borderRadius": "10px",
                                    "padding": "12px",
                                },
                            ),
                            html.Div(
                                _average_results_chart(),
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
                        children=[
                            html.H3("Browse Test Results", style={"marginTop": 0}),
                            _results_table(),
                        ],
                    ),
                ],
            ),
        ],
    )
