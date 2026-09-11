"""Unit tests for the HealthCheckService."""

import pytest
from app.health import HealthCheckService
from collectors.mock_pump_collector import MockPumpCollector
from config.settings import Settings
from telegram.client import TelegramNotifier


@pytest.mark.asyncio
async def test_health_check_service(session_factory, test_settings: Settings):
    """Verify that all components report HEALTHY with in-memory DB and mock collector."""
    collector = MockPumpCollector()
    telegram = TelegramNotifier(settings=test_settings)

    health_svc = HealthCheckService(
        session_factory=session_factory,
        collector=collector,
        telegram_notifier=telegram,
    )

    status = await health_svc.get_health_status()
    assert status["status"] == "HEALTHY"
    assert status["components"]["database"] == "UP"
    assert status["components"]["collector"] == "UP"
    assert status["components"]["telegram"] == "UP"
