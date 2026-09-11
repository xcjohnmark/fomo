"""Telegram bot notifier client supporting live dispatch and dry-run testing."""

import logging
from typing import Optional

try:
    from telegram._bot import Bot
except ImportError:
    Bot = None

from config.settings import Settings, get_settings
from models.domain import AlertCandidate
from telegram.formatter import format_telegram_alert

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Dispatches formatted alerts to a configured Telegram chat or logs them in dry-run mode."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.bot_token = self.settings.TELEGRAM_BOT_TOKEN
        self.chat_id = self.settings.TELEGRAM_CHAT_ID
        self.dry_run = self.settings.DRY_RUN

        self._bot = None
        if self.bot_token and Bot is not None:
            self._bot = Bot(token=self.bot_token)

    @property
    def is_configured(self) -> bool:
        """Return True if active Telegram bot credentials are set."""
        return bool(self.bot_token and self.chat_id and not self.dry_run and self._bot is not None)

    async def send_alert(self, candidate: AlertCandidate) -> bool:
        """Format and dispatch an alert to Telegram or logger."""
        text = format_telegram_alert(candidate)
        token_name = candidate.token.symbol or candidate.token.token_address[:8]

        if not self.is_configured:
            logger.info(
                "[TELEGRAM DRY-RUN ALERT] %s (Score: %s):\n%s",
                token_name,
                candidate.score_result.score,
                text,
            )
            return True

        try:
            assert self._bot is not None
            assert self.chat_id is not None
            await self._bot.send_message(chat_id=self.chat_id, text=text)
            logger.info("Telegram alert sent successfully for %s", token_name)
            return True
        except Exception as e:
            logger.error("Failed to send Telegram alert for %s: %s", token_name, e)
            return False

    async def health_check(self) -> bool:
        """Check if Telegram client is configured and reachable."""
        if not self.is_configured:
            # Running in dry-run mode is considered healthy for local dev
            return True
        try:
            assert self._bot is not None
            me = await self._bot.get_me()
            return me is not None
        except Exception as e:
            logger.warning("Telegram health check failed: %s", e)
            return False
