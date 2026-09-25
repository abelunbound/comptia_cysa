"""Results page ('/results'): overall performance donut + completed attempts."""

import dash
from dash import Input, Output, html
from flask_login import current_user

from components.results_view import empty_results_state, results_page_children
from components.shell import shell

dash.register_page(__name__, path="/results", name="Results")


def layout(**kwargs):
    """Layout function: check auth and return results or empty (Flask handles redirect)."""
    if not current_user.is_authenticated:
        return shell(html.Div())
    return shell(
        html.Div(
            [
                html.Div(id="results-page-ready"),
                html.Div(id="results-container"),
            ]
        )
    )


@dash.callback(
    Output("results-container", "children"),
    Input("results-page-ready", "id"),
)
def render_results(_ready):
    """Render results from Postgres (not session history)."""
    if not current_user.is_authenticated:
        return empty_results_state()
    return results_page_children(current_user.id)
