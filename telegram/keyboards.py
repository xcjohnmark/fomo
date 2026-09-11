"""Inline keyboard markup builders for alerts and interactive bot controls."""

from typing import Any, Dict, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_alert_keyboard(token_address: str, chain: str = "solana") -> InlineKeyboardMarkup:
    """Construct interactive inline action buttons for a Quick Flip alert.

    Buttons:
    - View Token (Direct DexScreener link)
    - Watch (Add to watchlist callback)
    - Paper Trade (Open simulated position callback)
    - Ignore (Acknowledge / dismiss callback)
    """
    dex_url = f"https://dexscreener.com/{chain}/{token_address}"

    keyboard = [
        [
            InlineKeyboardButton("🔍 View Token", url=dex_url),
            InlineKeyboardButton("👀 Watch", callback_data=f"watch:{token_address}"),
        ],
        [
            InlineKeyboardButton("📝 PAPER TRADE", callback_data=f"paper:{token_address}"),
            InlineKeyboardButton("❌ Ignore", callback_data=f"ignore:{token_address}"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_settings_keyboard(settings_data: Dict[str, Any]) -> InlineKeyboardMarkup:
    """Construct inline settings adjustment toggles."""
    paused = settings_data.get("alerts_paused", False)
    pause_text = "▶️ Resume Alerts" if paused else "⏸️ Pause Alerts"

    keyboard = [
        [
            InlineKeyboardButton(pause_text, callback_data="settings:toggle_pause"),
        ],
        [
            InlineKeyboardButton("Score -5", callback_data="settings:score_down"),
            InlineKeyboardButton("Score +5", callback_data="settings:score_up"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)
