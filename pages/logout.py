"""Logout page ('/logout'): clear session and redirect to login."""

import dash
from dash import Input, Output, dcc, html
from flask_login import logout_user

dash.register_page(__name__, path="/logout", name="Log Out")

layout = html.Div([
    dcc.Store(id="logout-redirect-to"),
    html.Div(id="logout-container"),
])


dash.clientside_callback(
    """
    function(redirectTo) {
        if (redirectTo) {
            window.location.assign(redirectTo);
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("logout-redirect-to", "data", allow_duplicate=True),
    Input("logout-redirect-to", "data"),
    prevent_initial_call=True,
)


@dash.callback(
    Output("logout-redirect-to", "data"),
    Input("_pages_location", "pathname"),
    prevent_initial_call=True,
)
def handle_logout(pathname):
    """Clear the user's session and redirect to login page."""
    if pathname == "/logout":
        logout_user()
        return "/login"
    return dash.no_update
