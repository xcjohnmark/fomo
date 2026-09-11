"""Verification of the Data Provider / Collector abstraction contract."""

import pytest
from collectors.base import BaseCollector
from collectors.mock_pump_collector import MockPumpCollector
from models.domain import NormalizedTokenData


@pytest.mark.asyncio
async def test_collector_contract_methods():
    """Verify that MockPumpCollector satisfies the BaseCollector contract."""
    collector: BaseCollector = MockPumpCollector()

    # 1. get_active_tokens returns a list of NormalizedTokenData
    tokens = await collector.get_active_tokens()
    assert isinstance(tokens, list)
    assert len(tokens) > 0
    for t in tokens:
        assert isinstance(t, NormalizedTokenData)
        assert t.market_cap >= 0.0
        assert t.liquidity >= 0.0
        assert 0.0 <= t.liquidity_ratio
        assert 0.0 <= t.buy_tx_ratio <= 100.0

    # 2. get_token_snapshot returns valid token snapshot
    target_addr = tokens[0].token_address
    snapshot = await collector.get_token_snapshot(target_addr)
    assert snapshot is not None
    assert snapshot.token_address == target_addr

    # 3. get_current_price returns a valid float price
    price = await collector.get_current_price(target_addr)
    assert price is not None
    assert price > 0.0

    # 4. health_check returns bool
    healthy = await collector.health_check()
    assert healthy is True
