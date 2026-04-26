"""
End-to-end PWA tests covering the service worker after the precache change
in static/sw.js.

Two behaviors are checked:

1. The runtime network-first CSS handler populates the cache with the
   actual versioned URLs the templates request (e.g. /static/ui_v1.css?v=28),
   so that CSS is reachable from cache after the first network fetch even
   though it is no longer in STATIC_ASSETS.
2. When the browser is offline, the network-first HTML handler falls back
   to the cached /offline page (which IS in STATIC_ASSETS).

These run only when the dev server is reachable on http://localhost:5000.
"""
from __future__ import annotations

import os
import time

import pytest

playwright_sync_api = pytest.importorskip(
    "playwright.sync_api",
    reason="playwright is required for the service-worker offline tests",
)
sync_playwright = playwright_sync_api.sync_playwright


BASE_URL = os.environ.get("CREWLOG_BASE_URL", "http://localhost:5000")


def _server_is_up() -> bool:
    """Probe BASE_URL itself so the skip logic stays aligned with whatever
    host:port the test target actually points at (CI overrides via
    CREWLOG_BASE_URL, e.g. preview URLs or remapped ports)."""
    try:
        from urllib.request import urlopen
        from urllib.error import URLError
    except ImportError:
        return False
    try:
        with urlopen(f"{BASE_URL}/login", timeout=2) as r:
            return 200 <= r.status < 500
    except (URLError, OSError):
        return False


@pytest.fixture(scope="module", autouse=True)
def _require_running_server():
    if not _server_is_up():
        pytest.skip(f"app not reachable on {BASE_URL}")


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        yield b
        b.close()


@pytest.fixture()
def fresh_page(browser):
    """A brand-new context (no shared cache, no shared SW) per test."""
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    yield ctx, page
    ctx.close()


def _register_and_activate_sw(page, timeout_ms: int = 10_000) -> None:
    """Register /sw.js and block until it has activated and controls the page.

    /login is a standalone template that does NOT extend layout.html, so
    the inline registration script in layout.html never runs there. Calling
    register() directly avoids needing an authenticated page just to install
    the worker, while still exercising the same script source the app ships.
    """
    result = page.evaluate(
        """async () => {
            if (!('serviceWorker' in navigator)) return { ok: false, error: 'unsupported' };
            try {
                const reg = await navigator.serviceWorker.register('/sw.js', { scope: '/' });
                return { ok: true, scope: reg.scope };
            } catch (e) {
                return { ok: false, error: String(e) };
            }
        }"""
    )
    if not result.get("ok"):
        pytest.fail(f"sw registration failed: {result.get('error')}")

    deadline = time.time() + timeout_ms / 1000
    while time.time() < deadline:
        ready = page.evaluate(
            """async () => {
                const reg = await navigator.serviceWorker.getRegistration();
                if (!reg) return 'no-reg';
                if (reg.active && navigator.serviceWorker.controller) return 'active';
                return 'pending';
            }"""
        )
        if ready == "active":
            return
        time.sleep(0.2)
    pytest.fail("service worker did not activate within timeout")


_FIND_ACTIVE_CACHE_JS = """async () => {
    const keys = await caches.keys();
    // The SW versions caches as 'crewlog-vN'; pick whichever the active SW
    // currently uses (the activate handler purges the rest, so on a healthy
    // install there is exactly one).
    const ours = keys.filter(k => k.startsWith('crewlog-'));
    return ours.length ? ours[0] : null;
}"""


def test_runtime_cache_picks_up_versioned_css(fresh_page):
    """The runtime network-first handler should cache the versioned CSS URL."""
    _, page = fresh_page

    # First load installs + activates the SW.
    page.goto(f"{BASE_URL}/login", wait_until="networkidle")
    _register_and_activate_sw(page)

    # Reload so the now-active SW intercepts the CSS requests on this load.
    page.goto(f"{BASE_URL}/login", wait_until="networkidle")

    # Read the actual versioned CSS URL the template requested. This couples
    # the test to the real ?v=N value templates use, which is the whole
    # point of the runtime cache (the precache list intentionally omits CSS).
    css_href = page.evaluate(
        """() => {
            const link = document.querySelector('link[rel=stylesheet][href*="/static/ui_v1.css"]');
            return link ? link.href : null;
        }"""
    )
    assert css_href, "expected a <link> to /static/ui_v1.css?v=... in /login"
    assert "?v=" in css_href, f"expected a cache-buster on the CSS URL, got {css_href}"

    cache_name = page.evaluate(_FIND_ACTIVE_CACHE_JS)
    assert cache_name, "no crewlog-* cache found — SW activate did not run?"

    cached = page.evaluate(
        """async ({ name, url }) => {
            const cache = await caches.open(name);
            const hit = await cache.match(url);
            return hit ? { ok: hit.ok, status: hit.status } : null;
        }""",
        {"name": cache_name, "url": css_href},
    )
    assert cached is not None, (
        f"expected runtime cache {cache_name!r} to contain {css_href}, "
        f"but cache.match returned null"
    )
    assert cached["ok"] is True, f"cached CSS was not ok: {cached}"


def test_offline_fallback_serves_offline_page(fresh_page):
    """With the network down, navigating to an HTML route should serve /offline."""
    ctx, page = fresh_page

    page.goto(f"{BASE_URL}/login", wait_until="networkidle")
    _register_and_activate_sw(page)

    # Confirm the precache holds /offline before we kill the network — the
    # SW install handler put it there as part of STATIC_ASSETS.
    offline_in_cache = page.evaluate(
        """async () => {
            const cache = await caches.open('crewlog-v29');
            const hit = await cache.match('/offline');
            return hit ? { ok: hit.ok, status: hit.status } : null;
        }"""
    )
    assert offline_in_cache is not None, "/offline missing from precache"
    assert offline_in_cache["ok"] is True

    # Take the context offline. Playwright's set_offline gates fetch() and
    # navigation through the SW, which is exactly what we want to exercise.
    ctx.set_offline(True)

    # Use fetch from inside the page so the SW's fetch handler runs. A full
    # page.goto is flaky offline because Playwright treats failed top-level
    # navigations as errors before the SW gets a chance to respond.
    body = page.evaluate(
        """async () => {
            const r = await fetch('/some-page-that-does-not-matter', {
                headers: { 'accept': 'text/html' },
            });
            return { ok: r.ok, status: r.status, body: await r.text() };
        }"""
    )

    assert body["ok"] is True, f"offline fallback did not return ok: {body['status']}"
    # Marker text from templates/offline.html ({{ t('offline.retry') }}
    # resolves to 'Erneut versuchen' / 'Retry'). Match the anchor href which
    # is locale-independent and uniquely identifies the offline template.
    assert 'href="/"' in body["body"] and 'btn-primary' in body["body"], (
        "response body does not look like the offline page"
    )
    assert "<title>" in body["body"].lower() or "<h1" in body["body"], (
        "response body is not a full HTML document"
    )

    ctx.set_offline(False)
