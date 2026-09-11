"""Deterministic 100-Point Momentum Scoring Engine strictly consuming TokenSnapshot."""

from typing import List, Tuple
from models.domain import MomentumScoreResult, ScoreBreakdown, TokenSnapshot


class MomentumScorer:
    """Calculates deterministic momentum scores across all 10 strategic dimensions.

    Strict Rule: Never invent or estimate missing data.
    If a dimension lacks provider metrics, it is added to unavailable_dimensions.
    """

    @classmethod
    def calculate_score(cls, token: TokenSnapshot) -> MomentumScoreResult:
        """Compute the full 10-dimension momentum score and risk/reason assessment."""
        unavail: List[str] = []

        mc_score = cls._score_market_cap(token, unavail)
        liq_score = cls._score_liquidity(token, unavail)
        vol_score = cls._score_volume(token, unavail)
        price_score = cls._score_price_momentum(token, unavail)
        pressure_score = cls._score_buy_sell_pressure(token, unavail)
        breadth_score = cls._score_buyer_seller_breadth(token, unavail)
        holders_score = cls._score_holders(token, unavail)
        top10_score = cls._score_top10(token, unavail)
        trader_score = cls._score_trader_activity(token, unavail)
        narrative_score = cls._score_narrative(token, unavail)

        breakdown = ScoreBreakdown(
            market_cap_score=mc_score,
            liquidity_score=liq_score,
            volume_score=vol_score,
            price_momentum_score=price_score,
            buy_sell_pressure_score=pressure_score,
            buyer_seller_breadth_score=breadth_score,
            holders_score=holders_score,
            top10_score=top10_score,
            trader_activity_score=trader_score,
            narrative_score=narrative_score,
            unavailable_dimensions=unavail,
        )

        total = breakdown.total_score

        # Section 29 Interpretation
        if total >= 85:
            summary = "STRONG CANDIDATE (WATCH / CONFIRM)"
        elif total >= 70:
            summary = "WATCH (10-20 MIN)"
        elif total >= 55:
            summary = "CONDITIONAL (WATCH ONLY IF SPECIFIC CATALYST)"
        elif total >= 40:
            summary = "WEAK (IGNORE)"
        else:
            summary = "REJECT (IGNORE)"

        missing = token.get_missing_fields()

        return MomentumScoreResult(
            score=total,
            breakdown=breakdown,
            status_summary=summary,
            missing_metrics=missing,
        )

    @staticmethod
    def _score_market_cap(token: TokenSnapshot, unavail: List[str]) -> float:
        """Section 19: Market-Cap Score (0 to 5 pts)."""
        if token.market_cap_usd is None:
            unavail.append("market_cap")
            return 0.0

        mc = token.market_cap_usd
        if 50000 <= mc <= 5000000:
            return 5.0
        elif (20000 <= mc < 50000) or (5000000 < mc <= 15000000):
            return 3.5
        elif (5000 <= mc < 20000) or (15000000 < mc <= 30000000):
            return 2.0
        elif mc < 5000 or mc > 50000000:
            return 0.5
        return 2.5

    @staticmethod
    def _score_liquidity(token: TokenSnapshot, unavail: List[str]) -> float:
        """Section 20: Liquidity Score (0 to 15 pts)."""
        if token.liquidity_usd is None:
            unavail.append("liquidity")
            return 0.0

        liq = token.liquidity_usd
        ratio = token.liquidity_ratio or 0.0

        if liq >= 30000 and ratio >= 15.0:
            return 14.5
        elif liq >= 15000 and ratio >= 10.0:
            return 11.0
        elif liq >= 5000 and ratio >= 5.0:
            return 7.0
        elif liq < 3000 or (token.liquidity_ratio is not None and ratio < 3.0):
            return 2.0
        return 5.0

    @staticmethod
    def _score_volume(token: TokenSnapshot, unavail: List[str]) -> float:
        """Section 21: Volume Activity Score (0 to 15 pts)."""
        if token.volume_5m_usd is None or token.volume_1h_usd is None:
            unavail.append("volume")
            return 0.0

        v5m = token.volume_5m_usd
        v1h = token.volume_1h_usd
        mc = max(token.market_cap_usd or 1.0, 1.0)

        ratio_5m = v5m / mc
        ratio_1h = v1h / mc

        pace_acceleration = (v5m * 12) >= (v1h * 0.8) if v1h > 0 else True

        if ratio_5m >= 0.05 and ratio_1h >= 0.20 and pace_acceleration:
            return 14.0
        elif ratio_5m >= 0.02 and ratio_1h >= 0.10:
            return 11.0
        elif ratio_5m >= 0.005 or ratio_1h >= 0.03:
            return 7.0
        elif v5m <= 100.0:
            return 2.0
        return 5.0

    @staticmethod
    def _score_price_momentum(token: TokenSnapshot, unavail: List[str]) -> float:
        """Section 22: Price Momentum Score (0 to 20 pts). Most important component."""
        if token.change_5m_pct is None or token.change_1h_pct is None:
            unavail.append("price_momentum")
            return 0.0

        p5m = token.change_5m_pct
        p1h = token.change_1h_pct
        p4h = token.change_4h_pct

        # Rule 3: Short timeframes matter more. Pump already reversing receives low score.
        if p5m < 0 and p1h < 0:
            return 2.0
        if p5m < -5.0:
            return 3.0

        # Strong continuation
        if p5m >= 5.0 and p1h >= 12.0 and (p4h is None or p4h >= 0.0):
            return 19.0
        elif p5m >= 3.0 and p1h >= 6.0:
            return 15.0
        elif p5m > 0 and p1h > 0:
            return 11.0
        elif p5m > 0 and p1h <= 0:
            return 9.0
        elif p5m <= 0 and p1h > 10.0:
            return 8.0
        return 4.0

    @staticmethod
    def _score_buy_sell_pressure(token: TokenSnapshot, unavail: List[str]) -> float:
        """Section 23: Buy/Sell Pressure Score (0 to 15 pts)."""
        # Prioritize volume imbalance if available
        if token.buy_volume_usd is not None and token.sell_volume_usd is not None:
            total_vol = token.buy_volume_usd + token.sell_volume_usd
            buy_pct = (token.buy_volume_usd / total_vol * 100.0) if total_vol > 0 else 50.0
        elif token.buy_tx_ratio is not None:
            buy_pct = token.buy_tx_ratio
        else:
            unavail.append("buy_sell_pressure")
            return 0.0

        if buy_pct >= 70.0:
            return 14.0
        elif buy_pct >= 58.0:
            return 10.5
        elif buy_pct >= 48.0:
            return 6.5
        elif buy_pct >= 35.0:
            return 3.0
        return 1.0

    @staticmethod
    def _score_buyer_seller_breadth(token: TokenSnapshot, unavail: List[str]) -> float:
        """Section 24: Buyer/Seller Breadth (0 to 10 pts)."""
        if token.buyer_ratio is None:
            unavail.append("buyer_seller_breadth")
            return 0.0

        ratio = token.buyer_ratio
        if ratio >= 65.0:
            return 9.0
        elif ratio >= 55.0:
            return 6.5
        elif ratio >= 45.0:
            return 4.5
        elif ratio >= 35.0:
            return 2.5
        return 1.0

    @staticmethod
    def _score_holders(token: TokenSnapshot, unavail: List[str]) -> float:
        """Section 25: Holders Score (0 to 5 pts)."""
        if token.holders_count is None:
            unavail.append("holders")
            return 0.0

        h = token.holders_count
        if h >= 1000:
            return 5.0
        elif h >= 500:
            return 3.5
        elif h >= 150:
            return 2.0
        elif h >= 30:
            return 1.0
        return 0.5

    @staticmethod
    def _score_top10(token: TokenSnapshot, unavail: List[str]) -> float:
        """Section 26: Top 10 Concentration (0 to 5 pts)."""
        if token.top10_holder_pct is None:
            unavail.append("top10_concentration")
            return 0.0

        top10 = token.top10_holder_pct
        if top10 <= 20.0:
            return 5.0
        elif top10 <= 35.0:
            return 3.5
        elif top10 <= 50.0:
            return 2.0
        elif top10 <= 70.0:
            return 1.0
        return 0.0

    @staticmethod
    def _score_trader_activity(token: TokenSnapshot, unavail: List[str]) -> float:
        """Section 27: Trader Activity (0 to 5 pts)."""
        if not token.trader_activity_summary or token.trader_activity_summary == "UNKNOWN":
            unavail.append("trader_activity")
            return 1.5  # Neutral baseline

        text = token.trader_activity_summary.lower()
        if any(w in text for w in ["increasing", "smart", "accumulation", "active", "multiple"]):
            return 4.5
        elif any(w in text for w in ["positive", "entering", "some"]):
            return 3.0
        elif "single" in text or "whale" in text:
            return 1.5
        elif any(w in text for w in ["exit", "selling", "dumping"]):
            return 0.5
        return 1.5

    @staticmethod
    def _score_narrative(token: TokenSnapshot, unavail: List[str]) -> float:
        """Section 28: Narrative (0 to 5 pts)."""
        if not token.narrative or token.narrative == "UNKNOWN":
            unavail.append("narrative")
            return 1.5  # Neutral baseline

        text = token.narrative.lower()
        if any(w in text for w in ["trend", "viral", "ai", "breakout", "major"]):
            return 4.5
        elif any(w in text for w in ["hype", "meme", "relevant", "new"]):
            return 3.0
        elif any(w in text for w in ["none", "dead", "scam", "old"]):
            return 0.5
        return 1.5
