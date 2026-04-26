"""Contract tests for the asset_version single-source-of-truth helper.

The helper feeds two places:
  * the `?v=` query string on every CSS <link> in the page templates,
  * the service worker `CACHE_NAME` served by the `/sw.js` route.

These tests pin down the behavior that lets a CSS deploy invalidate
both layers without anyone editing version constants.
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from asset_version import (
    CACHE_NAME_PLACEHOLDER,
    TRACKED_CSS,
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


def test_asset_version_changes_when_css_changes(tmp_path):
    target = Path(TRACKED_CSS[0])
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
        assert after != before, "version must rotate when stylesheet contents change"
    finally:
        target.write_bytes(original)
        invalidate_cache()


def test_sw_js_holds_placeholder_not_hardcoded_version():
    sw = Path("static/sw.js").read_text()
    assert CACHE_NAME_PLACEHOLDER in sw
    # Guard against the old hand-edited constants reappearing.
    assert "crewlog-v28" not in sw
    assert "crewlog-v29" not in sw


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
