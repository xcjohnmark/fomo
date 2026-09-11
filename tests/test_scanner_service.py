"""End-to-end integration test for the market scanning and outcome tracking pipeline."""

from datetime import datetime, timezone
import pytest
from collectors.mock_pump_collector import MockPumpCollector
from config.settings import Settings
from models.domain import TokenSnapshot
from services.alert_recorder import AlertRecorder
from services.outcome_tracker import OutcomeTracker
from services.scanner import MarketScannerService
from strategy.engine import MomentumStrategyEngine
from telegram.client import TelegramNotifier


@pytest.mark.asyncio
async def test_end_to_end_scanner_pipeline(
    session_factory, test_settings: Settings, sample_strong_token: TokenSnapshot, sample_weak_token: TokenSnapshot
):
    """Verify that scanner runs, detects strong candidate, persists alert, and tracks outcome."""
    collector = MockPumpCollector(initial_tokens=[sample_strong_token, sample_weak_token])
    strategy_engine = MomentumStrategyEngine(settings=test_settings)
    alert_recorder = AlertRecorder(session_factory=session_factory)
    outcome_tracker = OutcomeTracker(session_factory=session_factory, collector=collector)
    telegram_notifier = TelegramNotifier(settings=test_settings)

    scanner = MarketScannerService(
        collector=collector,
        strategy_engine=strategy_engine,
        alert_recorder=alert_recorder,
        outcome_tracker=outcome_tracker,
        telegram_notifier=telegram_notifier,
        settings=test_settings,
    )

    # 1. Execute single scan cycle
    candidates = await scanner.scan_once()
    assert len(candidates) == 1
    assert candidates[0].token.symbol == "STRONG"
    assert candidates[0].score_result.score >= 85.0

    # 2. Verify alert persisted in database
    recent_alerts = await alert_recorder.get_recent_alerts()
    assert len(recent_alerts) == 1
    alert = recent_alerts[0]
    assert alert.token_symbol == "STRONG"
    assert alert.momentum_score >= 85.0
    assert alert.price == sample_strong_token.price_usd

    # 3. Simulate price movement for outcome tracking
    # Price rises 25% after 10 minutes
    assert sample_strong_token.price_usd is not None
    new_token_state = sample_strong_token.model_copy(
        update={
            "price_usd": sample_strong_token.price_usd * 1.25,
            # Backdate alert timestamp so elapsed minutes >= 10
            "timestamp": datetime.fromtimestamp(
                sample_strong_token.timestamp.timestamp() - 700, tz=timezone.utc
            ),
        }
    )
    collector.set_token(new_token_state)

    # Update alert timestamp in DB to simulate 11 minutes having passed
    async with session_factory() as session:
        async with session.begin():
            db_alert = await session.get(type(alert), alert.id)
            db_alert.alert_timestamp = new_token_state.timestamp

    # Run outcome tracker
    tracked = await outcome_tracker.track_open_alerts()
    assert tracked >= 1

    # Check observations
    recent_alerts = await alert_recorder.get_recent_alerts()
    updated_alert = recent_alerts[0]
    assert len(updated_alert.observations) >= 1
    obs = updated_alert.observations[0]
    assert obs.interval_minutes in [5, 10]
    assert obs.return_percentage == 25.0
