"""Unit tests for the StatisticalEngine, all 13 breakdown dimensions, and /stats views."""

from datetime import datetime, timezone
import pytest

from models.db import StrategyCall
from models.domain import CallOutcomeStatus, CallResult
from services.statistical_engine import StatisticalEngine
from telegram.formatter import format_stats_message
from telegram.keyboards import get_stats_keyboard


def create_mock_call(
    call_id: str,
    timestamp: datetime,
    score: float = 88.0,
    mc: float = 180_000.0,
    liq: float = 30_000.0,
    vol_5m: float = 15_000.0,
    m5: float = 8.5,
    m1h: float = 25.0,
    token_age: int = 7200,
    top10: float = 28.0,
    bs_ratio: float = 1.6,
    buysell_ratio: float = 1.8,
    market_condition: str = "CONTINUATION",
    return_pct: float = 30.0,
    holding_sec: int = 1200,
    result: str = "TARGET_HIT",
    exit_reason: Optional[str] = None,
    mfe: float = 35.0,
    mae: float = -2.0,
    status: str = CallOutcomeStatus.RESOLVED.value,
) -> StrategyCall:
    """Helper to construct fully populated StrategyCall objects for research testing."""
    resolved_exit_reason = exit_reason if exit_reason is not None else result
    return StrategyCall(
        call_id=call_id,
        timestamp=timestamp,
        token_ca="TokenCA111111111111111111111111111111111111",
        chain="solana",
        symbol="TEST",
        strategy_version="v1.0",
        momentum_score=score,
        entry_price=0.000100,
        entry_market_cap=mc,
        entry_liquidity=liq,
        entry_5m_change_pct=m5,
        entry_1h_change_pct=m1h,
        entry_volume_5m=vol_5m,
        entry_volume_status="ACCELERATING",
        top10_concentration=top10,
        entry_token_age_seconds=token_age,
        entry_buyer_seller_ratio=bs_ratio,
        entry_buy_sell_ratio=buysell_ratio,
        entry_market_condition=market_condition,
        outcome_status=status,
        result=result,
        exit_reason=resolved_exit_reason,
        return_percentage=return_pct,
        holding_time=holding_sec,
        max_favorable_excursion=mfe,
        max_adverse_excursion=mae,
    )


def test_core_metrics_calculation():
    """Verify exact calculation of win rate, loss rate, averages, medians, expectancy, MFE, MAE, and holding times."""
    t0 = datetime(2026, 9, 11, 14, 0, 0, tzinfo=timezone.utc)
    calls = [
        # Call 1: +50% Win, 20 min hold, target hit
        create_mock_call(
            "c1", t0, return_pct=50.0, holding_sec=1200, result="TARGET_HIT", mfe=55.0, mae=-2.0
        ),
        # Call 2: +30% Win, 10 min hold, target hit
        create_mock_call(
            "c2", t0, return_pct=30.0, holding_sec=600, result="TARGET_HIT", mfe=35.0, mae=-1.0
        ),
        # Call 3: -20% Loss, 30 min hold, invalidated
        create_mock_call(
            "c3", t0, return_pct=-20.0, holding_sec=1800, result="INVALIDATED", mfe=5.0, mae=-20.0
        ),
        # Call 4: -10% Loss, 40 min hold, timeout
        create_mock_call(
            "c4", t0, return_pct=-10.0, holding_sec=2400, result="TIME_EXIT", mfe=8.0, mae=-12.0
        ),
    ]

    summary = StatisticalEngine.calculate_cohort_summary(calls)

    assert summary["calls"] == 4
    assert summary["win_rate"] == 50.0
    assert summary["loss_rate"] == 50.0

    # Avg win = (50 + 30) / 2 = 40.0%, Avg loss = (20 + 10) / 2 = 15.0%
    assert summary["avg_win"] == 40.0
    assert summary["avg_loss"] == 15.0

    # Median win = 40.0%, Median loss = 15.0%
    assert summary["median_win"] == 40.0
    assert summary["median_loss"] == 15.0

    # Expectancy: (0.50 * 40.0) - (0.50 * 15.0) = 20.0 - 7.5 = +12.5%
    assert summary["expectancy"] == 12.5

    # Holding times: (20 + 10 + 30 + 40) / 4 = 25.0 min
    assert summary["avg_holding_time_min"] == 25.0
    assert summary["median_holding_time_min"] == 25.0

    # Resolution rates
    assert summary["target_hit_rate"] == 50.0
    assert summary["invalidation_rate"] == 25.0
    assert summary["timeout_rate"] == 25.0

    # Excursions
    assert summary["avg_mfe"] == round((55.0 + 35.0 + 5.0 + 8.0) / 4.0, 2)
    assert summary["max_mfe"] == 55.0
    assert summary["avg_mae"] == round((-2.0 + -1.0 + -20.0 + -12.0) / 4.0, 2)
    assert summary["max_mae"] == -20.0

    # Profit Factor = (50 + 30) / (20 + 10) = 80 / 30 = 2.67
    assert summary["profit_factor"] == 2.67


def test_max_drawdown_calculation():
    """Verify peak-to-trough cumulative drawdown calculation over sequential strategy calls."""
    t1 = datetime(2026, 9, 11, 10, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 9, 11, 11, 0, 0, tzinfo=timezone.utc)
    t3 = datetime(2026, 9, 11, 12, 0, 0, tzinfo=timezone.utc)
    t4 = datetime(2026, 9, 11, 13, 0, 0, tzinfo=timezone.utc)

    # Sequence: 100 -> +50% (150) -> -20% (120) -> -10% (108) -> +40% (151.2)
    # Peak is 150. Trough is 108.
    # Max DD = (150 - 108) / 150 = 42 / 150 = 28.0%
    calls = [
        create_mock_call("c1", t1, return_pct=50.0),
        create_mock_call("c2", t2, return_pct=-20.0),
        create_mock_call("c3", t3, return_pct=-10.0),
        create_mock_call("c4", t4, return_pct=40.0),
    ]

    max_dd = StatisticalEngine.calculate_max_drawdown(calls)
    assert max_dd == 28.0


def test_all_13_breakdown_dimensions_present():
    """Verify all 13 requested analytical dimensions are computed and populated."""
    t_fri = datetime(2026, 9, 11, 15, 30, 0, tzinfo=timezone.utc)  # Friday 15:30 (US Peak)
    t_sat = datetime(2026, 9, 12, 4, 0, 0, tzinfo=timezone.utc)   # Saturday 04:00 (Asian)

    call1 = create_mock_call(
        "c1",
        t_fri,
        score=93.0,
        mc=85_000.0,
        liq=12_000.0,
        vol_5m=3_000.0,
        m5=4.0,
        m1h=12.0,
        token_age=1800,
        top10=18.0,
        bs_ratio=0.8,
        buysell_ratio=0.9,
        market_condition="EARLY_MOMENTUM",
        return_pct=45.0,
    )
    call2 = create_mock_call(
        "c2",
        t_sat,
        score=87.0,
        mc=300_000.0,
        liq=50_000.0,
        vol_5m=25_000.0,
        m5=15.0,
        m1h=45.0,
        token_age=20000,
        top10=42.0,
        bs_ratio=1.7,
        buysell_ratio=2.0,
        market_condition="BREAKOUT",
        return_pct=-15.0,
    )

    metrics = StatisticalEngine.compute_all_metrics([call1, call2])
    breakdowns = metrics["breakdowns"]

    expected_dimensions = [
        "market_cap",
        "liquidity",
        "volume",
        "momentum_5m",
        "momentum_1h",
        "token_age",
        "top10_concentration",
        "buyer_seller_ratio",
        "buy_sell_ratio",
        "time_of_day",
        "day_of_week",
        "market_conditions",
        "strategy_score",
    ]

    for dim in expected_dimensions:
        assert dim in breakdowns, f"Missing dimension: {dim}"
        assert isinstance(breakdowns[dim], dict)
        assert len(breakdowns[dim]) > 0

    # Check specific cohort bucketings
    assert breakdowns["market_cap"]["Micro (<$100K)"]["calls"] == 1
    assert breakdowns["market_cap"]["Mid ($250K-$500K)"]["calls"] == 1

    assert breakdowns["time_of_day"]["US Peak (14:00-21:00)"]["calls"] == 1
    assert breakdowns["time_of_day"]["Asian (00:00-08:00)"]["calls"] == 1

    assert breakdowns["day_of_week"]["Friday"]["calls"] == 1
    assert breakdowns["day_of_week"]["Saturday"]["calls"] == 1

    assert breakdowns["market_conditions"]["EARLY_MOMENTUM"]["calls"] == 1
    assert breakdowns["market_conditions"]["BREAKOUT"]["calls"] == 1

    assert breakdowns["strategy_score"]["Score 90-100 (Strong)"]["calls"] == 1
    assert breakdowns["strategy_score"]["Score 85-89 (Watch)"]["calls"] == 1


def test_telegram_formatter_views_and_keyboards():
    """Verify format_stats_message renders core overview and all 4 breakdown tabs."""
    t0 = datetime(2026, 9, 11, 14, 0, 0, tzinfo=timezone.utc)
    call = create_mock_call("c1", t0, score=91.0, return_pct=35.0)

    full_metrics = StatisticalEngine.compute_all_metrics([call])
    payload = {
        "total_alerts": 1,
        "total_trades": 1,
        "winning_trades": 1,
        "losing_trades": 0,
        "avg_gain_pct": 35.0,
        "avg_loss_pct": 0.0,
        "profit_factor": 99.0,
        "invalidation_rate": 0.0,
        "research_database": full_metrics,
    }

    # 1. Overview
    overview_text = format_stats_message(payload, view="overview")
    assert "RESEARCH DATABASE & EXPECTANCY (OVERVIEW)" in overview_text
    assert "Core Performance Metrics:" in overview_text
    assert "Mathematical Expectancy:" in overview_text
    assert "Execution & Duration:" in overview_text
    assert "Risk & Excursion Profile:" in overview_text

    # 2. MC & Liq
    mc_liq_text = format_stats_message(payload, view="mc_liq")
    assert "BREAKDOWN: MARKET CAP & LIQUIDITY" in mc_liq_text
    assert "Market Cap Cohorts:" in mc_liq_text
    assert "Pool Liquidity Cohorts:" in mc_liq_text

    # 3. Momentum & Flow
    mom_text = format_stats_message(payload, view="momentum_flow")
    assert "BREAKDOWN: MOMENTUM & FLOW DYNAMICS" in mom_text
    assert "5-Minute Price Momentum:" in mom_text
    assert "1-Hour Price Momentum:" in mom_text
    assert "Buyer / Seller Ratio Breadth:" in mom_text

    # 4. Timing & Structure
    time_text = format_stats_message(payload, view="timing_structure")
    assert "BREAKDOWN: TIMING & MICROSTRUCTURE" in time_text
    assert "Time of Day (UTC Trading Sessions):" in time_text
    assert "Token Age at Setup:" in time_text
    assert "Top-10 Wallet Concentration:" in time_text

    # 5. Scores & Regimes
    scores_text = format_stats_message(payload, view="scores_regimes")
    assert "BREAKDOWN: SCORES & MARKET CONDITIONS" in scores_text
    assert "Momentum Strategy Score Tiers:" in scores_text

    # Verify keyboard generation
    kb = get_stats_keyboard(current_view="overview")
    assert len(kb.inline_keyboard) == 3
    assert "Overview (active)" in kb.inline_keyboard[0][0].text
    assert kb.inline_keyboard[0][1].callback_data == "stats:mc_liq"
