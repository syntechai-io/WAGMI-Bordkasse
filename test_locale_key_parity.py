"""
Regression test: keep ``locales/de.json`` and ``locales/en.json`` in sync.

Why this exists
---------------
The sibling test ``test_i18n_no_hardcoded_strings.py`` only verifies that
every ``t('foo.bar')`` referenced in a template exists in *both* locale
files. It does **not** notice the inverse case: a key that exists in only
one of the files. Because :func:`i18n.t` falls back to the German value
when the English string is missing, a one-sided key silently regresses
English users to German — exactly the bug class the original i18n cleanup
was meant to prevent.

This test is intentionally tiny and pure-Python so it runs in well under a
second alongside the rest of the suite.

Adding a legitimate exception
-----------------------------
If a key is deliberately present in only one locale (for example, a
language-specific legal disclaimer), add the key string to
``PARITY_ALLOWLIST`` below with a brief comment explaining why.
"""

import json
from pathlib import Path

import pytest

LOCALES_DIR = Path(__file__).parent / "locales"
DE_PATH = LOCALES_DIR / "de.json"
EN_PATH = LOCALES_DIR / "en.json"

# Translation keys that may legitimately exist in only one locale file.
# Keep this list short and justify each entry with a comment.
PARITY_ALLOWLIST: frozenset[str] = frozenset()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_locale_key_parity():
    """``de.json`` and ``en.json`` must contain the exact same set of keys."""
    de_keys = set(_load(DE_PATH).keys())
    en_keys = set(_load(EN_PATH).keys())

    only_in_de = sorted((de_keys - en_keys) - PARITY_ALLOWLIST)
    only_in_en = sorted((en_keys - de_keys) - PARITY_ALLOWLIST)

    if not (only_in_de or only_in_en):
        return

    lines: list[str] = []
    for key in only_in_de:
        lines.append(f"  '{key}' is in locales/de.json but missing from locales/en.json")
    for key in only_in_en:
        lines.append(f"  '{key}' is in locales/en.json but missing from locales/de.json")

    pytest.fail(
        "Locale files are out of sync. Every key must appear in both "
        "locales/de.json and locales/en.json so users do not silently "
        "see the other language. Add the missing translations, or — if "
        "the asymmetry is intentional — extend PARITY_ALLOWLIST in "
        "test_locale_key_parity.py.\n\n" + "\n".join(lines)
    )
