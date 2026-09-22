"""Login page ('/login'): authenticate existing users."""

import dash
from dash import Input, Output, State, dcc, html
from flask_login import login_user

from auth import authenticate_user
from components.ui import (
    ACCENT_COLOR,
    HEADING_COLOR,
    PRIMARY_BUTTON_STYLE,
    SUBTEXT_COLOR,
)

dash.register_page(__name__, path="/login", name="Log In")

layout = html.Div(
    [
        dcc.Store(id="login-redirect-to"),
        html.Div(
            style={
                "display": "flex",
                "justifyContent": "center",
                "alignItems": "center",
                "minHeight": "100vh",
                "backgroundColor": "#f9fafb",
                "fontFamily": "Arial, sans-serif",
            },
            children=[
                html.Div(
            style={
                "backgroundColor": "white",
                "padding": "40px",
                "borderRadius": "12px",
                "boxShadow": "0 4px 6px rgba(0,0,0,0.1)",
                "width": "100%",
                "maxWidth": "400px",
            },
            children=[
                html.Div(
                    style={"textAlign": "center", "marginBottom": "32px"},
                    children=[
                        html.H1(
                            "Welcome Back",
                            style={"margin": 0, "color": HEADING_COLOR, "fontSize": "28px"},
                        ),
                        html.P(
                            "Log in to continue your CySA+ practice",
                            style={"color": SUBTEXT_COLOR, "marginTop": "8px"},
                        ),
                    ],
                ),
                html.Div(
                    id="login-error-msg",
                    style={
                        "color": "#dc2626",
                        "marginBottom": "16px",
                        "display": "none",
                        "padding": "12px",
                        "backgroundColor": "#fee2e2",
                        "borderRadius": "6px",
                        "fontSize": "14px",
                    },
                ),
                html.Div(
                    style={"marginBottom": "16px"},
                    children=[
                        html.Label(
                            "Email",
                            style={
                                "display": "block",
                                "marginBottom": "6px",
                                "fontWeight": "500",
                                "fontSize": "14px",
                            },
                        ),
                        dcc.Input(
                            id="login-email",
                            type="email",
                            placeholder="you@example.com",
                            required=True,
                            style={
                                "width": "100%",
                                "padding": "10px 12px",
                                "border": "1px solid #d1d5db",
                                "borderRadius": "6px",
                                "fontSize": "14px",
                                "boxSizing": "border-box",
                            },
                        ),
                    ],
                ),
                html.Div(
                    style={"marginBottom": "16px"},
                    children=[
                        html.Label(
                            "Password",
                            style={
                                "display": "block",
                                "marginBottom": "6px",
                                "fontWeight": "500",
                                "fontSize": "14px",
                            },
                        ),
                        dcc.Input(
                            id="login-password",
                            type="password",
                            placeholder="Enter your password",
                            required=True,
                            style={
                                "width": "100%",
                                "padding": "10px 12px",
                                "border": "1px solid #d1d5db",
                                "borderRadius": "6px",
                                "fontSize": "14px",
                                "boxSizing": "border-box",
                            },
                        ),
                    ],
                ),
                html.Button(
                    "Log In",
                    id="login-btn",
                    n_clicks=0,
                    style={**PRIMARY_BUTTON_STYLE, "width": "100%"},
                ),
                html.Div(
                    style={
                        "marginTop": "24px",
                        "textAlign": "center",
                        "fontSize": "14px",
                        "color": SUBTEXT_COLOR,
                    },
                    children=[
                        "Don't have an account? ",
                        dcc.Link(
                            "Sign up",
                            href="/signup",
                            style={"color": ACCENT_COLOR, "textDecoration": "none"},
                        ),
                    ],
                ),
            ],
        ),
            ],
        ),
    ]
)


dash.clientside_callback(
    """
    function(redirectTo) {
        if (redirectTo) {
            window.location.assign(redirectTo);
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("login-redirect-to", "data", allow_duplicate=True),
    Input("login-redirect-to", "data"),
    prevent_initial_call=True,
)


@dash.callback(
    Output("login-redirect-to", "data"),
    Output("login-error-msg", "children"),
    Output("login-error-msg", "style"),
    Input("login-btn", "n_clicks"),
    State("login-email", "value"),
    State("login-password", "value"),
    prevent_initial_call=True,
)
def handle_login(_n_clicks, email, password):
    """Authenticate user and redirect to exam page on success."""
    if not email or not password:
        return (
            dash.no_update,
            "Please enter both email and password.",
            {
                "color": "#dc2626",
                "marginBottom": "16px",
                "display": "block",
                "padding": "12px",
                "backgroundColor": "#fee2e2",
                "borderRadius": "6px",
                "fontSize": "14px",
            },
        )

    user = authenticate_user(email, password)
    if not user:
        return (
            dash.no_update,
            "Invalid email or password.",
            {
                "color": "#dc2626",
                "marginBottom": "16px",
                "display": "block",
                "padding": "12px",
                "backgroundColor": "#fee2e2",
                "borderRadius": "6px",
                "fontSize": "14px",
            },
        )

    login_user(user, remember=True)
    return "/", "", {"display": "none"}
