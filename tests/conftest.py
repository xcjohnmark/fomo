"""Pytest fixtures for async testing with in-memory database."""

import asyncio
from datetime import datetime, timezone
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from collectors.mock_pump_collector import MockPumpCollector
from config.settings import Settings
from database.base import Base
from models.domain import NormalizedTokenData, TokenSnapshot
from services.alert_recorder import AlertRecorder
from services.outcome_tracker import OutcomeTracker
from strategy.engine import MomentumStrategyEngine
from telegram.client import TelegramNotifier


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Provide testing settings with dry-run enabled."""
    return Settings(
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        TELEGRAM_BOT_TOKEN=None,
        TELEGRAM_CHAT_ID=None,
        MIN_MOMENTUM_SCORE=85,
        MIN_LIQUIDITY_USD=5000.0,
        DRY_RUN=True,
        LOG_LEVEL="DEBUG",
    )


@pytest_asyncio.fixture
async def async_engine(test_settings: Settings):
    """Create an isolated in-memory SQLite async engine."""
    engine = create_async_engine(
        test_settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
def session_factory(async_engine):
    """Provide an async sessionmaker bound to the in-memory engine."""
    return async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest.fixture
def sample_strong_token() -> TokenSnapshot:
    """Sample token qualifying as a high-momentum candidate (Score >= 85)."""
    return TokenSnapshot(
        timestamp=datetime.now(timezone.utc),
        symbol="STRONG",
        name="Strong Token",
        provider_source="test_feed",
        token_address="StrongMintAddress1111111111111111111111111",
        market_cap_usd=200000.0,
        price_usd=0.0002,
        liquidity_usd=45000.0,
        change_5m_pct=8.5,
        change_1h_pct=22.0,
        change_4h_pct=40.0,
        change_24h_pct=75.0,
        volume_5m_usd=18000.0,
        volume_1h_usd=110000.0,
        volume_24h_usd=500000.0,
        buys=250,
        sells=90,
        buy_volume_usd=14000.0,
        sell_volume_usd=4000.0,
        buyers=180,
        sellers=60,
        holders_count=2100,
        top10_holder_pct=16.5,
        token_age_seconds=6300,
        token_age_formatted="1h 45m",
        trader_activity_summary="Multiple smart traders active",
        narrative="Viral AI meme trend",
    )


@pytest.fixture
def sample_weak_token() -> TokenSnapshot:
    """Sample token with poor metrics that should be rejected (Score < 40)."""
    return TokenSnapshot(
        timestamp=datetime.now(timezone.utc),
        symbol="WEAK",
        name="Weak Token",
        provider_source="test_feed",
        token_address="WeakMintAddress222222222222222222222222222",
        market_cap_usd=50000.0,
        price_usd=0.00005,
        liquidity_usd=2000.0,  # poor liquidity
        change_5m_pct=-8.0,
        change_1h_pct=-15.0,
        change_4h_pct=50.0,
        change_24h_pct=200.0,
        volume_5m_usd=500.0,
        volume_1h_usd=2000.0,
        volume_24h_usd=25000.0,
        buys=10,
        sells=40,
        buyers=8,
        sellers=35,
        holders_count=80,
        top10_holder_pct=65.0,
        token_age_seconds=18000,
        token_age_formatted="5h 00m",
        trader_activity_summary="Dumping",
        narrative="None",
    )
