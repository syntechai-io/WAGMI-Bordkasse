"""Single source of truth for the static asset cache-buster.

Both the `?v=` query string on CSS link tags (rendered by the page
templates) and the service worker's `CACHE_NAME` (served by the
`/sw.js` route) are derived from a content hash of the bundled
stylesheets. A CSS deploy therefore automatically invalidates both
layers — no hand-edited version constants to forget.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, Iterable, Tuple

TRACKED_CSS: Tuple[str, ...] = (
    "static/ui_v1.css",
    "static/ui_desktop_skin.css",
    "static/ui_navy_contrast_fix.css",
    "static/ui_mobile_skin.css",
    "static/cl_design.css",
    "static/ui_ios_prime.css",
    "static/ui_night_mode.css",
)

CACHE_NAME_PLACEHOLDER = "__CREWLOG_CACHE_NAME__"

_cache: Dict[str, object] = {"sig": None, "version": None}


def _signature(paths: Iterable[Path]) -> Tuple[Tuple[str, float, int], ...]:
    sig = []
    for p in paths:
        try:
            st = p.stat()
            sig.append((p.as_posix(), st.st_mtime, st.st_size))
        except FileNotFoundError:
            sig.append((p.as_posix(), 0.0, 0))
    return tuple(sig)


def asset_version() -> str:
    """Short content-derived version string used for `?v=` cache busting.

    Recomputed when any tracked file's mtime/size changes; otherwise
    served from a module-level cache so template rendering stays cheap.
    The hash is over file contents, so identical bytes produce identical
    versions across machines (deploys are reproducible).
    """
    paths = [Path(p) for p in TRACKED_CSS]
    sig = _signature(paths)
    if _cache["sig"] == sig and _cache["version"]:
        return _cache["version"]  # type: ignore[return-value]
    h = hashlib.sha256()
    for p in paths:
        try:
            h.update(p.read_bytes())
        except FileNotFoundError:
            h.update(b"<missing>")
        h.update(b"\0")
    version = h.hexdigest()[:10]
    _cache["sig"] = sig
    _cache["version"] = version
    return version


def cache_name() -> str:
    """Service worker cache name derived from `asset_version()`."""
    return f"crewlog-v{asset_version()}"


def invalidate_cache() -> None:
    """Drop the memoized version (test helper / dev-time hook)."""
    _cache["sig"] = None
    _cache["version"] = None
