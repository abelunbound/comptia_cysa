"""Signup page ('/signup'): create a new user account."""

import dash
from dash import Input, Output, State, dcc, html
from flask_login import login_user

from auth import create_user
from components.ui import (
    ACCENT_COLOR,
    HEADING_COLOR,
    PRIMARY_BUTTON_STYLE,
    SUBTEXT_COLOR,
)

dash.register_page(__name__, path="/signup", name="Sign Up")

layout = html.Div(
    [
        dcc.Store(id="signup-redirect-to"),
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
                            "Create Account",
                            style={"margin": 0, "color": HEADING_COLOR, "fontSize": "28px"},
                        ),
                        html.P(
                            "Sign up to access the CySA+ practice exams",
                            style={"color": SUBTEXT_COLOR, "marginTop": "8px"},
                        ),
                    ],
                ),
                html.Div(
                    id="signup-error-msg",
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
                            id="signup-email",
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
                            id="signup-password",
                            type="password",
                            placeholder="At least 8 characters",
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
                            "Confirm Password",
                            style={
                                "display": "block",
                                "marginBottom": "6px",
                                "fontWeight": "500",
                                "fontSize": "14px",
                            },
                        ),
                        dcc.Input(
                            id="signup-password-confirm",
                            type="password",
                            placeholder="Re-enter your password",
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
                    "Sign Up",
                    id="signup-btn",
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
                        "Already have an account? ",
                        dcc.Link(
                            "Log in",
                            href="/login",
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
    Output("signup-redirect-to", "data", allow_duplicate=True),
    Input("signup-redirect-to", "data"),
    prevent_initial_call=True,
)


@dash.callback(
    Output("signup-redirect-to", "data"),
    Output("signup-error-msg", "children"),
    Output("signup-error-msg", "style"),
    Input("signup-btn", "n_clicks"),
    State("signup-email", "value"),
    State("signup-password", "value"),
    State("signup-password-confirm", "value"),
    prevent_initial_call=True,
)
def handle_signup(_n_clicks, email, password, password_confirm):
    """Create a new user account and redirect to exam page on success."""
    if not email or not password or not password_confirm:
        return (
            dash.no_update,
            "Please fill in all fields.",
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

    if password != password_confirm:
        return (
            dash.no_update,
            "Passwords do not match.",
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

    user, error = create_user(email, password)
    if error:
        return (
            dash.no_update,
            error,
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
