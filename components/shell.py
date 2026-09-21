"""Shared single-column layout shell used by the exam, results, and review pages.

The whole page is inset by 20% padding on the left and right, so content
sits centered in the middle 60% of the viewport. A small profile icon in
the top-right corner links to the admin dashboard, which has its own
full-page layout and does not use this shell.
"""

from dash import dcc, html

from components.ui import ACCENT_COLOR


def shell(content):
    """Wrap `content` in the centered, single-column page layout."""
    return html.Div(
        style={
            "minHeight": "100vh",
            "boxSizing": "border-box",
            "padding": "0 20%",
            "backgroundColor": "#ffffff",
            "fontFamily": "Arial, sans-serif",
        },
        children=html.Div(
            style={"padding": "32px 0", "boxSizing": "border-box"},
            children=[
                html.Div(
                    style={
                        "display": "flex",
                        "justifyContent": "flex-end",
                        "marginBottom": "16px",
                    },
                    children=dcc.Link(
                        html.Div(
                            "A",
                            title="Admin Dashboard",
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
                ),
                content,
            ],
        ),
    )
