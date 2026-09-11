"""Setup classification and objective reason/risk extraction strictly consuming TokenSnapshot."""

from typing import List, Tuple
from models.domain import (
    ConfirmationState,
    MomentumScoreResult,
    SetupClassification,
    TokenSnapshot,
)


class SetupClassifier:
    """Classifies setups and extracts objective reasons, risks, and invalidation criteria."""

    @classmethod
    def classify(cls, token: TokenSnapshot, score_result: MomentumScoreResult) -> SetupClassification:
        """Classify candidate into one of the 5 Section 41 setup profiles."""
        p5m = token.change_5m_pct or 0.0
        p1h = token.change_1h_pct or 0.0
        p4h = token.change_4h_pct or 0.0
        p24h = token.change_24h_pct or 0.0

        # 5. Exhaustion / High Risk: Extreme 24h pump with collapsing short timeframes
        if (p24h > 300.0 or p4h > 150.0) and (p5m < -5.0 or p1h < -10.0):
            return SetupClassification.EXHAUSTION

        # 4. Pullback Continuation: Controlled negative 5m within a strong 1h/4h uptrend
        buys = token.buys or 0
        sells = token.sells or 0
        if -8.0 <= p5m < 0.0 and p1h >= 10.0 and buys > sells:
            return SetupClassification.PULLBACK_CONTINUATION

        # 1. Early Momentum: Recent short-term acceleration, 1h still small
        if p5m >= 5.0 and p1h <= 8.0:
            return SetupClassification.EARLY_MOMENTUM

        # 3. Breakout: Multi-timeframe acceleration accompanied by volume surge
        v5m = token.volume_5m_usd or 0.0
        mc = max(token.market_cap_usd or 1.0, 1.0)
        if p5m >= 6.0 and p1h >= 12.0 and (v5m / mc) >= 0.04:
            return SetupClassification.BREAKOUT

        # 2. Continuation: Established move continuing smoothly
        return SetupClassification.CONTINUATION

    @classmethod
    def extract_reasons_and_risks(
        cls, token: TokenSnapshot, score_result: MomentumScoreResult
    ) -> Tuple[List[str], List[str]]:
        """Extract 2-4 objective factual reasons and 2-4 objective factual risks (Rule 8)."""
        reasons: List[str] = []
        risks: List[str] = []

        # Objective Reasons
        if token.change_5m_pct is not None and token.change_1h_pct is not None:
            if token.change_5m_pct > 0 and token.change_1h_pct > 0:
                reasons.append(
                    f"Positive price alignment across short timeframes (5M: +{token.change_5m_pct:.1f}%, 1H: +{token.change_1h_pct:.1f}%)"
                )

        if token.buyer_ratio is not None and token.buyer_ratio >= 55.0:
            reasons.append(
                f"Broad participant breadth with {token.buyers} buyers vs {token.sellers} sellers ({token.buyer_ratio:.1f}% buyer ratio)"
            )

        if token.buy_tx_ratio is not None and token.buy_tx_ratio >= 60.0:
            reasons.append(
                f"Strong buy transaction dominance ({token.buys} buys vs {token.sells} sells, {token.buy_tx_ratio:.1f}%)"
            )

        if token.liquidity_ratio is not None and token.liquidity_ratio >= 15.0 and token.liquidity_usd is not None:
            reasons.append(
                f"Healthy liquidity backing (${token.liquidity_usd:,.0f}, {token.liquidity_ratio:.1f}% of MC)"
            )

        if len(reasons) < 2 and token.volume_5m_usd is not None and token.volume_1h_usd is not None:
            reasons.append(
                f"Volume activity sustained at ${token.volume_5m_usd:,.0f} (5M) and ${token.volume_1h_usd:,.0f} (1H)"
            )
        if len(reasons) < 2:
            reasons.append("Multi-factor momentum score qualified for active watch list")

        # Objective Risks (Rule 8: avoid confirmation bias; never hide risk)
        if token.top10_holder_pct is not None and token.top10_holder_pct >= 35.0:
            risks.append(
                f"Concentration risk: top 10 wallets control {token.top10_holder_pct:.1f}% of supply"
            )
        elif token.top10_holder_pct is None:
            risks.append("Data limitation: top 10 holder concentration is UNAVAILABLE from current feed")

        if token.liquidity_usd is not None and token.liquidity_usd < 15000.0:
            risks.append(
                f"Execution slippage risk: absolute pool liquidity is thin at ${token.liquidity_usd:,.0f}"
            )

        if token.change_5m_pct is not None and token.change_5m_pct >= 15.0:
            risks.append(
                f"Overextended candle: rapid +{token.change_5m_pct:.1f}% jump in 5m may invite immediate profit-taking"
            )

        if token.sellers is not None and token.buyers is not None and token.sellers > token.buyers:
            risks.append(
                f"Seller breadth: sellers ({token.sellers}) currently outnumber buyers ({token.buyers})"
            )

        if len(risks) < 2:
            risks.append("Execution risk: volatile memecoin momentum prone to abrupt reversal")
        if len(risks) < 2:
            risks.append("Short holding window: setup invalidates if 5M continuation stalls")

        return reasons[:4], risks[:4]

    @classmethod
    def get_confirmation_and_invalidation(
        cls, token: TokenSnapshot, classification: SetupClassification
    ) -> Tuple[str, str, str, ConfirmationState]:
        """Generate confirmation requirements, invalidation criteria, next action, and state."""
        price = token.price_usd or 0.0

        if classification == SetupClassification.EXHAUSTION:
            return (
                "Reclaim of previous 1H highs with positive volume divergence",
                "Breakdown below 1H low or continued sell volume spike",
                "Ignore / High Risk Reversal",
                ConfirmationState.WEAKENING,
            )

        if classification == SetupClassification.PULLBACK_CONTINUATION:
            return (
                "Renewed buying volume and reclaim of 5M local high",
                f"Breakdown below current support level (${price * 0.92:.8f})",
                "Watch 10-20 min for renewed buying confirmation",
                ConfirmationState.CONFIRMATION,
            )

        # Early / Continuation / Breakout
        confirmation_needed = (
            "Higher highs on 5M timeframe accompanied by sustained or increasing buy volume"
        )
        invalidation = (
            f"Sharp 5M volume collapse or drop below support (${price * 0.90:.8f})"
        )
        next_action = "Watch 10-20 min / Verify volume continuation"
        state = ConfirmationState.CONFIRMATION

        return confirmation_needed, invalidation, next_action, state
