"""Deterministic setup classification, confirmation state derivation, and objective reason/risk extraction."""

from typing import List, Optional, Tuple
from models.domain import (
    ConfirmationState,
    MomentumScoreResult,
    ScoreTier,
    SetupClassification,
    TokenSnapshot,
)
from strategy.history_analyzer import HistoryTrends


class SetupClassifier:
    """Classifies setups and evaluates confirmation states strictly using deterministic logic."""

    @classmethod
    def classify(
        cls,
        token: TokenSnapshot,
        score_result: MomentumScoreResult,
        trends: Optional[HistoryTrends] = None,
    ) -> SetupClassification:
        """Classify candidate into one of the Section 41 setup profiles."""
        p5m = token.change_5m_pct or 0.0
        p1h = token.change_1h_pct or 0.0
        p4h = token.change_4h_pct or 0.0
        p24h = token.change_24h_pct or 0.0
        v5m = token.volume_5m_usd or 0.0
        mc = max(token.market_cap_usd or 1.0, 1.0)
        buys = token.buys or 0
        sells = token.sells or 0

        # 5. Exhaustion / High Risk: Extreme pump with collapsing short timeframes (Scenario 2)
        if (p24h > 200.0 or p4h > 150.0) and (p5m < -4.0 or p1h < -8.0):
            return SetupClassification.EXHAUSTION

        # Young Coin early setup (Scenario 13)
        if token.token_age_seconds is not None and token.token_age_seconds < 1800 and p5m >= 4.0:
            return SetupClassification.EARLY_MOMENTUM

        # 4. Pullback Continuation: Controlled negative 5m within strong 1h/4h uptrend (Scenario 8 & 15)
        if -8.0 <= p5m <= 0.0 and p1h >= 8.0:
            if buys >= sells or (trends and trends.pullback_with_declining_sell_volume):
                return SetupClassification.PULLBACK_CONTINUATION

        # 3. Breakout: Multi-timeframe acceleration accompanied by volume surge (Scenario 7 & 14)
        if p5m >= 6.0 and ((v5m / mc) >= 0.03 or (trends and trends.volume_5m_accelerating)):
            # If 1h is still very early (<= 8%), classify as Early Momentum, else Breakout
            if p1h <= 8.0:
                return SetupClassification.EARLY_MOMENTUM
            return SetupClassification.BREAKOUT

        # 1. Early Momentum: Recent short-term acceleration, 1h still small (Scenario 7 & 13)
        if p5m >= 4.0 and p1h <= 8.0:
            return SetupClassification.EARLY_MOMENTUM

        # 2. Continuation: Established move continuing smoothly across timeframes (Scenario 1)
        if p5m > 0.0 and p1h > 0.0 and score_result.score >= 55.0:
            return SetupClassification.CONTINUATION

        # Flat / No Momentum (Scenario 6) or rejected setups
        if score_result.score < 55.0 and abs(p5m) < 1.0 and abs(p1h) < 1.0:
            return SetupClassification.NONE

        return SetupClassification.NONE if score_result.score < 40.0 else SetupClassification.CONTINUATION

    @classmethod
    def determine_confirmation_state(
        cls,
        token: TokenSnapshot,
        score_result: MomentumScoreResult,
        classification: SetupClassification,
        trends: Optional[HistoryTrends] = None,
    ) -> ConfirmationState:
        """Derive confirmation state: CONFIRMED, DEVELOPING, WEAKENING, or INVALIDATED."""
        p5m = token.change_5m_pct or 0.0
        p1h = token.change_1h_pct or 0.0
        liq = token.liquidity_usd or 0.0
        score = score_result.score

        # 1. INVALIDATED: Sudden reversal or failed breakout
        if trends and trends.sudden_reversal:
            return ConfirmationState.INVALIDATED
        if classification == SetupClassification.EXHAUSTION and p5m <= -8.0:
            return ConfirmationState.INVALIDATED
        if p5m < -8.0 and p1h < -15.0:
            return ConfirmationState.INVALIDATED

        # 2. WEAKENING: Divergences, seller dominance, or momentum loss
        if trends and (trends.price_rising_volume_falling or trends.price_rising_participation_weakening):
            return ConfirmationState.WEAKENING
        if trends and trends.seller_dominance_detected and p5m <= 0.0:
            return ConfirmationState.WEAKENING
        if classification == SetupClassification.EXHAUSTION:
            return ConfirmationState.WEAKENING

        # Trader activity late extension slowing (Scenario 11)
        trader_text = (token.trader_activity_summary or "").lower()
        if "slowing" in trader_text or "exit" in trader_text:
            return ConfirmationState.WEAKENING

        # 3. DEVELOPING: Promising setups needing more confirmation
        if trends and trends.is_overextended:
            return ConfirmationState.DEVELOPING
        if classification in (
            SetupClassification.EARLY_MOMENTUM,
            SetupClassification.PULLBACK_CONTINUATION,
        ):
            return ConfirmationState.DEVELOPING
        if token.token_age_seconds is not None and token.token_age_seconds < 1800:
            return ConfirmationState.DEVELOPING
        if score < 85.0:
            return ConfirmationState.DEVELOPING

        # 4. CONFIRMED: High score, multi-timeframe alignment, healthy volume & buyers
        if (
            score >= 85.0
            and p5m > 0.0
            and p1h > 0.0
            and liq >= 15000.0
            and (token.buy_tx_ratio is None or token.buy_tx_ratio >= 55.0)
            and (token.buyer_ratio is None or token.buyer_ratio >= 55.0)
        ):
            return ConfirmationState.CONFIRMED

        return ConfirmationState.DEVELOPING

    @classmethod
    def extract_reasons_and_risks(
        cls,
        token: TokenSnapshot,
        score_result: MomentumScoreResult,
        trends: Optional[HistoryTrends] = None,
    ) -> Tuple[List[str], List[str]]:
        """Extract 2-4 objective factual reasons and 2-4 objective factual risks (Rule 8)."""
        reasons: List[str] = []
        risks: List[str] = []

        p5m = token.change_5m_pct
        p1h = token.change_1h_pct
        p4h = token.change_4h_pct
        p24h = token.change_24h_pct
        liq = token.liquidity_usd
        liq_ratio = token.liquidity_ratio
        buyers = token.buyers
        sellers = token.sellers
        buys = token.buys
        sells = token.sells
        top10 = token.top10_holder_pct
        age_sec = token.token_age_seconds

        # --- Objective Reasons ---
        if p5m is not None and p1h is not None and p5m > 0 and p1h > 0:
            reasons.append(
                f"Positive price alignment across short timeframes (5M: +{p5m:.1f}%, 1H: +{p1h:.1f}%)"
            )

        if token.buyer_ratio is not None and token.buyer_ratio >= 55.0:
            reasons.append(
                f"Broad participant breadth with {buyers} buyers vs {sellers} sellers ({token.buyer_ratio:.1f}% buyer ratio)"
            )

        if token.buy_tx_ratio is not None and token.buy_tx_ratio >= 58.0:
            reasons.append(
                f"Strong buy transaction dominance ({buys} buys vs {sells} sells, {token.buy_tx_ratio:.1f}%)"
            )

        if liq_ratio is not None and liq_ratio >= 12.0 and liq is not None and liq >= 15000.0:
            reasons.append(f"Healthy liquidity backing (${liq:,.0f}, {liq_ratio:.1f}% of MC)")

        if token.volume_5m_usd is not None and token.volume_1h_usd is not None:
            if len(reasons) < 4:
                reasons.append(
                    f"Active trading volume sustained at ${token.volume_5m_usd:,.0f} (5M) and ${token.volume_1h_usd:,.0f} (1H)"
                )

        if len(reasons) < 2:
            reasons.append("Multi-factor score qualified candidate for active momentum monitoring")

        # --- Objective Risks (Rule 8: Avoid confirmation bias; never hide risk) ---

        # Reversal warning (Scenario 2)
        if (p24h or 0.0) >= 200.0 and (p5m or 0.0) < 0.0:
            risks.append(
                f"Reversal warning: large historical 24H pump (+{p24h:.1f}%) experiencing sharp current collapse (5M: {p5m:.1f}%)"
            )

        # Execution / Low Liquidity Risk (Scenario 5)
        if liq is not None and (liq < 10000.0 or (liq_ratio is not None and liq_ratio < 5.0)):
            risks.append(
                f"Execution slippage risk: pool liquidity is thin at ${liq:,.0f} ({liq_ratio:.1f}% MC)"
            )

        # Concentration Risk (Scenario 12)
        if top10 is not None and top10 >= 35.0:
            risks.append(
                f"Concentration risk: top 10 wallets control {top10:.1f}% of supply"
            )
        elif top10 is None:
            risks.append("Data limitation: top 10 holder concentration is UNAVAILABLE from provider")

        # Overextended candle (Scenario 18)
        if p5m is not None and p5m >= 20.0:
            risks.append(
                f"Overextended candle: vertical +{p5m:.1f}% jump in 5m poses severe immediate mean-reversion risk"
            )

        # Smart trader late entry (Scenario 11)
        if token.trader_activity_summary and "slowing" in token.trader_activity_summary.lower():
            risks.append("Late trader entry: momentum slowing following initial run, do not chase")

        # Seller Dominance / Distribution (Scenario 4)
        if trends and trends.seller_dominance_detected:
            risks.append("Distribution risk: heavy selling volume dominates active market flow")

        # Volume masks buyer count (Scenario 9)
        if trends and trends.volume_masks_buyer_count:
            risks.append("Flow divergence: high buyer count is being overwhelmed by large seller volume")

        # Price rising while volume falling divergence (Scenario 3 & 16)
        if trends and trends.price_rising_volume_falling:
            risks.append("Divergence warning: 5M price is rising while volume is falling")
        if trends and trends.price_rising_participation_weakening:
            risks.append("Divergence warning: 5M price is rising while buyer participation weakens")

        # Very young coin risk (Scenario 13)
        if age_sec is not None and age_sec < 1800:
            risks.append(
                f"Young token risk: only {token.token_age_formatted or '15m'} old, extreme volatility and unproven liquidity"
            )

        # Strong narrative, weak market (Scenario 10)
        if token.narrative and p5m is not None and p1h is not None and p5m < 0.0 and p1h < 0.0:
            risks.append("Narrative divergence: strong narrative cannot compensate for negative market momentum")

        # Fallback general risks
        if len(risks) < 2:
            risks.append("Execution risk: volatile memecoin momentum prone to abrupt reversal")
        if len(risks) < 2:
            risks.append("Short holding window: setup invalidates if 5M continuation stalls")

        return reasons[:4], risks[:4]

    @classmethod
    def get_confirmation_and_invalidation(
        cls,
        token: TokenSnapshot,
        classification: SetupClassification,
        state: ConfirmationState,
        trends: Optional[HistoryTrends] = None,
    ) -> Tuple[List[str], List[str], str]:
        """Generate confirmation requirements, invalidation criteria, and recommended next action."""
        price = token.price_usd or 0.0
        conf: List[str] = []
        inval: List[str] = []

        if state == ConfirmationState.INVALIDATED or classification == SetupClassification.EXHAUSTION:
            conf.append("Reclaim of 1H high with renewed buyer volume dominance")
            inval.append("Continued sell flow or breakdown to new 24H low")
            return conf, inval, "Ignore / Invalidated Setup"

        if classification == SetupClassification.PULLBACK_CONTINUATION:
            conf.append("Renewed 5M buying volume and reclaim of local high")
            conf.append("Hold support zone without aggressive sell volume spikes")
            inval.append(f"Breakdown below local support level (${price * 0.93:.8f})")
            inval.append("Sell volume expands above 5M average on breakdown")
            return conf, inval, "Watch 10-20 min for renewed buying confirmation"

        if trends and trends.is_overextended:
            conf.append("Controlled pullback or base consolidation without deep breakdown")
            conf.append("Declining sell volume during pause followed by renewed buyer entry")
            inval.append(f"Sharp breakdown below breakout level (${price * 0.88:.8f})")
            return conf, inval, "Wait for controlled pullback / Do not chase"

        if classification == SetupClassification.EARLY_MOMENTUM:
            conf.append("Sustained 5M price acceleration with expanding buyer participation")
            conf.append("1H volume pace maintaining above initial breakout level")
            inval.append(f"Immediate rejection below breakout entry (${price * 0.92:.8f})")
            inval.append("5M volume collapses back to baseline")
            return conf, inval, "Watch closely for confirmation (10-20 min)"

        # Default Continuation / Confirmed
        conf.append("Higher highs on 5M timeframe accompanied by sustained volume")
        conf.append("Buyer-to-seller ratio remaining above 55%")
        inval.append(f"5M volume collapse or drop below support (${price * 0.90:.8f})")
        inval.append("Seller volume surging above buy volume")

        action = "High-priority confirmation / Observe 10-20 min" if state == ConfirmationState.CONFIRMED else "Watch 10-20 min"
        return conf, inval, action
