"""Browser smoke: login → exam UI paints → one Dash callback.

Flask's test client is not enough for this path — Playwright drives Chromium
against a live gunicorn process.
"""


def test_login_exam_paints_and_dash_action(page, live_server):
    base = live_server["base_url"]
    email = live_server["email"]
    password = live_server["password"]
    page.set_default_timeout(20_000)

    page.goto(f"{base}/signup")
    page.locator('input[name="email"]').fill(email)
    page.locator('input[name="password"]').fill(password)
    page.get_by_role("button", name="Create Account").click()
    page.wait_for_url(f"{base}/")

    page.goto(f"{base}/logout")
    page.wait_for_url(f"{base}/login")

    page.goto(f"{base}/login")
    page.get_by_role("heading", name="Log In").wait_for()
    page.locator('input[name="email"]').fill(email)
    page.locator('input[name="password"]').fill(password)
    page.get_by_role("button", name="Log In").click()
    page.wait_for_url(f"{base}/")

    page.get_by_text("CySA+ V4 (New Version)").wait_for()
    start = page.locator("#exam-mode-btn")
    start.wait_for(state="visible")

    start.click()
    page.get_by_text("Please select a Domain and Sub-Section first.").wait_for()
