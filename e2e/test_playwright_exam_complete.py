"""Playwright: login → start → answer → complete; results come from Postgres."""

from e2e.helpers import signup_and_land, start_seeded_exam, unique_email


def test_login_answer_complete_results_from_db(page, live_server):
    base = live_server["base_url"]
    email = unique_email("complete")
    password = live_server["password"]
    page.set_default_timeout(25_000)

    signup_and_land(page, base, email, password)
    start_seeded_exam(page)
    page.locator("#option-card-B").click()
    page.locator("#submit-exam-btn").click()
    page.wait_for_url(f"{base}/results")

    page.get_by_role("heading", name="Exam Results").wait_for()
    page.get_by_text("1/1 (100%)").wait_for()
    page.get_by_text("Total Test Attempted: 1").wait_for()
