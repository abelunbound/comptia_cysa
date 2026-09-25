"""Playwright: login → start → answer → refresh → resume → complete → DB results."""

from e2e.helpers import (
    signup_and_land,
    start_seeded_exam,
    unique_email,
    wait_for_in_progress_exam,
    wait_for_saved_option,
)


def test_refresh_resumes_then_complete_results_from_db(page, live_server):
    base = live_server["base_url"]
    email = unique_email("refresh")
    password = live_server["password"]
    page.set_default_timeout(25_000)

    signup_and_land(page, base, email, password)
    start_seeded_exam(page)
    page.locator("#option-card-B").click()
    wait_for_saved_option(page, "B")
    page.get_by_text("Question 1 of 1").wait_for()

    page.reload()
    wait_for_in_progress_exam(page, base)
    page.locator("#option-card-B").wait_for()

    page.locator("#submit-exam-btn").click()
    page.wait_for_url(f"{base}/results")
    page.get_by_role("heading", name="Exam Results").wait_for()
    page.get_by_text("1/1 (100%)").wait_for()
    page.get_by_text("Total Test Attempted: 1").wait_for()


def test_logout_login_resumes_in_progress(page, live_server):
    base = live_server["base_url"]
    email = unique_email("resume")
    password = live_server["password"]
    page.set_default_timeout(25_000)

    signup_and_land(page, base, email, password)
    start_seeded_exam(page)
    page.locator("#option-card-A").click()
    wait_for_saved_option(page, "A")

    page.goto(f"{base}/logout")
    page.wait_for_url(f"{base}/login")
    page.locator('input[name="email"]').fill(email)
    page.locator('input[name="password"]').fill(password)
    page.get_by_role("button", name="Log In").click()
    wait_for_in_progress_exam(page, base)
