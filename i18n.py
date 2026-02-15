import json
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

SUPPORTED_LANGS = ("de", "en")
DEFAULT_LANG = "de"
I18N_DEBUG = os.environ.get("I18N_DEBUG", "0") == "1"

_translations: dict[str, dict[str, str]] = {}


def _load_translations():
    global _translations
    locales_dir = os.path.join(os.path.dirname(__file__), "locales")
    for lang in SUPPORTED_LANGS:
        filepath = os.path.join(locales_dir, f"{lang}.json")
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                _translations[lang] = json.load(f)
        except FileNotFoundError:
            logger.error("Locale file not found: %s", filepath)
            _translations[lang] = {}
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON in locale file %s: %s", filepath, e)
            _translations[lang] = {}


_load_translations()


def reload_translations():
    _load_translations()


def get_lang(request) -> str:
    lang_param = None
    if hasattr(request, "query_params"):
        lang_param = request.query_params.get("lang")

    if lang_param and lang_param in SUPPORTED_LANGS:
        request.session["lang"] = lang_param
        return lang_param

    session_lang = request.session.get("lang")
    if session_lang and session_lang in SUPPORTED_LANGS:
        return session_lang

    accept = request.headers.get("accept-language", "")
    if accept:
        primary = accept.split(",")[0].strip().lower()
        if primary.startswith("en"):
            detected = "en"
        else:
            detected = "de"
        request.session["lang"] = detected
        return detected

    request.session["lang"] = DEFAULT_LANG
    return DEFAULT_LANG


def set_lang(request, lang: str):
    if lang in SUPPORTED_LANGS:
        request.session["lang"] = lang


def t(lang: str, key: str, **kwargs) -> str:
    lang_dict = _translations.get(lang, {})
    value = lang_dict.get(key)

    if value is None and lang != DEFAULT_LANG:
        fallback_dict = _translations.get(DEFAULT_LANG, {})
        value = fallback_dict.get(key)

    if value is None:
        if I18N_DEBUG:
            return f"\u27e6{key}\u27e7"
        return key

    if kwargs:
        try:
            return value.format(**kwargs)
        except (KeyError, IndexError):
            return value

    return value
