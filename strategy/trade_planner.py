"""Quick Flip Trade-Plan Engine calculating entry, target, invalidation, and holding periods."""

from datetime import datetime, timezone
import logging
from typing import List, Optional, Union

from models.domain import (
    ConfirmationState,
    MomentumAnalysis,
    PlanStatus,
    PriceZone,
    QuickFlipPlan,
    ScoreTier,
    SetupClassification,
    TokenSnapshot,
)
from strategy.history_analyzer import HistoryAnalyzer, HistoryTrends
from strategy.target_selector import TargetSelector

logger = logging.getLogger(__name__)


class QuickFlipTradePlanner:
    """Constructs disciplined, actionable trade blueprints from MomentumAnalysis and market micro-structure.

    Adheres strictly to the 8 Strategy Rules:
    1. Entry is based on current market structure, not arbitrary numbers.
    2. Overextended setups are classified as EXTENDED (never chased).
    3. Targets are derived via TargetSelector from structure, volatility, and momentum.
    4. Invalidation represents genuine structural breakdown of the thesis.
    5. Holding periods remain short-term (10-45 minutes).
    6. Targets are never guaranteed.
    7. Unviable, weak, invalidated, or low-liquidity setups return NO_PLAN.
    8. Missing data is never invented.
    """

    @classmethod
    def generate_plan(
        cls,
        analysis: MomentumAnalysis,
        history: Union[TokenSnapshot, List[TokenSnapshot]],
    ) -> QuickFlipPlan:
        """Construct a QuickFlipPlan from MomentumAnalysis and snapshot history."""
        if isinstance(history, TokenSnapshot):
            history_list = [history]
        else:
            history_list = list(history)

        if not history_list:
            return QuickFlipPlan(
                token_address=analysis.token_address,
                symbol=analysis.symbol,
                status=PlanStatus.NO_PLAN,
                plan_reason="No token history provided.",
            )

        trends = HistoryAnalyzer.analyze(history_list)
        current = sorted(history_list, key=lambda s: s.timestamp)[-1]
        token_address = current.token_address
        symbol = current.symbol
        now = datetime.now(timezone.utc)

        # Rule 8 & 7: Check for missing data
        if current.price_usd is None or current.market_cap_usd is None or current.liquidity_usd is None:
            missing = []
            if current.price_usd is None:
                missing.append("price")
            if current.market_cap_usd is None:
                missing.append("market_cap")
            if current.liquidity_usd is None:
                missing.append("liquidity")
            return QuickFlipPlan(
                token_address=token_address,
                symbol=symbol,
                timestamp=now,
                status=PlanStatus.NO_PLAN,
                plan_reason=f"Insufficient market data: missing {', '.join(missing)}. Rule 8: never invent data.",
            )

        price = current.price_usd
        mc = current.market_cap_usd
        liq = current.liquidity_usd
        liq_ratio = current.liquidity_ratio or 0.0

        # Rule 7: Low liquidity gate
        if liq < 5000.0 or (current.liquidity_ratio is not None and liq_ratio < 3.0):
            return QuickFlipPlan(
                token_address=token_address,
                symbol=symbol,
                timestamp=now,
                status=PlanStatus.NO_PLAN,
                entry_price=price,
                entry_market_cap=mc,
                plan_reason=f"Execution slippage hazard: pool liquidity is thin (${liq:,.0f}, {liq_ratio:.1f}% of MC).",
                risk_flags=["Critical liquidity risk: slippage makes quick-flip trade unviable"],
            )

        # Rule 7: Invalidated or Weakening setups
        if analysis.setup_state == ConfirmationState.INVALIDATED:
            return QuickFlipPlan(
                token_address=token_address,
                symbol=symbol,
                timestamp=now,
                status=PlanStatus.NO_PLAN,
                entry_price=price,
                entry_market_cap=mc,
                plan_reason="Momentum thesis invalidated: structure breakdown or sharp reversal underway.",
                risk_flags=["Invalidated momentum thesis"],
            )

        if analysis.setup_state == ConfirmationState.WEAKENING:
            return QuickFlipPlan(
                token_address=token_address,
                symbol=symbol,
                timestamp=now,
                status=PlanStatus.NO_PLAN,
                entry_price=price,
                entry_market_cap=mc,
                plan_reason="Momentum is weakening (divergence/sellers dominant): wait for renewed confirmation.",
                risk_flags=["Weakening momentum: volume or buyers failing to support price"],
            )

        # Rule 7: Weak or Reject score
        if analysis.score < 55.0 or analysis.score_tier in (ScoreTier.WEAK, ScoreTier.REJECT):
            return QuickFlipPlan(
                token_address=token_address,
                symbol=symbol,
                timestamp=now,
                status=PlanStatus.NO_PLAN,
                entry_price=price,
                entry_market_cap=mc,
                plan_reason=f"Score ({analysis.score:.1f}/100, Tier {analysis.score_tier.value}) is insufficient for quick flip trade.",
                risk_flags=["Insufficient momentum score"],
            )

        # Rule 2: Extended setup check (Do not chase vertical candles)
        is_extended = analysis.is_overextended or (
            current.change_5m_pct is not None and current.change_5m_pct >= 22.0
        )
        if is_extended:
            p5m = current.change_5m_pct or 0.0
            return QuickFlipPlan(
                token_address=token_address,
                symbol=symbol,
                timestamp=now,
                status=PlanStatus.EXTENDED,
                entry_price=price,
                entry_market_cap=mc,
                plan_reason=f"Token is overextended (+{p5m:.1f}% in 5m): high risk of immediate mean reversion. Rule 2: do not chase.",
                risk_flags=[
                    f"Overextended candle (+{p5m:.1f}% 5m): wait for controlled consolidation before entry"
                ],
            )

        # --- Rule 1: Entry Zone based on setup classification ---
        if analysis.classification == SetupClassification.PULLBACK_CONTINUATION:
            entry_low = round(price * 0.97, 8)
            entry_high = round(price * 1.01, 8)
        else:
            entry_low = round(price * 0.985, 8)
            entry_high = round(price * 1.015, 8)

        entry_zone = PriceZone(low=entry_low, high=entry_high, mid=price)

        # --- Rule 3: Dynamic Target Selection ---
        target_pct, target_price, target_zone = TargetSelector.select_target(
            current, analysis, trends
        )
        target_mc = round(mc * (1.0 + target_pct / 100.0), 2)

        # --- Rule 4: Structural Invalidation ---
        # High volatility / young token gets slightly wider invalidation
        is_young = (current.token_age_seconds is not None and current.token_age_seconds < 1800)
        is_high_vol = (current.change_5m_pct is not None and current.change_5m_pct >= 15.0)

        if is_young or is_high_vol:
            invalidation_pct = 10.5
        elif analysis.classification == SetupClassification.PULLBACK_CONTINUATION:
            invalidation_pct = 6.5
        else:
            invalidation_pct = 8.0

        invalidation_price = round(price * (1.0 - invalidation_pct / 100.0), 8)
        invalidation_mc = round(mc * (1.0 - invalidation_pct / 100.0), 2)

        rr_ratio = round(target_pct / invalidation_pct, 2)

        # --- Rule 5: Expected Holding Period (Minutes) ---
        if is_young or is_high_vol:
            holding_mins = 15
        elif analysis.classification == SetupClassification.PULLBACK_CONTINUATION:
            holding_mins = 30
        elif analysis.classification in (SetupClassification.BREAKOUT, SetupClassification.EARLY_MOMENTUM):
            holding_mins = 20
        else:
            holding_mins = 25

        # Risk Flags (never hide risk)
        risk_flags = list(analysis.warnings)
        if is_young:
            risk_flags.append("Young token volatility: rapid liquidity fluctuations possible")
        if rr_ratio < 1.8:
            risk_flags.append("Tight R:R: require disciplined entry at lower bound of entry zone")

        # Rationale
        plan_reason = (
            f"Validated {analysis.classification.value} setup with score {analysis.score:.1f}/100. "
            f"Target: +{target_pct:.1f}%, Invalidation: -{invalidation_pct:.1f}% (R:R {rr_ratio}:1, {holding_mins}m horizon)."
        )

        return QuickFlipPlan(
            token_address=token_address,
            symbol=symbol,
            timestamp=now,
            status=PlanStatus.READY,
            entry_price=price,
            entry_market_cap=mc,
            entry_zone=entry_zone,
            target_price=target_price,
            target_market_cap=target_mc,
            target_percentage=target_pct,
            target_zone=target_zone,
            invalidation_price=invalidation_price,
            invalidation_market_cap=invalidation_mc,
            invalidation_percentage=invalidation_pct,
            risk_reward_ratio=rr_ratio,
            expected_holding_minutes=holding_mins,
            risk_flags=risk_flags[:4],
            plan_reason=plan_reason,
        )
