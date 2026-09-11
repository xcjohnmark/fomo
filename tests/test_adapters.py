"""Unit tests for DexScreener, Birdeye, and Composite adapters."""

import pytest
from collectors.birdeye_adapter import BirdeyeAdapter
from collectors.composite_adapter import CompositeMarketDataProvider
from collectors.dexscreener_adapter import DexScreenerAdapter
from collectors.mock_pump_collector import MockPumpCollector
from models.domain import TokenSnapshot


def test_dexscreener_adapter_normalization():
    """Verify DexScreener adapter maps available fields and marks unavailable ones as None."""
    mock_pair = {
        "chainId": "solana",
        "dexId": "raydium",
        "pairAddress": "PoolAddressRaydium111111111111111111111111",
        "baseToken": {
            "address": "TokenMint1111111111111111111111111111111111",
            "name": "Pepe Solana",
            "symbol": "PEPE",
        },
        "priceUsd": "0.00042",
        "txns": {
            "m5": {"buys": 15, "sells": 5},
            "h1": {"buys": 140, "sells": 60},
            "h6": {"buys": 300, "sells": 150},
            "h24": {"buys": 900, "sells": 400},
        },
        "volume": {
            "m5": 12500.0,
            "h1": 85000.0,
            "h6": 210000.0,
            "h24": 520000.0,
        },
        "priceChange": {
            "m5": 6.5,
            "h1": 15.2,
            "h6": 25.0,
            "h24": 65.0,
        },
        "liquidity": {
            "usd": 38000.0,
        },
        "fdv": 210000.0,
        "marketCap": 210000.0,
        "pairCreatedAt": 1726040000000,
    }

    adapter = DexScreenerAdapter()
    snapshot = adapter.normalize_pair(mock_pair)

    assert snapshot is not None
    assert snapshot.token_address == "TokenMint1111111111111111111111111111111111"
    assert snapshot.symbol == "PEPE"
    assert snapshot.price_usd == 0.00042
    assert snapshot.market_cap_usd == 210000.0
    assert snapshot.liquidity_usd == 38000.0
    assert snapshot.change_5m_pct == 6.5
    assert snapshot.change_1h_pct == 15.2
    assert snapshot.change_24h_pct == 65.0
    assert snapshot.volume_5m_usd == 12500.0
    assert snapshot.volume_1h_usd == 85000.0
    assert snapshot.buys == 140
    assert snapshot.sells == 60
    assert snapshot.token_age_seconds is not None

    # STRICT CHECK: DexScreener does not provide 4h, unique buyers/sellers, holders, or top10%
    assert snapshot.change_4h_pct is None
    assert snapshot.buyers is None
    assert snapshot.sellers is None
    assert snapshot.holders_count is None
    assert snapshot.top10_holder_pct is None


def test_birdeye_adapter_normalization():
    """Verify Birdeye adapter normalizes overview and security payloads."""
    mock_overview = {
        "data": {
            "address": "BirdeyeMint2222222222222222222222222222222",
            "symbol": "BIRD",
            "name": "Bird Token",
            "price": 0.0012,
            "mc": 450000.0,
            "liquidity": 75000.0,
            "priceChange5mPercent": 5.1,
            "priceChange1hPercent": 14.2,
            "priceChange4hPercent": 32.0,
            "priceChange24hPercent": 55.0,
            "v5mUSD": 16000.0,
            "v1hUSD": 95000.0,
            "v24hUSD": 380000.0,
            "buy1h": 120,
            "sell1h": 45,
            "buyVolume1h": 65000.0,
            "sellVolume1h": 30000.0,
        }
    }

    mock_security = {
        "data": {
            "holder": 1420,
            "top10UserPercent": 0.195,  # 19.5%
        }
    }

    adapter = BirdeyeAdapter(api_key="mock_key")
    snapshot = adapter.normalize_birdeye_payload(mock_overview, mock_security)

    assert snapshot is not None
    assert snapshot.symbol == "BIRD"
    assert snapshot.change_4h_pct == 32.0
    assert snapshot.holders_count == 1420
    assert snapshot.top10_holder_pct == 19.5
    assert snapshot.buys == 120
    assert snapshot.sells == 45


@pytest.mark.asyncio
async def test_composite_provider_enrichment():
    """Verify CompositeMarketDataProvider merges primary market feed with enrichment data."""
    # Primary provider produces snapshot missing top10% and holders
    primary_snap = TokenSnapshot(
        token_address="CompositeMint33333333333333333333333333333",
        symbol="COMP",
        provider_source="primary_dex",
        price_usd=0.0005,
        market_cap_usd=200000.0,
        liquidity_usd=50000.0,
        change_5m_pct=8.0,
        change_1h_pct=20.0,
        volume_5m_usd=15000.0,
        volume_1h_usd=80000.0,
        buys=100,
        sells=40,
        top10_holder_pct=None,  # Missing from primary
        holders_count=None,     # Missing from primary
    )

    # Enrichment provider provides top 10% and holders
    enrichment_snap = TokenSnapshot(
        token_address="CompositeMint33333333333333333333333333333",
        provider_source="on_chain_rpc",
        top10_holder_pct=16.8,
        holders_count=1850,
    )

    primary_mock = MockPumpCollector(initial_tokens=[primary_snap])
    enricher_mock = MockPumpCollector(initial_tokens=[enrichment_snap])

    composite = CompositeMarketDataProvider(
        primary_provider=primary_mock,
        enrichment_provider=enricher_mock,
    )

    result = await composite.fetch_token_snapshot(primary_snap.token_address)

    assert result is not None
    assert result.symbol == "COMP"
    assert result.price_usd == 0.0005
    assert result.top10_holder_pct == 16.8
    assert result.holders_count == 1850
    assert "composite" in result.provider_source
