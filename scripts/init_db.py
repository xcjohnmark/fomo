"""Script to initialize or upgrade database schema."""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from app.logging import setup_logging
from config.settings import get_settings
from database.session import close_db, get_engine, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("init_db")


async def run_init() -> None:
    settings = get_settings()
    setup_logging(log_level=settings.LOG_LEVEL)
    logger.info("Initializing database tables for URL: %s", settings.DATABASE_URL)

    engine = get_engine()
    await init_db(engine)
    logger.info("[SUCCESS] Database tables created successfully!")
    await close_db()


if __name__ == "__main__":
    asyncio.run(run_init())
