"""Comprehensive unit tests for CallOutcomeMonitor (Phase 7 Call Recording & Phase 8 Outcome Monitor)."""

from datetime import datetime, timedelta, timezone
import pytest

from models.domain import (
    AlertCandidate,
    CallOutcomeStatus,
    CallResult,
    ConfirmationState,
    MomentumScoreResult,
    PlanStatus,
    PriceZone,
    QuickFlipPlan,
    ScoreBreakdown,
    ScoreTier,
    SetupClassification,
    TokenSnapshot,
)
from services.call_outcome_monitor import CallOutcomeMonitor


# =====================================================================
# Fixtures
# =====================================================================

@pytest.fixture
def sample_candidate() -> AlertCandidate:
    token = TokenSnapshot(
        token_address="TokenMintAddress1234567890abcdef12345678",
        symbol="PUMP",
        chain="solana",
        price_usd=1.00,
        market_cap_usd=100000.0,
        liquidity_usd=25000.0,
        change_5m_pct=8.5,
        change_1h_pct=22.0,
        volume_5m_usd=15000.0,
        buys=150,
        sells=90,
        buyers=120,
        sellers=75,
        top10_holder_pct=25.0,
        provider_source="dexscreener",
    )
    breakdown = ScoreBreakdown(
        market_cap_score=5.0,
        liquidity_score=15.0,
        volume_score=14.0,
        price_momentum_score=18.0,
        buy_sell_pressure_score=14.0,
        buyer_seller_breadth_score=9.0,
        holders_score=4.0,
        top10_score=4.0,
        trader_activity_score=4.0,
        narrative_score=4.0,
    )
    score_result = MomentumScoreResult(
        score=88.0,
        tier=ScoreTier.STRONG,
        classification=SetupClassification.CONTINUATION,
        status_summary="Strong continuation momentum",
        breakdown=breakdown,
    )
    plan = QuickFlipPlan(
        token_address=token.token_address,
        symbol=token.symbol,
        status=PlanStatus.READY,
        entry_price=1.00,
        entry_market_cap=100000.0,
        entry_zone=PriceZone(low=0.98, high=1.02, mid=1.00),
        target_price=1.30,
        target_market_cap=130000.0,
        target_percentage=30.0,
        target_zone=PriceZone(low=1.25, high=1.35, mid=1.30),
        invalidation_price=0.90,
        invalidation_market_cap=90000.0,
        invalidation_percentage=-10.0,
        risk_reward_ratio=3.0,
        expected_holding_minutes=20,
        risk_flags=["Volatility risk", "Top 10 concentration: 25%"],
        plan_reason="Clean continuation breakout",
    )
    return AlertCandidate(
        token=token,
        score_result=score_result,
        classification=SetupClassification.CONTINUATION,
        confirmation_state=ConfirmationState.CONFIRMED,
        alert_reason="5M momentum surge (+8.5%)",
        reasons=["5M momentum accelerating", "Buyers dominating"],
        risks=["Volatility risk", "Top 10 concentration: 25%"],
        confirmation_needed="Volume follow-through",
        invalidation_criteria="Below $0.90",
        next_action="Monitor entry",
        plan=plan,
    )


# =====================================================================
# Tests
# =====================================================================

@pytest.mark.asyncio
async def test_record_strategy_call_immutability(sample_candidate):
    """Verify permanent StrategyCall creation and immutable plan parameters."""
    monitor = CallOutcomeMonitor()
    call = await monitor.record_call(sample_candidate)

    assert call.call_id.startswith("call_")
    assert call.token_ca == sample_candidate.token.token_address
    assert call.symbol == "PUMP"
    assert call.entry_price == 1.00
    assert call.target_price == 1.30
    assert call.invalidation_price == 0.90
    assert call.expected_holding_minutes == 20
    assert call.outcome_status == CallOutcomeStatus.OPEN.value
    assert call.result is None
    assert call.max_favorable_excursion == 0.0
    assert call.max_adverse_excursion == 0.0

    # Verify immutable fields cannot be corrupted during an evaluation tick
    tick_time = call.timestamp + timedelta(minutes=5)
    updated = monitor.evaluate_tick(call, current_price=1.10, current_time=tick_time)

    assert updated.entry_price == 1.00
    assert updated.target_price == 1.30
    assert updated.invalidation_price == 0.90
    assert updated.expected_holding_minutes == 20
    assert updated.outcome_status == CallOutcomeStatus.OPEN.value
    assert updated.max_favorable_excursion == pytest.approx(10.0)


@pytest.mark.asyncio
async def test_target_first_scenario(sample_candidate):
    """Test scenario where price advances directly to profit target."""
    monitor = CallOutcomeMonitor()
    call = await monitor.record_call(sample_candidate)
    start_time = call.timestamp

    # Tick 1: Small bump after 2 min (+5%)
    t1 = start_time + timedelta(minutes=2)
    monitor.evaluate_tick(call, current_price=1.05, current_time=t1)
    assert call.outcome_status == CallOutcomeStatus.OPEN.value
    assert call.max_favorable_excursion == pytest.approx(5.0)

    # Tick 2: Reaches target 1.32 (+32%) after 8 min
    t2 = start_time + timedelta(minutes=8)
    resolved = monitor.evaluate_tick(call, current_price=1.32, current_time=t2)

    assert resolved.outcome_status == CallOutcomeStatus.RESOLVED.value
    assert resolved.result == CallResult.TARGET_HIT.value
    assert resolved.actual_exit_price == 1.32
    assert resolved.return_percentage == pytest.approx(32.0)
    assert resolved.time_to_target == 8 * 60
    assert resolved.holding_time == 8 * 60
    assert resolved.max_favorable_excursion == pytest.approx(32.0)
    assert "Reached target level" in resolved.exit_reason


@pytest.mark.asyncio
async def test_invalidation_first_strict_no_hindsight(sample_candidate):
    """Test scenario where price hits invalidation first, ensuring NO hindsight revision if price later pumps."""
    monitor = CallOutcomeMonitor()
    call = await monitor.record_call(sample_candidate)
    start_time = call.timestamp

    # Tick 1: Drops to 0.88 (-12%) after 5 min -> triggers invalidation stop
    t1 = start_time + timedelta(minutes=5)
    resolved = monitor.evaluate_tick(call, current_price=0.88, current_time=t1)

    assert resolved.outcome_status == CallOutcomeStatus.RESOLVED.value
    assert resolved.result == CallResult.INVALIDATED.value
    assert resolved.actual_exit_price == 0.88
    assert resolved.return_percentage == pytest.approx(-12.0)
    assert resolved.time_to_invalidation == 5 * 60
    assert resolved.holding_time == 5 * 60
    assert "Hit invalidation level" in resolved.exit_reason

    # Tick 2: 1 hour later, token pumps to $3.00 (+200% from entry)!
    # STRICT ANTI-HINDSIGHT RULE: The call must NOT be rewritten as a win.
    t2 = start_time + timedelta(hours=1)
    future_eval = monitor.evaluate_tick(resolved, current_price=3.00, current_time=t2)

    assert future_eval.outcome_status == CallOutcomeStatus.RESOLVED.value
    assert future_eval.result == CallResult.INVALIDATED.value
    assert future_eval.actual_exit_price == 0.88
    assert future_eval.return_percentage == pytest.approx(-12.0)
    assert future_eval.holding_time == 5 * 60


@pytest.mark.asyncio
async def test_timeout_time_exit_with_gain(sample_candidate):
    """Test timeout when holding window (2x expected) elapses with a partial positive return."""
    monitor = CallOutcomeMonitor()
    call = await monitor.record_call(sample_candidate)  # expected_holding_minutes = 20
    start_time = call.timestamp

    # After 45 minutes (>= 2x 20m), price is at 1.15 (+15%), didn't hit 1.30 or 0.90
    t_timeout = start_time + timedelta(minutes=45)
    resolved = monitor.evaluate_tick(call, current_price=1.15, current_time=t_timeout)

    assert resolved.outcome_status == CallOutcomeStatus.RESOLVED.value
    assert resolved.result == CallResult.TIME_EXIT.value
    assert resolved.actual_exit_price == 1.15
    assert resolved.return_percentage == pytest.approx(15.0)
    assert resolved.holding_time == 45 * 60
    assert "with partial gain" in resolved.exit_reason


@pytest.mark.asyncio
async def test_timeout_expired_loss_or_flat(sample_candidate):
    """Test timeout when holding window elapses with flat/negative return."""
    monitor = CallOutcomeMonitor()
    call = await monitor.record_call(sample_candidate)
    start_time = call.timestamp

    # After 42 minutes, price is at 0.96 (-4%), hasn't hit target (1.30) or invalidation (0.90)
    t_timeout = start_time + timedelta(minutes=42)
    resolved = monitor.evaluate_tick(call, current_price=0.96, current_time=t_timeout)

    assert resolved.outcome_status == CallOutcomeStatus.RESOLVED.value
    assert resolved.result == CallResult.EXPIRED.value
    assert resolved.actual_exit_price == 0.96
    assert resolved.return_percentage == pytest.approx(-4.0)
    assert resolved.holding_time == 42 * 60
    assert "without resolution" in resolved.exit_reason


@pytest.mark.asyncio
async def test_mfe_and_mae_tracking(sample_candidate):
    """Verify continuous tracking of Maximum Favorable Excursion and Maximum Adverse Excursion."""
    monitor = CallOutcomeMonitor()
    call = await monitor.record_call(sample_candidate)
    start_time = call.timestamp

    # Move up to 1.18 (+18%)
    monitor.evaluate_tick(call, current_price=1.18, current_time=start_time + timedelta(minutes=2))
    assert call.max_favorable_excursion == pytest.approx(18.0)
    assert call.max_adverse_excursion == pytest.approx(0.0)

    # Pullback down to 0.94 (-6%)
    monitor.evaluate_tick(call, current_price=0.94, current_time=start_time + timedelta(minutes=6))
    assert call.max_favorable_excursion == pytest.approx(18.0)
    assert call.max_adverse_excursion == pytest.approx(-6.0)

    # Rebound to 1.10 (+10%)
    monitor.evaluate_tick(call, current_price=1.10, current_time=start_time + timedelta(minutes=10))
    assert call.max_favorable_excursion == pytest.approx(18.0)
    assert call.max_adverse_excursion == pytest.approx(-6.0)


@pytest.mark.asyncio
async def test_data_error_handling(sample_candidate):
    """Verify non-positive or corrupted price data sets DATA_ERROR."""
    monitor = CallOutcomeMonitor()
    call = await monitor.record_call(sample_candidate)

    resolved = monitor.evaluate_tick(call, current_price=-0.5)
    assert resolved.outcome_status == CallOutcomeStatus.RESOLVED.value
    assert resolved.result == CallResult.DATA_ERROR.value
    assert "Invalid non-positive market price" in resolved.exit_reason


@pytest.mark.asyncio
async def test_research_statistics_aggregation(sample_candidate):
    """Verify statistical aggregation across a cohort of strategy calls."""
    monitor = CallOutcomeMonitor()

    # Call 1: Target hit (+30%) in 10 minutes
    c1 = await monitor.record_call(sample_candidate)
    monitor.evaluate_tick(c1, 1.30, current_time=c1.timestamp + timedelta(minutes=10))

    # Call 2: Invalidation (-10%) in 4 minutes
    c2 = await monitor.record_call(sample_candidate)
    monitor.evaluate_tick(c2, 0.90, current_time=c2.timestamp + timedelta(minutes=4))

    # Call 3: Time exit (+15%) in 40 minutes
    c3 = await monitor.record_call(sample_candidate)
    monitor.evaluate_tick(c3, 1.15, current_time=c3.timestamp + timedelta(minutes=40))

    # Call 4: Still OPEN
    await monitor.record_call(sample_candidate)

    stats = await monitor.get_research_statistics()

    assert stats["total_calls"] == 4
    assert stats["open_calls"] == 1
    assert stats["resolved_calls"] == 3
    assert stats["target_hit_count"] == 1
    assert stats["invalidated_count"] == 1
    assert stats["time_exit_count"] == 1
    assert stats["win_rate"] == pytest.approx(33.33, abs=0.1)
    assert stats["avg_time_to_target_minutes"] == pytest.approx(10.0)
    assert stats["avg_time_to_invalidation_minutes"] == pytest.approx(4.0)
    assert stats["profit_factor"] > 0
    assert stats["expectancy"] > 0
