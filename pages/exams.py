"""Exam catalog ('/exams'): cards that launch a quiz. Only CySA+ is unlocked."""

import dash
from dash import dcc, html
from flask_login import current_user

from components.admin_chrome import admin_chrome

dash.register_page(__name__, path="/exams", name="Exams")

EXAM_CARDS = (
    {
        "title": "CompTIA CySA+",
        "subtitle": "Cybersecurity Analyst practice exam",
        "href": "/",
        "locked": False,
    },
    {
        "title": "CompTIA Security+",
        "subtitle": "Coming soon",
        "href": None,
        "locked": True,
    },
    {
        "title": "CompTIA PenTest+",
        "subtitle": "Coming soon",
        "href": None,
        "locked": True,
    },
)


def layout(**kwargs):
    if not current_user.is_authenticated:
        return html.Div()
    return admin_chrome(_exams_content(), active="Exams")


def _exams_content():
    return html.Div(
        [
            html.H2("Exams", style={"margin": "0 0 8px 0"}),
            html.P(
                "Choose an exam. Locked cards are placeholders.",
                style={"color": "#6b7280", "marginBottom": "24px"},
            ),
            html.Div(
                style={
                    "display": "grid",
                    "gridTemplateColumns": "repeat(3, minmax(0, 1fr))",
                    "gap": "16px",
                },
                children=[_exam_card(card) for card in EXAM_CARDS],
            ),
        ]
    )


def _exam_card(card):
    if card["locked"]:
        return _locked_card(card)
    return dcc.Link(
        _card_body(card, locked=False),
        href=card["href"],
        style={"textDecoration": "none", "color": "inherit"},
    )


def _locked_card(card):
    return html.Div(
        _card_body(card, locked=True),
        style={"cursor": "not-allowed"},
    )


def _card_body(card, locked):
    if locked:
        side = html.Div(
            "\U0001f512",
            style={"fontSize": "28px", "lineHeight": "1", "opacity": "0.7"},
        )
        border = "1px solid #e5e7eb"
        background = "#f3f4f6"
        title_color = "#9ca3af"
        sub_color = "#9ca3af"
    else:
        side = html.Img(
            src=dash.get_asset_url("cysa_logo.webp"),
            style={"width": "56px", "height": "auto", "display": "block"},
        )
        border = "1px solid #c7d2fe"
        background = "#ffffff"
        title_color = "#1f2937"
        sub_color = "#6b7280"

    return html.Div(
        style={
            "display": "flex",
            "alignItems": "center",
            "gap": "16px",
            "backgroundColor": background,
            "border": border,
            "borderRadius": "10px",
            "padding": "20px",
            "minHeight": "96px",
            "boxSizing": "border-box",
            "opacity": "0.65" if locked else "1",
            "filter": "grayscale(1)" if locked else "none",
        },
        children=[
            side,
            html.Div(
                [
                    html.Div(
                        card["title"],
                        style={
                            "fontWeight": "bold",
                            "fontSize": "16px",
                            "color": title_color,
                        },
                    ),
                    html.Div(
                        card["subtitle"],
                        style={"fontSize": "13px", "color": sub_color, "marginTop": "4px"},
                    ),
                ]
            ),
        ],
    )
