"""Unit tests for QuickFlipTradePlanner and TargetSelector across all 7 strategy conditions."""

from datetime import datetime, timezone
import pytest

from models.domain import (
    ConfirmationState,
    PlanStatus,
    ScoreTier,
    SetupClassification,
    TokenSnapshot,
)
from strategy.engine import MomentumStrategyEngine
from strategy.trade_planner import QuickFlipTradePlanner


@pytest.fixture
def engine() -> MomentumStrategyEngine:
    return MomentumStrategyEngine()


# =====================================================================
# 1. Normal Setup
# =====================================================================
def test_normal_setup(engine: MomentumStrategyEngine):
    """High quality candidate with score >= 85 and healthy liquidity produces READY plan."""
    token = TokenSnapshot(
        token_address="NormSetup1111111111111111111111111111111",
        symbol="NORM",
        name="Normal Setup Token",
        market_cap_usd=250000.0,
        price_usd=0.00025,
        liquidity_usd=45000.0,
        change_5m_pct=5.5,
        change_1h_pct=18.0,
        change_4h_pct=35.0,
        volume_5m_usd=16000.0,
        volume_1h_usd=80000.0,
        buys=180,
        sells=60,
        buyers=140,
        sellers=50,
        holders_count=1600,
        top10_holder_pct=18.0,
        token_age_seconds=7200,
        trader_activity_summary="Multiple smart traders active and accumulating",
        narrative="AI meme trend breakout",
    )

    analysis = engine.analyze(token)
    assert analysis.score >= 85.0
    assert analysis.setup_state == ConfirmationState.CONFIRMED

    plan = QuickFlipTradePlanner.generate_plan(analysis, token)
    assert plan.status == PlanStatus.READY
    assert plan.entry_price == 0.00025
    assert plan.entry_market_cap == 250000.0
    assert plan.entry_zone is not None
    assert plan.entry_zone.low < plan.entry_price < plan.entry_zone.high

    # Target sanity: not arbitrary 2x, but realistic 15% to 35%
    assert plan.target_percentage is not None
    assert 15.0 <= plan.target_percentage <= 35.0
    assert plan.target_price is not None
    assert plan.target_price > plan.entry_price
    assert plan.target_market_cap > plan.entry_market_cap

    # Invalidation sanity: thesis failure 6% to 10% below entry
    assert plan.invalidation_percentage is not None
    assert 6.0 <= plan.invalidation_percentage <= 10.0
    assert plan.invalidation_price is not None
    assert plan.invalidation_price < plan.entry_price

    # Favorable R:R and short-term holding window
    assert plan.risk_reward_ratio is not None
    assert plan.risk_reward_ratio >= 1.8
    assert plan.expected_holding_minutes is not None
    assert 15 <= plan.expected_holding_minutes <= 35
    assert "R:R" in plan.plan_reason


# =====================================================================
# 2. Extended Setup (Do Not Chase)
# =====================================================================
def test_extended_setup(engine: MomentumStrategyEngine):
    """Vertical move (+25% 5M) marked as EXTENDED to prevent chasing."""
    token = TokenSnapshot(
        token_address="ExtSetup22222222222222222222222222222222",
        symbol="EXT",
        market_cap_usd=300000.0,
        price_usd=0.0003,
        liquidity_usd=50000.0,
        change_5m_pct=26.0,  # overextended vertical jump
        change_1h_pct=40.0,
        volume_5m_usd=35000.0,
        volume_1h_usd=90000.0,
        buys=250,
        sells=50,
        buyers=180,
        sellers=40,
        holders_count=1800,
    )

    analysis = engine.analyze(token)
    assert analysis.is_overextended is True

    plan = QuickFlipTradePlanner.generate_plan(analysis, token)
    assert plan.status == PlanStatus.EXTENDED
    assert "overextended" in plan.plan_reason.lower()
    assert "do not chase" in plan.plan_reason.lower()
    assert plan.target_price is None


# =====================================================================
# 3. Weak Setup
# =====================================================================
def test_weak_setup(engine: MomentumStrategyEngine):
    """Low momentum candidate (Score < 55) returns NO_PLAN."""
    token = TokenSnapshot(
        token_address="WeakSetup3333333333333333333333333333333",
        symbol="WEAK",
        market_cap_usd=60000.0,
        price_usd=0.00006,
        liquidity_usd=12000.0,
        change_5m_pct=0.5,
        change_1h_pct=1.0,
        volume_5m_usd=400.0,
        volume_1h_usd=2000.0,
        buys=15,
        sells=25,
        buyers=10,
        sellers=20,
        holders_count=100,
    )

    analysis = engine.analyze(token)
    assert analysis.score < 55.0
    assert analysis.score_tier in (ScoreTier.WEAK, ScoreTier.REJECT)

    plan = QuickFlipTradePlanner.generate_plan(analysis, token)
    assert plan.status == PlanStatus.NO_PLAN
    assert "insufficient" in plan.plan_reason.lower()


# =====================================================================
# 4. Invalidated Setup
# =====================================================================
def test_invalidated_setup(engine: MomentumStrategyEngine):
    """Reversing pump or breakdown thesis returns NO_PLAN."""
    token = TokenSnapshot(
        token_address="InvalSetup444444444444444444444444444444",
        symbol="INVAL",
        market_cap_usd=400000.0,
        price_usd=0.0004,
        liquidity_usd=35000.0,
        change_5m_pct=-10.0,
        change_1h_pct=-22.0,
        change_4h_pct=180.0,
        change_24h_pct=600.0,  # collapsed pump
        volume_5m_usd=20000.0,
        volume_1h_usd=120000.0,
        buys=30,
        sells=190,
        buyers=25,
        sellers=150,
    )

    analysis = engine.analyze(token)
    assert analysis.setup_state in (ConfirmationState.INVALIDATED, ConfirmationState.WEAKENING)

    plan = QuickFlipTradePlanner.generate_plan(analysis, token)
    assert plan.status == PlanStatus.NO_PLAN
    assert "invalidated" in plan.plan_reason.lower() or "weakening" in plan.plan_reason.lower()


# =====================================================================
# 5. Insufficient Data
# =====================================================================
def test_insufficient_data(engine: MomentumStrategyEngine):
    """Missing essential price, MC, or liquidity returns NO_PLAN (never invent data)."""
    token = TokenSnapshot(
        token_address="MissingData5555555555555555555555555555",
        symbol="MISSING",
        market_cap_usd=None,  # missing MC!
        price_usd=0.0001,
        liquidity_usd=None,   # missing liquidity!
        change_5m_pct=8.0,
        change_1h_pct=20.0,
    )

    analysis = engine.analyze(token)
    plan = QuickFlipTradePlanner.generate_plan(analysis, token)
    assert plan.status == PlanStatus.NO_PLAN
    assert "Insufficient market data" in plan.plan_reason
    assert "never invent data" in plan.plan_reason.lower()


# =====================================================================
# 6. High-Volatility Setup (Young Token)
# =====================================================================
def test_high_volatility_setup(engine: MomentumStrategyEngine):
    """Very young token (15m old) with high 5m volatility produces plan with adjusted invalidation."""
    token = TokenSnapshot(
        token_address="HighVolSetup666666666666666666666666666",
        symbol="HVOL",
        market_cap_usd=140000.0,
        price_usd=0.00014,
        liquidity_usd=25000.0,
        change_5m_pct=16.0,  # high 5m volatility
        change_1h_pct=16.0,
        volume_5m_usd=20000.0,
        volume_1h_usd=20000.0,
        buys=140,
        sells=35,
        buyers=110,
        sellers=25,
        holders_count=350,
        token_age_seconds=900,  # 15 minutes old
        token_age_formatted="15m",
    )

    analysis = engine.analyze(token)
    plan = QuickFlipTradePlanner.generate_plan(analysis, token)

    assert plan.status == PlanStatus.READY
    # Dynamic target accounts for high volatility & elasticity
    assert plan.target_percentage is not None
    assert plan.target_percentage >= 20.0
    # Dynamic invalidation allows slightly wider room for young token volatility
    assert plan.invalidation_percentage is not None
    assert plan.invalidation_percentage >= 10.0
    # Expected holding period is quick (15m)
    assert plan.expected_holding_minutes == 15
    assert any("volatility" in f.lower() for f in plan.risk_flags)


# =====================================================================
# 7. Low-Liquidity Setup
# =====================================================================
def test_low_liquidity_setup(engine: MomentumStrategyEngine):
    """Low liquidity (< $5,000 or < 3% MC) returns NO_PLAN due to slippage hazard."""
    token = TokenSnapshot(
        token_address="LowLiqSetup7777777777777777777777777777",
        symbol="THIN",
        market_cap_usd=160000.0,
        price_usd=0.00016,
        liquidity_usd=3500.0,  # only $3,500 liquidity!
        change_5m_pct=14.0,
        change_1h_pct=30.0,
        volume_5m_usd=12000.0,
        volume_1h_usd=35000.0,
        buys=120,
        sells=25,
        buyers=90,
        sellers=20,
    )

    analysis = engine.analyze(token)
    plan = QuickFlipTradePlanner.generate_plan(analysis, token)

    assert plan.status == PlanStatus.NO_PLAN
    assert "slippage hazard" in plan.plan_reason.lower()
    assert any("liquidity" in f.lower() for f in plan.risk_flags)
