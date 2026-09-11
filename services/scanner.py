"""Market scanner service orchestrating scan, score, alert, persistence, and tracking."""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional

from collectors.base import BaseCollector
from config.settings import Settings, get_settings
from models.domain import AlertCandidate
from services.alert_recorder import AlertRecorder
from services.outcome_tracker import OutcomeTracker
from strategy.engine import MomentumStrategyEngine
from telegram.client import TelegramNotifier

logger = logging.getLogger(__name__)


class MarketScannerService:
    """Core market scanner orchestrator managing the pipeline."""

    def __init__(
        self,
        collector: BaseCollector,
        strategy_engine: MomentumStrategyEngine,
        alert_recorder: AlertRecorder,
        outcome_tracker: OutcomeTracker,
        telegram_notifier: TelegramNotifier,
        settings: Optional[Settings] = None,
    ):
        self.collector = collector
        self.strategy_engine = strategy_engine
        self.alert_recorder = alert_recorder
        self.outcome_tracker = outcome_tracker
        self.telegram_notifier = telegram_notifier
        self.settings = settings or get_settings()

        # Cooldown map: token_address -> last_alert_timestamp
        self._alert_cooldowns: Dict[str, datetime] = {}
        self._cooldown_seconds = 1800  # 30 minutes cooldown before re-alerting same token

    def is_on_cooldown(self, token_address: str) -> bool:
        """Check if a token has been alerted recently."""
        last_alert = self._alert_cooldowns.get(token_address)
        if last_alert is None:
            return False
        elapsed = (datetime.now(timezone.utc) - last_alert).total_seconds()
        return elapsed < self._cooldown_seconds

    async def scan_once(self) -> List[AlertCandidate]:
        """Execute a single scan, score, alert, record, and outcome tracking cycle."""
        logger.debug("Executing market scan cycle...")

        # 1. Fetch normalized market data
        tokens = await self.collector.get_active_tokens()
        logger.debug("Fetched %d tokens from collector", len(tokens))

        # 2. Evaluate against strategy engine
        candidates = self.strategy_engine.evaluate_tokens(tokens)
        logger.debug("Strategy engine identified %d candidates", len(candidates))

        dispatched_candidates: List[AlertCandidate] = []

        # 3. Process each qualified candidate
        for candidate in candidates:
            address = candidate.token.token_address
            if self.is_on_cooldown(address):
                logger.debug("Skipping %s: currently on cooldown", candidate.token.token)
                continue

            logger.info(
                "[ALERT TRIGGERED] Momentum Alert: %s (Score: %s/100, MC: $%s, Liq: $%s)",
                candidate.token.token,
                candidate.score_result.score,
                f"{candidate.token.market_cap:,.0f}",
                f"{candidate.token.liquidity:,.0f}",
            )

            # Send Telegram alert
            sent = await self.telegram_notifier.send_alert(candidate)

            # Persist alert record to database
            await self.alert_recorder.record_alert(candidate)

            # Set cooldown timestamp
            self._alert_cooldowns[address] = datetime.now(timezone.utc)
            dispatched_candidates.append(candidate)

        # 4. Check and track existing open alerts for outcome observations
        tracked = await self.outcome_tracker.track_open_alerts()
        if tracked > 0:
            logger.debug("Recorded %d price observations for active setups", tracked)

        return dispatched_candidates

    async def run_loop(self, stop_event: asyncio.Event) -> None:
        """Continuously run scanner at configured intervals until stop_event is set."""
        logger.info(
            "Starting market scanner loop (Interval: %ds, Min Score: %s)",
            self.settings.SCAN_INTERVAL_SECONDS,
            self.settings.MIN_MOMENTUM_SCORE,
        )

        while not stop_event.is_set():
            try:
                await self.scan_once()
            except Exception as e:
                logger.error("Unexpected error in scanner cycle: %s", e, exc_info=True)

            try:
                await asyncio.wait_for(
                    stop_event.wait(), timeout=self.settings.SCAN_INTERVAL_SECONDS
                )
            except asyncio.TimeoutError:
                pass

        logger.info("Market scanner loop stopped gracefully.")
