"""End-to-end checks that the desktop sidebar appears at and only at the
laptop breakpoint, and that mobile widths still get the hamburger + bottom
tab bar.

Why this test exists
--------------------
Task #27 promoted the off-canvas drawer into a permanent left sidebar.
Originally the cutoff was 1024px (iPad portrait), but commit 046b0bf
("Apply mobile-web visual fixes ... iPad breakpoint") deliberately moved
the threshold to 1280px because iPad Pro at 1024px landscape exposed a
Chrome quirk that left a 220px empty gap on the left of the page.

So the *current* truth on disk is:
  - <  1280px  → mobile drawer pattern: hamburger visible, bottom tab bar
                 visible, drawer offscreen, main content has no left margin
  - >= 1280px  → permanent 220px left sidebar, hamburger + tab bar hidden,
                 topbar pushed to left:220px, main content margin-left:220px

If a future CSS or JS change shifts the breakpoint or breaks the
.cl-sidebar.drawer-open ~ ... push selectors, this test will catch it
instead of users seeing the empty 220px gap or the missing-hamburger bug.

The four widths from the task description (768 / 1023 / 1024 / 1280) are
all included; an extra 1279 (just-below the real threshold) is added so a
regression that drops the breakpoint back to 1024 would surface clearly.

Per-route coverage (task #58)
-----------------------------
The same sidebar/topbar/tabbar/margin-left assertions are spot-checked on
``/trips/``, ``/logbook`` and ``/expenses`` at the laptop (1280px) and
iPad-portrait (1024px) widths. They all extend the same ``layout.html``
shell, but a future per-template tweak (e.g. an extra wrapper div on
``/expenses``) could break the layout on one route while the dashboard
still passes the original test. The per-route test will surface that.
"""
from __future__ import annotations

import os
import secrets
from pathlib import Path

import pytest

playwright_sync_api = pytest.importorskip(
    "playwright.sync_api",
    reason="playwright is required for the desktop-sidebar e2e tests",
)
sync_playwright = playwright_sync_api.sync_playwright


BASE_URL = os.environ.get("TEST_BASE_URL", os.environ.get("CREWLOG_BASE_URL", "http://localhost:5000"))
ARTIFACT_DIR = Path("test_artifacts/desktop_sidebar")

# Width -> expected layout. is_desktop=True means the permanent sidebar
# should be visible and the hamburger + bottom tab bar should be hidden.
LAYOUT_CASES = [
    (768, False, "mobile_phone"),
    (1023, False, "just_below_1024"),
    (1024, False, "ipad_portrait"),   # below 1280 → still mobile per current code
    (1279, False, "just_below_1280"),
    (1280, True, "laptop"),
]

# Per-route spot-check (task #58): the two "interesting" widths from
# LAYOUT_CASES — iPad portrait (mobile regime) and laptop (sidebar
# regime) — applied to every authenticated page that shares layout.html.
ROUTE_CASES = [
    ("/trips/",     1024, False, "trips_ipad_portrait"),
    ("/trips/",     1280, True,  "trips_laptop"),
    ("/logbook",    1024, False, "logbook_ipad_portrait"),
    ("/logbook",    1280, True,  "logbook_laptop"),
    ("/expenses",   1024, False, "expenses_ipad_portrait"),
    ("/expenses",   1280, True,  "expenses_laptop"),
    # Task #63: secondary pages that share layout.html
    ("/balances",   1024, False, "balances_ipad_portrait"),
    ("/balances",   1280, True,  "balances_laptop"),
    ("/deposits",   1024, False, "deposits_ipad_portrait"),
    ("/deposits",   1280, True,  "deposits_laptop"),
    ("/settlement", 1024, False, "settlement_ipad_portrait"),
    ("/settlement", 1280, True,  "settlement_laptop"),
    ("/templates",  1024, False, "templates_ipad_portrait"),
    ("/templates",  1280, True,  "templates_laptop"),
    ("/groups",     1024, False, "groups_ipad_portrait"),
    ("/groups",     1280, True,  "groups_laptop"),
]


def _server_is_up() -> bool:
    """Derive host/port from CREWLOG_BASE_URL so non-standard CI hosts
    (e.g. when the app runs on a different port) don't skip silently."""
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


@pytest.fixture(scope="module", autouse=True)
def _require_running_server():
    if not _server_is_up():
        pytest.skip(f"app not reachable on {BASE_URL}")
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture(scope="module")
def auth_storage_state(browser, admin_credentials, tmp_path_factory):
    """Log in once for the whole module and stash the session cookies on
    disk so each parametrized viewport can reuse them without hitting the
    rate-limited /login endpoint five times.

    Also POSTs ``/trips/{trip_id}/select`` so the session cookie carries a
    ``selected_trip_id``. Without it, ``/logbook`` and ``/expenses`` (used
    by the per-route test below) would 303 back to ``/trips/`` and we
    wouldn't actually be exercising those templates' layouts.
    """
    state_file = tmp_path_factory.mktemp("sidebar_auth") / "state.json"
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    try:
        _login(page, admin_credentials)
        # Sanity check: a follow-up request should land on an authed page
        page.goto(f"{BASE_URL}/", wait_until="networkidle")
        assert "/login" not in page.url, (
            f"login did not stick — landed on {page.url}"
        )
        # Pin the trip to the session so /logbook and /expenses don't
        # redirect to /trips/. Use a XHR so we can assert the response
        # rather than chasing the 303.
        select_resp = page.evaluate(
            """async (tripId) => {
                const csrf = (document.cookie.split('; ').find(r => r.startsWith('csrftoken='))||'').split('=')[1] || '';
                const r = await fetch('/trips/' + tripId + '/select', {
                    method: 'POST',
                    redirect: 'manual',
                    headers: {'x-csrftoken': csrf},
                });
                return {status: r.status, type: r.type};
            }""",
            admin_credentials["trip_id"],
        )
        assert select_resp["status"] in (0, 200, 303), (
            f"selecting trip failed: {select_resp}"
        )
        ctx.storage_state(path=str(state_file))
    finally:
        ctx.close()
    return str(state_file)


@pytest.fixture(scope="module")
def admin_credentials():
    """Provision a legacy admin (and a trip we can select) so we can hit
    authenticated pages that require an active trip."""
    from db import SessionLocal
    from models import User, Trip, UserRole
    from datetime import date

    username = f"e2e_sidebar_admin_{secrets.token_hex(3)}"
    password = secrets.token_urlsafe(12)
    db = SessionLocal()
    user_id = None
    created_trip_id = None
    try:
        user = User(username=username, role=UserRole.admin)
        user.set_password(password)
        db.add(user)
        existing_trip = db.query(Trip).first()
        if existing_trip is None:
            trip = Trip(name="E2E Sidebar Trip", start_date=date.today())
            db.add(trip)
            db.flush()
            created_trip_id = trip.id
            trip_id = trip.id
        else:
            trip_id = existing_trip.id
        db.commit()
        user_id = user.id
        yield {
            "username": username,
            "password": password,
            "trip_id": trip_id,
        }
    finally:
        try:
            u = db.query(User).filter(User.id == user_id).first()
            if u:
                db.delete(u)
            # Only clean up the trip we created ourselves; never touch a
            # pre-existing trip we merely borrowed.
            if created_trip_id is not None:
                t = db.query(Trip).filter(Trip.id == created_trip_id).first()
                if t:
                    db.delete(t)
            db.commit()
        except Exception:
            db.rollback()
        db.close()


def _login(page, creds):
    """POST credentials to /login and confirm the session cookie sticks."""
    page.goto(f"{BASE_URL}/login", wait_until="networkidle")
    resp = page.evaluate(
        """async ({u, p}) => {
            const csrf = (document.cookie.split('; ').find(r => r.startsWith('csrftoken='))||'').split('=')[1] || '';
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


def _is_offscreen_or_hidden(page, selector: str) -> bool:
    """A drawer counts as 'offscreen' when it's display:none, has zero
    width, or is translated/positioned outside the viewport."""
    return page.evaluate(
        """(sel) => {
            const el = document.querySelector(sel);
            if (!el) return true;
            const cs = getComputedStyle(el);
            if (cs.display === 'none' || cs.visibility === 'hidden') return true;
            const rect = el.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) return true;
            // off the left edge of the viewport
            if (rect.right <= 0) return true;
            return false;
        }""",
        selector,
    )


def _assert_layout(page, *, route: str, width: int, is_desktop: bool) -> None:
    """Run the sidebar/topbar/tabbar/margin-left assertions on the page
    that's already been navigated to.

    Extracted so the dashboard test (5 widths) and the per-route spot
    check (3 routes × 2 widths) share exactly the same expectations and
    diagnostic messages.
    """
    # Give applyLayout() in ui_nav.js a beat to bootstrap
    page.wait_for_timeout(150)

    # ── Hamburger button ────────────────────────────────────────────────
    hamburger = page.locator("#drawer-open")
    assert hamburger.count() == 1, (
        f"{route} @{width}px: drawer-open hamburger missing from markup"
    )
    hamburger_visible = hamburger.is_visible()

    # ── Bottom tab bar ──────────────────────────────────────────────────
    tabbar = page.locator(".cl-tabbar")
    tabbar_visible = tabbar.count() > 0 and tabbar.first.is_visible()

    # ── Sidebar / drawer ────────────────────────────────────────────────
    drawer = page.locator("#nav-drawer")
    assert drawer.count() == 1, (
        f"{route} @{width}px: nav-drawer missing from markup"
    )
    drawer_offscreen = _is_offscreen_or_hidden(page, "#nav-drawer")

    # ── Main content offset ─────────────────────────────────────────────
    # Capture both margins so we can distinguish "pushed by sidebar"
    # (margin-left ≈ 220, margin-right ≈ 0) from normal symmetric
    # auto-centering of .ui-container (max-width:1180 → equal margins
    # at viewports > 1180px).
    main_margins = page.evaluate(
        """() => {
            const m = document.querySelector('main.cl-main-content') ||
                      document.querySelector('.cl-main-content');
            if (!m) return null;
            const cs = getComputedStyle(m);
            return {
                left: parseFloat(cs.marginLeft) || 0,
                right: parseFloat(cs.marginRight) || 0,
            };
        }"""
    )
    assert main_margins is not None, (
        f"{route} @{width}px: main.cl-main-content not found"
    )
    main_margin_left = main_margins["left"]

    # ── Topbar offset ───────────────────────────────────────────────────
    topbar_left = page.evaluate(
        """() => {
            const t = document.querySelector('.topbar');
            if (!t) return null;
            return parseFloat(getComputedStyle(t).left) || 0;
        }"""
    )

    if is_desktop:
        # Permanent left sidebar regime
        assert not hamburger_visible, (
            f"{route} @{width}px: hamburger should be hidden, but is visible"
        )
        assert not tabbar_visible, (
            f"{route} @{width}px: bottom tab bar should be hidden, but is visible"
        )
        assert not drawer_offscreen, (
            f"{route} @{width}px: sidebar should be visible on the left, "
            f"but is offscreen/hidden"
        )
        # Sidebar should be 220px wide and pinned to the left edge
        geom = page.evaluate(
            """() => {
                const d = document.querySelector('#nav-drawer');
                const r = d.getBoundingClientRect();
                return {left: r.left, width: r.width};
            }"""
        )
        assert abs(geom["width"] - 220) <= 1, (
            f"{route} @{width}px: sidebar width {geom['width']}px, expected 220"
        )
        assert geom["left"] == 0, (
            f"{route} @{width}px: sidebar left edge {geom['left']}px, expected 0"
        )
        assert main_margin_left >= 219, (
            f"{route} @{width}px: main content margin-left {main_margin_left}px, "
            f"expected >=220 to clear the sidebar"
        )
        assert topbar_left >= 219, (
            f"{route} @{width}px: topbar left {topbar_left}px, "
            f"expected >=220 to clear the sidebar"
        )
    else:
        # Mobile drawer regime
        assert hamburger_visible, (
            f"{route} @{width}px: hamburger should be visible, but is hidden"
        )
        assert tabbar_visible, (
            f"{route} @{width}px: bottom tab bar should be visible, but is hidden"
        )
        assert drawer_offscreen, (
            f"{route} @{width}px: drawer should be offscreen by default, "
            f"but is visible (would create empty 220px gap)"
        )
        # Sidebar push must NOT be active. The push selector forces
        # margin-left:220px. Auto-centering of .ui-container produces
        # symmetric margins (left ≈ right), so a left-only push is the
        # tell-tale regression we want to catch.
        assert main_margin_left < 100, (
            f"{route} @{width}px: main content margin-left {main_margin_left}px "
            f"looks like a sidebar push (expected <100px symmetric "
            f"auto-margin or 0)"
        )
        assert abs(main_margin_left - main_margins["right"]) < 5, (
            f"{route} @{width}px: asymmetric main margins "
            f"L={main_margin_left} R={main_margins['right']} — "
            f"sidebar push selector seems to be firing"
        )
        # Topbar should not be pushed right by a sidebar
        assert topbar_left == 0, (
            f"{route} @{width}px: topbar left {topbar_left}px, expected 0"
        )


@pytest.mark.parametrize("width,is_desktop,label", LAYOUT_CASES,
                         ids=[c[2] for c in LAYOUT_CASES])
def test_dashboard_layout_at_width(browser, auth_storage_state,
                                   width, is_desktop, label):
    ctx = browser.new_context(
        viewport={"width": width, "height": 900},
        storage_state=auth_storage_state,
    )
    page = ctx.new_page()
    try:
        page.goto(f"{BASE_URL}/", wait_until="networkidle")
        assert "/login" not in page.url, (
            f"@{width}px: dashboard redirected to login — auth state lost"
        )
        page.screenshot(
            path=str(ARTIFACT_DIR / f"dashboard_{width}_{label}.png"),
            full_page=False,
        )
        _assert_layout(page, route="/", width=width, is_desktop=is_desktop)
    finally:
        ctx.close()


@pytest.mark.parametrize("route,width,is_desktop,label", ROUTE_CASES,
                         ids=[c[3] for c in ROUTE_CASES])
def test_authed_route_layout_at_width(browser, auth_storage_state,
                                      route, width, is_desktop, label):
    """Spot-check the layout shell on every authed route that extends
    layout.html, at both the laptop and iPad-portrait widths.

    These are the two widths most likely to regress: 1280px is the
    sidebar/mobile boundary, and 1024px (iPad portrait) was the original
    breakpoint that briefly broke the layout in commit 046b0bf.
    """
    ctx = browser.new_context(
        viewport={"width": width, "height": 900},
        storage_state=auth_storage_state,
    )
    page = ctx.new_page()
    try:
        page.goto(f"{BASE_URL}{route}", wait_until="networkidle")
        assert "/login" not in page.url, (
            f"{route} @{width}px: redirected to login — auth state lost"
        )
        # Real regression we want to catch: the route 303-ed away (e.g.
        # /logbook → /trips/ when no trip is selected). If that happens
        # the auth fixture's /trips/{id}/select didn't take effect and
        # we'd be silently retesting /trips/ instead.
        landed = page.url.split("?", 1)[0].rstrip("/")
        expected = f"{BASE_URL}{route}".rstrip("/")
        assert landed == expected, (
            f"{route} @{width}px: ended up on {page.url} instead of {route}"
        )
        page.screenshot(
            path=str(ARTIFACT_DIR / f"route_{label}_{width}.png"),
            full_page=False,
        )
        _assert_layout(page, route=route, width=width, is_desktop=is_desktop)
    finally:
        ctx.close()
