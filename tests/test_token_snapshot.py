"""Unit tests for TokenSnapshot schema, normalization, and missing-data handling."""

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError
from models.domain import TokenSnapshot


def test_token_snapshot_fully_populated():
    """Verify TokenSnapshot initialization with complete market data."""
    now = datetime.now(timezone.utc)
    snap = TokenSnapshot(
        token_address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        chain="solana",
        symbol="USDC",
        name="USD Coin",
        timestamp=now,
        provider_source="test_provider",
        price_usd=1.0,
        market_cap_usd=5000000.0,
        liquidity_usd=1000000.0,
        change_5m_pct=0.1,
        change_1h_pct=0.2,
        change_4h_pct=0.4,
        change_24h_pct=0.5,
        volume_5m_usd=50000.0,
        volume_1h_usd=200000.0,
        volume_24h_usd=1500000.0,
        buys=120,
        sells=80,
        buyers=95,
        sellers=65,
        holders_count=25000,
        top10_holder_pct=15.5,
        token_age_seconds=86400,
        token_age_formatted="1d 0h",
        trader_activity_summary="Healthy activity",
        narrative="Major stablecoin",
    )

    assert snap.token_address == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    assert snap.symbol == "USDC"
    assert snap.liquidity_ratio == 20.0
    assert snap.buy_tx_ratio == 60.0
    assert round(snap.buyer_ratio, 2) == 59.38
    assert len(snap.get_missing_fields()) == 0
    assert snap.is_available("price_usd") is True


def test_missing_data_strictly_none():
    """Verify Rule 1: missing data is None and never estimated or defaulted to 0."""
    snap = TokenSnapshot(
        token_address="MintWithoutMetrics1111111111111111111111111",
        price_usd=0.005,
    )

    # Missing metrics must be None
    assert snap.market_cap_usd is None
    assert snap.liquidity_usd is None
    assert snap.change_4h_pct is None
    assert snap.buyers is None
    assert snap.sellers is None
    assert snap.holders_count is None
    assert snap.top10_holder_pct is None

    # Computed properties must be None when prerequisites are missing
    assert snap.liquidity_ratio is None
    assert snap.buy_tx_ratio is None
    assert snap.buyer_ratio is None

    assert snap.is_available("change_4h_pct") is False
    missing = snap.get_missing_fields()
    assert "change_4h_pct" in missing
    assert "top10_holder_pct" in missing
    assert "holders_count" in missing


def test_zero_denominator_safety():
    """Verify computed ratios return None safely when total transactions or MC is zero."""
    snap = TokenSnapshot(
        token_address="ZeroTradeMint1111111111111111111111111111111",
        market_cap_usd=0.0,
        liquidity_usd=100.0,
        buys=0,
        sells=0,
        buyers=0,
        sellers=0,
    )

    assert snap.liquidity_ratio is None
    assert snap.buy_tx_ratio is None
    assert snap.buyer_ratio is None


def test_validation_constraints():
    """Verify pydantic enforces bounds (e.g. top10 % cannot exceed 100)."""
    with pytest.raises(ValidationError):
        TokenSnapshot(
            token_address="InvalidPctMint11111111111111111111111111111",
            top10_holder_pct=105.0,  # Invalid: > 100%
        )

    with pytest.raises(ValidationError):
        TokenSnapshot(
            token_address="NegativePriceMint11111111111111111111111111",
            price_usd=-1.5,  # Invalid: negative price
        )
