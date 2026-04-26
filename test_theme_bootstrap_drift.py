"""
Regression test: catch drift in the early-paint theme bootstrap script.

Why this exists
---------------
The tiny ``<script>`` block that runs at the top of every ``<head>`` to apply
the saved theme on first paint (so the page doesn't flash light then go
dark) used to live in two places: ``templates/layout.html`` for the signed-in
flow with server-seeded preferences, and ``templates/login.html`` for the
simpler unauth flow. They shared most of their logic — read
``crewlog-theme`` from localStorage, resolve ``auto`` against
``prefers-color-scheme``, set ``data-theme="night"`` on ``<html>`` — but
were kept in sync by hand. If someone tweaked the resolution logic in one,
the other silently fell behind.

The shared logic now lives in ``templates/_theme_bootstrap.html``. This test
fails if a future change re-introduces an inline early-paint theme
``<script>`` block in either top-level template instead of including the
shared partial.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent
BOOTSTRAP_PARTIAL = REPO / "templates" / "_theme_bootstrap.html"
LAYOUT = REPO / "templates" / "layout.html"
LOGIN = REPO / "templates" / "login.html"


# Tokens that uniquely identify the early-paint theme bootstrap logic. If any
# of these appear inside an inline <script> block in a top-level template,
# the shared partial has been bypassed.
BOOTSTRAP_TOKENS = (
    "crewlog-theme",
    "__crewlogThemePref",
    "__crewlogThemeAuthoritative",
)


def test_bootstrap_partial_exists_and_is_non_trivial() -> None:
    """The shared partial must exist and contain the early-paint logic."""
    assert BOOTSTRAP_PARTIAL.is_file(), (
        f"{BOOTSTRAP_PARTIAL.relative_to(REPO)} is missing — it is the "
        f"single source of truth for the early-paint theme bootstrap."
    )
    src = BOOTSTRAP_PARTIAL.read_text(encoding="utf-8")
    for token in BOOTSTRAP_TOKENS:
        assert token in src, (
            f"{BOOTSTRAP_PARTIAL.relative_to(REPO)} is missing token "
            f"{token!r}; the partial must own the full bootstrap logic."
        )


@pytest.mark.parametrize("template", [LAYOUT, LOGIN])
def test_top_level_templates_include_bootstrap_partial(template: Path) -> None:
    """``layout.html`` and ``login.html`` must include the shared partial
    instead of inlining their own early-paint theme ``<script>`` block."""
    src = template.read_text(encoding="utf-8")
    assert '{% include "_theme_bootstrap.html" %}' in src, (
        f"{template.relative_to(REPO)} must include "
        f'`{{% include "_theme_bootstrap.html" %}}` so the early-paint '
        f"theme script stays in one place."
    )

    # And it must NOT redefine its own inline early-paint theme logic — that
    # is the exact drift we're trying to prevent.
    head_match = re.search(r"<head>(.*?)</head>", src, re.DOTALL | re.IGNORECASE)
    assert head_match, f"{template.relative_to(REPO)} has no <head> block"
    head = head_match.group(1)
    inline_scripts = re.findall(
        r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>",
        head,
        re.DOTALL,
    )
    for block in inline_scripts:
        for token in BOOTSTRAP_TOKENS:
            assert token not in block, (
                f"{template.relative_to(REPO)} still contains an inline "
                f"<script> block referencing {token!r}. Move that logic "
                f"into templates/_theme_bootstrap.html so the early-paint "
                f"theme bootstrap has a single source of truth."
            )
