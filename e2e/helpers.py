"""Shared Playwright steps for exam flows."""


def select_dash_dropdown(page, dropdown_id, option_text):
    page.locator(f"#{dropdown_id}").click()
    page.get_by_text(option_text, exact=True).click()


def start_seeded_exam(page, mode="exam"):
    page.get_by_text("CySA+ V4 (New Version)").wait_for()
    select_dash_dropdown(page, "domain-dropdown", "1.0 Security Operations")
    select_dash_dropdown(page, "subsection-dropdown", "1.1 Explain concepts")
    button_id = "practice-mode-btn" if mode == "practice" else "exam-mode-btn"
    page.locator(f"#{button_id}").click()
    page.get_by_text("Question 1 of 1").wait_for()


def signup_and_land(page, base, email, password):
    page.goto(f"{base}/signup")
    page.locator('input[name="email"]').fill(email)
    page.locator('input[name="password"]').fill(password)
    page.get_by_role("button", name="Create Account").click()
    page.wait_for_url(f"{base}/")
