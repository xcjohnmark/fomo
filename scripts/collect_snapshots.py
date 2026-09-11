"""CLI runner for the Automated Market-Data Collector.

Allows running single collection cycles, continuous background loops,
or inspecting stored database statistics without triggering any strategy
or sending Telegram notifications.
"""

import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import List, Optional

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from app.logging import setup_logging
from collectors.birdeye_adapter import BirdeyeAdapter
from collectors.dexscreener_adapter import DexScreenerAdapter
from collectors.mock_pump_collector import MockPumpCollector
from config.settings import get_settings
from database.session import close_db, get_engine, async_session_factory, init_db
from services.data_collector import AutomatedDataCollector

logger = logging.getLogger("collect_snapshots")


def get_provider(provider_name: str, settings):
    """Instantiate requested market data provider."""
    name = provider_name.lower().strip()
    if name == "dexscreener":
        return DexScreenerAdapter()
    elif name == "mock":
        return MockPumpCollector()
    elif name == "birdeye":
        api_key = settings.BIRDEYE_API_KEY
        if not api_key:
            logger.warning("BIRDEYE_API_KEY not configured. Falling back to DexScreener.")
            return DexScreenerAdapter()
        return BirdeyeAdapter(api_key=api_key)
    else:
        logger.warning("Unknown provider '%s', defaulting to DexScreener.", provider_name)
        return DexScreenerAdapter()


async def show_stats(collector: AutomatedDataCollector) -> None:
    """Print current counts of stored entities."""
    stats = await collector.get_stats()
    print("\n" + "=" * 50)
    print("      FOMO MARKET INTELLIGENCE DATABASE STATS")
    print("=" * 50)
    print(f"  Data Sources:     {stats['data_sources']}")
    print(f"  Tracked Tokens:   {stats['tokens']}")
    print(f"  Liquidity Pools:  {stats['pools']}")
    print(f"  Market Snapshots: {stats['market_snapshots']}")
    print("=" * 50 + "\n")


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fomo Automated Market-Data Collector (Phase 3)"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Execute a single collection pass and exit immediately.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum tokens to discover/collect per cycle (default: 5).",
    )
    parser.add_argument(
        "--tokens",
        type=str,
        default=None,
        help="Comma-separated list of specific token mint addresses to collect.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Interval in seconds between collection cycles in loop mode (default: 30s).",
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="dexscreener",
        choices=["dexscreener", "mock", "birdeye"],
        help="Data provider adapter to use (default: dexscreener).",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Display current database record statistics and exit.",
    )

    args = parser.parse_args()

    settings = get_settings()
    setup_logging(log_level=settings.LOG_LEVEL)

    engine = get_engine()
    # Ensure database schema is created
    await init_db(engine)

    session_factory = async_session_factory()
    provider = get_provider(args.provider, settings)

    collector = AutomatedDataCollector(
        session_factory=session_factory,
        provider=provider,
        dedupe_window_seconds=60,
    )

    try:
        if args.stats:
            await show_stats(collector)
            return

        target_addresses: Optional[List[str]] = None
        if args.tokens:
            target_addresses = [t.strip() for t in args.tokens.split(",") if t.strip()]

        if args.once:
            logger.info("Executing single snapshot collection pass...")
            stored = await collector.collect_snapshots_once(
                limit=args.limit,
                target_addresses=target_addresses,
            )
            logger.info("Completed single pass. %d snapshots stored.", len(stored))
            await show_stats(collector)
        else:
            stop_event = asyncio.Event()

            # Handle termination signals on supported platforms
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                try:
                    loop.add_signal_handler(sig, stop_event.set)
                except (NotImplementedError, AttributeError):
                    # Windows loop might not implement add_signal_handler
                    pass

            logger.info(
                "Starting continuous collector loop (press Ctrl+C to stop)..."
            )
            try:
                await collector.run_collection_loop(
                    stop_event=stop_event,
                    interval_seconds=args.interval,
                    limit=args.limit,
                    target_addresses=target_addresses,
                )
            except (KeyboardInterrupt, asyncio.CancelledError):
                logger.info("Termination signal received. Exiting loop.")
                stop_event.set()

            await show_stats(collector)

    finally:
        if hasattr(provider, "close"):
            await provider.close()
        await close_db()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete.")
