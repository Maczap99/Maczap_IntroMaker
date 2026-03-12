"""
lang_manager.py
───────────────
Lightweight i18n helper.

Folder layout:
    IntroMaker/
        scripts/       ← .py source files (including this one)
        lang/          ← de.json, en.json

    PyInstaller bundle (sys._MEIPASS):
        lang/          ← bundled via --add-data "%CD%\lang;lang"
        lang_manager.py, main.py, ...  ← all flat in _MEIPASS root

Usage
-----
    from lang_manager import tr, set_language, available_languages

    set_language("de")
    tr("bottom.status_ready")    # → "Bereit"
    tr("stepper.minutes", 5)     # → "5 min"
"""

import json
import os
import sys


# ── Path resolution ───────────────────────────────────────────────────────────

def _find_lang_dir() -> str:
    """
    Find lang/ regardless of working directory or bundle state.

    Case 1 — PyInstaller .exe:
        sys._MEIPASS is set → lang/ is directly inside _MEIPASS
        (because --add-data "lang;lang" puts it there)

    Case 2 — Normal run from scripts/:
        __file__ = IntroMaker/scripts/lang_manager.py
        lang/    = IntroMaker/lang/
        → go one level up from scripts/

    Case 3 — Flat layout / testing (scripts/ == lang/ parent):
        __file__ = IntroMaker/lang_manager.py
        lang/    = IntroMaker/lang/
        → same directory as this file
    """
    # Case 1: bundled EXE
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "lang")

    this_dir = os.path.dirname(os.path.abspath(__file__))

    # Case 2: scripts/ subfolder → parent is project root
    parent_candidate = os.path.join(os.path.dirname(this_dir), "lang")
    if os.path.isdir(parent_candidate):
        return parent_candidate

    # Case 3: flat layout — lang/ next to this file
    flat_candidate = os.path.join(this_dir, "lang")
    return flat_candidate   # may not exist yet, handled gracefully below


_LANG_DIR      = _find_lang_dir()
_DEFAULT_LANG  = "de"
_FALLBACK_LANG = "en"


# ── In-memory state ───────────────────────────────────────────────────────────

_strings: dict = {}
_current: str  = _DEFAULT_LANG


# ── Internal helpers ──────────────────────────────────────────────────────────

def _load_file(lang_code: str) -> dict:
    path = os.path.join(_LANG_DIR, f"{lang_code}.json")
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _flatten(d: dict, prefix: str = "") -> dict:
    """Recursively flatten nested dict → dot-separated keys."""
    out = {}
    for k, v in d.items():
        full_key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out.update(_flatten(v, full_key))
        else:
            out[full_key] = v
    return out


# ── Public API ────────────────────────────────────────────────────────────────

def available_languages() -> list:
    """Return [(code, native_name), …] for every .json found in lang/."""
    _NATIVE = {"de": "Deutsch", "en": "English", "ru": "Русский"}
    langs = []
    if os.path.isdir(_LANG_DIR):
        for fn in sorted(os.listdir(_LANG_DIR)):
            if fn.endswith(".json"):
                code = fn[:-5]
                langs.append((code, _NATIVE.get(code, code.upper())))
    return langs if langs else [(_DEFAULT_LANG, "Deutsch")]


def set_language(lang_code: str):
    """Load language strings into memory (with fallback to English)."""
    global _strings, _current
    fallback = _flatten(_load_file(_FALLBACK_LANG))
    primary  = _flatten(_load_file(lang_code))
    _strings = {**fallback, **primary}
    _current = lang_code


def current_language() -> str:
    return _current


def tr(key: str, *args) -> str:
    """Look up *key* and optionally format with positional *args*.

    Returns the key itself if not found — never crashes.
    """
    raw = _strings.get(key, key)
    if not args:
        return raw
    try:
        return raw.format(*args)
    except (IndexError, KeyError):
        return raw


# ── Auto-initialise on import ─────────────────────────────────────────────────
set_language(_DEFAULT_LANG)