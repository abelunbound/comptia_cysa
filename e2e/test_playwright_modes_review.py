"""Playwright: practice Grade Now, quit/abandon, and review after complete."""

from e2e.helpers import signup_and_land, start_seeded_exam, unique_email


def test_practice_mode_grade_now_after_selection(page, live_server):
    base = live_server["base_url"]
    email = unique_email("practice")
    password = live_server["password"]
    page.set_default_timeout(25_000)

    signup_and_land(page, base, email, password)
    start_seeded_exam(page, mode="practice")

    grade = page.locator("#grade-btn")
    assert grade.is_disabled()

    page.locator("#option-card-A").click()
    page.wait_for_function(
        "() => { const el = document.querySelector('#grade-btn'); return el && !el.disabled; }"
    )
    grade.click()
    page.get_by_text("Incorrect", exact=False).wait_for()
    page.get_by_text("Because.").wait_for()
    page.get_by_text("See Explanation").wait_for()


def test_quit_abandon_returns_to_setup(page, live_server):
    base = live_server["base_url"]
    email = unique_email("abandon")
    password = live_server["password"]
    page.set_default_timeout(25_000)

    signup_and_land(page, base, email, password)
    start_seeded_exam(page)
    page.locator("#option-card-B").click()

    page.locator("#quit-exam-btn").click()
    page.get_by_text("Quit this exam?").wait_for()
    page.locator("#quit-confirm-btn").click()

    page.locator("#exam-mode-btn").wait_for(state="visible")
    page.get_by_text("Question 1 of 1").wait_for(state="hidden")


def test_results_review_loads_from_db(page, live_server):
    base = live_server["base_url"]
    email = unique_email("review")
    password = live_server["password"]
    page.set_default_timeout(25_000)

    signup_and_land(page, base, email, password)
    start_seeded_exam(page)
    page.locator("#option-card-B").click()
    page.locator("#submit-exam-btn").click()
    page.wait_for_url(f"{base}/results")

    page.get_by_role("link", name="Review current attempt").click()
    page.wait_for_url("**/review**")
    page.get_by_role("heading", name="Review").wait_for()
    page.get_by_text("Explanation:").wait_for()
    page.get_by_text("Because.").wait_for()
    page.get_by_text("What is ingestion?").wait_for()
