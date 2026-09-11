"""Unit tests for the deterministic 100-point momentum scoring engine strictly consuming TokenSnapshot."""

import pytest
from models.domain import TokenSnapshot
from strategy.scoring import MomentumScorer


def test_strong_candidate_scoring(sample_strong_token: TokenSnapshot):
    """Verify that a token with strong multi-timeframe alignment scores >= 85."""
    result = MomentumScorer.calculate_score(sample_strong_token)
    assert result.score >= 85.0
    assert "STRONG CANDIDATE" in result.status_summary

    # Check that individual breakdown values are within valid ranges
    b = result.breakdown
    assert 0 <= b.market_cap_score <= 5
    assert 0 <= b.liquidity_score <= 15
    assert 0 <= b.volume_score <= 15
    assert 0 <= b.price_momentum_score <= 20
    assert 0 <= b.buy_sell_pressure_score <= 15
    assert 0 <= b.buyer_seller_breadth_score <= 10
    assert 0 <= b.holders_score <= 5
    assert 0 <= b.top10_score <= 5
    assert 0 <= b.trader_activity_score <= 5
    assert 0 <= b.narrative_score <= 5
    assert len(b.unavailable_dimensions) == 0


def test_weak_candidate_scoring(sample_weak_token: TokenSnapshot):
    """Verify that a declining token with low liquidity scores poorly."""
    result = MomentumScorer.calculate_score(sample_weak_token)
    assert result.score < 50.0
    assert "WEAK" in result.status_summary or "REJECT" in result.status_summary


def test_rule_3_pump_already_reversing_penalized(sample_strong_token: TokenSnapshot):
    """Verify Rule 3: huge 24H gain does NOT compensate for negative short timeframes."""
    token = sample_strong_token.model_copy(
        update={
            "change_24h_pct": 1200.0,
            "change_4h_pct": 400.0,
            "change_1h_pct": -20.0,
            "change_5m_pct": -10.0,
        }
    )
    result = MomentumScorer.calculate_score(token)
    assert result.breakdown.price_momentum_score <= 4.0
    assert result.score < 85.0


def test_liquidity_scoring_bounds(sample_strong_token: TokenSnapshot):
    """Verify liquidity score responds properly to thin pool liquidity."""
    thin_token = sample_strong_token.model_copy(
        update={"liquidity_usd": 1500.0, "market_cap_usd": 150000.0}
    )
    result = MomentumScorer.calculate_score(thin_token)
    assert result.breakdown.liquidity_score <= 4.0


def test_scoring_with_missing_metrics_never_invents_data(sample_strong_token: TokenSnapshot):
    """Verify missing dimensions are assigned 0/neutral and tracked in unavailable_dimensions."""
    partial_token = sample_strong_token.model_copy(
        update={
            "top10_holder_pct": None,
            "holders_count": None,
            "buyers": None,
            "sellers": None,
        }
    )
    result = MomentumScorer.calculate_score(partial_token)
    b = result.breakdown
    assert b.top10_score == 0.0
    assert b.holders_score == 0.0
    assert b.buyer_seller_breadth_score == 0.0
    assert "top10_concentration" in b.unavailable_dimensions
    assert "holders" in b.unavailable_dimensions
    assert "buyer_seller_breadth" in b.unavailable_dimensions
    assert "top10_holder_pct" in result.missing_metrics
