"""CySA+ Domain Practice Exam - a multi-page Dash app.

Pages (see pages/):
- /        exam setup (Domain/Sub-Section) + question-by-question exam taking
- /results overall performance donut chart + this session's attempt history
- /review  per-question breakdown of a completed attempt
- /admin   static admin dashboard mockup, reached via the profile icon

Session-scoped state lives in two dcc.Store components below (outside the
page container so they survive navigation between pages, but reset when the
browser tab closes):

- exam-session-store: the exam currently in progress or just completed
- exam-history-store: every attempt completed so far this session
"""

import dash
from dash import Dash, dcc, html

app = Dash(__name__, use_pages=True, suppress_callback_exceptions=True)
app.title = "CySA+ Domain Practice Exam"
server = app.server

app.layout = html.Div(
    [
        dcc.Store(id="exam-session-store", storage_type="session"),
        dcc.Store(id="exam-history-store", storage_type="session"),
        dash.page_container,
    ]
)

if __name__ == "__main__":
    app.run(debug=True)
