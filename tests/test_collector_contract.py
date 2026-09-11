"""Verification of the Data Provider / Collector abstraction contract."""

import pytest
from collectors.base import MarketDataProvider
from collectors.mock_pump_collector import MockPumpCollector
from models.domain import TokenSnapshot


@pytest.mark.asyncio
async def test_collector_contract_methods():
    """Verify that MockPumpCollector satisfies the MarketDataProvider contract."""
    collector: MarketDataProvider = MockPumpCollector()

    # 1. fetch_active_tokens returns a list of TokenSnapshot
    tokens = await collector.fetch_active_tokens()
    assert isinstance(tokens, list)
    assert len(tokens) > 0
    for t in tokens:
        assert isinstance(t, TokenSnapshot)
        assert t.market_cap_usd is not None and t.market_cap_usd >= 0.0
        assert t.liquidity_usd is not None and t.liquidity_usd >= 0.0
        assert t.liquidity_ratio is not None and 0.0 <= t.liquidity_ratio
        assert t.buy_tx_ratio is not None and 0.0 <= t.buy_tx_ratio <= 100.0

    # 2. fetch_token_snapshot returns valid TokenSnapshot
    target_addr = tokens[0].token_address
    snapshot = await collector.fetch_token_snapshot(target_addr)
    assert snapshot is not None
    assert snapshot.token_address == target_addr

    # 3. get_current_price returns a valid float price
    price = await collector.get_current_price(target_addr)
    assert price is not None
    assert price > 0.0

    # 4. health_check returns bool
    healthy = await collector.health_check()
    assert healthy is True
