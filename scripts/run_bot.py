"""CLI entry point to launch the interactive Telegram bot daemon."""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from app.logging import setup_logging
from collectors.mock_pump_collector import MockPumpCollector
from config.settings import get_settings
from database.session import async_session_factory, close_db, get_engine, init_db
from services.paper_trader import PaperTraderService
from services.watchlist import WatchlistService
from strategy.engine import MomentumStrategyEngine
from telegram.bot import TelegramBotService

logger = logging.getLogger("fomo_telegram_bot")


async def main() -> None:
    """Initialize database and start the interactive Telegram bot."""
    settings = get_settings()
    setup_logging(log_level=settings.LOG_LEVEL, log_file=settings.LOG_FILE)

    logger.info("Initializing Fomo Telegram Bot Daemon...")
    logger.info("Database URL: %s", settings.DATABASE_URL)
    logger.info("Dry-Run Mode: %s", settings.DRY_RUN)

    # 1. Initialize Database Tables
    engine = get_engine()
    await init_db(engine)
    session_factory = async_session_factory(engine)

    # 2. Initialize Services & Components
    collector = MockPumpCollector()
    strategy_engine = MomentumStrategyEngine(settings=settings)
    paper_trader = PaperTraderService(session_factory=session_factory)
    watchlist = WatchlistService(session_factory=session_factory)

    bot_service = TelegramBotService(
        settings=settings,
        paper_trader=paper_trader,
        watchlist=watchlist,
        session_factory=session_factory,
        collector=collector,
        strategy_engine=strategy_engine,
    )

    if not bot_service.is_configured():
        logger.warning(
            "TELEGRAM_BOT_TOKEN is not set or DRY_RUN=true. "
            "Bot cannot start live Telegram polling. "
            "To connect live: set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env and restart."
        )
        # Verify in-memory/dry-run capabilities
        status_text = await bot_service.status_command(None, None)
        logger.info("System dry-run status verification:\n%s", status_text)
        await close_db()
        return

    logger.info("Starting live Telegram polling application...")
    app = bot_service.build_application()
    assert app is not None

    try:
        # Run long-polling
        app.run_polling()
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
