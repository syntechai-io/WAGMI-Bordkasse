"""End-to-end regression guard: Expenses and Crew card layout at ≤640 px.

Why this test exists
--------------------
The Expenses and Crew pages switch from a traditional table to a card-per-row
layout at ``max-width: 640px`` (iPhone viewports).  The CSS lives in the
``@media (max-width: 640px)`` block inside ``static/cl_design.css``.

Without this test a future CSS or template change could silently:
- Restore the hidden ``<thead>`` (re-introducing the redundant column headers
  in card mode), or
- Cause the scroll wrapper to re-acquire ``overflow-x: auto``, meaning rows
  could overflow horizontally on narrow screens.

This test renders each page at 390 × 844 px (iPhone 14 logical pixels) and
asserts:

1. ``.cl-expenses-table thead`` and ``.cl-crew-table thead`` are **not**
   visible (display: none in card mode).
2. The table rows (``tbody tr``) are **block-level** elements, confirming the
   card layout is active.
3. The scroll wrapper (``.cl-expenses-table-scroll`` /
   ``.cl-crew-table-scroll``) has ``overflow-x: visible`` (not ``auto`` or
   ``scroll``), so no horizontal scrollbar can appear.

Determinism guarantee
---------------------
The fixture seeds its own isolated trip, a crew member, and an expense, then
cleans everything up after the module finishes.  It never borrows pre-existing
database rows, so the row-level assertions (tbody tr display, body scroll
width) are always exercised against real rendered cards.
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

BASE_URL = os.environ.get("CREWLOG_BASE_URL", "http://localhost:5000")
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

def _assert_card_layout(page, *, route: str, table_cls: str, scroll_cls: str) -> None:
    """Assert that the card-mode CSS is active for the given table.

    Checks:
      1. The ``<thead>`` of the table is display:none (hidden in card mode).
      2. The first ``tbody tr`` is display:block (card layout active).
         Fails the test if no rows are present — the fixture must seed data.
      3. The scroll wrapper has overflow-x that is NOT ``auto`` or ``scroll``
         (so no horizontal scrollbar can appear on the page).
    """
    page.wait_for_timeout(200)  # allow layout CSS to settle

    # 1. thead must be invisible
    thead_display = page.evaluate(
        """(cls) => {
            const thead = document.querySelector('.' + cls + ' thead');
            if (!thead) return 'MISSING';
            return getComputedStyle(thead).display;
        }""",
        table_cls,
    )
    assert thead_display == "none", (
        f"{route} @{IPHONE_WIDTH}px: expected .{table_cls} thead to be "
        f"display:none (card mode), got display:{thead_display}"
    )

    # 2. tbody tr must be display:block — rows are required (seeded by fixture)
    tr_display = page.evaluate(
        """(cls) => {
            const tr = document.querySelector('.' + cls + ' tbody tr');
            if (!tr) return 'NO_ROWS';
            return getComputedStyle(tr).display;
        }""",
        table_cls,
    )
    assert tr_display != "NO_ROWS", (
        f"{route} @{IPHONE_WIDTH}px: no rows in .{table_cls} tbody — "
        f"the fixture must seed at least one row so card rendering is exercised"
    )
    assert tr_display == "block", (
        f"{route} @{IPHONE_WIDTH}px: expected .{table_cls} tbody tr to be "
        f"display:block in card mode, got display:{tr_display}"
    )

    # 3. The scroll wrapper must not have overflow-x: auto or scroll
    overflow_x = page.evaluate(
        """(cls) => {
            const wrap = document.querySelector('.' + cls);
            if (!wrap) return 'MISSING';
            return getComputedStyle(wrap).overflowX;
        }""",
        scroll_cls,
    )
    assert overflow_x not in ("auto", "scroll"), (
        f"{route} @{IPHONE_WIDTH}px: .{scroll_cls} has overflow-x:{overflow_x} "
        f"— horizontal scrollbar would reappear on iPhone. Expected 'visible'."
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
        # Scroll the table into view before screenshotting so cards are visible
        page.evaluate(
            """() => {
                const tbl = document.querySelector('.cl-expenses-table');
                if (tbl) tbl.scrollIntoView({block: 'start'});
            }"""
        )
        page.wait_for_timeout(100)
        page.screenshot(
            path=str(ARTIFACT_DIR / "expenses_iphone390.png"),
            full_page=False,
        )
        _assert_card_layout(
            page,
            route="/expenses",
            table_cls="cl-expenses-table",
            scroll_cls="cl-expenses-table-scroll",
        )
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
        # Scroll the crew table into view before screenshotting
        page.evaluate(
            """() => {
                const tbl = document.querySelector('.cl-crew-table');
                if (tbl) tbl.scrollIntoView({block: 'start'});
            }"""
        )
        page.wait_for_timeout(100)
        page.screenshot(
            path=str(ARTIFACT_DIR / "crew_iphone390.png"),
            full_page=False,
        )
        _assert_card_layout(
            page,
            route="/crew",
            table_cls="cl-crew-table",
            scroll_cls="cl-crew-table-scroll",
        )
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
