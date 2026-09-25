"""Shared single-column layout shell used by the exam, results, and review pages.

The whole page is inset by 20% padding on the left and right, so content
sits centered in the middle 60% of the viewport. A small profile icon in
the top-right corner links to the admin dashboard, which has its own
full-page layout and does not use this shell.
"""

from dash import html

from components.ui import account_controls


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
                html.Div(account_controls(), style={"marginBottom": "16px"}),
                content,
            ],
        ),
    )
