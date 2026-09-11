"""Deterministic 100-Point Momentum Scoring Engine according to Sections 18-28."""

from models.domain import MomentumScoreResult, NormalizedTokenData, ScoreBreakdown


class MomentumScorer:
    """Calculates deterministic momentum scores across all 10 strategic dimensions."""

    @classmethod
    def calculate_score(cls, token: NormalizedTokenData) -> MomentumScoreResult:
        """Compute the full 10-dimension momentum score and risk/reason assessment."""
        mc_score = cls._score_market_cap(token)
        liq_score = cls._score_liquidity(token)
        vol_score = cls._score_volume(token)
        price_score = cls._score_price_momentum(token)
        pressure_score = cls._score_buy_sell_pressure(token)
        breadth_score = cls._score_buyer_seller_breadth(token)
        holders_score = cls._score_holders(token)
        top10_score = cls._score_top10(token)
        trader_score = cls._score_trader_activity(token)
        narrative_score = cls._score_narrative(token)

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

        return MomentumScoreResult(
            score=total,
            breakdown=breakdown,
            status_summary=summary,
        )

    @staticmethod
    def _score_market_cap(token: NormalizedTokenData) -> float:
        """Section 19: Market-Cap Score (0 to 5 pts)."""
        mc = token.market_cap
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
    def _score_liquidity(token: NormalizedTokenData) -> float:
        """Section 20: Liquidity Score (0 to 15 pts)."""
        liq = token.liquidity
        ratio = token.liquidity_ratio

        if liq >= 30000 and ratio >= 15.0:
            return 14.5
        elif liq >= 15000 and ratio >= 10.0:
            return 11.0
        elif liq >= 5000 and ratio >= 5.0:
            return 7.0
        elif liq < 3000 or ratio < 3.0:
            return 2.0
        return 5.0

    @staticmethod
    def _score_volume(token: NormalizedTokenData) -> float:
        """Section 21: Volume Activity Score (0 to 15 pts)."""
        # Volume relative to market cap
        v5m = token.volume_5m
        v1h = token.volume_1h
        mc = max(token.market_cap, 1.0)

        ratio_5m = v5m / mc
        ratio_1h = v1h / mc

        # Check acceleration: 5m volume pace exceeding 1h average pace
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
    def _score_price_momentum(token: NormalizedTokenData) -> float:
        """Section 22: Price Momentum Score (0 to 20 pts). Most important component."""
        p5m = token.change_5m
        p1h = token.change_1h
        p4h = token.change_4h

        # Rule 3: Short timeframes matter more. Pump already reversing receives low score.
        if p5m < 0 and p1h < 0:
            return 2.0
        if p5m < -5.0:
            return 3.0

        # Strong continuation
        if p5m >= 5.0 and p1h >= 12.0 and p4h >= 0.0:
            return 19.0
        elif p5m >= 3.0 and p1h >= 6.0:
            return 15.0
        elif p5m > 0 and p1h > 0:
            return 11.0
        elif p5m > 0 and p1h <= 0:  # early/mixed momentum
            return 9.0
        elif p5m <= 0 and p1h > 10.0:  # slight pullback in strong trend
            return 8.0
        return 4.0

    @staticmethod
    def _score_buy_sell_pressure(token: NormalizedTokenData) -> float:
        """Section 23: Buy/Sell Pressure Score (0 to 15 pts)."""
        # Prioritize volume imbalance over raw tx count if volume available
        if token.buy_volume is not None and token.sell_volume is not None:
            total_vol = token.buy_volume + token.sell_volume
            if total_vol > 0:
                buy_pct = (token.buy_volume / total_vol) * 100.0
            else:
                buy_pct = token.buy_tx_ratio
        else:
            buy_pct = token.buy_tx_ratio

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
    def _score_buyer_seller_breadth(token: NormalizedTokenData) -> float:
        """Section 24: Buyer/Seller Breadth (0 to 10 pts)."""
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
    def _score_holders(token: NormalizedTokenData) -> float:
        """Section 25: Holders Score (0 to 5 pts)."""
        h = token.holders
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
    def _score_top10(token: NormalizedTokenData) -> float:
        """Section 26: Top 10 Concentration (0 to 5 pts)."""
        top10 = token.top10_percentage
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
    def _score_trader_activity(token: NormalizedTokenData) -> float:
        """Section 27: Trader Activity (0 to 5 pts)."""
        text = token.trader_activity.lower()
        if any(w in text for w in ["increasing", "smart", "accumulation", "active", "multiple"]):
            return 4.5
        elif any(w in text for w in ["positive", "entering", "some"]):
            return 3.0
        elif "single" in text or "whale" in text:
            return 1.5
        elif "unknown" in text:
            return 2.0
        elif any(w in text for w in ["exit", "selling", "dumping"]):
            return 0.5
        return 2.0

    @staticmethod
    def _score_narrative(token: NormalizedTokenData) -> float:
        """Section 28: Narrative (0 to 5 pts)."""
        text = token.narrative.lower()
        if any(w in text for w in ["trend", "viral", "ai", "breakout", "major"]):
            return 4.5
        elif any(w in text for w in ["hype", "meme", "relevant", "new"]):
            return 3.0
        elif "unknown" in text:
            return 2.0
        elif any(w in text for w in ["none", "dead", "scam", "old"]):
            return 0.5
        return 2.0
