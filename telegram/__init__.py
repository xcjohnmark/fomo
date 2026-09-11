"""Telegram alerts notification package bridging local components with python-telegram-bot."""

import sys
from pathlib import Path
import importlib.machinery
import importlib.util

# 1. Add site-packages/telegram to __path__ so python-telegram-bot submodules are accessible
_this_project_root = str(Path(__file__).parent.parent.resolve()).lower()
_search_paths = [
    p for p in sys.path
    if p and not str(Path(p).resolve()).lower().startswith(_this_project_root)
]
_spec = importlib.machinery.PathFinder.find_spec("telegram", _search_paths)
_real_mod = None

if _spec and _spec.submodule_search_locations:
    for loc in _spec.submodule_search_locations:
        if loc not in __path__:
            __path__.append(loc)

if _spec and _spec.loader:
    try:
        _real_mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_real_mod)
        for attr in dir(_real_mod):
            if not attr.startswith("__"):
                globals()[attr] = getattr(_real_mod, attr)
    except Exception:
        pass


def __getattr__(name):
    if _real_mod and hasattr(_real_mod, name):
        val = getattr(_real_mod, name)
        globals()[name] = val
        return val
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


# Export local components alongside python-telegram-bot symbols
from telegram.formatter import format_telegram_alert
from telegram.client import TelegramNotifier

__all__ = [
    "format_telegram_alert",
    "TelegramNotifier",
]

