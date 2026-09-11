"""Telegram alerts notification package bridging local components with python-telegram-bot."""

import sys
from pathlib import Path

# Extend __path__ with site-packages/telegram so python-telegram-bot submodules are accessible
_this_project_root = str(Path(__file__).parent.parent.resolve()).lower()
for p in sys.path:
    if p and not str(Path(p).resolve()).lower().startswith(_this_project_root):
        candidate = Path(p) / "telegram"
        if candidate.is_dir() and (candidate / "_bot.py").exists():
            cand_str = str(candidate.resolve())
            if cand_str not in __path__:
                __path__.append(cand_str)
            break

# Export Bot from python-telegram-bot alongside local components
try:
    from telegram._bot import Bot
except ImportError:
    Bot = None  # Fallback for offline/mock environments

from telegram.formatter import format_telegram_alert
from telegram.client import TelegramNotifier

__all__ = ["Bot", "format_telegram_alert", "TelegramNotifier"]
