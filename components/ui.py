"""Small reusable UI building blocks shared across pages."""

from dash import dcc, html
import plotly.graph_objects as go

OPTION_LETTERS = ["A", "B", "C", "D"]

CORRECT_COLOR = "#16a34a"
INCORRECT_COLOR = "#dc2626"
NEUTRAL_COLOR = "#9ca3af"

ACCENT_COLOR = "#711c74"
ACCENT_LIGHT = "#f3e8f6"
HEADING_COLOR = "#1a1a1a"
SUBTEXT_COLOR = "#4b5563"

PAGE_BG_COLOR = "#ffffff"
CARD_BG_COLOR = "#f5f6f8"

PAGE_CARD_STYLE = {
    "backgroundColor": CARD_BG_COLOR,
    "borderRadius": "12px",
    "padding": "28px",
}

INTRO_CARD_STYLE = {
    "backgroundColor": "#ffffff",
    "borderRadius": "12px",
    "padding": "28px",
    "boxShadow": "6px 6px 14px rgba(0, 0, 0, 0.12)",
}

PRIMARY_BUTTON_STYLE = {
    "padding": "10px 20px",
    "backgroundColor": ACCENT_COLOR,
    "color": "white",
    "border": "none",
    "borderRadius": "6px",
    "cursor": "pointer",
    "fontSize": "14px",
}

SECONDARY_BUTTON_STYLE = {
    "padding": "10px 20px",
    "backgroundColor": "white",
    "color": "#111827",
    "border": "1px solid #d1d5db",
    "borderRadius": "6px",
    "cursor": "pointer",
    "fontSize": "14px",
}

DISABLED_BUTTON_STYLE = {
    **SECONDARY_BUTTON_STYLE,
    "color": "#9ca3af",
    "cursor": "not-allowed",
}

CARD_STYLE = {
    "border": "1px solid #e5e7eb",
    "borderRadius": "8px",
    "padding": "24px",
    "backgroundColor": "white",
}


def progress_bar(percent, color=CORRECT_COLOR, height="8px"):
    """A simple horizontal progress bar filled to `percent` (0-100)."""
    percent = max(0, min(100, percent))
    return html.Div(
        style={
            "width": "100%",
            "height": height,
            "backgroundColor": "#e5e7eb",
            "borderRadius": "999px",
            "overflow": "hidden",
        },
        children=html.Div(
            style={
                "width": f"{percent}%",
                "height": "100%",
                "backgroundColor": color,
                "borderRadius": "999px",
                "transition": "width 0.3s ease",
            }
        ),
    )


def score_header(score, total):
    """Score + percentage title with a progress bar underneath."""
    percent = round((score / total) * 100) if total else 0
    color = CORRECT_COLOR if percent >= 70 else ("#d97706" if percent >= 40 else INCORRECT_COLOR)
    return html.Div(
        [
            html.Div(
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "baseline",
                    "marginBottom": "8px",
                },
                children=[
                    html.H3(f"Score: {score}/{total}", style={"margin": 0}),
                    html.Span(
                        f"{percent}%",
                        style={"fontWeight": "bold", "color": color, "fontSize": "18px"},
                    ),
                ],
            ),
            progress_bar(percent, color=color),
        ]
    )


def score_ring_figure(correct, total, size=180, incorrect=0):
    """A small donut go.Figure showing 'correct/total' -- usable as a callback Output.

    `incorrect` gets its own red slice so a graded-but-wrong question is visibly
    different from a question that simply hasn't been graded yet (both would
    otherwise render as the same gray "remainder" slice).
    """
    total = max(total, 1)
    incorrect = max(0, min(incorrect, total - correct))
    remainder = max(total - correct - incorrect, 0)

    fig = go.Figure(
        data=[
            go.Pie(
                values=[correct, incorrect, remainder],
                hole=0.72,
                marker={"colors": [ACCENT_COLOR, INCORRECT_COLOR, "#e5e7eb"]},
                textinfo="none",
                sort=False,
                direction="clockwise",
            )
        ]
    )
    fig.update_layout(
        showlegend=False,
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        height=size,
        width=size,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        annotations=[
            {
                "text": f"{correct}/{total}",
                "font": {"size": 22, "color": "#111827", "family": "Arial, sans-serif"},
                "showarrow": False,
            }
        ],
    )
    return fig


def score_ring(correct, total, size=180, incorrect=0):
    """A small donut ring showing 'correct/total', wrapped as a standalone dcc.Graph."""
    return dcc.Graph(
        figure=score_ring_figure(correct, total, size=size, incorrect=incorrect),
        config={"displayModeBar": False, "staticPlot": True},
        style={"width": f"{size}px", "height": f"{size}px"},
    )


def account_controls():
    """Logout + profile icon (links to the dashboard)."""
    return html.Div(
        style={
            "display": "flex",
            "justifyContent": "flex-end",
            "alignItems": "center",
            "gap": "12px",
        },
        children=[
            html.A(
                "Logout",
                href="/logout",
                style={
                    "fontSize": "14px",
                    "color": ACCENT_COLOR,
                    "textDecoration": "none",
                    "fontWeight": "500",
                },
            ),
            dcc.Link(
                html.Div(
                    "A",
                    title="Dashboard",
                    style={
                        "width": "40px",
                        "height": "40px",
                        "borderRadius": "50%",
                        "backgroundColor": ACCENT_COLOR,
                        "display": "flex",
                        "alignItems": "center",
                        "justifyContent": "center",
                        "fontSize": "15px",
                        "fontWeight": "bold",
                        "color": "white",
                        "cursor": "pointer",
                    },
                ),
                href="/admin",
                style={"textDecoration": "none"},
            ),
        ],
    )


