"""Comprehensive unit tests for the Telegram bot, alert formatting, keyboards, paper trader, and callbacks."""

from datetime import datetime, timezone
import re
from typing import Any
from unittest.mock import AsyncMock, MagicMock
import pytest

from models.domain import (
    AlertCandidate,
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
from services.paper_trader import PaperTraderService
from services.watchlist import WatchlistService
from telegram.bot import TelegramBotService
from telegram.formatter import (
    fmt_compact_usd,
    fmt_pct,
    fmt_price,
    fmt_val,
    format_history_message,
    format_paper_message,
    format_scan_summary,
    format_settings_message,
    format_stats_message,
    format_status_message,
    format_telegram_alert,
    format_watchlist_message,
)
from telegram.keyboards import get_alert_keyboard, get_settings_keyboard


# =====================================================================
# Fixtures
# =====================================================================

@pytest.fixture
def sample_snapshot() -> TokenSnapshot:
    return TokenSnapshot(
        token_address="7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
        symbol="ABC",
        name="Alphabet Token",
        chain="solana",
        price_usd=0.000185,
        market_cap_usd=180000.0,
        liquidity_usd=35000.0,
        change_5m_pct=8.4,
        change_1h_pct=24.0,
        change_4h_pct=31.0,
        volume_5m_usd=25000.0,
        volume_1h_usd=60000.0,
        buys=318,
        sells=201,
        buyers=214,
        sellers=137,
        top10_holder_pct=28.0,
        provider_source="dexscreener",
    )


@pytest.fixture
def sample_candidate(sample_snapshot) -> AlertCandidate:
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
        token_address=sample_snapshot.token_address,
        symbol="ABC",
        status=PlanStatus.READY,
        entry_price=0.000185,
        entry_market_cap=180000.0,
        entry_zone=PriceZone(low=0.000180, high=0.000192, mid=0.000186),
        target_price=0.000320,
        target_market_cap=320000.0,
        target_percentage=77.0,
        target_zone=PriceZone(low=0.000300, high=0.000350, mid=0.000320),
        invalidation_price=0.000160,
        invalidation_market_cap=160000.0,
        invalidation_percentage=-13.5,
        risk_reward_ratio=5.7,
        expected_holding_minutes=35,
        risk_flags=["High short-term volatility", "Top-holder concentration: 28%"],
        plan_reason="Clean momentum continuation",
    )
    return AlertCandidate(
        token=sample_snapshot,
        score_result=score_result,
        classification=SetupClassification.CONTINUATION,
        confirmation_state=ConfirmationState.CONFIRMED,
        alert_reason="5M price acceleration (+8.4%) with strong flow",
        reasons=[
            "5M momentum accelerating",
            "Volume expanding",
            "Buyers dominating sellers",
            "Liquidity acceptable",
            "Participation increasing",
        ],
        risks=[
            "High short-term volatility",
            "Top-holder concentration: 28%",
            "Setup becomes weaker if volume collapses",
        ],
        confirmation_needed="Volume follow-through above $15K on next 5M bar",
        invalidation_criteria="5M price drops below $160K MC",
        next_action="Confirm and monitor entry zone",
        plan=plan,
    )


# =====================================================================
# 1. Standardized Alert Formatting Tests
# =====================================================================

def test_alert_formatting_matches_spec(sample_candidate):
    """Verify format matches Section 13 specification precisely."""
    alert_text = format_telegram_alert(sample_candidate)

    # Core headers and symbols
    assert "⚡ QUICK FLIP SETUP" in alert_text
    assert "$ABC" in alert_text
    assert f"CA: {sample_candidate.token.token_address}" in alert_text
    assert "Momentum Score: 88/100" in alert_text
    assert "Status: CONFIRMED" in alert_text

    # Micro-structure metrics
    assert "MC: $180K" in alert_text
    assert "Liquidity: $35K" in alert_text
    assert "5M: +8.4%" in alert_text
    assert "1H: +24.0%" in alert_text
    assert "4H: +31.0%" in alert_text

    # Flow and volume
    assert "Volume: ACCELERATING" in alert_text
    assert "Buyers/Sellers: 214 / 137" in alert_text
    assert "Buys/Sells: 318 / 201" in alert_text

    # Trade plan sections
    assert "ENTRY ZONE" in alert_text
    assert "TARGET" in alert_text
    assert "Potential:" in alert_text
    assert "INVALIDATION" in alert_text
    assert "Below $160K MC" in alert_text
    assert "EXPECTED HOLD" in alert_text

    # Rationale, risks, and disciplined plan
    assert "WHY" in alert_text
    assert "• 5M momentum accelerating" in alert_text
    assert "RISKS" in alert_text
    assert "• High short-term volatility" in alert_text
    assert "PLAN" in alert_text
    assert "Quick momentum flip." in alert_text
    assert "Not a long-term hold." in alert_text
    assert "Take profit into strength." in alert_text


def test_anti_hype_tone_guarantee(sample_candidate):
    """Ensure zero banned hype or certainty phrases are used."""
    alert_text = format_telegram_alert(sample_candidate).lower()

    banned_phrases = [
        "guaranteed",
        "100x",
        "free money",
        "easy profit",
        "will moon",
        "gem",
        "can't lose",
        "rocket",
    ]
    for phrase in banned_phrases:
        assert phrase not in alert_text, f"Banned hype phrase found: '{phrase}'"


def test_missing_data_formatting():
    """Ensure None values display safely as N/A without fabricating numbers."""
    bare_snapshot = TokenSnapshot(
        token_address="BareTokenAddress111111111111111111111111",
        chain="solana",
        # None for market_cap, liquidity, price, etc.
    )
    bare_candidate = AlertCandidate(
        token=bare_snapshot,
        score_result=MomentumScoreResult(
            score=86.0,
            tier=ScoreTier.STRONG,
            classification=SetupClassification.EARLY_MOMENTUM,
            status_summary="Developing setup",
            breakdown=ScoreBreakdown(
                market_cap_score=0.0,
                liquidity_score=0.0,
                volume_score=0.0,
                price_momentum_score=0.0,
                buy_sell_pressure_score=0.0,
                buyer_seller_breadth_score=0.0,
                holders_score=0.0,
                top10_score=0.0,
                trader_activity_score=0.0,
                narrative_score=0.0,
            ),
        ),
        classification=SetupClassification.EARLY_MOMENTUM,
        confirmation_state=ConfirmationState.DEVELOPING,
        alert_reason="Testing missing metrics",
        reasons=["Test rationale"],
        risks=["Test risk"],
        confirmation_needed="None",
        invalidation_criteria="None",
        next_action="Watch",
    )

    alert_text = format_telegram_alert(bare_candidate)
    assert "MC: N/A" in alert_text
    assert "Liquidity: N/A" in alert_text
    assert "5M: N/A" in alert_text
    assert "Buyers/Sellers: N/A / N/A" in alert_text


# =====================================================================
# 2. Keyboards Tests
# =====================================================================

def test_inline_keyboard_generation(sample_candidate):
    """Verify inline keyboard contains all 4 interactive buttons with correct parameters."""
    kb = get_alert_keyboard(sample_candidate.token.token_address, chain="solana")
    assert len(kb.inline_keyboard) == 2

    # Row 1: [View Token] [Watch]
    row1 = kb.inline_keyboard[0]
    assert row1[0].text == "🔍 View Token"
    assert sample_candidate.token.token_address in row1[0].url
    assert row1[1].text == "👀 Watch"
    assert row1[1].callback_data == f"watch:{sample_candidate.token.token_address}"

    # Row 2: [Paper Trade] [Ignore]
    row2 = kb.inline_keyboard[1]
    assert row2[0].text == "📝 Paper Trade"
    assert row2[0].callback_data == f"paper:{sample_candidate.token.token_address}"
    assert row2[1].text == "❌ Ignore"
    assert row2[1].callback_data == f"ignore:{sample_candidate.token.token_address}"


def test_settings_keyboard_generation():
    """Verify settings adjustment keyboard buttons."""
    kb = get_settings_keyboard({"alerts_paused": False})
    assert len(kb.inline_keyboard) == 2
    assert kb.inline_keyboard[0][0].text == "⏸️ Pause Alerts"
    assert kb.inline_keyboard[0][0].callback_data == "settings:toggle_pause"

    kb_paused = get_settings_keyboard({"alerts_paused": True})
    assert kb_paused.inline_keyboard[0][0].text == "▶️ Resume Alerts"


# =====================================================================
# 3. Paper Trader Service Tests
# =====================================================================

@pytest.mark.asyncio
async def test_paper_trader_lifecycle():
    """Test full paper trade simulation: open, target exit, loss stop, and stats."""
    trader = PaperTraderService()

    # 1. Open simulated winning trade
    trade1 = await trader.open_trade(
        token_address="TokenA",
        symbol="WIN",
        entry_price=1.0,
        entry_market_cap=100000.0,
        target_price=1.30,
        invalidation_price=0.90,
    )
    assert trade1.status == "OPEN"
    open_trades = await trader.get_open_trades()
    assert len(open_trades) == 1
    assert open_trades[0]["token_address"] == "TokenA"

    # Close with win (+30%)
    closed1 = await trader.close_trade("TokenA", exit_price=1.30, reason="TARGET_HIT")
    assert closed1 is not None
    assert closed1.status == "TARGET_HIT"
    assert closed1.pnl_pct == pytest.approx(30.0)

    # 2. Open simulated losing trade
    await trader.open_trade(
        token_address="TokenB",
        symbol="LOSS",
        entry_price=2.0,
        invalidation_price=1.80,
    )
    closed2 = await trader.close_trade("TokenB", exit_price=1.80, reason="INVALIDATED")
    assert closed2 is not None
    assert closed2.status == "INVALIDATED"
    assert closed2.pnl_pct == pytest.approx(-10.0)

    # 3. Performance stats
    stats = await trader.get_performance_stats()
    assert stats["total_trades"] == 2
    assert stats["winning_trades"] == 1
    assert stats["losing_trades"] == 1
    assert stats["avg_gain_pct"] == pytest.approx(30.0)
    assert stats["avg_loss_pct"] == pytest.approx(-10.0)
    assert stats["profit_factor"] == pytest.approx(3.0)
    assert stats["invalidation_rate"] == pytest.approx(50.0)


# =====================================================================
# 4. Watchlist Service Tests
# =====================================================================

@pytest.mark.asyncio
async def test_watchlist_service():
    """Test adding, checking, listing, and removing tokens from watchlist."""
    watchlist = WatchlistService()
    addr = "WatchToken111111111111111111111111"

    assert not await watchlist.is_watched(addr)

    # Add
    added = await watchlist.add_token(addr, symbol="WATCH")
    assert added is True
    assert await watchlist.is_watched(addr)

    tokens = await watchlist.get_watchlist()
    assert len(tokens) == 1
    assert tokens[0]["token_address"] == addr
    assert tokens[0]["symbol"] == "WATCH"

    # Remove
    removed = await watchlist.remove_token(addr)
    assert removed is True
    assert not await watchlist.is_watched(addr)


# =====================================================================
# 5. Interactive Bot Command Handlers Tests
# =====================================================================

@pytest.mark.asyncio
async def test_bot_commands_execution(sample_candidate):
    """Test all interactive bot command responses."""
    bot = TelegramBotService()

    # /start
    start_resp = await bot.start_command(None, None)
    assert "⚡ FOMO MOMENTUM RESEARCH BOT" in start_resp
    assert "/scan" in start_resp

    # /status
    status_resp = await bot.status_command(None, None)
    assert "SYSTEM OPERATIONAL STATUS" in status_resp
    assert "Min Score Cutoff: 85.0/100" in status_resp

    # /watch & /unwatch
    ctx_watch = MagicMock()
    ctx_watch.args = ["Mint123", "SOL"]
    watch_resp = await bot.watch_command(None, ctx_watch)
    assert "Added `Mint123`" in watch_resp

    ctx_unwatch = MagicMock()
    ctx_unwatch.args = ["Mint123"]
    unwatch_resp = await bot.unwatch_command(None, ctx_unwatch)
    assert "Removed `Mint123`" in unwatch_resp

    # /history
    history_resp = await bot.history_command(None, None)
    assert "ALERT HISTORY" in history_resp

    # /stats
    stats_resp = await bot.stats_command(None, None)
    assert "RESEARCH & PERFORMANCE STATS" in stats_resp

    # /paper
    paper_resp = await bot.paper_command(None, None)
    assert "SIMULATED PAPER TRADING" in paper_resp

    # /settings
    settings_resp = await bot.settings_command(None, None)
    assert "SYSTEM SETTINGS" in settings_resp


# =====================================================================
# 6. Interactive Callback Query Handlers Tests
# =====================================================================

@pytest.mark.asyncio
async def test_bot_callbacks():
    """Test interactive button callback reactions (watch, paper, ignore, settings)."""
    bot = TelegramBotService()

    # Mock Telegram Update & CallbackQuery
    update_mock = MagicMock()
    query_mock = AsyncMock()
    update_mock.callback_query = query_mock

    # 1. Test Watch callback
    query_mock.data = "watch:Token12345"
    res1 = await bot.button_callback(update_mock, None)
    assert res1 == "watched"
    assert await bot.watchlist.is_watched("Token12345")
    query_mock.answer.assert_called()

    # 2. Test Paper Trade callback
    query_mock.data = "paper:Token12345"
    res2 = await bot.button_callback(update_mock, None)
    assert res2 == "paper_opened"
    open_trades = await bot.paper_trader.get_open_trades()
    assert len(open_trades) == 1
    assert open_trades[0]["token_address"] == "Token12345"

    # 3. Test Ignore callback
    query_mock.data = "ignore:Token12345"
    res3 = await bot.button_callback(update_mock, None)
    assert res3 == "ignored"

    # 4. Test Settings Pause callback
    query_mock.data = "settings:toggle_pause"
    res4 = await bot.button_callback(update_mock, None)
    assert res4 == "settings_updated"
    assert bot.alerts_paused is True
