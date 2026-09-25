"""Results Database ('/admin/results'): Exam Results beside the admin sidebar."""

import dash
from dash import html
from flask_login import current_user

from components.admin_chrome import admin_chrome

dash.register_page(__name__, path="/admin/results", name="Results Database")


def layout(**kwargs):
    if not current_user.is_authenticated:
        return html.Div()
    return admin_chrome(
        html.Div(
            [
                html.Div(id="results-page-ready"),
                html.Div(id="results-container"),
            ]
        ),
        active="Results Database",
    )
