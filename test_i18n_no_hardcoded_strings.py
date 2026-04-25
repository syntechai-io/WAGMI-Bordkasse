"""
Regression test: catch hardcoded German strings in templates before they ship.

Why this exists
---------------
Every visible string in a template should be wrapped in ``{{ t('some.key') }}``
so that German and English users see their own language. Hardcoded German
tokens like "Törn" or "Statistik" in templates have repeatedly slipped past
review. This test scans every ``templates/*.html`` file and fails if it finds
German-only characters or known German words outside translation calls,
template comments, ``<script>``/``<style>`` blocks, and an explicit allowlist.

It also cross-checks that every ``t('foo.bar')`` referenced in the templates
has a matching key in both ``locales/de.json`` and ``locales/en.json``.

The test is intentionally lightweight (pure-Python, regex-based, no Jinja
parser) so it runs in well under a second alongside the rest of the suite.

Adding a legitimate exception
-----------------------------
If a template legitimately contains a German-looking token (e.g. a date
format string like ``"d. MMM"``, a brand name such as "Müller GmbH", or a
proper noun used in both languages), add a tuple ``(filename, snippet)`` to
``ALLOWLIST`` below. ``snippet`` is matched as a substring of the offending
*line*, so a small unique fragment is enough.

Likewise, if a ``t('...')`` key is intentionally added for a future locale
release and not yet present in both JSON files, add the key to
``MISSING_KEY_ALLOWLIST``.
"""

import json
import re
from pathlib import Path

import pytest

TEMPLATES_DIR = Path(__file__).parent / "templates"
LOCALES_DIR = Path(__file__).parent / "locales"

# Known German-only tokens that should never appear as static template text.
# Umlauts already cover most cases; this list catches the umlaut-free ones.
GERMAN_TOKENS = (
    "Törn",
    "Statistik",
    "Zurück",
    "Sprache",
    "Datum",
    "Bordkasse",
    "Bitte",
    "Anmelden",
    "Abmelden",
    "Speichern",
    "Löschen",
    "Bearbeiten",
    "Hinzufügen",
    "Heute",
    "Gestern",
    "Morgen",
    "Einstellungen",
    "Übersicht",
    "Auswählen",
    "Wählen",
)

# Any non-ASCII character that is part of the German alphabet.
GERMAN_CHARS = "äöüÄÖÜß"

# Compiled pattern for one violation: a German-only character or token.
_VIOLATION_RE = re.compile(
    "[" + GERMAN_CHARS + "]|" + "|".join(re.escape(tok) for tok in GERMAN_TOKENS)
)

# Strip Jinja comments {# ... #} (multiline)
_JINJA_COMMENT_RE = re.compile(r"\{#.*?#\}", re.DOTALL)
# Strip HTML comments <!-- ... --> (multiline)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
# Strip <script>...</script> blocks (developer-facing strings, separate task)
_SCRIPT_RE = re.compile(r"<script\b[^>]*>.*?</script>", re.DOTALL | re.IGNORECASE)
# Strip <style>...</style> blocks (no user-facing copy lives here)
_STYLE_RE = re.compile(r"<style\b[^>]*>.*?</style>", re.DOTALL | re.IGNORECASE)
# Strip any {{ ... }} expression that contains a t( translation call.
# Uses a lazy, dot-all match so it can span newlines if a t() argument list wraps.
_T_CALL_RE = re.compile(r"\{\{[^{}]*?\bt\s*\([^{}]*?\}\}", re.DOTALL)
# Strip {% ... t(...) ... %} statements (e.g. {% set x = t('foo') %})
_T_STATEMENT_RE = re.compile(r"\{%[^{}]*?\bt\s*\([^{}]*?%\}", re.DOTALL)

# Pattern that pulls every t('...') / t("...") key reference out of a template.
_T_KEY_RE = re.compile(r"\bt\s*\(\s*['\"]([^'\"]+)['\"]")


# ---------------------------------------------------------------------------
# Allowlist: legitimate exceptions per template
# ---------------------------------------------------------------------------
# Each entry is (template_filename, substring_of_offending_line). The substring
# match is generous on purpose — pick a small unique fragment of the line that
# legitimately contains the German-looking token. Keep this list short and
# justify each entry with a comment.
# ---------------------------------------------------------------------------
ALLOWLIST: tuple[tuple[str, str], ...] = (
    # Example shape, kept commented out so the test starts empty and explicit:
    # ("about.html", "Müller GmbH"),
)

# Translation keys that may legitimately be missing from one or both locale
# files (e.g. staged for a future release). Keep this short.
MISSING_KEY_ALLOWLIST: frozenset[str] = frozenset()


def _strip_safe_regions(text: str) -> str:
    """Remove regions of the template where German text is OK or out of scope.

    Order matters: comments first (they may contain ``{{ ... }}``-shaped
    text), then ``<script>``/``<style>`` blocks, finally the translation
    calls themselves.
    """
    text = _JINJA_COMMENT_RE.sub("", text)
    text = _HTML_COMMENT_RE.sub("", text)
    text = _SCRIPT_RE.sub("", text)
    text = _STYLE_RE.sub("", text)
    text = _T_CALL_RE.sub("", text)
    text = _T_STATEMENT_RE.sub("", text)
    return text


def _is_allowlisted(filename: str, line: str) -> bool:
    return any(fname == filename and snippet in line for fname, snippet in ALLOWLIST)


def _iter_templates() -> list[Path]:
    files = sorted(TEMPLATES_DIR.rglob("*.html"))
    assert files, f"No templates found under {TEMPLATES_DIR}"
    return files


def test_no_hardcoded_german_in_templates():
    """No German-only characters or words outside ``t(...)`` / comments."""
    failures: list[str] = []

    for path in _iter_templates():
        original = path.read_text(encoding="utf-8")
        scrubbed = _strip_safe_regions(original)

        # Scan line-by-line so we can report a precise location *and* match
        # the allowlist against the surrounding line.
        for line_no, line in enumerate(scrubbed.splitlines(), start=1):
            if not _VIOLATION_RE.search(line):
                continue
            if _is_allowlisted(path.name, line):
                continue
            failures.append(
                f"{path.name}:{line_no}: hardcoded German text outside t(...): "
                f"{line.strip()[:160]}"
            )

    if failures:
        msg = (
            "Found hardcoded German strings in templates. Wrap them in "
            "{{ t('your.key') }} (and add the key to locales/de.json + "
            "locales/en.json), or — if it is a legitimate exception — "
            "extend ALLOWLIST in test_i18n_no_hardcoded_strings.py.\n\n"
            + "\n".join(failures)
        )
        pytest.fail(msg)


def test_translation_keys_referenced_in_templates_exist():
    """Every ``t('foo.bar')`` in a template must exist in de.json and en.json."""
    de = json.loads((LOCALES_DIR / "de.json").read_text(encoding="utf-8"))
    en = json.loads((LOCALES_DIR / "en.json").read_text(encoding="utf-8"))

    missing: list[str] = []
    for path in _iter_templates():
        text = path.read_text(encoding="utf-8")
        for match in _T_KEY_RE.finditer(text):
            key = match.group(1)
            if key in MISSING_KEY_ALLOWLIST:
                continue
            if key not in de:
                missing.append(f"{path.name}: '{key}' missing from locales/de.json")
            if key not in en:
                missing.append(f"{path.name}: '{key}' missing from locales/en.json")

    if missing:
        # Deduplicate while preserving order so the failure list stays readable.
        seen: set[str] = set()
        unique = [m for m in missing if not (m in seen or seen.add(m))]
        pytest.fail(
            "Translation keys referenced in templates are missing from one or "
            "both locale files. Add them to locales/de.json and locales/en.json, "
            "or extend MISSING_KEY_ALLOWLIST in "
            "test_i18n_no_hardcoded_strings.py.\n\n" + "\n".join(unique)
        )
