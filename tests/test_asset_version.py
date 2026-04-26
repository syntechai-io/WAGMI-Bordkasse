"""Contract tests for the asset_version single-source-of-truth helper.

The helper feeds two places:
  * the `?v=` query string on every CSS <link> and JS <script> in the
    page templates,
  * the service worker `CACHE_NAME` served by the `/sw.js` route.

These tests pin down the behavior that lets a CSS- or JS-only deploy
invalidate both layers without anyone editing version constants.
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from asset_version import (
    CACHE_NAME_PLACEHOLDER,
    TRACKED_ASSETS,
    TRACKED_CSS,
    TRACKED_JS,
    asset_version,
    cache_name,
    invalidate_cache,
)


def test_asset_version_is_stable_for_unchanged_files():
    invalidate_cache()
    v1 = asset_version()
    v2 = asset_version()
    assert v1 == v2
    assert v1, "asset_version() must return a non-empty string"
    # Short-but-unique hex prefix; long enough to avoid practical collisions.
    assert len(v1) >= 8
    assert all(c in "0123456789abcdef" for c in v1)


def test_cache_name_uses_asset_version():
    assert cache_name() == f"crewlog-v{asset_version()}"


def _assert_version_rotates_when_file_changes(target: Path) -> None:
    original = target.read_bytes()
    invalidate_cache()
    before = asset_version()
    try:
        # Append a comment so the byte content + size change. mtime alone is
        # not enough on filesystems with low-resolution timestamps; size + sha
        # ensure the new signature is detected.
        target.write_bytes(original + b"\n/* cache-buster sentinel */\n")
        # Nudge mtime forward in case the test runs faster than fs resolution.
        future = time.time() + 2
        import os
        os.utime(target, (future, future))
        invalidate_cache()
        after = asset_version()
        assert after != before, (
            f"asset_version must rotate when {target} contents change"
        )
    finally:
        target.write_bytes(original)
        invalidate_cache()


def test_asset_version_changes_when_css_changes():
    _assert_version_rotates_when_file_changes(Path(TRACKED_CSS[0]))


def test_asset_version_changes_when_js_changes():
    _assert_version_rotates_when_file_changes(Path(TRACKED_JS[0]))


def test_sw_js_holds_placeholder_not_hardcoded_version():
    sw = Path("static/sw.js").read_text()
    assert CACHE_NAME_PLACEHOLDER in sw
    # Guard against the old hand-edited constants reappearing.
    assert "crewlog-v28" not in sw
    assert "crewlog-v29" not in sw


def test_sw_js_does_not_precache_unversioned_css_or_js():
    """Templates request CSS/JS with `?v=<asset_version>`. Precaching the
    unversioned URLs in the service worker just wastes a network round
    trip — the cached entries would never satisfy the page's actual
    requests. Guard against the old precache list creeping back."""
    sw = Path("static/sw.js").read_text()
    for css in TRACKED_CSS:
        url = "/" + css  # e.g. "/static/cl_design.css"
        assert f"'{url}'" not in sw and f'"{url}"' not in sw, (
            f"Unversioned CSS {url} must not be precached by the service worker"
        )
    for js in TRACKED_JS:
        url = "/" + js  # e.g. "/static/ui_nav.js"
        assert f"'{url}'" not in sw and f'"{url}"' not in sw, (
            f"Unversioned JS {url} must not be precached by the service worker"
        )


def test_tracked_css_covers_every_versioned_css_link_in_templates():
    """If a template adds a new `/static/<file>.css?v={{ asset_version }}`
    link, that file must also be in TRACKED_CSS — otherwise a deploy that
    only changes the new stylesheet would not rotate the asset version
    and the browser would keep serving the cached copy.
    """
    import re

    pattern = re.compile(r'/static/([A-Za-z0-9_./-]+\.css)\?v=\{\{\s*asset_version\s*\}\}')
    referenced: set[str] = set()
    for tpl in Path("templates").rglob("*.html"):
        for match in pattern.finditer(tpl.read_text()):
            referenced.add(f"static/{match.group(1)}")

    tracked = set(TRACKED_CSS)
    missing = referenced - tracked
    assert not missing, (
        "Templates reference cache-busted CSS files that are not in "
        f"asset_version.TRACKED_CSS: {sorted(missing)}. Add them so a "
        "stylesheet-only deploy rotates the asset version."
    )

    # Sanity: every tracked file actually exists on disk.
    for css in TRACKED_CSS:
        assert Path(css).exists(), f"TRACKED_CSS entry {css!r} does not exist"


def test_tracked_js_covers_every_versioned_js_reference_in_templates():
    """Mirror of the CSS contract for JS files. Catches both regular
    `<script src="/static/foo.js?v={{ asset_version }}">` tags and inline
    JS that builds the URL dynamically (e.g. the Capacitor bridge loader
    in `templates/layout.html` and `templates/login.html`).
    """
    import re

    pattern = re.compile(r'/static/([A-Za-z0-9_./-]+\.js)\?v=\{\{\s*asset_version\s*\}\}')
    referenced: set[str] = set()
    for tpl in Path("templates").rglob("*.html"):
        for match in pattern.finditer(tpl.read_text()):
            referenced.add(f"static/{match.group(1)}")

    tracked = set(TRACKED_JS)
    missing = referenced - tracked
    assert not missing, (
        "Templates reference cache-busted JS files that are not in "
        f"asset_version.TRACKED_JS: {sorted(missing)}. Add them so a "
        "JS-only deploy rotates the asset version."
    )

    # Sanity: every tracked file actually exists on disk.
    for js in TRACKED_JS:
        assert Path(js).exists(), f"TRACKED_JS entry {js!r} does not exist"


def test_no_template_uses_hand_edited_js_version():
    """Stale hand-edited cache-busters (e.g. `?v=5`) on `/static/*.js`
    URLs are exactly the bug task #59 fixed — they leak through deploys
    until someone notices. Guard against any reappearing.
    """
    import re

    # Match `/static/...js?v=<value>` where <value> is NOT a Jinja
    # expression. Catches `?v=5`, `?v=2025-01-01`, etc.
    bad = re.compile(
        r'/static/[A-Za-z0-9_./-]+\.js\?v=(?!\{\{)[^"\'\s>]+'
    )
    offenders: list[tuple[str, int, str]] = []
    for tpl in Path("templates").rglob("*.html"):
        for line_no, line in enumerate(tpl.read_text().splitlines(), 1):
            for match in bad.finditer(line):
                offenders.append((str(tpl), line_no, match.group(0)))
    assert not offenders, (
        "Hand-edited JS version queries detected — use "
        "`?v={{ asset_version }}` instead:\n"
        + "\n".join(f"  {f}:{ln} → {snippet}" for f, ln, snippet in offenders)
    )


def test_every_static_js_script_in_templates_is_versioned():
    """Every `<script src="/static/*.js">` tag and every inline
    `s.src = '/static/*.js'` assignment must include
    `?v={{ asset_version }}`. Catches the original miss in task #59:
    several script tags shipped with no cache-buster at all, so a
    JS-only deploy left users on stale code until the browser happened
    to revalidate.
    """
    import re

    script_tag = re.compile(
        r'<script[^>]*\bsrc=["\'](/static/[A-Za-z0-9_./-]+\.js)([^"\']*)["\']'
    )
    inline_assign = re.compile(
        r'\.src\s*=\s*["\'](/static/[A-Za-z0-9_./-]+\.js)([^"\']*)["\']'
    )

    offenders: list[tuple[str, str]] = []
    for tpl in Path("templates").rglob("*.html"):
        text = tpl.read_text()
        for pattern in (script_tag, inline_assign):
            for match in pattern.finditer(text):
                url, suffix = match.group(1), match.group(2)
                if "{{ asset_version }}" not in suffix:
                    offenders.append((str(tpl), url + suffix))

    assert not offenders, (
        "JS references missing `?v={{ asset_version }}`:\n"
        + "\n".join(f"  {f} → {snippet}" for f, snippet in offenders)
    )


def test_tracked_assets_is_css_plus_js():
    assert TRACKED_ASSETS == TRACKED_CSS + TRACKED_JS


def test_sw_route_substitutes_cache_name():
    try:
        from fastapi.testclient import TestClient
        from main import app
    except Exception as e:
        pytest.skip(f"app not importable: {e}")

    client = TestClient(app)
    r = client.get("/sw.js")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/javascript")
    body = r.text
    assert CACHE_NAME_PLACEHOLDER not in body
    assert cache_name() in body
