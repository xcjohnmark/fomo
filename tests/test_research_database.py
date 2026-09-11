"""Unit tests for Phase 10 Research Database and Expectancy Analysis."""

import json
from pathlib import Path
import tempfile
import pytest
import pandas as pd
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from models.db import Base, StrategyCall
from models.domain import CallOutcomeStatus, CallResult
from services.research_database import ResearchDatabaseService
from telegram.formatter import format_history_message, format_stats_message


@pytest.fixture
async def in_memory_db():
    """Create in-memory SQLite database engine and session factory."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    yield session_factory
    await engine.dispose()


@pytest.fixture
async def populated_db(in_memory_db):
    """Populate database with structured historical calls across score and MC tiers."""
    async with in_memory_db() as session:
        # Call 1: High Score Win (92/100, MC $150K)
        call1 = StrategyCall(
            call_id="call-001-win",
            token_ca="TokenCA111111111111111111111111111111111111",
            chain="solana",
            pool_address="Pool111111111111111111111111111111111111",
            symbol="ALPHA",
            strategy_version="1.0.0",
            momentum_score=92.0,
            setup_state="CONFIRMED",
            entry_price=0.000150,
            entry_market_cap=150000.0,
            entry_liquidity=32000.0,
            entry_5m_change_pct=12.5,
            entry_1h_change_pct=35.0,
            entry_volume_5m=18000.0,
            entry_volume_status="ACCELERATING",
            top10_concentration=24.5,
            entry_zone_low=0.000145,
            entry_zone_high=0.000155,
            target_price=0.000210,
            target_market_cap=210000.0,
            target_percentage=40.0,
            invalidation_price=0.000130,
            invalidation_market_cap=130000.0,
            expected_holding_minutes=30,
            reasons=["Volume expanding", "Buyers dominating"],
            risk_flags=["High short-term volatility"],
            # Outcome fields
            outcome_status=CallOutcomeStatus.RESOLVED.value,
            result=CallResult.TARGET_HIT.value,
            is_winning=True,
            actual_peak_price=0.000220,
            actual_peak_market_cap=220000.0,
            actual_low_price=0.000148,
            actual_exit_price=0.000210,
            time_to_target=18.0,
            time_to_invalidation=None,
            max_favorable_excursion=46.6,
            max_adverse_excursion=-1.3,
            return_percentage=40.0,
            holding_time=18.0,
            exit_reason="TARGET_HIT",
        )

        # Call 2: Mid Score Loss (86/100, MC $220K)
        call2 = StrategyCall(
            call_id="call-002-loss",
            token_ca="TokenCA222222222222222222222222222222222222",
            chain="solana",
            pool_address="Pool222222222222222222222222222222222222",
            symbol="BETA",
            strategy_version="1.0.0",
            momentum_score=86.0,
            setup_state="CONFIRMED",
            entry_price=0.000220,
            entry_market_cap=220000.0,
            entry_liquidity=25000.0,
            entry_5m_change_pct=8.0,
            entry_1h_change_pct=18.0,
            entry_volume_5m=9000.0,
            entry_volume_status="EXPANDING",
            top10_concentration=31.0,
            entry_zone_low=0.000215,
            entry_zone_high=0.000225,
            target_price=0.000330,
            target_market_cap=330000.0,
            target_percentage=50.0,
            invalidation_price=0.000176,
            invalidation_market_cap=176000.0,
            expected_holding_minutes=45,
            reasons=["5M momentum accelerating"],
            risk_flags=["Top-holder concentration: 31%"],
            # Outcome fields
            outcome_status=CallOutcomeStatus.RESOLVED.value,
            result=CallResult.INVALIDATED.value,
            is_winning=False,
            actual_peak_price=0.000230,
            actual_peak_market_cap=230000.0,
            actual_low_price=0.000175,
            actual_exit_price=0.000176,
            time_to_target=None,
            time_to_invalidation=22.0,
            max_favorable_excursion=4.5,
            max_adverse_excursion=-20.0,
            return_percentage=-20.0,
            holding_time=22.0,
            exit_reason="INVALIDATED",
        )

        # Call 3: Active Monitoring (Score 89, still open)
        call3 = StrategyCall(
            call_id="call-003-active",
            token_ca="TokenCA333333333333333333333333333333333333",
            chain="solana",
            pool_address="Pool333333333333333333333333333333333333",
            symbol="GAMMA",
            strategy_version="1.0.0",
            momentum_score=89.0,
            setup_state="CONFIRMED",
            entry_price=0.000100,
            entry_market_cap=100000.0,
            entry_liquidity=18000.0,
            entry_5m_change_pct=10.0,
            outcome_status=CallOutcomeStatus.OPEN.value,
            result=None,
            is_winning=None,
            return_percentage=None,
        )

        session.add_all([call1, call2, call3])
        await session.commit()

    return in_memory_db


@pytest.mark.asyncio
async def test_tripartite_records_structure(populated_db):
    """Verify ResearchDatabaseService builds exact Section 17 tripartite records."""
    service = ResearchDatabaseService(populated_db)
    records = await service.get_tripartite_records()

    assert len(records) == 3
    rec1 = next(r for r in records if r["call_id"] == "call-001-win")

    # 1. Top-level metadata
    assert rec1["symbol"] == "ALPHA"
    assert rec1["token_ca"] == "TokenCA111111111111111111111111111111111111"
    assert rec1["strategy_version"] == "1.0.0"

    # 2. What did we see?
    seen = rec1["what_did_we_see"]
    assert seen["score"] == 92.0
    assert seen["entry_market_cap_usd"] == 150000.0
    assert seen["entry_price_usd"] == 0.000150
    assert seen["liquidity_usd"] == 32000.0
    assert seen["change_5m_pct"] == 12.5
    assert seen["volume_status"] == "ACCELERATING"
    assert seen["top10_concentration_pct"] == 24.5
    assert "Volume expanding" in seen["reasons"]

    # 3. What was predicted?
    pred = rec1["what_was_predicted"]
    assert pred["target_market_cap"] == 210000.0
    assert pred["target_percentage"] == 40.0
    assert pred["invalidation_market_cap"] == 130000.0
    assert pred["expected_holding_minutes"] == 30

    # 4. What actually happened?
    happened = rec1["what_actually_happened"]
    assert happened["outcome_status"] == "RESOLVED"
    assert happened["result"] == "WIN"
    assert happened["is_winning"] is True
    assert happened["return_percentage"] == 40.0
    assert happened["actual_peak_market_cap"] == 220000.0
    assert happened["max_favorable_excursion"] == 46.6
    assert happened["exit_reason"] == "TARGET_HIT"


@pytest.mark.asyncio
async def test_empirical_expectancy_calculation(populated_db):
    """Verify deterministic mathematical expectancy calculation: E = (P_win * Avg Win) - (P_loss * Avg Loss)."""
    service = ResearchDatabaseService(populated_db)
    stats = await service.compute_empirical_expectancy()

    assert stats["total_calls"] == 3
    assert stats["resolved_calls"] == 2
    assert stats["winning_calls"] == 1
    assert stats["losing_calls"] == 1
    assert stats["empirical_win_rate"] == 50.0
    assert stats["avg_win_pct"] == 40.0
    assert stats["avg_loss_pct"] == 20.0

    # E = (0.50 * 40.0) - (0.50 * 20.0) = 20.0 - 10.0 = +10.0%
    assert stats["mathematical_expectancy_pct"] == 10.0
    # Profit factor = 40.0 / 20.0 = 2.00
    assert stats["profit_factor"] == 2.0

    # Test score tier segmentation
    tiers = stats["by_score_tier"]
    assert "90-100 (Strong)" in tiers
    assert tiers["90-100 (Strong)"]["win_rate"] == 100.0
    assert tiers["90-100 (Strong)"]["expectancy_pct"] == 40.0

    assert "85-89 (Watch)" in tiers
    assert tiers["85-89 (Watch)"]["win_rate"] == 0.0
    assert tiers["85-89 (Watch)"]["expectancy_pct"] == -20.0


@pytest.mark.asyncio
async def test_export_to_csv_and_json(populated_db):
    """Verify structured file export generates valid CSV and JSON documents."""
    service = ResearchDatabaseService(populated_db)

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "research_export.csv"
        json_path = Path(tmpdir) / "research_export.json"

        # Export CSV
        exported_csv = await service.export_to_csv(str(csv_path))
        assert exported_csv.exists()
        df_from_csv = pd.read_csv(exported_csv)
        assert len(df_from_csv) == 3
        assert "seen_score" in df_from_csv.columns
        assert "predicted_target_pct" in df_from_csv.columns
        assert "outcome_return_pct" in df_from_csv.columns

        # Export JSON
        exported_json = await service.export_to_json(str(json_path))
        assert exported_json.exists()
        with open(exported_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 3
        assert data[0]["symbol"] in ("ALPHA", "BETA", "GAMMA")
        assert "what_did_we_see" in data[0]


@pytest.mark.asyncio
async def test_get_dataframe(populated_db):
    """Verify get_dataframe returns a properly typed pandas DataFrame."""
    service = ResearchDatabaseService(populated_db)
    df = await service.get_dataframe()

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3
    assert set(["call_id", "symbol", "seen_score", "outcome_result"]).issubset(df.columns)


def test_telegram_formatters_tripartite_and_stats():
    """Verify Telegram formatting renders Section 17 format and expectancy correctly."""
    tripartite_alerts = [
        {
            "call_id": "call-123456-001",
            "symbol": "ALPHA",
            "what_did_we_see": {
                "score": 91.0,
                "entry_market_cap_usd": 120000.0,
                "liquidity_usd": 25000.0,
                "change_5m_pct": 12.0,
            },
            "what_was_predicted": {
                "target_percentage": 80.0,
                "target_market_cap": 216000.0,
                "invalidation_market_cap": 105000.0,
            },
            "what_actually_happened": {
                "outcome_status": "RESOLVED",
                "result": "WIN",
                "return_percentage": 80.0,
            },
        }
    ]

    hist_text = format_history_message(tripartite_alerts)
    assert "RESEARCH DATABASE — CALL HISTORY" in hist_text
    assert "$ALPHA" in hist_text
    assert "Seen: Score 91" in hist_text
    assert "MC $120K" in hist_text
    assert "Predicted: Target +80.0%" in hist_text
    assert "Outcome: WIN (+80.0%)" in hist_text

    # Stats with empirical expectancy
    stats_data = {
        "total_trades": 1,
        "winning_trades": 1,
        "losing_trades": 0,
        "profit_factor": 2.5,
        "research_database": {
            "total_calls": 25,
            "resolved_calls": 20,
            "empirical_win_rate": 65.0,
            "mathematical_expectancy_pct": 18.5,
            "profit_factor": 2.15,
            "avg_win_pct": 42.0,
            "avg_loss_pct": 15.0,
            "by_score_tier": {
                "90-100": {"win_rate": 75.0, "expectancy_pct": 28.0, "resolved_calls": 8}
            },
        },
    }

    stats_text = format_stats_message(stats_data)
    assert "RESEARCH DATABASE & EXPECTANCY" in stats_text
    assert "Total Calls Logged: 25" in stats_text
    assert "Empirical Win Rate: 65.0%" in stats_text
    assert "Mathematical Expectancy (E): +18.5% per call" in stats_text
    assert "90-100: WR 75.0% | E: +28.0% (8 calls)" in stats_text
