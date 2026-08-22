"""End-to-end regression guard: Expenses and Crew card layout at ≤640 px.

Why this test exists
--------------------
The Expenses and Crew pages render a ``.cl-row-card`` list (see
``static/cl_design.css``) at every viewport width — there is no separate
desktop ``<table>`` that gets toggled to a card layout via a media query;
the card markup is the only markup.

Without this test a future template change could silently:
- Reintroduce a ``<table>``/``<thead>`` (undoing the card-list layout), or
- Cause a row to widen beyond the viewport, reintroducing a horizontal
  scrollbar on narrow screens.

This test renders each page at 390 × 844 px (iPhone 14 logical pixels) and
asserts:

1. No ``<table>`` element exists on the page.
2. At least one ``.cl-row-card`` renders and is visible.
3. The row's rendered width fits inside the viewport (no horizontal
   overflow).

Determinism guarantee
---------------------
The fixture seeds its own isolated trip, a crew member, and an expense, then
cleans everything up after the module finishes.  It never borrows pre-existing
database rows, so the row-level assertions are always exercised against real
rendered cards.
"""
from __future__ import annotations

import os
import secrets
from datetime import date, datetime
from pathlib import Path

import pytest

playwright_sync_api = pytest.importorskip(
    "playwright.sync_api",
    reason="playwright is required for the mobile card-layout e2e tests",
)
sync_playwright = playwright_sync_api.sync_playwright

BASE_URL = os.environ.get("TEST_BASE_URL", os.environ.get("CREWLOG_BASE_URL", "http://localhost:5000"))
ARTIFACT_DIR = Path("test_artifacts/mobile_card_layout")

# iPhone 14 logical resolution (390 × 844) — well inside the ≤640 px breakpoint.
IPHONE_WIDTH = 390
IPHONE_HEIGHT = 844


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _server_is_up() -> bool:
    import socket
    from urllib.parse import urlparse
    parsed = urlparse(BASE_URL)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False


def _login(page, creds: dict) -> None:
    page.goto(f"{BASE_URL}/login", wait_until="networkidle")
    resp = page.evaluate(
        """async ({u, p}) => {
            const csrf = (document.cookie.split('; ')
                .find(r => r.startsWith('csrftoken=')) || '').split('=')[1] || '';
            const body = new URLSearchParams({username: u, password: p, trip_id: ''});
            const r = await fetch('/login', {
                method: 'POST',
                redirect: 'manual',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'x-csrftoken': csrf,
                },
                body: body.toString(),
            });
            return {status: r.status, type: r.type};
        }""",
        {"u": creds["username"], "p": creds["password"]},
    )
    assert resp["status"] in (0, 200, 303), f"login failed: {resp}"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module", autouse=True)
def _require_running_server():
    if not _server_is_up():
        pytest.skip(f"app not reachable on {BASE_URL}")
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        yield b
        b.close()


@pytest.fixture(scope="module")
def seeded_data():
    """Provision a self-contained dataset for this test module.

    Creates (and cleans up after the module):
    - a legacy admin user
    - a dedicated trip
    - one crew member on that trip
    - one expense paid by that crew member

    The fixture yields a dict with all IDs and credentials needed by
    ``auth_storage_state`` and the tests.
    """
    from db import SessionLocal
    from models import (
        User, UserRole,
        Trip,
        CrewMember,
        Expense, PaidFromEnum, SplitModeEnum, Currency,
    )

    suffix = secrets.token_hex(3)
    username = f"e2e_cardlayout_{suffix}"
    password = secrets.token_urlsafe(12)

    db = SessionLocal()
    user_id = trip_id = member_id = expense_id = None
    try:
        # User
        user = User(username=username, role=UserRole.admin)
        user.set_password(password)
        db.add(user)

        # Trip
        trip = Trip(name=f"CardLayout Test Trip {suffix}", start_date=date.today())
        db.add(trip)
        db.flush()
        trip_id = trip.id

        # Crew member
        member = CrewMember(
            trip_id=trip_id,
            code=f"TM{suffix[:4].upper()}",
            name="Test Mariner",
            is_trip_admin=1,
        )
        db.add(member)
        db.flush()
        member_id = member.id

        # Expense paid by the crew member
        today = date.today()
        expense = Expense(
            trip_id=trip_id,
            payer_id=member_id,
            date=today,
            occurred_at=datetime.utcnow(),
            category="fuel",
            description="E2E Card Layout Test Fuel",
            amount=42.50,
            currency=Currency.EUR,
            amount_eur=42.50,
            paid_from=PaidFromEnum.private,
            split_mode=SplitModeEnum.equal,
        )
        db.add(expense)
        db.flush()
        expense_id = expense.id

        db.commit()
        user_id = user.id

        yield {
            "username": username,
            "password": password,
            "trip_id": trip_id,
            "member_id": member_id,
            "expense_id": expense_id,
        }
    finally:
        try:
            # Delete in reverse-dependency order
            if expense_id:
                e = db.query(Expense).filter(Expense.id == expense_id).first()
                if e:
                    db.delete(e)
            if member_id:
                m = db.query(CrewMember).filter(CrewMember.id == member_id).first()
                if m:
                    db.delete(m)
            if trip_id:
                t = db.query(Trip).filter(Trip.id == trip_id).first()
                if t:
                    db.delete(t)
            if user_id:
                u = db.query(User).filter(User.id == user_id).first()
                if u:
                    db.delete(u)
            db.commit()
        except Exception:
            db.rollback()
        db.close()


@pytest.fixture(scope="module")
def auth_storage_state(browser, seeded_data, tmp_path_factory):
    """Log in once and persist the session (with the seeded trip selected)
    for all tests in this module."""
    state_file = tmp_path_factory.mktemp("cardlayout_auth") / "state.json"
    ctx = browser.new_context(
        viewport={"width": IPHONE_WIDTH, "height": IPHONE_HEIGHT},
    )
    page = ctx.new_page()
    try:
        _login(page, seeded_data)
        page.goto(f"{BASE_URL}/", wait_until="networkidle")
        assert "/login" not in page.url, (
            f"login did not stick — landed on {page.url}"
        )
        # Select the seeded trip so /expenses and /crew resolve correctly.
        select_resp = page.evaluate(
            """async (tripId) => {
                const csrf = (document.cookie.split('; ')
                    .find(r => r.startsWith('csrftoken=')) || '').split('=')[1] || '';
                const r = await fetch('/trips/' + tripId + '/select', {
                    method: 'POST',
                    redirect: 'manual',
                    headers: {'x-csrftoken': csrf},
                });
                return {status: r.status, type: r.type};
            }""",
            seeded_data["trip_id"],
        )
        assert select_resp["status"] in (0, 200, 303), (
            f"selecting trip failed: {select_resp}"
        )
        ctx.storage_state(path=str(state_file))
    finally:
        ctx.close()
    return str(state_file)


# ---------------------------------------------------------------------------
# Core assertion helper
# ---------------------------------------------------------------------------

def _assert_card_layout(page, *, route: str) -> None:
    """Assert that the ``.cl-row-card`` list layout is rendering correctly.

    Checks:
      1. No ``<table>`` exists — these pages never had one; they render a
         ``.cl-row-card`` per row at every viewport width.
      2. At least one ``.cl-row-card`` is present and visible (not
         ``display: none``). Fails if no rows are present — the fixture
         must seed data.
      3. The row's rendered width fits inside the viewport, so no
         horizontal scrollbar can appear.
    """
    page.wait_for_timeout(200)  # allow layout CSS to settle

    has_table = page.evaluate("() => !!document.querySelector('table')")
    assert not has_table, (
        f"{route} @{IPHONE_WIDTH}px: found a <table> — expected the "
        f".cl-row-card list layout used at every viewport width instead"
    )

    row = page.evaluate(
        """() => {
            const row = document.querySelector('.cl-row-card');
            if (!row) return null;
            const r = row.getBoundingClientRect();
            return {display: getComputedStyle(row).display, width: r.width};
        }"""
    )
    assert row is not None, (
        f"{route} @{IPHONE_WIDTH}px: no .cl-row-card rows found — "
        f"the fixture must seed at least one row so card rendering is exercised"
    )
    assert row["display"] != "none", (
        f"{route} @{IPHONE_WIDTH}px: .cl-row-card is display:none"
    )
    assert row["width"] <= IPHONE_WIDTH, (
        f"{route} @{IPHONE_WIDTH}px: .cl-row-card width={row['width']}px "
        f"exceeds the viewport — horizontal overflow detected"
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_expenses_card_layout_on_iphone(browser, auth_storage_state):
    """/expenses at iPhone width renders card layout, not a scrolling table."""
    ctx = browser.new_context(
        viewport={"width": IPHONE_WIDTH, "height": IPHONE_HEIGHT},
        storage_state=auth_storage_state,
    )
    page = ctx.new_page()
    try:
        page.goto(f"{BASE_URL}/expenses", wait_until="networkidle")
        assert "/login" not in page.url, (
            "/expenses redirected to login — auth state lost"
        )
        landed = page.url.split("?", 1)[0].rstrip("/")
        expected = f"{BASE_URL}/expenses".rstrip("/")
        assert landed == expected, (
            f"/expenses redirected to {page.url} — trip may not be selected"
        )
        # Scroll the row list into view before screenshotting so cards are visible
        page.evaluate(
            """() => {
                const row = document.querySelector('.cl-row-card');
                if (row) row.scrollIntoView({block: 'start'});
            }"""
        )
        page.wait_for_timeout(100)
        page.screenshot(
            path=str(ARTIFACT_DIR / "expenses_iphone390.png"),
            full_page=False,
        )
        _assert_card_layout(page, route="/expenses")
    finally:
        ctx.close()


def test_crew_card_layout_on_iphone(browser, auth_storage_state):
    """/crew at iPhone width renders card layout, not a scrolling table."""
    ctx = browser.new_context(
        viewport={"width": IPHONE_WIDTH, "height": IPHONE_HEIGHT},
        storage_state=auth_storage_state,
    )
    page = ctx.new_page()
    try:
        page.goto(f"{BASE_URL}/crew", wait_until="networkidle")
        assert "/login" not in page.url, (
            "/crew redirected to login — auth state lost"
        )
        landed = page.url.split("?", 1)[0].rstrip("/")
        expected = f"{BASE_URL}/crew".rstrip("/")
        assert landed == expected, (
            f"/crew redirected to {page.url} — trip may not be selected"
        )
        # Scroll the row list into view before screenshotting
        page.evaluate(
            """() => {
                const row = document.querySelector('.cl-row-card');
                if (row) row.scrollIntoView({block: 'start'});
            }"""
        )
        page.wait_for_timeout(100)
        page.screenshot(
            path=str(ARTIFACT_DIR / "crew_iphone390.png"),
            full_page=False,
        )
        _assert_card_layout(page, route="/crew")
    finally:
        ctx.close()


def test_expenses_no_overflow_at_iphone_width(browser, auth_storage_state):
    """The expenses page body must not overflow horizontally at 390 px.

    This catches the class of bug where a deeply-nested element (e.g. a
    flex row inside a card, or a long description string) widens beyond
    390 px and silently reintroduces a horizontal scrollbar on the page.
    The seeded expense row ensures the card content is rendered.
    """
    ctx = browser.new_context(
        viewport={"width": IPHONE_WIDTH, "height": IPHONE_HEIGHT},
        storage_state=auth_storage_state,
    )
    page = ctx.new_page()
    try:
        page.goto(f"{BASE_URL}/expenses", wait_until="networkidle")
        scroll_width = page.evaluate("() => document.body.scrollWidth")
        assert scroll_width <= IPHONE_WIDTH + 1, (
            f"/expenses @{IPHONE_WIDTH}px: body.scrollWidth={scroll_width}px "
            f"exceeds the viewport — horizontal overflow detected"
        )
    finally:
        ctx.close()


def test_crew_no_overflow_at_iphone_width(browser, auth_storage_state):
    """The crew page body must not overflow horizontally at 390 px.

    The seeded crew member ensures the card content is rendered.
    """
    ctx = browser.new_context(
        viewport={"width": IPHONE_WIDTH, "height": IPHONE_HEIGHT},
        storage_state=auth_storage_state,
    )
    page = ctx.new_page()
    try:
        page.goto(f"{BASE_URL}/crew", wait_until="networkidle")
        scroll_width = page.evaluate("() => document.body.scrollWidth")
        assert scroll_width <= IPHONE_WIDTH + 1, (
            f"/crew @{IPHONE_WIDTH}px: body.scrollWidth={scroll_width}px "
            f"exceeds the viewport — horizontal overflow detected"
        )
    finally:
        ctx.close()
