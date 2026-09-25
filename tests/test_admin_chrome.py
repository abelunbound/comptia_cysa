"""Dashboard chrome: sidebar labels, account controls, page size."""

from dash import dcc, html

from attempts import RESULTS_PAGE_SIZE
from components.admin_chrome import NAV_ITEMS, admin_chrome, sidebar
from components.ui import account_controls


def test_results_page_size_is_five():
    assert RESULTS_PAGE_SIZE == 5


def test_sidebar_brand_and_temporary_nav_placeholders():
    assert NAV_ITEMS == (
        ("Dashboard", "/admin"),
        ("Exams", "/exams"),
        ("Results Database", "/admin/results"),
        ("Certificates", None),
        ("Settings", None),
        ("Help", None),
    )
    tree = sidebar(active="Dashboard")
    assert _contains_text(tree, "CyberSec App")
    assert _contains_text(tree, "Certificates")
    assert not _contains_text(tree, "CySA+ Admin")


def test_account_controls_are_logout_and_dashboard_icon():
    tree = account_controls()
    logout = _first(tree, lambda n: isinstance(n, html.A) and n.children == "Logout")
    assert logout is not None
    assert logout.href == "/logout"
    icon = _first(tree, lambda n: isinstance(n, dcc.Link) and n.href == "/admin")
    assert icon is not None


def test_admin_chrome_puts_account_controls_in_main_pane():
    tree = admin_chrome(html.Div("body"), active="Exams")
    assert _contains_text(tree, "Logout")
    assert _contains_text(tree, "CyberSec App")


def _contains_text(node, text):
    if getattr(node, "children", None) == text:
        return True
    children = getattr(node, "children", None)
    if children is None:
        return False
    if not isinstance(children, (list, tuple)):
        children = [children]
    return any(_contains_text(child, text) for child in children)


def _first(node, predicate):
    if predicate(node):
        return node
    children = getattr(node, "children", None)
    if children is None:
        return None
    if not isinstance(children, (list, tuple)):
        children = [children]
    for child in children:
        found = _first(child, predicate)
        if found is not None:
            return found
    return None
