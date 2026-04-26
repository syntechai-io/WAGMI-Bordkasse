"""
Regression test: catch drift between the inline first-paint Night Mode CSS
and the full Night Mode stylesheet.

Why this exists
---------------
The dark Night Mode palette is shipped twice on purpose:

1. ``static/ui_night_mode.css`` — the full rule set.
2. ``templates/_night_critical.html`` — a tiny inline ``<style>`` block in
   ``<head>`` so the dark palette renders on first paint, before the
   external stylesheet has loaded.

If someone edits the palette tokens (``--night-bg`` / ``--night-text`` /
etc.) in the full stylesheet but forgets to update the inline block, the
page will briefly flash the wrong colours on first paint. This test fails
when the two get out of sync, so contributors are reminded immediately.

It also makes sure both top-level templates (``layout.html`` and
``login.html``) actually include the shared partial — if a future change
re-introduces an inline ``<style>`` block instead, this test catches it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent
CRITICAL_PARTIAL = REPO / "templates" / "_night_critical.html"
NIGHT_CSS = REPO / "static" / "ui_night_mode.css"
LAYOUT = REPO / "templates" / "layout.html"
LOGIN = REPO / "templates" / "login.html"

# Palette tokens that MUST stay identical between the partial and the full
# stylesheet. These are the values that drive first-paint colours; if they
# differ, the page flashes the wrong shade before the external CSS loads.
TRACKED_TOKENS = (
    "--night-bg",
    "--night-surface",
    "--night-text",
    "--night-muted",
    "--night-border",
)

_TOKEN_RE_TEMPLATE = r"{token}\s*:\s*([#a-zA-Z0-9_().,\s-]+?)\s*[;}}]"


def _normalize_color(value: str) -> str:
    """Treat #000 and #000000 as the same colour for comparison purposes."""
    v = value.strip().lower()
    if re.fullmatch(r"#[0-9a-f]{3}", v):
        return "#" + "".join(ch * 2 for ch in v[1:])
    return v


def _extract_token(source: str, token: str) -> str | None:
    """Return the first value assigned to ``token`` inside the
    ``html[data-theme="night"]`` block of ``source``."""
    # Find the night-theme block first so we don't pick up the same token
    # being redefined elsewhere.
    block_re = re.compile(
        r'html\[data-theme="night"\]\s*\{([^}]*)\}',
        re.DOTALL,
    )
    match = block_re.search(source)
    if not match:
        return None
    body = match.group(1)
    token_match = re.search(
        _TOKEN_RE_TEMPLATE.format(token=re.escape(token)), body
    )
    if not token_match:
        return None
    return _normalize_color(token_match.group(1))


@pytest.mark.parametrize("token", TRACKED_TOKENS)
def test_night_palette_tokens_match(token: str) -> None:
    """Every tracked palette token in the inline partial matches the full
    stylesheet, so first paint and post-load paint use the same colour."""
    partial_src = CRITICAL_PARTIAL.read_text(encoding="utf-8")
    css_src = NIGHT_CSS.read_text(encoding="utf-8")

    inline_value = _extract_token(partial_src, token)
    full_value = _extract_token(css_src, token)

    assert inline_value is not None, (
        f"{token} not found in {CRITICAL_PARTIAL.relative_to(REPO)} — "
        f"the inline first-paint block must define it."
    )
    assert full_value is not None, (
        f"{token} not found in {NIGHT_CSS.relative_to(REPO)} — "
        f"the full stylesheet must define it."
    )
    assert inline_value == full_value, (
        f"Night Mode palette drift: {token} is {inline_value!r} in "
        f"{CRITICAL_PARTIAL.relative_to(REPO)} but {full_value!r} in "
        f"{NIGHT_CSS.relative_to(REPO)}. Update both so first paint and "
        f"post-load paint show the same colour."
    )


@pytest.mark.parametrize("template", [LAYOUT, LOGIN])
def test_top_level_templates_include_critical_partial(template: Path) -> None:
    """``layout.html`` and ``login.html`` must include the shared partial
    instead of inlining their own ``<style>`` block."""
    src = template.read_text(encoding="utf-8")
    assert '{% include "_night_critical.html" %}' in src, (
        f"{template.relative_to(REPO)} must include "
        f'`{{% include "_night_critical.html" %}}` so the inline first-paint '
        f"Night Mode CSS stays in one place."
    )

    # And it must NOT redefine its own inline night-theme rules — that's the
    # exact drift we're trying to prevent.
    head_match = re.search(r"<head>(.*?)</head>", src, re.DOTALL | re.IGNORECASE)
    assert head_match, f"{template.relative_to(REPO)} has no <head> block"
    head = head_match.group(1)
    inline_styles = re.findall(r"<style[^>]*>(.*?)</style>", head, re.DOTALL)
    for block in inline_styles:
        assert 'data-theme="night"' not in block, (
            f"{template.relative_to(REPO)} still contains an inline "
            f'<style> block with `data-theme="night"` rules. Move them into '
            f"templates/_night_critical.html so the night palette has a "
            f"single source of truth."
        )
