"""Application entry point and lifecycle orchestrator."""

import argparse
import asyncio
import logging
import signal
import sys

from app.health import HealthCheckService
from app.logging import setup_logging
from collectors.mock_pump_collector import MockPumpCollector
from config.settings import get_settings
from database.session import async_session_factory, close_db, get_engine, init_db
from services.alert_recorder import AlertRecorder
from services.outcome_tracker import OutcomeTracker
from services.scanner import MarketScannerService
from strategy.engine import MomentumStrategyEngine
from telegram.client import TelegramNotifier

logger = logging.getLogger("fomo_momentum")


async def main() -> None:
    """Initialize system and start market scanning pipeline."""
    parser = argparse.ArgumentParser(description="Pump.fun Momentum Research & Alerting System")
    parser.add_argument("--once", action="store_true", help="Execute one scan cycle and exit")
    parser.add_argument("--health", action="store_true", help="Run health check and exit")
    args = parser.parse_args()

    settings = get_settings()
    setup_logging(log_level=settings.LOG_LEVEL, log_file=settings.LOG_FILE)

    logger.info("Starting Pump.fun Momentum Research System...")
    logger.info("Database URL: %s", settings.DATABASE_URL)
    logger.info("Min Momentum Score: %s", settings.MIN_MOMENTUM_SCORE)
    logger.info("Telegram Configured: %s", bool(settings.TELEGRAM_BOT_TOKEN))

    # 1. Initialize Database Tables
    engine = get_engine()
    await init_db(engine)
    session_factory = async_session_factory(engine)

    # 2. Initialize Data Provider / Collector
    # In production, swap with a live Pump.fun / DEX collector without touching strategy
    collector = MockPumpCollector()

    # 3. Initialize Strategy & Alerting Infrastructure
    strategy_engine = MomentumStrategyEngine(settings=settings)
    telegram_notifier = TelegramNotifier(settings=settings)
    alert_recorder = AlertRecorder(session_factory=session_factory)
    outcome_tracker = OutcomeTracker(session_factory=session_factory, collector=collector)

    # 4. Health Check
    health_service = HealthCheckService(
        session_factory=session_factory,
        collector=collector,
        telegram_notifier=telegram_notifier,
    )
    health_status = await health_service.get_health_status()
    logger.info("System Health Status: %s", health_status)

    if args.health:
        print(f"Health Status: {health_status}")
        await close_db()
        return

    # 5. Build Scanner Service
    scanner = MarketScannerService(
        collector=collector,
        strategy_engine=strategy_engine,
        alert_recorder=alert_recorder,
        outcome_tracker=outcome_tracker,
        telegram_notifier=telegram_notifier,
        settings=settings,
    )

    if args.once:
        logger.info("Executing single scan cycle (--once)...")
        candidates = await scanner.scan_once()
        logger.info("Single scan completed. Detected %d candidates.", len(candidates))
        await close_db()
        return

    # 6. Continuous loop with graceful shutdown
    stop_event = asyncio.Event()

    def request_stop(*_):
        logger.info("Shutdown signal received. Stopping scanner...")
        stop_event.set()

    # Register OS signals where supported (Windows supports SIGINT and SIGTERM)
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, request_stop)
        except Exception:
            pass

    try:
        await scanner.run_loop(stop_event)
    finally:
        logger.info("Cleaning up and closing database connections...")
        await close_db()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
