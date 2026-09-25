"""Shared Playwright steps for exam flows."""

import re
import uuid
from urllib.parse import urlparse


def unique_email(prefix="e2e"):
    return f"{prefix}-{uuid.uuid4().hex[:10]}@example.com"


def wait_for_home(page, base):
    """Match only `/`, not `/results` or `/review`."""
    page.wait_for_url(re.compile(rf"^{re.escape(base.rstrip('/'))}/?$"))


def wait_for_dashboard(page, base):
    page.wait_for_url(re.compile(rf"^{re.escape(base.rstrip('/'))}/admin/?$"))


def _page_base(page):
    parsed = urlparse(page.url)
    return f"{parsed.scheme}://{parsed.netloc}"


def open_cysa_exam(page, base=None):
    """Dashboard/sidebar → Exams → CySA+ card → exam setup on `/`."""
    base = base or _page_base(page)
    page.get_by_role("link", name="Exams", exact=True).click()
    page.wait_for_url(re.compile(rf"^{re.escape(base.rstrip('/'))}/exams/?$"))
    page.get_by_text("CompTIA CySA+", exact=True).click()
    wait_for_home(page, base)


def select_dash_dropdown(page, dropdown_id, option_text):
    page.locator(f"#{dropdown_id}").click()
    page.get_by_text(option_text, exact=True).click()


def wait_for_saved_option(page, letter):
    """Wait until the thin persist callback has written the choice."""
    page.locator("#exam-persist-ack").filter(has_text=f"saved:{letter}").wait_for(
        state="attached"
    )


def wait_for_in_progress_exam(page, base):
    """Resume must stay on `/` and show the current question."""
    wait_for_home(page, base)
    page.get_by_text("Question 1 of 1").wait_for()
    page.locator("#exam-mode-btn").wait_for(state="hidden")


def start_seeded_exam(page, mode="exam"):
    open_cysa_exam(page)
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
    wait_for_dashboard(page, base)
