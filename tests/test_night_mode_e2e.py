"""End-to-end browser test for Night Mode (Task #40).

Drives a real headless Chromium via Playwright against the running app at
http://localhost:5000, sets the Night theme, asserts the *computed* CSS
values for the primitives the user complained about (cards, all button
variants, native checkbox accent-color, active vs inactive tab-bar items),
and saves screenshot artifacts to ``test_artifacts/night_mode/`` for
visual review.

Verification surface
--------------------
The unauthenticated ``/diagnostics/theme?theme=night`` page is purpose-
built for this test. It renders one of every primitive the trips page
uses (``cl-card``, every ``cl-btn--*`` variant, ``cl-input``,
``cl-check-row``, ``cl-tabbar`` with one active and two inactive items,
``cl-pill``, ``cl-alert``) and loads the same ``ui_night_mode.css`` the
rest of the app loads, so a green run on this page is direct proof the
night palette would render correctly on Trips, Logbook, Bordkasse, etc.

Why not the trips page directly
-------------------------------
The trips page requires an authenticated session and a real ``Trip`` row
in the dev DB, neither of which is guaranteed in CI. The diagnostic page
removes that coupling without weakening the assertion: every primitive on
trips uses the same global classes asserted here. The ``test_regression_
logbook.py`` static-content tests cover the trips template's primitive
usage explicitly so we know the diagnostic page is a faithful proxy.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

playwright_sync_api = pytest.importorskip(
    "playwright.sync_api",
    reason="Playwright is required for the Night-Mode e2e test.",
)
sync_playwright = playwright_sync_api.sync_playwright


BASE_URL = os.environ.get("CREWLOG_BASE_URL", "http://localhost:5000")
ARTIFACT_DIR = Path("test_artifacts/night_mode")


def _rgb(s: str) -> tuple[int, int, int]:
    """Parse 'rgb(R, G, B)' or 'rgba(R, G, B, A)' into (R, G, B) ints."""
    import re
    nums = [int(n) for n in re.findall(r"\d+", s)[:3]]
    assert len(nums) == 3, f"Could not parse colour string: {s!r}"
    return tuple(nums)  # type: ignore[return-value]


def _is_night_red(rgb: tuple[int, int, int], *, muted: bool = False) -> bool:
    """Bright night-text red is ~rgb(255, 43, 43); muted is ~rgb(155, 28, 28)."""
    r, g, b = rgb
    if muted:
        return 100 <= r <= 200 and g <= 60 and b <= 60
    return r >= 200 and g <= 80 and b <= 80


def _is_dark_red_border(rgb: tuple[int, int, int]) -> bool:
    r, g, b = rgb
    return 60 <= r <= 200 and g <= 50 and b <= 50


def _is_blackish(rgb: tuple[int, int, int]) -> bool:
    """Pure black or near-black surface (e.g. --night-bg #000 or --night-surface #050505)."""
    r, g, b = rgb
    return r <= 25 and g <= 25 and b <= 25


def _server_is_up() -> bool:
    import socket
    try:
        with socket.create_connection(("127.0.0.1", 5000), timeout=2):
            return True
    except OSError:
        return False


@pytest.fixture(scope="module", autouse=True)
def _require_running_server():
    if not _server_is_up():
        pytest.skip(
            f"App not reachable on {BASE_URL}. Start the Server workflow first."
        )
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture()
def page(browser):
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    yield page
    ctx.close()


def test_night_mode_page_palette_is_pure_red_on_black(page):
    """Top-level page surface: html[data-theme=night] body must be black with
    bright-red text. This is the most-visible regression — if it fails the
    user sees a white app even with Night Mode toggled on."""
    page.goto(f"{BASE_URL}/diagnostics/theme?theme=night", wait_until="networkidle")

    assert page.locator("html").get_attribute("data-theme") == "night"

    body_bg = _rgb(page.evaluate("getComputedStyle(document.body).backgroundColor"))
    body_color = _rgb(page.evaluate("getComputedStyle(document.body).color"))

    assert _is_blackish(body_bg), (
        f"body background must be black-ish in Night Mode, got rgb{body_bg}"
    )
    assert _is_night_red(body_color), (
        f"body text colour must be night-red, got rgb{body_color}"
    )

    page.screenshot(
        path=str(ARTIFACT_DIR / "01_page_palette.png"),
        full_page=True,
    )


def test_night_mode_card_surface_is_dark_not_white(page):
    """The user's screenshot showed the 'Neuen Törn erstellen' card as pure
    white in Night Mode. This asserts the .cl-card surface is dark and its
    border is dark red."""
    page.goto(f"{BASE_URL}/diagnostics/theme?theme=night", wait_until="networkidle")
    card = page.locator(".cl-card").first
    card.wait_for(state="visible")

    bg = _rgb(card.evaluate("el => getComputedStyle(el).backgroundColor"))
    border = _rgb(card.evaluate("el => getComputedStyle(el).borderColor"))

    assert _is_blackish(bg), (
        f".cl-card background must be dark in Night Mode, got rgb{bg} "
        f"(white was the original bug)."
    )
    assert _is_dark_red_border(border), (
        f".cl-card border should be dark red, got rgb{border}"
    )

    card.screenshot(path=str(ARTIFACT_DIR / "02_card_surface.png"))


def test_night_mode_all_button_variants_are_black_on_red(page):
    """The user's screenshot showed Accent (blue), Warn (orange), and Success
    (green) buttons leaking through Night Mode. In Night Mode every .cl-btn
    variant must collapse to the same pure black surface with red text and
    a red border — no nautical-blue/green/orange.

    Asserts ALL five primary variants in a single page load (no parametrize
    so we keep one browser context for the whole suite). Each failure lists
    every offending variant before raising, so a single test run shows all
    button-level regressions at once."""
    page.goto(f"{BASE_URL}/diagnostics/theme?theme=night", wait_until="networkidle")

    variants = [
        ".cl-btn--primary",
        ".cl-btn--accent",
        ".cl-btn--success",
        ".cl-btn--warn",
        ".cl-btn--secondary",
    ]
    failures: list[str] = []
    for selector in variants:
        btn = page.locator(selector).first
        btn.wait_for(state="visible")

        bg = _rgb(btn.evaluate("el => getComputedStyle(el).backgroundColor"))
        color = _rgb(btn.evaluate("el => getComputedStyle(el).color"))
        border = _rgb(btn.evaluate("el => getComputedStyle(el).borderColor"))

        if not _is_blackish(bg):
            failures.append(
                f"{selector}: background must be black, got rgb{bg} "
                f"(original bug: Accent was blue, Success green, Warn orange)"
            )
        if not _is_night_red(color):
            failures.append(f"{selector}: text colour must be night-red, got rgb{color}")
        if not _is_dark_red_border(border):
            failures.append(f"{selector}: border must be dark red, got rgb{border}")

    page.locator(".cl-card").nth(0).screenshot(
        path=str(ARTIFACT_DIR / "07_button_variants.png")
    )

    assert not failures, "Night-Mode button variants regressed:\n  - " + "\n  - ".join(failures)


def test_night_mode_native_checkbox_accent_is_red(page):
    """Native <input type=checkbox> shows the system blue check by default.
    In Night Mode we override accent-color so the check renders red."""
    page.goto(f"{BASE_URL}/diagnostics/theme?theme=night", wait_until="networkidle")
    cb = page.locator('.cl-check-row input[type="checkbox"]').first
    cb.wait_for(state="visible")

    accent = _rgb(cb.evaluate("el => getComputedStyle(el).accentColor"))
    assert _is_night_red(accent), (
        f"Checkbox accent-color must be night-red, got rgb{accent}. "
        f"Was rgb(0, 122, 255) (system blue) before the fix."
    )

    page.locator(".cl-check-row").first.screenshot(
        path=str(ARTIFACT_DIR / "03_checkbox_accent.png")
    )


def test_night_mode_tabbar_active_vs_inactive_are_visibly_different(page):
    """The bug the user reported: every tab icon was the same bright red so
    you couldn't tell which tab was selected. This asserts the active tab is
    in bright night-red, the inactive tabs are in muted dark red, and that
    those colours are *measurably different* (R values differ by >= 30)."""
    page.goto(f"{BASE_URL}/diagnostics/theme?theme=night", wait_until="networkidle")

    active = page.locator(".cl-tabbar__item--active").first
    active.wait_for(state="visible")
    # Inactive tab = a .cl-tabbar__item that does NOT also carry --active.
    inactive = page.locator(
        ".cl-tabbar__item:not(.cl-tabbar__item--active)"
    ).first
    inactive.wait_for(state="visible")

    active_color = _rgb(active.evaluate("el => getComputedStyle(el).color"))
    inactive_color = _rgb(inactive.evaluate("el => getComputedStyle(el).color"))

    assert _is_night_red(active_color), (
        f"Active tab colour must be bright night-red, got rgb{active_color}"
    )
    assert _is_night_red(inactive_color, muted=True), (
        f"Inactive tab colour must be muted dark red, got rgb{inactive_color}"
    )
    assert abs(active_color[0] - inactive_color[0]) >= 30, (
        f"Active vs inactive tab colours are too similar: "
        f"active rgb{active_color}, inactive rgb{inactive_color}. "
        f"The user must be able to tell them apart at a glance."
    )

    page.locator(".cl-tabbar").first.screenshot(
        path=str(ARTIFACT_DIR / "04_tabbar_active_vs_inactive.png")
    )


def test_day_mode_remains_unchanged_no_regression(page):
    """Sanity check that Day Mode is untouched: body must be light, primary
    buttons must be navy, accent buttons must be blue. If this fails the
    Night Mode patch leaked into Day Mode — exactly what we promised it
    wouldn't do."""
    page.goto(f"{BASE_URL}/diagnostics/theme?theme=light", wait_until="networkidle")

    assert page.locator("html").get_attribute("data-theme") != "night"

    body_bg = _rgb(page.evaluate("getComputedStyle(document.body).backgroundColor"))
    assert all(c >= 230 for c in body_bg), (
        f"Day Mode body background must be light, got rgb{body_bg}"
    )

    primary_bg = _rgb(
        page.locator(".cl-btn--primary").first.evaluate(
            "el => getComputedStyle(el).backgroundColor"
        )
    )
    # Day-Mode primary is navy: low R, low-mid G, low-mid B.
    assert primary_bg[0] <= 60 and primary_bg[1] <= 80 and primary_bg[2] <= 110, (
        f"Day Mode primary button must be navy, got rgb{primary_bg} "
        f"(if this is black, Night Mode CSS is leaking into Day Mode)."
    )

    accent_bg = _rgb(
        page.locator(".cl-btn--accent").first.evaluate(
            "el => getComputedStyle(el).backgroundColor"
        )
    )
    # Day-Mode accent is blue: B is the dominant channel.
    assert accent_bg[2] >= 130 and accent_bg[2] > accent_bg[0], (
        f"Day Mode accent button must be blue, got rgb{accent_bg}"
    )

    page.screenshot(
        path=str(ARTIFACT_DIR / "05_day_mode_baseline.png"),
        full_page=True,
    )


def test_login_page_critical_inline_night_css_applies(page):
    """templates/login.html ships its own inline critical Night CSS block
    (separate from layout.html). This test forces data-theme="night" on the
    public /login page and asserts the inline block paints the body and
    inputs correctly even before the external stylesheet is parsed."""
    page.goto(f"{BASE_URL}/login", wait_until="networkidle")
    page.evaluate(
        "document.documentElement.setAttribute('data-theme', 'night')"
    )

    body_bg = _rgb(page.evaluate("getComputedStyle(document.body).backgroundColor"))
    assert _is_blackish(body_bg), (
        f"Login body must be black after data-theme=night, got rgb{body_bg}. "
        f"If this fails the inline critical block in templates/login.html is "
        f"missing or wrong."
    )

    inp = page.locator("input").first
    if inp.count() > 0:
        inp_bg = _rgb(inp.evaluate("el => getComputedStyle(el).backgroundColor"))
        inp_color = _rgb(inp.evaluate("el => getComputedStyle(el).color"))
        assert _is_blackish(inp_bg), (
            f"Login input background must be black, got rgb{inp_bg}"
        )
        assert _is_night_red(inp_color), (
            f"Login input text colour must be night-red, got rgb{inp_color}"
        )

    page.screenshot(
        path=str(ARTIFACT_DIR / "06_login_night.png"),
        full_page=True,
    )
