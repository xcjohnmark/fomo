"""Target selection module dynamically determining realistic profit targets based on market structure."""

from typing import Optional, Tuple
from models.domain import MomentumAnalysis, PriceZone, SetupClassification, TokenSnapshot
from strategy.history_analyzer import HistoryTrends


class TargetSelector:
    """Calculates deterministic, market-structure-based profit targets without arbitrary multipliers."""

    @classmethod
    def select_target(
        cls,
        token: TokenSnapshot,
        analysis: MomentumAnalysis,
        trends: Optional[HistoryTrends] = None,
    ) -> Tuple[float, float, PriceZone]:
        """Compute realistic target percentage, target price, and target exit zone.

        Returns:
            (target_percentage, target_price, target_zone)
        """
        entry_price = token.price_usd or 0.0
        mc = token.market_cap_usd or 200000.0
        liq = token.liquidity_usd or 30000.0

        # 1. Base Target based on Setup Classification
        if analysis.classification == SetupClassification.BREAKOUT:
            base_target_pct = 25.0
        elif analysis.classification == SetupClassification.EARLY_MOMENTUM:
            base_target_pct = 22.0
        elif analysis.classification == SetupClassification.PULLBACK_CONTINUATION:
            base_target_pct = 18.0
        elif analysis.classification == SetupClassification.CONTINUATION:
            base_target_pct = 20.0
        else:
            base_target_pct = 15.0

        # 2. Market Cap Elasticity Adjustment
        # Smaller caps move with greater elasticity; larger caps need heavy capital
        if mc < 200000.0:
            base_target_pct += 4.0
        elif mc > 2000000.0 and mc <= 10000000.0:
            base_target_pct -= 4.0
        elif mc > 10000000.0:
            base_target_pct -= 6.0

        # 3. Momentum & Volume Velocity Boost
        v5m = token.volume_5m_usd or 0.0
        if (v5m / mc) >= 0.05:
            base_target_pct += 3.0
        if token.buy_tx_ratio is not None and token.buy_tx_ratio >= 65.0:
            base_target_pct += 2.0
        if trends and trends.volume_5m_accelerating:
            base_target_pct += 2.0

        # 4. Volatility / Young Token Adjustment
        if token.token_age_seconds is not None and token.token_age_seconds < 1800:
            base_target_pct += 3.0

        # 5. Liquidity Constraint (cap target if pool is modest to prevent illiquid exit traps)
        if liq < 25000.0:
            base_target_pct = min(base_target_pct, 20.0)

        # 6. Strict Bounds: Never promise an arbitrary 2x / 100%+. Quick flips target 12% to 38%.
        target_pct = round(max(min(base_target_pct, 38.0), 12.0), 1)

        target_price = round(entry_price * (1.0 + target_pct / 100.0), 8)
        zone_low = round(entry_price * (1.0 + (target_pct - 2.5) / 100.0), 8)
        zone_high = round(entry_price * (1.0 + (target_pct + 2.5) / 100.0), 8)

        target_zone = PriceZone(low=zone_low, high=zone_high, mid=target_price)

        return target_pct, target_price, target_zone
