"""End-to-end regression guard: card layout at ≤640 px for Balances, Deposits,
Settlement, Templates, and Groups pages.

Why this test exists
--------------------
The Balances, Deposits, Settlement, Templates, and Groups pages will gain
card-per-row layout at ``max-width: 640px`` (iPhone viewports), mirroring the
same ``@media (max-width: 640px)`` blocks already present in
``static/cl_design.css`` for the Expenses and Crew pages.

Without this test a future CSS or template change could silently:
- Restore a hidden ``<thead>`` (re-introducing redundant column headers in card
  mode), or
- Cause the scroll wrapper to re-acquire ``overflow-x: auto``, meaning rows
  could overflow horizontally on narrow screens.

This test renders each page at 390 × 844 px (iPhone 14 logical pixels) and
asserts:

1. The table ``<thead>`` on each page is **not** visible (display: none in card
   mode).
2. The table rows (``tbody tr``) are **block-level** elements, confirming the
   card layout is active.
3. The scroll wrapper has ``overflow-x: visible`` (not ``auto`` or ``scroll``),
   so no horizontal scrollbar can appear.

Determinism guarantee
---------------------
The fixture seeds its own isolated dataset (user, trip, crew member, expense,
deposit, expense template, and crew group), then cleans everything up after the
module finishes.  It never borrows pre-existing database rows so the row-level
assertions are always exercised against real rendered cards.

This test follows the same fixture/skip pattern as
``tests/test_mobile_card_layout_e2e.py``.
"""
from __future__ import annotations

import os
import secrets
from datetime import date, datetime
from pathlib import Path

import pytest

playwright_sync_api = pytest.importorskip(
    "playwright.sync_api",
    reason="playwright is required for the mobile card-layout extended e2e tests",
)
sync_playwright = playwright_sync_api.sync_playwright

BASE_URL = os.environ.get("CREWLOG_BASE_URL", "http://localhost:5000")
ARTIFACT_DIR = Path("test_artifacts/mobile_card_layout_extended")

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
    - one crew member on that trip (serves as the representative for the group)
    - one expense paid by that crew member  (needed for /balances, /settlement)
    - one deposit by that crew member       (needed for /deposits)
    - one expense template                  (needed for /templates)
    - one crew group with that member       (needed for /groups)

    The fixture yields a dict with all IDs and credentials needed by
    ``auth_storage_state`` and the tests.
    """
    from db import SessionLocal
    from models import (
        User, UserRole,
        Trip,
        CrewMember,
        Expense, PaidFromEnum, SplitModeEnum, Currency,
        Deposit,
        ExpenseTemplate,
        CrewGroup, CrewGroupMember,
    )

    suffix = secrets.token_hex(3)
    username = f"e2e_cardext_{suffix}"
    password = secrets.token_urlsafe(12)

    db = SessionLocal()
    (user_id, trip_id, member_id, expense_id,
     deposit_id, template_id, group_id) = (None,) * 7
    try:
        # User
        user = User(username=username, role=UserRole.admin)
        user.set_password(password)
        db.add(user)

        # Trip
        trip = Trip(
            name=f"CardLayout Extended Test Trip {suffix}",
            start_date=date.today(),
        )
        db.add(trip)
        db.flush()
        trip_id = trip.id

        # Crew member
        member = CrewMember(
            trip_id=trip_id,
            code=f"TX{suffix[:4].upper()}",
            name="Extended Test Mariner",
            is_trip_admin=1,
        )
        db.add(member)
        db.flush()
        member_id = member.id

        # Expense (for /balances and /settlement to show a row)
        today = date.today()
        expense = Expense(
            trip_id=trip_id,
            payer_id=member_id,
            date=today,
            occurred_at=datetime.utcnow(),
            category="fuel",
            description="E2E Extended Card Layout Test Fuel",
            amount=55.00,
            currency=Currency.EUR,
            amount_eur=55.00,
            paid_from=PaidFromEnum.private,
            split_mode=SplitModeEnum.equal,
        )
        db.add(expense)
        db.flush()
        expense_id = expense.id

        # Deposit (for /deposits to show a row)
        deposit = Deposit(
            trip_id=trip_id,
            member_id=member_id,
            amount=100.00,
            currency=Currency.EUR,
            amount_eur=100.00,
            date=today,
            note="E2E test deposit",
        )
        db.add(deposit)
        db.flush()
        deposit_id = deposit.id

        # Expense template (for /templates to show a row)
        template = ExpenseTemplate(
            name=f"E2E Test Template {suffix}",
            category="fuel",
            default_amount=30.00,
            currency=Currency.EUR,
            paid_from=PaidFromEnum.wallet,
            split_mode=SplitModeEnum.equal,
        )
        db.add(template)
        db.flush()
        template_id = template.id

        # Crew group (for /groups to show a row)
        group = CrewGroup(
            trip_id=trip_id,
            name=f"E2E Test Group {suffix}",
            representative_member_id=member_id,
        )
        db.add(group)
        db.flush()
        group_id = group.id

        # Add the member to the group
        group_member = CrewGroupMember(group_id=group_id, member_id=member_id)
        db.add(group_member)

        db.commit()
        user_id = user.id

        yield {
            "username": username,
            "password": password,
            "trip_id": trip_id,
            "member_id": member_id,
            "expense_id": expense_id,
            "deposit_id": deposit_id,
            "template_id": template_id,
            "group_id": group_id,
        }
    finally:
        try:
            # Delete in reverse-dependency order
            if group_id:
                # CrewGroupMember rows cascade-delete via group
                g = db.query(CrewGroup).filter(CrewGroup.id == group_id).first()
                if g:
                    db.delete(g)
            if template_id:
                tmpl = db.query(ExpenseTemplate).filter(
                    ExpenseTemplate.id == template_id
                ).first()
                if tmpl:
                    db.delete(tmpl)
            if deposit_id:
                dep = db.query(Deposit).filter(Deposit.id == deposit_id).first()
                if dep:
                    db.delete(dep)
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
    state_file = (
        tmp_path_factory.mktemp("cardlayout_ext_auth") / "state.json"
    )
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
        # Select the seeded trip so all pages resolve correctly.
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
# Helper: navigate and assert correct landing
# ---------------------------------------------------------------------------

def _navigate(page, route: str) -> None:
    """Navigate to ``route`` and assert the page loaded (not redirected to login)."""
    page.goto(f"{BASE_URL}{route}", wait_until="networkidle")
    assert "/login" not in page.url, (
        f"{route} redirected to login — auth state lost"
    )
    landed = page.url.split("?", 1)[0].rstrip("/")
    expected = f"{BASE_URL}{route}".rstrip("/")
    assert landed == expected, (
        f"{route} redirected to {page.url} — trip may not be selected"
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_balances_card_layout_on_iphone(browser, auth_storage_state):
    """/balances at iPhone width renders card layout, not a scrolling table."""
    ctx = browser.new_context(
        viewport={"width": IPHONE_WIDTH, "height": IPHONE_HEIGHT},
        storage_state=auth_storage_state,
    )
    page = ctx.new_page()
    try:
        _navigate(page, "/balances")
        page.evaluate(
            """() => {
                const tbl = document.querySelector('.cl-balances-table');
                if (tbl) tbl.scrollIntoView({block: 'start'});
            }"""
        )
        page.wait_for_timeout(100)
        page.screenshot(
            path=str(ARTIFACT_DIR / "balances_iphone390.png"),
            full_page=False,
        )
        _assert_card_layout(
            page,
            route="/balances",
            table_cls="cl-balances-table",
            scroll_cls="cl-balances-table-scroll",
        )
    finally:
        ctx.close()


def test_deposits_card_layout_on_iphone(browser, auth_storage_state):
    """/deposits at iPhone width renders card layout, not a scrolling table."""
    ctx = browser.new_context(
        viewport={"width": IPHONE_WIDTH, "height": IPHONE_HEIGHT},
        storage_state=auth_storage_state,
    )
    page = ctx.new_page()
    try:
        _navigate(page, "/deposits")
        page.evaluate(
            """() => {
                const tbl = document.querySelector('.cl-deposits-table');
                if (tbl) tbl.scrollIntoView({block: 'start'});
            }"""
        )
        page.wait_for_timeout(100)
        page.screenshot(
            path=str(ARTIFACT_DIR / "deposits_iphone390.png"),
            full_page=False,
        )
        _assert_card_layout(
            page,
            route="/deposits",
            table_cls="cl-deposits-table",
            scroll_cls="cl-deposits-table-scroll",
        )
    finally:
        ctx.close()


def test_settlement_card_layout_on_iphone(browser, auth_storage_state):
    """/settlement at iPhone width renders card layout, not a scrolling table."""
    ctx = browser.new_context(
        viewport={"width": IPHONE_WIDTH, "height": IPHONE_HEIGHT},
        storage_state=auth_storage_state,
    )
    page = ctx.new_page()
    try:
        _navigate(page, "/settlement")
        page.evaluate(
            """() => {
                const tbl = document.querySelector('.cl-settlement-table');
                if (tbl) tbl.scrollIntoView({block: 'start'});
            }"""
        )
        page.wait_for_timeout(100)
        page.screenshot(
            path=str(ARTIFACT_DIR / "settlement_iphone390.png"),
            full_page=False,
        )
        _assert_card_layout(
            page,
            route="/settlement",
            table_cls="cl-settlement-table",
            scroll_cls="cl-settlement-table-scroll",
        )
    finally:
        ctx.close()


def test_templates_card_layout_on_iphone(browser, auth_storage_state):
    """/templates at iPhone width renders card layout, not a scrolling table."""
    ctx = browser.new_context(
        viewport={"width": IPHONE_WIDTH, "height": IPHONE_HEIGHT},
        storage_state=auth_storage_state,
    )
    page = ctx.new_page()
    try:
        _navigate(page, "/templates")
        page.evaluate(
            """() => {
                const tbl = document.querySelector('.cl-templates-table');
                if (tbl) tbl.scrollIntoView({block: 'start'});
            }"""
        )
        page.wait_for_timeout(100)
        page.screenshot(
            path=str(ARTIFACT_DIR / "templates_iphone390.png"),
            full_page=False,
        )
        _assert_card_layout(
            page,
            route="/templates",
            table_cls="cl-templates-table",
            scroll_cls="cl-templates-table-scroll",
        )
    finally:
        ctx.close()


def test_groups_card_layout_on_iphone(browser, auth_storage_state):
    """/groups at iPhone width renders card layout, not a scrolling table."""
    ctx = browser.new_context(
        viewport={"width": IPHONE_WIDTH, "height": IPHONE_HEIGHT},
        storage_state=auth_storage_state,
    )
    page = ctx.new_page()
    try:
        _navigate(page, "/groups")
        page.evaluate(
            """() => {
                const tbl = document.querySelector('.cl-groups-table');
                if (tbl) tbl.scrollIntoView({block: 'start'});
            }"""
        )
        page.wait_for_timeout(100)
        page.screenshot(
            path=str(ARTIFACT_DIR / "groups_iphone390.png"),
            full_page=False,
        )
        _assert_card_layout(
            page,
            route="/groups",
            table_cls="cl-groups-table",
            scroll_cls="cl-groups-table-scroll",
        )
    finally:
        ctx.close()


def test_balances_no_overflow_at_iphone_width(browser, auth_storage_state):
    """The balances page body must not overflow horizontally at 390 px."""
    ctx = browser.new_context(
        viewport={"width": IPHONE_WIDTH, "height": IPHONE_HEIGHT},
        storage_state=auth_storage_state,
    )
    page = ctx.new_page()
    try:
        page.goto(f"{BASE_URL}/balances", wait_until="networkidle")
        scroll_width = page.evaluate("() => document.body.scrollWidth")
        assert scroll_width <= IPHONE_WIDTH + 1, (
            f"/balances @{IPHONE_WIDTH}px: body.scrollWidth={scroll_width}px "
            f"exceeds the viewport — horizontal overflow detected"
        )
    finally:
        ctx.close()


def test_deposits_no_overflow_at_iphone_width(browser, auth_storage_state):
    """The deposits page body must not overflow horizontally at 390 px."""
    ctx = browser.new_context(
        viewport={"width": IPHONE_WIDTH, "height": IPHONE_HEIGHT},
        storage_state=auth_storage_state,
    )
    page = ctx.new_page()
    try:
        page.goto(f"{BASE_URL}/deposits", wait_until="networkidle")
        scroll_width = page.evaluate("() => document.body.scrollWidth")
        assert scroll_width <= IPHONE_WIDTH + 1, (
            f"/deposits @{IPHONE_WIDTH}px: body.scrollWidth={scroll_width}px "
            f"exceeds the viewport — horizontal overflow detected"
        )
    finally:
        ctx.close()


def test_settlement_no_overflow_at_iphone_width(browser, auth_storage_state):
    """The settlement page body must not overflow horizontally at 390 px."""
    ctx = browser.new_context(
        viewport={"width": IPHONE_WIDTH, "height": IPHONE_HEIGHT},
        storage_state=auth_storage_state,
    )
    page = ctx.new_page()
    try:
        page.goto(f"{BASE_URL}/settlement", wait_until="networkidle")
        scroll_width = page.evaluate("() => document.body.scrollWidth")
        assert scroll_width <= IPHONE_WIDTH + 1, (
            f"/settlement @{IPHONE_WIDTH}px: body.scrollWidth={scroll_width}px "
            f"exceeds the viewport — horizontal overflow detected"
        )
    finally:
        ctx.close()


def test_templates_no_overflow_at_iphone_width(browser, auth_storage_state):
    """The templates page body must not overflow horizontally at 390 px."""
    ctx = browser.new_context(
        viewport={"width": IPHONE_WIDTH, "height": IPHONE_HEIGHT},
        storage_state=auth_storage_state,
    )
    page = ctx.new_page()
    try:
        page.goto(f"{BASE_URL}/templates", wait_until="networkidle")
        scroll_width = page.evaluate("() => document.body.scrollWidth")
        assert scroll_width <= IPHONE_WIDTH + 1, (
            f"/templates @{IPHONE_WIDTH}px: body.scrollWidth={scroll_width}px "
            f"exceeds the viewport — horizontal overflow detected"
        )
    finally:
        ctx.close()


def test_groups_no_overflow_at_iphone_width(browser, auth_storage_state):
    """The groups page body must not overflow horizontally at 390 px."""
    ctx = browser.new_context(
        viewport={"width": IPHONE_WIDTH, "height": IPHONE_HEIGHT},
        storage_state=auth_storage_state,
    )
    page = ctx.new_page()
    try:
        page.goto(f"{BASE_URL}/groups", wait_until="networkidle")
        scroll_width = page.evaluate("() => document.body.scrollWidth")
        assert scroll_width <= IPHONE_WIDTH + 1, (
            f"/groups @{IPHONE_WIDTH}px: body.scrollWidth={scroll_width}px "
            f"exceeds the viewport — horizontal overflow detected"
        )
    finally:
        ctx.close()
