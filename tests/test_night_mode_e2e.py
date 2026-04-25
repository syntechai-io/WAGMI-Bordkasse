from __future__ import annotations

import os
import secrets
from pathlib import Path

import pytest

playwright_sync_api = pytest.importorskip(
    "playwright.sync_api",
    reason="playwright is required for the night-mode e2e tests",
)
sync_playwright = playwright_sync_api.sync_playwright


BASE_URL = os.environ.get("CREWLOG_BASE_URL", "http://localhost:5000")
ARTIFACT_DIR = Path("test_artifacts/night_mode")


def _rgb(s: str) -> tuple[int, int, int]:
    import re
    nums = [int(n) for n in re.findall(r"\d+", s)[:3]]
    assert len(nums) == 3, f"could not parse colour: {s!r}"
    return tuple(nums)  # type: ignore[return-value]


def _is_night_red(rgb: tuple[int, int, int], *, muted: bool = False) -> bool:
    r, g, b = rgb
    if muted:
        return 100 <= r <= 200 and g <= 60 and b <= 60
    return r >= 200 and g <= 80 and b <= 80


def _is_dark_red_border(rgb: tuple[int, int, int]) -> bool:
    r, g, b = rgb
    return 60 <= r <= 200 and g <= 50 and b <= 50


def _is_blackish(rgb: tuple[int, int, int]) -> bool:
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
        pytest.skip(f"app not reachable on {BASE_URL}")
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


@pytest.fixture(scope="module")
def admin_credentials():
    """Provision a legacy admin with a known password and ensure ≥1 trip exists."""
    from db import SessionLocal
    from models import User, Trip, UserRole
    from datetime import date

    username = f"e2e_night_admin_{secrets.token_hex(3)}"
    password = secrets.token_urlsafe(12)
    db = SessionLocal()
    user_id = None
    try:
        user = User(username=username, role=UserRole.admin)
        user.set_password(password)
        db.add(user)
        if db.query(Trip).count() == 0:
            db.add(Trip(name="E2E Night Trip", start_date=date.today()))
        db.commit()
        user_id = user.id
        yield {"username": username, "password": password}
    finally:
        try:
            u = db.query(User).filter(User.id == user_id).first()
            if u:
                db.delete(u)
                db.commit()
        except Exception:
            db.rollback()
        db.close()


def test_night_mode_page_palette_is_pure_red_on_black(page):
    page.goto(f"{BASE_URL}/diagnostics/theme?theme=night", wait_until="networkidle")
    assert page.locator("html").get_attribute("data-theme") == "night"

    body_bg = _rgb(page.evaluate("getComputedStyle(document.body).backgroundColor"))
    body_color = _rgb(page.evaluate("getComputedStyle(document.body).color"))

    assert _is_blackish(body_bg), f"body bg not black: rgb{body_bg}"
    assert _is_night_red(body_color), f"body text not night-red: rgb{body_color}"

    page.screenshot(path=str(ARTIFACT_DIR / "01_page_palette.png"), full_page=True)


def test_night_mode_card_surface_is_dark_not_white(page):
    page.goto(f"{BASE_URL}/diagnostics/theme?theme=night", wait_until="networkidle")
    card = page.locator(".cl-card").first
    card.wait_for(state="visible")

    bg = _rgb(card.evaluate("el => getComputedStyle(el).backgroundColor"))
    border = _rgb(card.evaluate("el => getComputedStyle(el).borderColor"))

    assert _is_blackish(bg), f".cl-card bg not dark: rgb{bg}"
    assert _is_dark_red_border(border), f".cl-card border not dark red: rgb{border}"

    card.screenshot(path=str(ARTIFACT_DIR / "02_card_surface.png"))


def test_night_mode_all_button_variants_are_black_on_red(page):
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
            failures.append(f"{selector} bg={bg} expected black")
        if not _is_night_red(color):
            failures.append(f"{selector} color={color} expected night-red")
        if not _is_dark_red_border(border):
            failures.append(f"{selector} border={border} expected dark red")

    page.locator(".cl-card").nth(0).screenshot(path=str(ARTIFACT_DIR / "07_button_variants.png"))
    assert not failures, "button regressions:\n  - " + "\n  - ".join(failures)


def test_night_mode_native_checkbox_accent_is_red(page):
    page.goto(f"{BASE_URL}/diagnostics/theme?theme=night", wait_until="networkidle")
    cb = page.locator('.cl-check-row input[type="checkbox"]').first
    cb.wait_for(state="visible")

    accent = _rgb(cb.evaluate("el => getComputedStyle(el).accentColor"))
    assert _is_night_red(accent), f"checkbox accent not red: rgb{accent}"

    page.locator(".cl-check-row").first.screenshot(path=str(ARTIFACT_DIR / "03_checkbox_accent.png"))


def test_night_mode_tabbar_active_vs_inactive_are_visibly_different(page):
    page.goto(f"{BASE_URL}/diagnostics/theme?theme=night", wait_until="networkidle")
    active = page.locator(".cl-tabbar__item--active").first
    active.wait_for(state="visible")
    inactive = page.locator(".cl-tabbar__item:not(.cl-tabbar__item--active)").first
    inactive.wait_for(state="visible")

    active_color = _rgb(active.evaluate("el => getComputedStyle(el).color"))
    inactive_color = _rgb(inactive.evaluate("el => getComputedStyle(el).color"))

    assert _is_night_red(active_color), f"active tab not bright red: rgb{active_color}"
    assert _is_night_red(inactive_color, muted=True), f"inactive tab not muted red: rgb{inactive_color}"
    assert abs(active_color[0] - inactive_color[0]) >= 30, (
        f"active vs inactive tab too similar: {active_color} vs {inactive_color}"
    )

    page.locator(".cl-tabbar").first.screenshot(path=str(ARTIFACT_DIR / "04_tabbar_active_vs_inactive.png"))


def test_day_mode_remains_unchanged_no_regression(page):
    page.goto(f"{BASE_URL}/diagnostics/theme?theme=light", wait_until="networkidle")
    assert page.locator("html").get_attribute("data-theme") != "night"

    body_bg = _rgb(page.evaluate("getComputedStyle(document.body).backgroundColor"))
    assert all(c >= 230 for c in body_bg), f"day-mode body not light: rgb{body_bg}"

    primary_bg = _rgb(page.locator(".cl-btn--primary").first.evaluate(
        "el => getComputedStyle(el).backgroundColor"
    ))
    assert primary_bg[0] <= 60 and primary_bg[1] <= 80 and primary_bg[2] <= 110, (
        f"day-mode primary not navy: rgb{primary_bg}"
    )

    accent_bg = _rgb(page.locator(".cl-btn--accent").first.evaluate(
        "el => getComputedStyle(el).backgroundColor"
    ))
    assert accent_bg[2] >= 130 and accent_bg[2] > accent_bg[0], (
        f"day-mode accent not blue: rgb{accent_bg}"
    )

    page.screenshot(path=str(ARTIFACT_DIR / "05_day_mode_baseline.png"), full_page=True)


def test_login_page_critical_inline_night_css_applies(page):
    page.goto(f"{BASE_URL}/login", wait_until="networkidle")
    page.evaluate("document.documentElement.setAttribute('data-theme', 'night')")

    body_bg = _rgb(page.evaluate("getComputedStyle(document.body).backgroundColor"))
    assert _is_blackish(body_bg), f"login body not black: rgb{body_bg}"

    inp = page.locator("input").first
    if inp.count() > 0:
        inp_bg = _rgb(inp.evaluate("el => getComputedStyle(el).backgroundColor"))
        inp_color = _rgb(inp.evaluate("el => getComputedStyle(el).color"))
        assert _is_blackish(inp_bg), f"login input bg not black: rgb{inp_bg}"
        assert _is_night_red(inp_color), f"login input color not red: rgb{inp_color}"

    page.screenshot(path=str(ARTIFACT_DIR / "06_login_night.png"), full_page=True)


def test_trips_page_renders_night_palette_after_persisting_preference(page, admin_credentials):
    """Login as legacy admin, POST /api/preferences/theme=night, load /trips/,
    assert computed styles on real page primitives."""
    page.goto(f"{BASE_URL}/login", wait_until="networkidle")

    login_resp = page.evaluate(
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
        {"u": admin_credentials["username"], "p": admin_credentials["password"]},
    )
    assert login_resp["status"] in (0, 200, 303), f"login failed: {login_resp}"

    csrf = page.evaluate(
        "() => (document.cookie.split('; ').find(r => r.startsWith('csrftoken='))||'').split('=')[1] || ''"
    )
    resp = page.evaluate(
        """async (csrf) => {
            const r = await fetch('/api/preferences/theme', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'x-csrftoken': csrf},
                body: JSON.stringify({theme: 'night'}),
            });
            return {status: r.status, body: await r.text()};
        }""",
        csrf,
    )
    assert resp["status"] == 200, f"theme POST failed: {resp}"

    page.goto(f"{BASE_URL}/trips/", wait_until="networkidle")
    assert "/login" not in page.url, f"trips redirected to login: {page.url}"
    assert page.locator("html").get_attribute("data-theme") == "night", (
        "trips page did not apply data-theme=night from server preference"
    )

    body_bg = _rgb(page.evaluate("getComputedStyle(document.body).backgroundColor"))
    assert _is_blackish(body_bg), f"trips body bg not black: rgb{body_bg}"

    card = page.locator(".cl-card").first
    if card.count() > 0:
        card.wait_for(state="visible")
        card_bg = _rgb(card.evaluate("el => getComputedStyle(el).backgroundColor"))
        card_border = _rgb(card.evaluate("el => getComputedStyle(el).borderColor"))
        assert _is_blackish(card_bg), f"trips .cl-card bg not dark: rgb{card_bg}"
        assert _is_dark_red_border(card_border), f"trips .cl-card border not dark red: rgb{card_border}"

    for sel in (".cl-btn--primary", ".cl-btn--accent", ".cl-btn--success", ".cl-btn--warn"):
        btn = page.locator(sel).first
        if btn.count() == 0:
            continue
        btn.wait_for(state="visible")
        bg = _rgb(btn.evaluate("el => getComputedStyle(el).backgroundColor"))
        color = _rgb(btn.evaluate("el => getComputedStyle(el).color"))
        assert _is_blackish(bg), f"trips {sel} bg not black: rgb{bg}"
        assert _is_night_red(color), f"trips {sel} color not red: rgb{color}"

    page.screenshot(path=str(ARTIFACT_DIR / "08_trips_night.png"), full_page=True)
