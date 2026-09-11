"""Health-check mechanism verifying database, collector, and alerting services."""

import logging
from typing import Any, Dict
from sqlalchemy import text
from collectors.base import BaseCollector, MarketDataProvider
from telegram.client import TelegramNotifier

logger = logging.getLogger(__name__)


class HealthCheckService:
    """Provides comprehensive health status for system components."""

    def __init__(
        self,
        session_factory,
        collector: MarketDataProvider,
        telegram_notifier: TelegramNotifier,
    ):
        self.session_factory = session_factory
        self.collector = collector
        self.telegram_notifier = telegram_notifier

    async def check_database(self) -> bool:
        """Verify database connectivity with a ping query."""
        try:
            async with self.session_factory() as session:
                result = await session.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            logger.error("Database health check failed: %s", e)
            return False

    async def check_collector(self) -> bool:
        """Verify collector provider status."""
        try:
            return await self.collector.health_check()
        except Exception as e:
            logger.error("Collector health check failed: %s", e)
            return False

    async def check_telegram(self) -> bool:
        """Verify Telegram service status."""
        try:
            return await self.telegram_notifier.health_check()
        except Exception as e:
            logger.error("Telegram health check failed: %s", e)
            return False

    async def get_health_status(self) -> Dict[str, Any]:
        """Collect status across all subsystems."""
        db_ok = await self.check_database()
        collector_ok = await self.check_collector()
        telegram_ok = await self.check_telegram()

        is_healthy = db_ok and collector_ok and telegram_ok

        return {
            "status": "HEALTHY" if is_healthy else "DEGRADED",
            "components": {
                "database": "UP" if db_ok else "DOWN",
                "collector": "UP" if collector_ok else "DOWN",
                "telegram": "UP" if telegram_ok else "DOWN",
            },
        }
