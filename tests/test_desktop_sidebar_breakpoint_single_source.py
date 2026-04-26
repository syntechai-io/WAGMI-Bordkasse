"""Static-source check that the desktop-sidebar breakpoint is declared in
one place and that all four call sites agree with that declaration.

Why this test exists
--------------------
Task #49 found a stale 1024px copy of the desktop-sidebar threshold in
``static/ui_v1.css`` that left a 1024–1279px dead zone with no hamburger
AND no permanent sidebar. The end-to-end test
``tests/test_desktop_sidebar_breakpoint_e2e.py`` catches the layout
regression at runtime, but only when Playwright is available.

This test is the cheap, always-on companion: it parses the canonical
declaration in ``static/ui_breakpoints.css`` and asserts that
``static/ui_ios_prime.css``, ``static/ui_v1.css``, and
``static/ui_nav.js`` all reference exactly that same number — so a
future edit that bumps one place and forgets the others fails the
suite immediately, before anyone has to spin up a browser.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


CANONICAL_FILE = Path("static/ui_breakpoints.css")
IOS_PRIME = Path("static/ui_ios_prime.css")
UI_V1 = Path("static/ui_v1.css")
UI_NAV_JS = Path("static/ui_nav.js")
LAYOUT_TPL = Path("templates/layout.html")


def _strip_block_comments(css: str) -> str:
    """Remove `/* ... */` blocks so comment text doesn't taint regex
    searches that look for live `@media` literals."""
    return re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)


def _strip_js_comments(js: str) -> str:
    """Remove both `//` line and `/* */` block comments from JS."""
    js = re.sub(r"/\*.*?\*/", "", js, flags=re.DOTALL)
    js = re.sub(r"//[^\n]*", "", js)
    return js


@pytest.fixture(scope="module")
def canonical_value() -> int:
    """Parse `--cl-desktop-min-px` (the unitless integer form) from
    ``static/ui_breakpoints.css`` — the single source of truth."""
    assert CANONICAL_FILE.exists(), (
        f"{CANONICAL_FILE} is missing — the canonical breakpoint file "
        "was deleted. Recreate it or move the declaration somewhere a "
        "future engineer will find it."
    )
    text = CANONICAL_FILE.read_text(encoding="utf-8")
    m_px = re.search(r"--cl-desktop-min\s*:\s*(\d+)px\s*;", text)
    m_int = re.search(r"--cl-desktop-min-px\s*:\s*(\d+)\s*;", text)
    assert m_px is not None, (
        "ui_breakpoints.css must declare `--cl-desktop-min: <N>px;`"
    )
    assert m_int is not None, (
        "ui_breakpoints.css must declare `--cl-desktop-min-px: <N>;` "
        "(unitless integer, read by static/ui_nav.js at runtime)"
    )
    px_value = int(m_px.group(1))
    int_value = int(m_int.group(1))
    assert px_value == int_value, (
        f"--cl-desktop-min ({px_value}px) and --cl-desktop-min-px "
        f"({int_value}) must be the same number"
    )
    return px_value


def test_canonical_file_has_sane_value(canonical_value: int) -> None:
    """A breakpoint outside ~1024–1920 is almost certainly a typo
    (off-by-one, fat-finger, or unit mix-up). Catch it loudly."""
    assert 1024 <= canonical_value <= 1920, (
        f"canonical breakpoint {canonical_value}px is outside the sane "
        "1024–1920 range — likely a typo"
    )


def test_ui_ios_prime_desktop_media_uses_canonical(canonical_value: int) -> None:
    """Every desktop-sidebar `@media (min-width: ...)` block in
    ui_ios_prime.css must use the canonical value, and every paired
    mobile `@media (max-width: ...)` block must use canonical-1."""
    css = _strip_block_comments(IOS_PRIME.read_text(encoding="utf-8"))

    min_widths = [int(n) for n in re.findall(r"@media\s*\(\s*min-width:\s*(\d+)px\s*\)", css)]
    max_widths = [int(n) for n in re.findall(r"@media\s*\(\s*max-width:\s*(\d+)px\s*\)", css)]

    assert canonical_value in min_widths, (
        f"ui_ios_prime.css has no `@media (min-width: {canonical_value}px)` "
        f"block — the desktop-sidebar @media block has drifted from "
        f"--cl-desktop-min in {CANONICAL_FILE}"
    )

    sidebar_min_widths = [w for w in min_widths if w >= 1024]
    drift = [w for w in sidebar_min_widths if w != canonical_value]
    assert not drift, (
        f"ui_ios_prime.css has stray desktop-min @media values {drift} "
        f"that don't match canonical {canonical_value}px — the desktop "
        f"sidebar threshold has drifted from {CANONICAL_FILE}"
    )

    expected_mobile = canonical_value - 1
    mobile_drift = [w for w in max_widths if w >= 1024 and w != expected_mobile]
    assert not mobile_drift, (
        f"ui_ios_prime.css has `@media (max-width: ...)` blocks "
        f"{mobile_drift} in the desktop-adjacent range that don't match "
        f"canonical-1 ({expected_mobile}px) — there is now a dead zone "
        f"between mobile and desktop layouts"
    )


def test_ui_v1_desktop_drawer_hide_uses_canonical(canonical_value: int) -> None:
    """The `#drawer-open` desktop hide rule in ui_v1.css must use the
    canonical breakpoint — this is the regression discovered in task #49."""
    css = _strip_block_comments(UI_V1.read_text(encoding="utf-8"))

    block = re.search(
        r"@media\s*\(\s*min-width:\s*(\d+)px\s*\)\s*\{[^}]*#drawer-open[^}]*\}",
        css,
        re.DOTALL,
    )
    assert block is not None, (
        "ui_v1.css no longer has a `@media (min-width: <N>px)` block "
        "that hides #drawer-open. Either restore it or update this test "
        "if the rule moved."
    )
    found = int(block.group(1))
    assert found == canonical_value, (
        f"ui_v1.css hides #drawer-open at {found}px, but the canonical "
        f"breakpoint is {canonical_value}px ({CANONICAL_FILE}). The "
        f"{min(found, canonical_value)}–{max(found, canonical_value) - 1}px "
        "range now has no hamburger AND no sidebar — exactly the bug "
        "task #49 fixed."
    )


def test_ui_nav_js_reads_canonical_and_has_no_literal(canonical_value: int) -> None:
    """ui_nav.js must read the breakpoint from `--cl-desktop-min-px`
    (so it tracks the canonical value automatically) and must not
    sprinkle bare `1280` literals through `window.innerWidth` checks."""
    js_raw = UI_NAV_JS.read_text(encoding="utf-8")
    js = _strip_js_comments(js_raw)

    assert "--cl-desktop-min-px" in js, (
        "ui_nav.js must read the canonical breakpoint via "
        "`getComputedStyle(...).getPropertyValue('--cl-desktop-min-px')` "
        "instead of hardcoding the value."
    )

    leaked = re.findall(
        r"window\.innerWidth\s*[<>]=?\s*(\d{3,4})",
        js,
    )
    assert not leaked, (
        f"ui_nav.js still compares window.innerWidth against literal "
        f"value(s) {leaked} — replace with the DESKTOP_MIN constant so "
        f"the breakpoint stays in sync with {CANONICAL_FILE}."
    )

    fallback = re.findall(rf"\b{canonical_value}\b", js)
    assert len(fallback) <= 1, (
        f"ui_nav.js has {len(fallback)} occurrences of the literal "
        f"{canonical_value}; expected at most one (the documented "
        "fallback inside the DESKTOP_MIN initializer). Replace the "
        "extras with the DESKTOP_MIN constant."
    )


def test_layout_template_loads_canonical_file() -> None:
    """`templates/layout.html` must include ui_breakpoints.css so the
    custom property is defined before `ui_nav.js` runs and reads it."""
    tpl = LAYOUT_TPL.read_text(encoding="utf-8")
    assert "ui_breakpoints.css" in tpl, (
        "templates/layout.html does not include ui_breakpoints.css. "
        "Without it, --cl-desktop-min-px is undefined and ui_nav.js "
        "falls back to its hardcoded default — defeating the single "
        "source of truth."
    )
    # Order matters: ui_breakpoints.css must come before ui_nav.js
    bp_idx = tpl.find("ui_breakpoints.css")
    nav_idx = tpl.find("ui_nav.js")
    assert nav_idx == -1 or bp_idx < nav_idx, (
        "ui_breakpoints.css must be loaded BEFORE ui_nav.js in "
        "layout.html so the custom property is parsed before the JS "
        "reads it."
    )
