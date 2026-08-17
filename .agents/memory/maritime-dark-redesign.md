---
name: Full-app dark maritime redesign
description: How the whole-app HarborDeck dark theme was implemented — token files, component additions, day-mode override, table → card conversions.
---

## What was done
Converted the entire app from a light off-white theme to the HarborDeck dark maritime palette.

## Token files changed
- `static/cl_design.css` `:root` — dark navy values (`--cl-bg: #0b1d2e`, `--cl-surface: #112233`, etc.)
- `static/ui_v1.css` `:root` — legacy `--bg/--surface/--text` tokens updated to match
- Both files are the single source of truth for light/dark token values

## Day-mode override
`static/ui_night_mode.css` — appended `html[data-theme="day"]` block that restores the original light palette for users who explicitly chose Day mode. Night mode (black/red) is unaffected.

**Why:** Making dark the `:root` default means Day mode now needs an explicit override or it also goes dark.

## New CSS components (appended to cl_design.css)
- `.cl-pageheader` — overridden to gradient hero band (`linear-gradient(148deg, #071929 0%, #0c3260 52%, #1455a8 100%)`) + `::after` wave SVG cutout + radial shimmer. Applied to all pages that use `.cl-pageheader` (most main pages).
- `.cl-row-list` / `.cl-row-card` / `.cl-row-card--wrap` / `.cl-row-card__foot` — card-list replacement for `<table>` layouts.

## Templates converted (table → row cards)
- `templates/expenses.html` — expense list
- `templates/crew_list.html` — crew roster
- `templates/deposits.html` — deposit list
- `templates/balances.html` — balance summary

## Dropdown fix
`static/ui_navy_contrast_fix.css` — updated `.navy-shell .dropdown-content` from white to dark navy (`#112233`) with matching text/hover colors.

## Pages NOT yet converted
- `templates/logbook.html` — already card-based, but no wave hero (uses different header structure)
- `templates/settlement.html` — already card-based
- `templates/templates.html`, `groups.html` — covered by existing task #79
- Login/auth pages — don't extend layout.html, use own CSS

## How to add wave hero to a non-cl-pageheader page
Add `<header class="cl-pageheader"><div class="cl-pageheader__main"><h1 class="cl-title">…</h1></div></header>` at the top of the `.cl-page` block and the wave gradient applies automatically.

## Button variant system (dark-theme rules — all have !important on color)
- `cl-btn--ghost` — dark-glass (rgba white bg, #eef2f6 text). Use for neutral actions (View, Track, Archive, Back).
- `cl-btn--ghost-success` — same dark-glass but `color: var(--cl-success)`. Use for Reopen / positive ghost actions. **Do NOT use inline style="color:var(--cl-success)" on cl-btn--ghost** — the !important on ghost overrides inline styles.
- `cl-btn--ghost-danger` — transparent bg, `color: var(--cl-danger)`. Use for destructive actions (Finalize/Abschließen, Delete). **Must use `a.cl-btn--ghost-danger` CSS alias** because trips.html finalize is an `<a>` tag; `a { color: var(--accent) }` in ui_v1.css catches all `<a>` elements.

## Root link-color bugs (partially fixed, partially task #86)
- `ui_v1.css:222` — `a { color: var(--accent); }` bare tag selector catches all `<a>` including `<a class="cl-btn">`. Workaround: `!important` on all dark button text colors + explicit `a.cl-btn--ghost-danger` rule in cl_design.css. Permanent fix is task #86.
- `ui_desktop_skin.css` — `a:not(.btn)` link rule was catching `<a class="cl-btn">` (different class name). Fixed to `a:not(.btn):not(.cl-btn)`.
- All three theme modes (default dark, day, night) have overrides for ghost/ghost-success/ghost-danger in ui_night_mode.css.

## Table theme guard
Legacy desktop/table skins must use the active theme tokens for row and hover backgrounds, not hardcoded light grays. Component tables also set their cell background explicitly so later `tr:hover td` rules cannot reveal white cells in dark mode.

**Why:** The Trips log view had alternating and hovered rows turn nearly white while text remained dark-theme colors, making most content unreadable.

**How to apply:** When adding or changing table skins, use `var(--surface)` / `var(--surface-2)` or the `--cl-*` equivalents, and keep `.cl-table tbody td` / hover-cell rules explicit.

## Login native select contrast
The login page needs an explicit class on its trip `<select>` with matching `<option>` colors; the desktop form skin forces a white select surface while the dark default tokens otherwise provide light text.

**Why:** A populated trip appeared almost invisible because the value inherited the light-on-dark text color and rendered on the desktop skin’s white select background.

**How to apply:** Keep the default/day login select as dark text on a light native control, and provide a separate black/red `data-theme="night"` override. Do not rely on inherited `select` colors.
