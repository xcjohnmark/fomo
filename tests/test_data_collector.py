"""Tests for AutomatedDataCollector service, deduplication, and resilience handlers."""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
import httpx
import pytest
from sqlalchemy import select

from collectors.mock_pump_collector import MockMarketDataProvider
from collectors.resilience import AsyncRateLimiter, execute_with_retry
from models.db import DataSource, MarketSnapshot, Pool, Token
from models.domain import TokenSnapshot
from services.data_collector import AutomatedDataCollector, compute_snapshot_hash


@pytest.mark.asyncio
async def test_compute_snapshot_hash():
    """Verify deterministic hash for identical snapshot data."""
    snap1 = TokenSnapshot(
        token_address="Mint123",
        symbol="ABC",
        price_usd=0.005,
        market_cap_usd=50000.0,
        liquidity_usd=10000.0,
        volume_5m_usd=2000.0,
        volume_1h_usd=8000.0,
        buys=50,
        sells=20,
    )
    snap2 = TokenSnapshot(
        token_address="Mint123",
        symbol="ABC",
        price_usd=0.005,
        market_cap_usd=50000.0,
        liquidity_usd=10000.0,
        volume_5m_usd=2000.0,
        volume_1h_usd=8000.0,
        buys=50,
        sells=20,
    )
    # Different price
    snap3 = TokenSnapshot(
        token_address="Mint123",
        symbol="ABC",
        price_usd=0.006,
        market_cap_usd=50000.0,
        liquidity_usd=10000.0,
        volume_5m_usd=2000.0,
        volume_1h_usd=8000.0,
        buys=50,
        sells=20,
    )

    h1 = compute_snapshot_hash(snap1)
    h2 = compute_snapshot_hash(snap2)
    h3 = compute_snapshot_hash(snap3)

    assert h1 == h2
    assert h1 != h3


@pytest.mark.asyncio
async def test_get_or_create_data_source(session_factory):
    """Verify DataSource is created once and reused on subsequent requests."""
    provider = MockMarketDataProvider(provider_name="test_source")
    collector = AutomatedDataCollector(session_factory=session_factory, provider=provider)

    async with session_factory() as session:
        async with session.begin():
            src1 = await collector.get_or_create_data_source(session)
            assert src1.id is not None
            assert src1.name == "test_source"

        async with session.begin():
            src2 = await collector.get_or_create_data_source(session)
            assert src2.id == src1.id

    # Verify only 1 record in DB
    async with session_factory() as session:
        sources = (await session.execute(select(DataSource))).scalars().all()
        assert len(sources) == 1


@pytest.mark.asyncio
async def test_upsert_token_and_pool(session_factory, sample_strong_token):
    """Verify token and pool creation and updates."""
    provider = MockMarketDataProvider()
    collector = AutomatedDataCollector(session_factory=session_factory, provider=provider)

    sample_strong_token.pool_address = "PoolAddress111111111111111111111"

    async with session_factory() as session:
        async with session.begin():
            token, pool = await collector.upsert_token_and_pool(session, sample_strong_token)
            assert token.address == sample_strong_token.token_address
            assert token.symbol == "STRONG"
            assert pool is not None
            assert pool.address == "PoolAddress111111111111111111111"

    # Upsert again with updated name/symbol
    sample_strong_token.symbol = "STRONG_V2"
    async with session_factory() as session:
        async with session.begin():
            token_updated, pool_updated = await collector.upsert_token_and_pool(session, sample_strong_token)
            assert token_updated.symbol == "STRONG_V2"
            assert token_updated.id == token.id


@pytest.mark.asyncio
async def test_deduplication_of_identical_snapshots(session_factory, sample_strong_token):
    """Ensure identical observations within window are deduplicated, but saved if changed."""
    provider = MockMarketDataProvider()
    collector = AutomatedDataCollector(
        session_factory=session_factory,
        provider=provider,
        dedupe_window_seconds=60,
    )

    # First insertion -> saved
    async with session_factory() as session:
        async with session.begin():
            s1 = await collector.store_snapshot(session, sample_strong_token)
            assert s1 is not None

    # Immediate second insertion with identical metrics -> skipped (deduplicated)
    async with session_factory() as session:
        async with session.begin():
            s2 = await collector.store_snapshot(session, sample_strong_token)
            assert s2 is None

    # Third insertion with price change -> saved
    sample_strong_token.price_usd = sample_strong_token.price_usd * 1.10
    async with session_factory() as session:
        async with session.begin():
            s3 = await collector.store_snapshot(session, sample_strong_token)
            assert s3 is not None

    # Total stored snapshots should be 2
    async with session_factory() as session:
        snaps = (await session.execute(select(MarketSnapshot))).scalars().all()
        assert len(snaps) == 2


@pytest.mark.asyncio
async def test_collect_snapshots_once_and_stats(session_factory, sample_strong_token, sample_weak_token):
    """Test full single-pass discovery and ingestion loop with stats verification."""
    provider = MockMarketDataProvider(initial_tokens=[sample_strong_token, sample_weak_token])

    collector = AutomatedDataCollector(
        session_factory=session_factory,
        provider=provider,
        dedupe_window_seconds=60,
    )

    stored = await collector.collect_snapshots_once(limit=10)
    assert len(stored) == 2

    stats = await collector.get_stats()
    assert stats["tokens"] == 2
    assert stats["market_snapshots"] == 2
    assert stats["data_sources"] == 1

    # Running again without metric changes deduplicates all
    stored_again = await collector.collect_snapshots_once(limit=10)
    assert len(stored_again) == 0

    stats_after = await collector.get_stats()
    assert stats_after["market_snapshots"] == 2


@pytest.mark.asyncio
async def test_async_rate_limiter():
    """Verify rate limiter allows requests up to capacity without waiting."""
    limiter = AsyncRateLimiter(max_rate_per_minute=600, burst_size=5)
    # Burst 5 immediately
    for _ in range(5):
        await limiter.acquire()
    assert limiter.tokens < 1.0


@pytest.mark.asyncio
async def test_execute_with_retry_transient_recovery():
    """Verify retry handler recovers from transient errors."""
    call_count = 0

    async def flaky_call():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            req = httpx.Request("GET", "https://example.com")
            resp = httpx.Response(500, request=req)
            raise httpx.HTTPStatusError("Server Error", request=req, response=resp)
        return "success"

    result = await execute_with_retry(
        flaky_call,
        max_retries=3,
        initial_delay=0.01,
        backoff_factor=1.5,
    )
    assert result == "success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_execute_with_retry_exhausted():
    """Verify retry handler raises when retries are exhausted."""
    async def always_fails():
        req = httpx.Request("GET", "https://example.com")
        resp = httpx.Response(503, request=req)
        raise httpx.HTTPStatusError("Service Unavailable", request=req, response=resp)

    with pytest.raises(httpx.HTTPStatusError):
        await execute_with_retry(
            always_fails,
            max_retries=2,
            initial_delay=0.01,
        )
