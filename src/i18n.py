"""Small JSON-backed localization layer for the installer."""
from __future__ import annotations
import json
import locale
import os
import subprocess

_ROOT = os.path.dirname(os.path.abspath(__file__))
_LOCALES = os.path.join(_ROOT, "locales")
_CACHE = {}

def normalize_language(value):
    value = (value or "").strip().lower().replace("_", "-")
    return "es" if value.startswith("es") else "en"

def detect_language():
    forced = os.environ.get("CINECONIA_LANG")
    if forced:
        return normalize_language(forced)
    try:
        current = locale.getlocale()[0]
        if current:
            return normalize_language(current)
    except Exception:
        pass
    try:
        r = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", "(Get-Culture).Name"],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode == 0 and r.stdout.strip():
            return normalize_language(r.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return "en"

def get_language():
    return normalize_language(os.environ.get("CINECONIA_LANG") or detect_language())

def _load(lang):
    lang = normalize_language(lang)
    if lang in _CACHE:
        return _CACHE[lang]
    path = os.path.join(_LOCALES, f"{lang}.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {}
    _CACHE[lang] = data
    return data

def t(key, lang=None, **kwargs):
    lang = normalize_language(lang or get_language())
    primary = _load(lang)
    fallback = _load("en")
    text = primary.get(key, fallback.get(key, key))
    try:
        return text.format(**kwargs)
    except (KeyError, ValueError):
        return text
