"""Chronological token snapshot history analysis and multi-metric trend detection."""

from dataclasses import dataclass
from typing import List, Optional
from models.domain import TokenSnapshot


@dataclass
class HistoryTrends:
    """Extracted directional trends across snapshot observations."""

    has_history: bool
    snapshots_count: int

    # Volume trends
    volume_5m_delta: Optional[float] = None
    volume_5m_accelerating: Optional[bool] = None
    volume_5m_falling: Optional[bool] = None

    # Price / volume divergence
    price_rising_volume_falling: bool = False
    price_rising_participation_weakening: bool = False

    # Participation & Flow trends
    buyers_delta: Optional[int] = None
    sellers_delta: Optional[int] = None
    buyers_increasing: Optional[bool] = None
    sellers_increasing: Optional[bool] = None
    holders_delta: Optional[int] = None
    holders_growing: Optional[bool] = None

    # Structural shifts
    sudden_reversal: bool = False
    pullback_with_declining_sell_volume: bool = False
    is_overextended: bool = False
    seller_dominance_detected: bool = False
    volume_masks_buyer_count: bool = False


class HistoryAnalyzer:
    """Deterministic analyzer evaluating multi-metric agreement across snapshot history."""

    @staticmethod
    def analyze(history: List[TokenSnapshot]) -> HistoryTrends:
        """Analyze a chronological list of snapshots for multi-metric agreement."""
        if not history:
            return HistoryTrends(has_history=False, snapshots_count=0)

        # Sort chronologically by timestamp
        sorted_history = sorted(history, key=lambda s: s.timestamp)
        curr = sorted_history[-1]

        # Overextension check on current snapshot (Section 59: Scenario 18)
        is_overextended = False
        if curr.change_5m_pct is not None and curr.change_5m_pct >= 20.0:
            is_overextended = True

        # Volume vs buyer count mismatch (Section 50: Scenario 9)
        # High buyer count but large seller volume
        volume_masks_buyer_count = False
        if (
            curr.buy_volume_usd is not None
            and curr.sell_volume_usd is not None
            and curr.buyers is not None
            and curr.sellers is not None
        ):
            if curr.buyers > curr.sellers and curr.sell_volume_usd >= (curr.buy_volume_usd * 2.0):
                volume_masks_buyer_count = True

        # Heavy seller dominance detection (Section 45: Scenario 4)
        seller_dominance = False
        if curr.buy_volume_usd is not None and curr.sell_volume_usd is not None:
            if curr.sell_volume_usd > curr.buy_volume_usd and curr.sell_volume_usd >= 10000.0:
                if curr.buy_volume_usd / (curr.buy_volume_usd + curr.sell_volume_usd) < 0.45:
                    seller_dominance = True
        elif curr.buys is not None and curr.sells is not None and curr.sells > curr.buys:
            if curr.buy_tx_ratio is not None and curr.buy_tx_ratio < 45.0:
                seller_dominance = True

        if len(sorted_history) == 1:
            return HistoryTrends(
                has_history=False,
                snapshots_count=1,
                is_overextended=is_overextended,
                volume_masks_buyer_count=volume_masks_buyer_count,
                seller_dominance_detected=seller_dominance,
            )

        prev = sorted_history[-2]

        # 1. Volume 5m Delta
        vol_5m_delta: Optional[float] = None
        vol_accel: Optional[bool] = None
        vol_falling: Optional[bool] = None
        if curr.volume_5m_usd is not None and prev.volume_5m_usd is not None:
            vol_5m_delta = curr.volume_5m_usd - prev.volume_5m_usd
            vol_accel = vol_5m_delta > 0
            vol_falling = vol_5m_delta < 0

        # 2. Buyers / Sellers Delta
        buyers_delta: Optional[int] = None
        sellers_delta: Optional[int] = None
        buyers_increasing: Optional[bool] = None
        sellers_increasing: Optional[bool] = None
        if curr.buyers is not None and prev.buyers is not None:
            buyers_delta = curr.buyers - prev.buyers
            buyers_increasing = buyers_delta > 0
        if curr.sellers is not None and prev.sellers is not None:
            sellers_delta = curr.sellers - prev.sellers
            sellers_increasing = sellers_delta > 0

        # 3. Holders Delta
        holders_delta: Optional[int] = None
        holders_growing: Optional[bool] = None
        if curr.holders_count is not None and prev.holders_count is not None:
            holders_delta = curr.holders_count - prev.holders_count
            holders_growing = holders_delta > 0

        # 4. Divergences (Section 44 & 57: Scenario 3 & 16)
        # Price rising while volume falling
        price_rising = (curr.change_5m_pct or 0.0) > 0.0
        price_rising_vol_down = False
        if price_rising and vol_falling:
            price_rising_vol_down = True

        # Price rising while participation (buyers) weakening or sellers increasing
        price_rising_part_weak = False
        if price_rising and (
            (buyers_delta is not None and buyers_delta <= 0)
            or (sellers_increasing is True)
        ):
            price_rising_part_weak = True

        # 5. Sudden Reversal / Invalidation (Section 58: Scenario 17)
        sudden_reversal = False
        prev_p5m = prev.change_5m_pct or 0.0
        curr_p5m = curr.change_5m_pct or 0.0
        if prev_p5m >= 4.0 and curr_p5m <= -4.0:
            sudden_reversal = True

        # 6. Pullback with declining sell volume (Section 49: Scenario 8)
        pullback_healthy = False
        p1h = curr.change_1h_pct or 0.0
        if -8.0 <= curr_p5m < 0.0 and p1h >= 10.0:
            if vol_falling or (sellers_delta is not None and sellers_delta <= 0):
                pullback_healthy = True

        return HistoryTrends(
            has_history=True,
            snapshots_count=len(sorted_history),
            volume_5m_delta=vol_5m_delta,
            volume_5m_accelerating=vol_accel,
            volume_5m_falling=vol_falling,
            price_rising_volume_falling=price_rising_vol_down,
            price_rising_participation_weakening=price_rising_part_weak,
            buyers_delta=buyers_delta,
            sellers_delta=sellers_delta,
            buyers_increasing=buyers_increasing,
            sellers_increasing=sellers_increasing,
            holders_delta=holders_delta,
            holders_growing=holders_growing,
            sudden_reversal=sudden_reversal,
            pullback_with_declining_sell_volume=pullback_healthy,
            is_overextended=is_overextended,
            seller_dominance_detected=seller_dominance,
            volume_masks_buyer_count=volume_masks_buyer_count,
        )
