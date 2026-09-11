"""Deterministic statistical analytics engine for Momentum / Quick Flip research."""

from datetime import datetime, timezone
import math
from statistics import mean, median
from typing import Any, Callable, Dict, List, Optional

from models.db import StrategyCall
from models.domain import CallOutcomeStatus


class StatisticalEngine:
    """Calculates comprehensive empirical performance metrics and multi-dimensional cohort breakdowns."""

    @staticmethod
    def _safe_mean(values: List[float], default: float = 0.0) -> float:
        return round(float(mean(values)), 2) if values else default

    @staticmethod
    def _safe_median(values: List[float], default: float = 0.0) -> float:
        return round(float(median(values)), 2) if values else default

    @classmethod
    def calculate_cohort_summary(cls, cohort: List[StrategyCall]) -> Dict[str, Any]:
        """Compute complete statistical metrics for any subset / cohort of strategy calls."""
        total_calls = len(cohort)
        if total_calls == 0:
            return {
                "calls": 0,
                "win_rate": 0.0,
                "loss_rate": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "median_win": 0.0,
                "median_loss": 0.0,
                "expectancy": 0.0,
                "profit_factor": 0.0,
                "avg_holding_time_min": 0.0,
                "median_holding_time_min": 0.0,
                "target_hit_rate": 0.0,
                "invalidation_rate": 0.0,
                "timeout_rate": 0.0,
                "avg_mfe": 0.0,
                "max_mfe": 0.0,
                "avg_mae": 0.0,
                "max_mae": 0.0,
                "max_drawdown": 0.0,
            }

        winning = [c for c in cohort if (c.return_percentage or 0.0) > 0.0]
        losing = [c for c in cohort if (c.return_percentage or 0.0) <= 0.0]

        n_win = len(winning)
        n_loss = len(losing)

        p_win = n_win / total_calls
        p_loss = n_loss / total_calls

        win_returns = [c.return_percentage for c in winning if c.return_percentage is not None]
        loss_returns = [abs(c.return_percentage) for c in losing if c.return_percentage is not None]

        avg_win = cls._safe_mean(win_returns)
        avg_loss = cls._safe_mean(loss_returns)
        med_win = cls._safe_median(win_returns)
        med_loss = cls._safe_median(loss_returns)

        # Mathematical Expectancy: E = (P_win * Avg Win) - (P_loss * Avg Loss)
        expectancy = round((p_win * avg_win) - (p_loss * avg_loss), 2)

        # Profit Factor
        gross_gains = sum(win_returns)
        gross_losses = sum(loss_returns)
        if gross_losses > 0:
            profit_factor = round(gross_gains / gross_losses, 2)
        else:
            profit_factor = 99.0 if gross_gains > 0 else 0.0

        # Holding Time (seconds -> minutes)
        holding_mins = [
            round(c.holding_time / 60.0, 1)
            for c in cohort
            if c.holding_time is not None and c.holding_time > 0
        ]
        avg_holding = cls._safe_mean(holding_mins)
        med_holding = cls._safe_median(holding_mins)

        # Resolution distribution
        target_hits = sum(
            1 for c in cohort if c.result == "TARGET_HIT" or c.exit_reason == "TARGET_HIT"
        )
        invalidations = sum(
            1 for c in cohort if c.result == "INVALIDATED" or c.exit_reason == "INVALIDATED"
        )
        timeouts = sum(
            1
            for c in cohort
            if c.result in ("TIME_EXIT", "EXPIRED") or c.exit_reason in ("TIME_EXIT", "EXPIRED")
        )

        target_hit_rate = round(target_hits / total_calls * 100.0, 1)
        invalidation_rate = round(invalidations / total_calls * 100.0, 1)
        timeout_rate = round(timeouts / total_calls * 100.0, 1)

        # Excursions (MFE / MAE)
        mfes = [c.max_favorable_excursion for c in cohort if c.max_favorable_excursion is not None]
        maes = [c.max_adverse_excursion for c in cohort if c.max_adverse_excursion is not None]

        avg_mfe = cls._safe_mean(mfes)
        max_mfe = round(max(mfes), 2) if mfes else 0.0
        avg_mae = cls._safe_mean(maes)
        # max adverse excursion is the most negative excursion
        max_mae = round(min(maes), 2) if maes else 0.0

        # Maximum Drawdown %
        max_drawdown = cls.calculate_max_drawdown(cohort)

        return {
            "calls": total_calls,
            "win_rate": round(p_win * 100.0, 1),
            "loss_rate": round(p_loss * 100.0, 1),
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "median_win": med_win,
            "median_loss": med_loss,
            "expectancy": expectancy,
            "expectancy_pct": expectancy,
            "profit_factor": profit_factor,
            "avg_holding_time_min": avg_holding,
            "median_holding_time_min": med_holding,
            "target_hit_rate": target_hit_rate,
            "invalidation_rate": invalidation_rate,
            "timeout_rate": timeout_rate,
            "avg_mfe": avg_mfe,
            "max_mfe": max_mfe,
            "avg_mae": avg_mae,
            "max_mae": max_mae,
            "max_drawdown": max_drawdown,
        }

    @staticmethod
    def calculate_max_drawdown(cohort: List[StrategyCall]) -> float:
        """Calculate peak-to-trough maximum drawdown percentage over sequential calls."""
        if not cohort:
            return 0.0

        # Sort calls chronologically by timestamp
        sorted_calls = sorted(
            cohort,
            key=lambda c: c.timestamp or datetime.fromtimestamp(0, tz=timezone.utc),
        )

        equity = 100.0
        peak = 100.0
        max_dd = 0.0

        for c in sorted_calls:
            ret = c.return_percentage or 0.0
            equity *= 1.0 + (ret / 100.0)
            if equity > peak:
                peak = equity
            if peak > 0:
                dd = (peak - equity) / peak * 100.0
                if dd > max_dd:
                    max_dd = dd

        return round(max_dd, 2)

    @classmethod
    def compute_all_metrics(cls, calls: List[StrategyCall]) -> Dict[str, Any]:
        """Compute full statistical research suite: core metrics and all 13 breakdown dimensions."""
        total_calls = len(calls)
        resolved = [c for c in calls if c.outcome_status == CallOutcomeStatus.RESOLVED.value]
        active = [c for c in calls if c.outcome_status != CallOutcomeStatus.RESOLVED.value]

        core = cls.calculate_cohort_summary(resolved)
        core["total_calls_logged"] = total_calls
        core["resolved_calls"] = len(resolved)
        core["active_calls"] = len(active)

        # Breakdowns across 13 required dimensions
        breakdowns = cls.compute_breakdowns(resolved)

        return {
            "core": core,
            "breakdowns": breakdowns,
        }

    @classmethod
    def compute_breakdowns(cls, resolved: List[StrategyCall]) -> Dict[str, Dict[str, Any]]:
        """Compute cohort performance segmented across 13 analytical dimensions."""

        # 1. Market Cap
        mc_groups = {
            "Micro (<$100K)": [c for c in resolved if (c.entry_market_cap or 0.0) < 100_000],
            "Low ($100K-$250K)": [c for c in resolved if 100_000 <= (c.entry_market_cap or 0.0) < 250_000],
            "Mid ($250K-$500K)": [c for c in resolved if 250_000 <= (c.entry_market_cap or 0.0) < 500_000],
            "High ($500K+)": [c for c in resolved if (c.entry_market_cap or 0.0) >= 500_000],
        }

        # 2. Liquidity
        liq_groups = {
            "Thin (<$15K)": [c for c in resolved if (c.entry_liquidity or 0.0) < 15_000],
            "Moderate ($15K-$35K)": [c for c in resolved if 15_000 <= (c.entry_liquidity or 0.0) < 35_000],
            "Deep ($35K-$75K)": [c for c in resolved if 35_000 <= (c.entry_liquidity or 0.0) < 75_000],
            "Prime ($75K+)": [c for c in resolved if (c.entry_liquidity or 0.0) >= 75_000],
        }

        # 3. Volume (5m)
        vol_groups = {
            "Low (<$5K)": [c for c in resolved if (c.entry_volume_5m or 0.0) < 5_000],
            "Moderate ($5K-$20K)": [c for c in resolved if 5_000 <= (c.entry_volume_5m or 0.0) < 20_000],
            "High ($20K-$50K)": [c for c in resolved if 20_000 <= (c.entry_volume_5m or 0.0) < 50_000],
            "Surge ($50K+)": [c for c in resolved if (c.entry_volume_5m or 0.0) >= 50_000],
        }

        # 4. 5M Momentum
        m5_groups = {
            "Modest (0%-5%)": [c for c in resolved if (c.entry_5m_change_pct or 0.0) < 5.0],
            "Strong (5%-12%)": [c for c in resolved if 5.0 <= (c.entry_5m_change_pct or 0.0) < 12.0],
            "Explosive (12%-25%)": [c for c in resolved if 12.0 <= (c.entry_5m_change_pct or 0.0) < 25.0],
            "Parabolic (>25%)": [c for c in resolved if (c.entry_5m_change_pct or 0.0) >= 25.0],
        }

        # 5. 1H Momentum
        m1h_groups = {
            "Base (<15%)": [c for c in resolved if (c.entry_1h_change_pct or 0.0) < 15.0],
            "Trending (15%-40%)": [c for c in resolved if 15.0 <= (c.entry_1h_change_pct or 0.0) < 40.0],
            "Runner (40%-100%)": [c for c in resolved if 40.0 <= (c.entry_1h_change_pct or 0.0) < 100.0],
            "Hyper (>100%)": [c for c in resolved if (c.entry_1h_change_pct or 0.0) >= 100.0],
        }

        # 6. Token Age
        def get_age_group(c: StrategyCall) -> str:
            age = c.entry_token_age_seconds
            if age is None:
                return "Unknown"
            if age < 3600:
                return "Fresh (<1h)"
            if age < 14400:
                return "Early (1-4h)"
            if age < 43200:
                return "Developing (4-12h)"
            return "Established (>12h)"

        age_groups: Dict[str, List[StrategyCall]] = {
            "Fresh (<1h)": [],
            "Early (1-4h)": [],
            "Developing (4-12h)": [],
            "Established (>12h)": [],
        }
        for c in resolved:
            grp = get_age_group(c)
            if grp in age_groups:
                age_groups[grp].append(c)

        # 7. Top-10 Concentration
        def get_top10_group(c: StrategyCall) -> str:
            val = c.top10_concentration
            if val is None:
                return "Unknown"
            if val < 20.0:
                return "Low (<20%)"
            if val < 35.0:
                return "Moderate (20%-35%)"
            if val < 50.0:
                return "Elevated (35%-50%)"
            return "High (>50%)"

        top10_groups: Dict[str, List[StrategyCall]] = {
            "Low (<20%)": [],
            "Moderate (20%-35%)": [],
            "Elevated (35%-50%)": [],
            "High (>50%)": [],
        }
        for c in resolved:
            grp = get_top10_group(c)
            if grp in top10_groups:
                top10_groups[grp].append(c)

        # 8. Buyer / Seller Ratio
        def get_bs_group(c: StrategyCall) -> str:
            val = c.entry_buyer_seller_ratio
            if val is None:
                return "Unknown"
            if val < 1.0:
                return "Seller Heavy (<1.0)"
            if val < 1.4:
                return "Balanced (1.0-1.4)"
            if val < 2.0:
                return "Buyer Dominant (1.4-2.0)"
            return "Strong Buyers (>2.0)"

        bs_groups: Dict[str, List[StrategyCall]] = {
            "Seller Heavy (<1.0)": [],
            "Balanced (1.0-1.4)": [],
            "Buyer Dominant (1.4-2.0)": [],
            "Strong Buyers (>2.0)": [],
        }
        for c in resolved:
            grp = get_bs_group(c)
            if grp in bs_groups:
                bs_groups[grp].append(c)

        # 9. Buy / Sell Ratio
        def get_buysell_group(c: StrategyCall) -> str:
            val = c.entry_buy_sell_ratio
            if val is None:
                return "Unknown"
            if val < 1.0:
                return "Sell Heavy (<1.0)"
            if val < 1.5:
                return "Balanced (1.0-1.5)"
            if val < 2.5:
                return "Buy Heavy (1.5-2.5)"
            return "Extreme Buys (>2.5)"

        buysell_groups: Dict[str, List[StrategyCall]] = {
            "Sell Heavy (<1.0)": [],
            "Balanced (1.0-1.5)": [],
            "Buy Heavy (1.5-2.5)": [],
            "Extreme Buys (>2.5)": [],
        }
        for c in resolved:
            grp = get_buysell_group(c)
            if grp in buysell_groups:
                buysell_groups[grp].append(c)

        # 10. Time of Day (UTC Sessions)
        def get_tod_group(c: StrategyCall) -> str:
            if not c.timestamp:
                return "Unknown"
            hour = c.timestamp.hour
            if 0 <= hour < 8:
                return "Asian (00:00-08:00)"
            if 8 <= hour < 14:
                return "European (08:00-14:00)"
            if 14 <= hour < 21:
                return "US Peak (14:00-21:00)"
            return "Late US (21:00-24:00)"

        tod_groups: Dict[str, List[StrategyCall]] = {
            "Asian (00:00-08:00)": [],
            "European (08:00-14:00)": [],
            "US Peak (14:00-21:00)": [],
            "Late US (21:00-24:00)": [],
        }
        for c in resolved:
            grp = get_tod_group(c)
            if grp in tod_groups:
                tod_groups[grp].append(c)

        # 11. Day of Week
        days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        dow_groups: Dict[str, List[StrategyCall]] = {d: [] for d in days_order}
        for c in resolved:
            if c.timestamp:
                day_name = c.timestamp.strftime("%A")
                if day_name in dow_groups:
                    dow_groups[day_name].append(c)

        # 12. Market Conditions / Setups
        cond_groups: Dict[str, List[StrategyCall]] = {}
        for c in resolved:
            cond = c.entry_market_condition or c.setup_state or "CONTINUATION"
            cond_groups.setdefault(cond, []).append(c)

        # 13. Strategy Score
        score_groups = {
            "Score 90-100 (Strong)": [c for c in resolved if c.momentum_score >= 90.0],
            "Score 85-89 (Watch)": [c for c in resolved if 85.0 <= c.momentum_score < 90.0],
            "Score 70-84 (Conditional)": [c for c in resolved if 70.0 <= c.momentum_score < 85.0],
            "Score <70 (Weak)": [c for c in resolved if c.momentum_score < 70.0],
        }

        def summarize_group(mapping: Dict[str, List[StrategyCall]]) -> Dict[str, Any]:
            return {name: cls.calculate_cohort_summary(cohort) for name, cohort in mapping.items()}

        return {
            "market_cap": summarize_group(mc_groups),
            "liquidity": summarize_group(liq_groups),
            "volume": summarize_group(vol_groups),
            "momentum_5m": summarize_group(m5_groups),
            "momentum_1h": summarize_group(m1h_groups),
            "token_age": summarize_group(age_groups),
            "top10_concentration": summarize_group(top10_groups),
            "buyer_seller_ratio": summarize_group(bs_groups),
            "buy_sell_ratio": summarize_group(buysell_groups),
            "time_of_day": summarize_group(tod_groups),
            "day_of_week": summarize_group(dow_groups),
            "market_conditions": summarize_group(cond_groups),
            "strategy_score": summarize_group(score_groups),
        }
