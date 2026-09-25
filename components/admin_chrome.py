"""Shared admin sidebar + page frame for /admin, /exams, and /admin/results."""

from dash import dcc, html

from components.ui import account_controls

NAV_ITEMS = (
    ("Dashboard", "/admin"),
    ("Exams", "/exams"),
    ("Results Database", "/admin/results"),
    ("Certificates", None),
    ("Settings", None),
    ("Help", None),
)


def _nav_style(active):
    return {
        "padding": "10px 16px",
        "borderRadius": "6px",
        "marginBottom": "4px",
        "backgroundColor": "#eef2ff" if active else "transparent",
        "color": "#4338ca" if active else "#374151",
        "fontWeight": "600" if active else "normal",
        "fontSize": "14px",
        "textDecoration": "none",
        "display": "block",
    }


def sidebar(active="Dashboard"):
    nav_children = []
    for label, href in NAV_ITEMS:
        is_active = label == active
        style = _nav_style(is_active)
        if href:
            nav_children.append(dcc.Link(label, href=href, style=style))
        else:
            nav_children.append(html.Div(label, style=style))

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
                        "CyberSec App",
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


def admin_chrome(content, active="Dashboard"):
    return html.Div(
        style={"display": "flex", "minHeight": "100vh", "fontFamily": "Arial, sans-serif"},
        children=[
            sidebar(active),
            html.Div(
                style={
                    "flex": 1,
                    "padding": "24px 32px 32px",
                    "backgroundColor": "#f9fafb",
                    "boxSizing": "border-box",
                },
                children=[
                    html.Div(
                        account_controls(),
                        style={"marginBottom": "8px"},
                    ),
                    html.Div(content),
                ],
            ),
        ],
    )
