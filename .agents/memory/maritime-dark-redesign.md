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
