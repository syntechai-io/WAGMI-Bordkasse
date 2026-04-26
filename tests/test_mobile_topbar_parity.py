"""Static-source check for the mobile/iPad topbar parity contract
(task #65).

Background
----------
Before #65, the day-mode topbar at <1280px hid the theme switch and the
account chip — both lived inside `nav.topbar .desktop-nav`, which is
`display: none !important` until 1280px. The user reported that the
iPhone day-recap view felt visually anaemic next to the polished night
mode.

This test pins down four pieces of the fix so a future cleanup
(e.g. consolidating the topbar markup) can't silently regress them:

1. `templates/layout.html` exposes a `.topbar-mobile-actions`
   container with a `#topbar-mobile-theme-slot` and an
   `#topbar-account-chip` button.
2. `static/js/night-mode.js` mounts a switch into that slot at boot
   and wires the chip click to open the drawer.
3. `static/ui_ios_prime.css` declares the container hidden by default
   and visible at <1280px (so it stays out of the desktop nav).
4. The day-mode card-hierarchy bump exists and is scoped to
   `html:not([data-theme="night"])` so night mode is unaffected.
"""
from __future__ import annotations

import re
from pathlib import Path

LAYOUT_TPL = Path("templates/layout.html")
NIGHT_JS = Path("static/js/night-mode.js")
IOS_PRIME = Path("static/ui_ios_prime.css")


def _read(p: Path) -> str:
    assert p.exists(), f"{p} is missing"
    return p.read_text(encoding="utf-8")


# --- 1. layout markup -----------------------------------------------------

def test_layout_has_mobile_topbar_actions_container() -> None:
    tpl = _read(LAYOUT_TPL)
    assert "topbar-mobile-actions" in tpl, (
        "templates/layout.html no longer renders .topbar-mobile-actions — "
        "the mobile/iPad topbar will revert to the pre-#65 state where "
        "the theme switch and account chip are invisible at <1280px."
    )
    assert 'id="topbar-mobile-theme-slot"' in tpl, (
        "templates/layout.html no longer exposes #topbar-mobile-theme-slot — "
        "static/js/night-mode.js needs this hook to mount the 3-segment "
        "theme switch in the mobile topbar."
    )


def test_layout_has_account_chip_when_authenticated() -> None:
    tpl = _read(LAYOUT_TPL)
    assert 'id="topbar-account-chip"' in tpl, (
        "templates/layout.html no longer renders #topbar-account-chip — "
        "the mobile topbar account affordance from #65 is gone."
    )
    # Chip must be gated on an authenticated session so anonymous /login
    # views don't render an empty initial.
    assert (
        "user_id" in tpl and "saas_user_id" in tpl
    ), "account chip must be gated on session.user_id OR session.saas_user_id"


# --- 2. night-mode.js wiring ---------------------------------------------

def test_night_mode_js_mounts_into_mobile_slot() -> None:
    js = _read(NIGHT_JS)
    assert "ensureMobileTopbarSwitch" in js, (
        "static/js/night-mode.js no longer defines ensureMobileTopbarSwitch — "
        "the mobile topbar theme slot will be empty."
    )
    assert "topbar-mobile-theme-slot" in js, (
        "static/js/night-mode.js no longer references "
        "#topbar-mobile-theme-slot — the mobile mount point is broken."
    )
    # Confirm the function is actually invoked on DOMContentLoaded.
    dom_ready_block = re.search(
        r"DOMContentLoaded[^{]*\{([^}]*)\}", js, re.DOTALL
    )
    assert dom_ready_block, "DOMContentLoaded handler missing in night-mode.js"
    body = dom_ready_block.group(1)
    assert "ensureMobileTopbarSwitch" in body, (
        "ensureMobileTopbarSwitch is defined but never called from "
        "DOMContentLoaded — the mobile topbar switch will not appear."
    )
    assert "wireMobileAccountChip" in body, (
        "wireMobileAccountChip is not invoked — clicking the chip "
        "will do nothing instead of opening the drawer."
    )


def test_account_chip_opens_the_drawer() -> None:
    js = _read(NIGHT_JS)
    assert "topbar-account-chip" in js, (
        "static/js/night-mode.js no longer wires #topbar-account-chip — "
        "the chip will be a dead button."
    )
    # The chip should delegate to the existing hamburger so we don't
    # duplicate drawer-open logic. Look for both the chip lookup and
    # a drawer-open click in the same function.
    wire = re.search(
        r"function\s+wireMobileAccountChip[^{]*\{(.*?)\n\s*\}",
        js,
        re.DOTALL,
    )
    assert wire is not None, "wireMobileAccountChip() function is missing"
    fn = wire.group(1)
    assert "topbar-account-chip" in fn and "drawer-open" in fn, (
        "wireMobileAccountChip must look up #topbar-account-chip and "
        "delegate the click to #drawer-open (the existing hamburger)."
    )


# --- 3. CSS visibility gates ---------------------------------------------

def test_topbar_mobile_actions_visible_only_below_desktop() -> None:
    css = _read(IOS_PRIME)

    # Default (no media query) must hide the container so it never
    # overlaps the .desktop-nav block at >=1280px.
    default = re.search(
        r"\.topbar-mobile-actions\s*\{[^}]*display:\s*none[^}]*\}",
        css,
    )
    assert default is not None, (
        "ui_ios_prime.css must declare a base `.topbar-mobile-actions "
        "{ display: none; }` rule — without it, the chip and theme "
        "switch will duplicate the desktop nav at >=1280px."
    )

    # And there must be a (max-width: 1279px) block that re-enables it
    # via display: inline-flex (or flex). 1279 = canonical 1280 - 1.
    mobile_block = re.search(
        r"@media\s*\(\s*max-width:\s*1279px\s*\)\s*\{[^{}]*"
        r"\.topbar-mobile-actions\s*\{[^}]*display:\s*"
        r"(?:inline-flex|flex)[^}]*\}",
        css,
        re.DOTALL,
    )
    assert mobile_block is not None, (
        "ui_ios_prime.css must show .topbar-mobile-actions inside a "
        "`@media (max-width: 1279px)` block so the mobile/iPad topbar "
        "renders the theme switch and account chip."
    )


def test_account_chip_has_compact_height_override() -> None:
    """The global rule in ui_ios_prime.css forces every button to
    `min-height: 44px`, which would blow the chip out of the 48px
    topbar row. The chip must override that with `min-height: 32px
    !important` (or smaller) inside the topbar."""
    css = _read(IOS_PRIME)
    chip = re.search(
        r"\.topbar-account-chip\s*\{[^}]*min-height:\s*(\d+)px\s*!important",
        css,
    )
    assert chip is not None, (
        "ui_ios_prime.css must override the global `button { min-height: "
        "44px }` for .topbar-account-chip — otherwise the chip stretches "
        "the 48px topbar row."
    )
    height = int(chip.group(1))
    assert height <= 36, (
        f".topbar-account-chip min-height override is {height}px — "
        "must be <= 36px so the chip fits inside the 48px topbar row."
    )


# --- 4. Day-mode card hierarchy scoped to non-night theme ----------------

def test_day_mode_card_hierarchy_is_scoped_to_light_theme() -> None:
    css = _read(IOS_PRIME)
    # Look for the strong-border bump on .cl-card and confirm it is
    # gated on `html:not([data-theme="night"])` so night mode (which
    # provides its own red-on-black palette in ui_night_mode.css) is
    # not shadowed.
    rule = re.search(
        r"html:not\(\[data-theme=\"night\"\]\)\s+\.cl-card[^{]*\{"
        r"[^}]*border:\s*[^;]*var\(--cl-border-strong",
        css,
    )
    assert rule is not None, (
        "ui_ios_prime.css must bump .cl-card to --cl-border-strong "
        "under `html:not([data-theme=\"night\"])` so day-mode cards "
        "have visible separation from the page background — the core "
        "fix from task #65."
    )
