---
name: Trips page view switcher
description: Cards/Log toggle feature on the real trips page — how it's built and what to watch for.
---

## What was built
The trips list page (`/trips`, `templates/trips.html`) now has a **Cards / Log** segmented toggle in the section header. Both views share the same Jinja2 data (`trips`, `active_trip`, `trip_totals`).

- **Cards view** (`.cl-trv-cards`): navy gradient hero card for `active_trip` with animated SVG waves + sailboat watermark, then a compact card list for all trips.
- **Log view** (`.cl-trv-log`): the original `<table class="cl-trips-table">` unchanged.
- Toggle is a `<div class="cl-trips-toggle">` with two `data-trips-view` buttons inside `<section id="cl-trips-view-wrap" data-view="cards">`.
- CSS show/hide: `#cl-trips-view-wrap[data-view="cards"] .cl-trv-log { display:none }` and vice versa.
- Preference persisted in `localStorage` under key `trips-view` (default: `cards`).

## CSS location
All new styles appended to `static/cl_design.css` under the comment `/* Trips — two-view switcher */`. Class prefix: `cl-trv-` (trips view).

Wave animations: `@keyframes cl-trv-wave1/2/3`. Boat animation: `@keyframes cl-trv-boat`.

## Rename forms
Both views render rename forms. Cards view IDs: `trip-name-display-{id}` / `trip-rename-form-{id}`. Log view IDs: `trip-name-display-log-{id}` / `trip-rename-form-log-{id}`. The `toggleRename()` JS function handles both suffixes with a loop.

**Why:** Duplicate IDs would break the toggle; each view needs its own DOM IDs.

## Template editing pitfall
The trips.html file contains emoji (⛵, 📋, etc.) which prevent verbatim Edit-tool replacements. Use Python line-range replacement instead when editing large blocks of this file. Also: Python heredoc escaping leaks backslashes into Jinja2 template strings — verify with `python3 -c "from jinja2 import Environment, FileSystemLoader; ..."` after any template write.

## Mockup reference
Design source: `artifacts/mockup-sandbox/src/components/mockups/trips/HarborDeck.tsx` and `TripsSwitcher.tsx`.
