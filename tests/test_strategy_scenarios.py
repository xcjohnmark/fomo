"""Extensive unit test suite verifying all 18 strategy scenarios defined in STRATEGY.md."""

from datetime import datetime, timedelta, timezone
import pytest

from models.domain import (
    ConfirmationState,
    ScoreTier,
    SetupClassification,
    TokenSnapshot,
)
from strategy.engine import MomentumStrategyEngine


@pytest.fixture
def engine() -> MomentumStrategyEngine:
    return MomentumStrategyEngine()


# =====================================================================
# Scenario 1 — Strong Momentum Continuation (Section 42)
# =====================================================================
def test_scenario_01_strong_momentum_continuation(engine: MomentumStrategyEngine):
    """5M: +5%, 1H: +17%, 4H: +35%, 24H: +60%, increasing volume, healthy liquidity."""
    token = TokenSnapshot(
        token_address="Scen1MintAddress111111111111111111111111",
        symbol="SCEN1",
        name="Scenario 1 Token",
        market_cap_usd=200000.0,
        price_usd=0.0002,
        liquidity_usd=45000.0,
        change_5m_pct=5.0,
        change_1h_pct=17.0,
        change_4h_pct=35.0,
        change_24h_pct=60.0,
        volume_5m_usd=15000.0,
        volume_1h_usd=80000.0,
        volume_24h_usd=350000.0,
        buys=200,
        sells=80,
        buyers=150,
        sellers=60,
        holders_count=1500,
        top10_holder_pct=18.0,
        token_age_seconds=7200,
        token_age_formatted="2h 00m",
        trader_activity_summary="Multiple smart traders active and accumulating",
        narrative="Viral meme trend breakout",
    )

    analysis = engine.analyze(token)
    assert analysis.score >= 85.0
    assert analysis.score_tier == ScoreTier.STRONG
    assert analysis.classification == SetupClassification.CONTINUATION
    assert analysis.setup_state == ConfirmationState.CONFIRMED
    assert not analysis.is_overextended
    assert len(analysis.reasons) >= 2


# =====================================================================
# Scenario 2 — Huge 24H Pump, Current Collapse (Section 43)
# =====================================================================
def test_scenario_02_huge_24h_pump_current_collapse(engine: MomentumStrategyEngine):
    """24H: +700%, 4H: +300%, 1H: -25%, 5M: -12%. Reversal/exhaustion warning."""
    token = TokenSnapshot(
        token_address="Scen2MintAddress222222222222222222222222",
        symbol="SCEN2",
        market_cap_usd=400000.0,
        price_usd=0.0004,
        liquidity_usd=30000.0,
        change_5m_pct=-12.0,
        change_1h_pct=-25.0,
        change_4h_pct=300.0,
        change_24h_pct=700.0,
        volume_5m_usd=25000.0,
        volume_1h_usd=150000.0,
        volume_24h_usd=1200000.0,
        buys=40,
        sells=220,
        buyers=30,
        sellers=180,
        holders_count=1100,
        top10_holder_pct=42.0,
        token_age_seconds=28800,
    )

    analysis = engine.analyze(token)
    assert analysis.score <= 40.0
    assert analysis.score_tier == ScoreTier.REJECT
    assert analysis.classification == SetupClassification.EXHAUSTION
    assert analysis.setup_state in (ConfirmationState.INVALIDATED, ConfirmationState.WEAKENING)
    assert any("Reversal warning" in w for w in analysis.warnings)


# =====================================================================
# Scenario 3 — Price Rising but Volume Falling (Section 44)
# =====================================================================
def test_scenario_03_price_rising_volume_falling(engine: MomentumStrategyEngine):
    """5M: +6%, 1H: +15%, 5M Volume falling, buyers stagnant, sellers increasing."""
    now = datetime.now(timezone.utc)
    t0 = TokenSnapshot(
        token_address="Scen3MintAddress333333333333333333333333",
        symbol="SCEN3",
        timestamp=now - timedelta(minutes=5),
        market_cap_usd=250000.0,
        price_usd=0.00025,
        liquidity_usd=40000.0,
        change_5m_pct=4.0,
        change_1h_pct=10.0,
        volume_5m_usd=30000.0,
        volume_1h_usd=80000.0,
        buyers=100,
        sellers=40,
    )
    t1 = TokenSnapshot(
        token_address="Scen3MintAddress333333333333333333333333",
        symbol="SCEN3",
        timestamp=now,
        market_cap_usd=265000.0,
        price_usd=0.000265,
        liquidity_usd=40000.0,
        change_5m_pct=6.0,
        change_1h_pct=15.0,
        volume_5m_usd=12000.0,  # volume fell sharply
        volume_1h_usd=92000.0,
        buyers=95,  # buyers fell
        sellers=60,  # sellers increased
    )

    analysis = engine.analyze([t0, t1])
    assert any("rising while volume is falling" in w for w in analysis.warnings)
    assert analysis.setup_state == ConfirmationState.WEAKENING


# =====================================================================
# Scenario 4 — Huge Volume but Sellers Dominate (Section 45)
# =====================================================================
def test_scenario_04_huge_volume_sellers_dominate(engine: MomentumStrategyEngine):
    """24H Vol extremely high, Buys: 4000, Sells: 4500, Buy Vol: $300K, Sell Vol: $600K."""
    token = TokenSnapshot(
        token_address="Scen4MintAddress444444444444444444444444",
        symbol="SCEN4",
        market_cap_usd=800000.0,
        price_usd=0.0008,
        liquidity_usd=60000.0,
        change_5m_pct=-1.5,
        change_1h_pct=2.0,
        change_24h_pct=80.0,
        volume_5m_usd=50000.0,
        volume_1h_usd=250000.0,
        volume_24h_usd=2500000.0,
        buys=4000,
        sells=4500,
        buy_volume_usd=300000.0,
        sell_volume_usd=600000.0,  # heavy sell volume dominance
        buyers=1200,
        sellers=1400,
    )

    analysis = engine.analyze(token)
    assert analysis.score_breakdown["buy_sell_pressure"] <= 3.0
    assert any("Distribution risk" in w for w in analysis.warnings)
    assert analysis.setup_state != ConfirmationState.CONFIRMED


# =====================================================================
# Scenario 5 — Low Liquidity Explosive Move (Section 46)
# =====================================================================
def test_scenario_05_low_liquidity_explosive_move(engine: MomentumStrategyEngine):
    """Market Cap: $150K, Liquidity: $5K, 5M: +18%, Volume increasing, Buyers increasing."""
    token = TokenSnapshot(
        token_address="Scen5MintAddress555555555555555555555555",
        symbol="SCEN5",
        market_cap_usd=150000.0,
        price_usd=0.00015,
        liquidity_usd=5000.0,  # 3.3% liquidity ratio!
        change_5m_pct=18.0,
        change_1h_pct=40.0,
        volume_5m_usd=15000.0,
        volume_1h_usd=40000.0,
        buys=150,
        sells=40,
        buyers=120,
        sellers=30,
        holders_count=400,
    )

    analysis = engine.analyze(token)
    assert analysis.score_breakdown["liquidity"] <= 7.0
    assert any("Execution slippage risk" in w for w in analysis.warnings)


# =====================================================================
# Scenario 6 — High Liquidity but No Momentum (Section 47)
# =====================================================================
def test_scenario_06_high_liquidity_no_momentum(engine: MomentumStrategyEngine):
    """Market Cap: $20M, Liquidity: $3M, 5M: +0.2%, 1H: -0.4%, 4H: +1%, Volume stable."""
    token = TokenSnapshot(
        token_address="Scen6MintAddress666666666666666666666666",
        symbol="SCEN6",
        market_cap_usd=20000000.0,
        price_usd=0.02,
        liquidity_usd=3000000.0,
        change_5m_pct=0.2,
        change_1h_pct=-0.4,
        change_4h_pct=1.0,
        change_24h_pct=3.0,
        volume_5m_usd=5000.0,
        volume_1h_usd=25000.0,
        buys=30,
        sells=32,
        buyers=25,
        sellers=28,
        holders_count=8000,
    )

    analysis = engine.analyze(token)
    assert analysis.score_breakdown["price_momentum"] <= 4.0
    assert analysis.score <= 54.0
    assert analysis.score_tier in (ScoreTier.WEAK, ScoreTier.REJECT)


# =====================================================================
# Scenario 7 — Early Breakout (Section 48)
# =====================================================================
def test_scenario_07_early_breakout(engine: MomentumStrategyEngine):
    """5M: +9%, 1H: +4%, 4H: -2%, 24H: +8%, 5M volume suddenly increasing, buyers increasing."""
    token = TokenSnapshot(
        token_address="Scen7MintAddress777777777777777777777777",
        symbol="SCEN7",
        market_cap_usd=120000.0,
        price_usd=0.00012,
        liquidity_usd=25000.0,
        change_5m_pct=9.0,
        change_1h_pct=4.0,
        change_4h_pct=-2.0,
        change_24h_pct=8.0,
        volume_5m_usd=12000.0,  # 10% of MC in 5 minutes!
        volume_1h_usd=18000.0,
        buys=90,
        sells=25,
        buyers=75,
        sellers=20,
        holders_count=600,
    )

    analysis = engine.analyze(token)
    assert analysis.classification in (SetupClassification.EARLY_MOMENTUM, SetupClassification.BREAKOUT)
    assert analysis.setup_state == ConfirmationState.DEVELOPING


# =====================================================================
# Scenario 8 — Pullback With Healthy Structure (Section 49)
# =====================================================================
def test_scenario_08_pullback_with_healthy_structure(engine: MomentumStrategyEngine):
    """Initial move +40%, then 5M: -4%, 1H: +15%, selling volume declines, buyers remain active."""
    token = TokenSnapshot(
        token_address="Scen8MintAddress888888888888888888888888",
        symbol="SCEN8",
        market_cap_usd=300000.0,
        price_usd=0.0003,
        liquidity_usd=55000.0,
        change_5m_pct=-4.0,
        change_1h_pct=15.0,
        change_4h_pct=40.0,
        change_24h_pct=75.0,
        volume_5m_usd=8000.0,
        volume_1h_usd=90000.0,
        buys=80,
        sells=50,
        buyers=65,
        sellers=40,
        holders_count=1600,
    )

    analysis = engine.analyze(token)
    assert analysis.classification == SetupClassification.PULLBACK_CONTINUATION
    assert analysis.setup_state == ConfirmationState.DEVELOPING
    assert "renewed buying confirmation" in analysis.next_action.lower()


# =====================================================================
# Scenario 9 — High Buyer Count but Large Seller Volume (Section 50)
# =====================================================================
def test_scenario_09_high_buyer_count_large_seller_volume(engine: MomentumStrategyEngine):
    """Buyers: 1500, Sellers: 500, but Buy Volume: $100K, Sell Volume: $500K."""
    token = TokenSnapshot(
        token_address="Scen9MintAddress999999999999999999999999",
        symbol="SCEN9",
        market_cap_usd=500000.0,
        price_usd=0.0005,
        liquidity_usd=50000.0,
        change_5m_pct=-2.0,
        change_1h_pct=5.0,
        buyers=1500,
        sellers=500,
        buy_volume_usd=100000.0,
        sell_volume_usd=500000.0,  # overwhelming seller volume
        buys=1600,
        sells=600,
    )

    analysis = engine.analyze(token)
    assert analysis.score_breakdown["buy_sell_pressure"] <= 3.0
    assert any("overwhelmed by large seller volume" in w for w in analysis.warnings)


# =====================================================================
# Scenario 10 — Strong Narrative, Weak Market (Section 51)
# =====================================================================
def test_scenario_10_strong_narrative_weak_market(engine: MomentumStrategyEngine):
    """Viral narrative, but 5M: -5%, 1H: -12%, volume declining, sellers > buyers."""
    token = TokenSnapshot(
        token_address="Scen10MintAddress101010101010101010101010",
        symbol="SCEN10",
        market_cap_usd=150000.0,
        price_usd=0.00015,
        liquidity_usd=20000.0,
        change_5m_pct=-5.0,
        change_1h_pct=-12.0,
        volume_5m_usd=2000.0,
        volume_1h_usd=10000.0,
        buys=15,
        sells=60,
        buyers=12,
        sellers=50,
        narrative="Extremely popular viral meme AI trend",
    )

    analysis = engine.analyze(token)
    assert analysis.score <= 45.0
    assert analysis.score_tier in (ScoreTier.WEAK, ScoreTier.REJECT)
    assert any("Narrative divergence" in w for w in analysis.warnings)


# =====================================================================
# Scenario 11 — Strong Trader Activity but Late Entry (Section 52)
# =====================================================================
def test_scenario_11_strong_trader_activity_late_entry(engine: MomentumStrategyEngine):
    """Smart trader entered, price +20%, then 5M momentum slowing, selling increasing."""
    token = TokenSnapshot(
        token_address="Scen11MintAddress111111111111111111111111",
        symbol="SCEN11",
        market_cap_usd=300000.0,
        price_usd=0.0003,
        liquidity_usd=35000.0,
        change_5m_pct=2.0,
        change_1h_pct=22.0,
        change_4h_pct=50.0,
        volume_5m_usd=12000.0,
        volume_1h_usd=90000.0,
        buys=80,
        sells=90,
        buyers=70,
        sellers=80,
        trader_activity_summary="Smart trader entered earlier, momentum now slowing and selling increasing",
    )

    analysis = engine.analyze(token)
    assert any("do not chase" in w.lower() for w in analysis.warnings)
    assert analysis.setup_state in (ConfirmationState.WEAKENING, ConfirmationState.DEVELOPING)


# =====================================================================
# Scenario 12 — Healthy Momentum but High Top-10 Concentration (Section 53)
# =====================================================================
def test_scenario_12_healthy_momentum_high_top10_concentration(engine: MomentumStrategyEngine):
    """5M: +7%, 1H: +22%, volume increasing, buyers > sellers, liquidity healthy, Top 10: 55%."""
    token = TokenSnapshot(
        token_address="Scen12MintAddress121212121212121212121212",
        symbol="SCEN12",
        market_cap_usd=250000.0,
        price_usd=0.00025,
        liquidity_usd=40000.0,
        change_5m_pct=7.0,
        change_1h_pct=22.0,
        volume_5m_usd=20000.0,
        volume_1h_usd=85000.0,
        buys=180,
        sells=70,
        buyers=140,
        sellers=50,
        holders_count=1200,
        top10_holder_pct=55.0,  # High concentration
    )

    analysis = engine.analyze(token)
    assert analysis.score_breakdown["top_10_concentration"] <= 2.5
    assert any("Concentration risk" in w for w in analysis.warnings)


# =====================================================================
# Scenario 13 — Very Young Coin (Section 54)
# =====================================================================
def test_scenario_13_very_young_coin(engine: MomentumStrategyEngine):
    """Age: 15 minutes, 5M: +20%, volume rapidly increasing, liquidity moderate."""
    token = TokenSnapshot(
        token_address="Scen13MintAddress131313131313131313131313",
        symbol="SCEN13",
        token_age_seconds=900,
        token_age_formatted="15m",
        market_cap_usd=120000.0,
        price_usd=0.00012,
        liquidity_usd=22000.0,
        change_5m_pct=20.0,
        change_1h_pct=20.0,
        volume_5m_usd=18000.0,
        volume_1h_usd=18000.0,
        buys=120,
        sells=30,
        buyers=95,
        sellers=20,
        holders_count=280,
    )

    analysis = engine.analyze(token)
    assert analysis.classification == SetupClassification.EARLY_MOMENTUM
    assert any("Young token risk" in w for w in analysis.warnings)
    assert analysis.setup_state == ConfirmationState.DEVELOPING


# =====================================================================
# Scenario 14 — Mature Coin Suddenly Accelerates (Section 55)
# =====================================================================
def test_scenario_14_mature_coin_suddenly_accelerates(engine: MomentumStrategyEngine):
    """Age: 3 months, MC: $2M, previously flat, now 5M: +8%, volume rapidly increasing."""
    token = TokenSnapshot(
        token_address="Scen14MintAddress141414141414141414141414",
        symbol="SCEN14",
        token_age_seconds=7776000,  # 90 days
        token_age_formatted="90d",
        market_cap_usd=2000000.0,
        price_usd=0.002,
        liquidity_usd=300000.0,
        change_5m_pct=8.0,
        change_1h_pct=9.0,
        volume_5m_usd=80000.0,
        volume_1h_usd=90000.0,
        buys=350,
        sells=80,
        buyers=280,
        sellers=60,
        holders_count=4500,
        top10_holder_pct=15.0,
    )

    analysis = engine.analyze(token)
    assert analysis.classification in (SetupClassification.BREAKOUT, SetupClassification.EARLY_MOMENTUM)
    assert analysis.score >= 75.0


# =====================================================================
# Scenario 15 — Everything Looks Good Except 5M Momentum (Section 56)
# =====================================================================
def test_scenario_15_everything_looks_good_except_5m_momentum(engine: MomentumStrategyEngine):
    """MC suitable, liquidity strong, volume strong, holders healthy, 5M: -1%, 1H: +15%, 4H: +30%."""
    token = TokenSnapshot(
        token_address="Scen15MintAddress151515151515151515151515",
        symbol="SCEN15",
        market_cap_usd=350000.0,
        price_usd=0.00035,
        liquidity_usd=60000.0,
        change_5m_pct=-1.0,  # slight pause
        change_1h_pct=15.0,
        change_4h_pct=30.0,
        change_24h_pct=50.0,
        volume_5m_usd=12000.0,
        volume_1h_usd=85000.0,
        buys=140,
        sells=70,
        buyers=110,
        sellers=55,
        holders_count=2000,
        top10_holder_pct=16.0,
        narrative="AI meme narrative",
    )

    analysis = engine.analyze(token)
    assert analysis.score_tier in (ScoreTier.WATCH, ScoreTier.STRONG)
    assert analysis.score >= 70.0
    assert analysis.classification == SetupClassification.PULLBACK_CONTINUATION
    assert analysis.setup_state == ConfirmationState.DEVELOPING


# =====================================================================
# Scenario 16 — Strong Price Increase With Weak Participation (Section 57)
# =====================================================================
def test_scenario_16_strong_price_increase_weak_participation(engine: MomentumStrategyEngine):
    """5M: +10%, 1H: +20%, but volume declining, buyers declining, sellers increasing."""
    now = datetime.now(timezone.utc)
    t0 = TokenSnapshot(
        token_address="Scen16MintAddress161616161616161616161616",
        symbol="SCEN16",
        timestamp=now - timedelta(minutes=5),
        market_cap_usd=200000.0,
        price_usd=0.0002,
        liquidity_usd=30000.0,
        change_5m_pct=5.0,
        volume_5m_usd=25000.0,
        buyers=120,
        sellers=40,
    )
    t1 = TokenSnapshot(
        token_address="Scen16MintAddress161616161616161616161616",
        symbol="SCEN16",
        timestamp=now,
        market_cap_usd=220000.0,
        price_usd=0.00022,
        liquidity_usd=30000.0,
        change_5m_pct=10.0,
        change_1h_pct=20.0,
        volume_5m_usd=8000.0,  # volume down
        buyers=70,  # buyers down
        sellers=65,  # sellers up
    )

    analysis = engine.analyze([t0, t1])
    assert any("Divergence warning" in w for w in analysis.warnings)
    assert analysis.setup_state == ConfirmationState.WEAKENING


# =====================================================================
# Scenario 17 — Strong Setup Suddenly Invalidated (Section 58)
# =====================================================================
def test_scenario_17_strong_setup_suddenly_invalidated(engine: MomentumStrategyEngine):
    """Prior snapshot had 5M: +8%, current snapshot has 5M: -6%, volume falling, sellers surging."""
    now = datetime.now(timezone.utc)
    t0 = TokenSnapshot(
        token_address="Scen17MintAddress171717171717171717171717",
        symbol="SCEN17",
        timestamp=now - timedelta(minutes=5),
        market_cap_usd=250000.0,
        price_usd=0.00025,
        liquidity_usd=40000.0,
        change_5m_pct=8.0,
        change_1h_pct=25.0,
        volume_5m_usd=30000.0,
        buys=180,
        sells=60,
    )
    t1 = TokenSnapshot(
        token_address="Scen17MintAddress171717171717171717171717",
        symbol="SCEN17",
        timestamp=now,
        market_cap_usd=220000.0,
        price_usd=0.00022,
        liquidity_usd=38000.0,
        change_5m_pct=-6.0,  # sharp flip from +8% to -6%
        change_1h_pct=10.0,
        volume_5m_usd=10000.0,
        buys=40,
        sells=150,
    )

    analysis = engine.analyze([t0, t1])
    assert analysis.setup_state == ConfirmationState.INVALIDATED
    assert "Invalidated" in analysis.next_action


# =====================================================================
# Scenario 18 — High Score but Bad Entry (Overextended) (Section 59)
# =====================================================================
def test_scenario_18_high_score_bad_entry_overextended(engine: MomentumStrategyEngine):
    """5M: +25% vertical candle in minutes, Score high (>=85), but candle is overextended."""
    token = TokenSnapshot(
        token_address="Scen18MintAddress181818181818181818181818",
        symbol="SCEN18",
        market_cap_usd=280000.0,
        price_usd=0.00028,
        liquidity_usd=50000.0,
        change_5m_pct=25.0,  # vertical jump
        change_1h_pct=35.0,
        volume_5m_usd=40000.0,
        volume_1h_usd=90000.0,
        buys=250,
        sells=50,
        buyers=180,
        sellers=40,
        holders_count=1800,
        top10_holder_pct=18.0,
    )

    analysis = engine.analyze(token)
    assert analysis.score >= 85.0
    assert analysis.is_overextended is True
    assert any("Overextended candle" in w for w in analysis.warnings)
    # Must NOT be CONFIRMED for immediate entry; must be DEVELOPING (wait for pullback)
    assert analysis.setup_state == ConfirmationState.DEVELOPING
    assert "do not chase" in analysis.next_action.lower()
