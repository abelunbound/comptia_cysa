"""Logout page ('/logout'): clear session and redirect to login."""

import dash
from dash import Input, Output, html
from flask_login import logout_user

dash.register_page(__name__, path="/logout", name="Log Out")

layout = html.Div(id="logout-container")


@dash.callback(
    Output("_pages_location", "pathname", allow_duplicate=True),
    Input("_pages_location", "pathname"),
    prevent_initial_call=True,
)
def handle_logout(pathname):
    """Clear the user's session and redirect to login page."""
    if pathname == "/logout":
        logout_user()
        return "/login"
    return dash.no_update
