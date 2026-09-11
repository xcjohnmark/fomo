"""Research Database service providing structured tripartite records, exports, and expectancy analytics."""

import csv
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from models.db import StrategyCall
from models.domain import CallOutcomeStatus, CallResult

logger = logging.getLogger(__name__)


class ResearchDatabaseService:
    """Provides structured research intelligence across permanent strategy calls."""

    def __init__(
        self,
        session_factory: Optional[async_sessionmaker[AsyncSession]] = None,
        memory_calls: Optional[List[StrategyCall]] = None,
    ):
        self.session_factory = session_factory
        self._memory_calls = memory_calls if memory_calls is not None else []

    async def get_all_calls(self, limit: int = 1000) -> List[StrategyCall]:
        """Fetch calls from database or in-memory cache."""
        if self.session_factory:
            async with self.session_factory() as session:
                stmt = select(StrategyCall).order_by(desc(StrategyCall.id)).limit(limit)
                res = await session.execute(stmt)
                return list(res.scalars().all())
        return list(reversed(self._memory_calls))[:limit]

    async def get_tripartite_records(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Retrieve calls organized into the core research structure:

        1. What did we see?
        2. What did the strategy predict?
        3. What actually happened?
        """
        calls = await self.get_all_calls(limit=limit)
        records: List[Dict[str, Any]] = []

        for call in calls:
            target_pct = None
            if call.target_price and call.entry_price and call.entry_price > 0:
                target_pct = round(((call.target_price - call.entry_price) / call.entry_price) * 100.0, 1)

            holding_min = round(call.holding_time / 60.0, 1) if call.holding_time else None
            time_to_target_min = (
                round(call.time_to_target / 60.0, 1) if call.time_to_target is not None else None
            )
            time_to_inval_min = (
                round(call.time_to_invalidation / 60.0, 1)
                if call.time_to_invalidation is not None
                else None
            )
            seen_data = {
                "score": call.momentum_score,
                "momentum_score": call.momentum_score,
                "entry_market_cap_usd": call.entry_market_cap,
                "entry_price_usd": call.entry_price,
                "liquidity_usd": call.entry_liquidity,
                "change_5m_pct": call.entry_5m_change_pct,
                "change_1h_pct": call.entry_1h_change_pct,
                "volume_5m_usd": call.entry_volume_5m,
                "volume_status": call.entry_volume_status or "ACCELERATING",
                "top10_concentration_pct": call.top10_concentration,
                "reasons": call.reasons,
                "risk_flags": call.risk_flags,
            }

            predicted_data = {
                "setup_state": call.setup_state,
                "strategy_version": call.strategy_version,
                "entry_zone_low": call.entry_zone_low,
                "entry_zone_high": call.entry_zone_high,
                "target_price": call.target_price,
                "target_market_cap": call.target_market_cap,
                "target_percentage": call.target_percentage if call.target_percentage is not None else target_pct,
                "invalidation_price": call.invalidation_price,
                "invalidation_market_cap": call.invalidation_market_cap,
                "expected_holding_minutes": call.expected_holding_minutes,
            }

            # High-level result WIN/LOSS/PENDING or exact result
            res_val = call.result
            if call.is_winning is True:
                res_val = "WIN"
            elif call.is_winning is False:
                res_val = "LOSS"

            happened_data = {
                "outcome_status": call.outcome_status,
                "result": res_val,
                "raw_result": call.result,
                "is_winning": call.is_winning,
                "actual_exit_price": call.actual_exit_price,
                "return_percentage": call.return_percentage,
                "actual_peak_price": call.actual_peak_price,
                "actual_peak_market_cap": call.actual_peak_market_cap,
                "max_favorable_excursion": call.max_favorable_excursion,
                "max_adverse_excursion": call.max_adverse_excursion,
                "time_to_target_minutes": time_to_target_min,
                "time_to_invalidation_minutes": time_to_inval_min,
                "holding_time_minutes": holding_min,
                "exit_reason": call.exit_reason,
            }

            record = {
                "call_id": call.call_id,
                "timestamp": call.timestamp.isoformat() if call.timestamp else None,
                "symbol": call.symbol,
                "token_ca": call.token_ca,
                "chain": call.chain,
                "strategy_version": call.strategy_version,
                # Both standard and section-17 keys supported
                "what_we_saw": seen_data,
                "what_did_we_see": seen_data,
                "what_predicted": predicted_data,
                "what_was_predicted": predicted_data,
                "what_happened": happened_data,
                "what_actually_happened": happened_data,
            }
            records.append(record)

        return records

    async def get_flat_records(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Retrieve flattened research rows suitable for tabular export and DataFrames."""
        tripartite = await self.get_tripartite_records(limit=limit)
        flat_rows: List[Dict[str, Any]] = []

        for r in tripartite:
            saw = r["what_did_we_see"]
            pred = r["what_was_predicted"]
            happened = r["what_actually_happened"]

            flat_rows.append(
                {
                    "call_id": r["call_id"],
                    "timestamp": r["timestamp"],
                    "symbol": r["symbol"],
                    "token_ca": r["token_ca"],
                    "chain": r["chain"],
                    # What did we see?
                    "score": saw["momentum_score"],
                    "seen_score": saw["momentum_score"],
                    "entry_mc": saw["entry_market_cap_usd"],
                    "entry_price": saw["entry_price_usd"],
                    "entry_liquidity": saw["liquidity_usd"],
                    "change_5m_pct": saw["change_5m_pct"],
                    "change_1h_pct": saw["change_1h_pct"],
                    "volume_5m_usd": saw["volume_5m_usd"],
                    "volume_status": saw["volume_status"],
                    "top10_concentration_pct": saw["top10_concentration_pct"],
                    # What was predicted?
                    "target_price": pred["target_price"],
                    "target_mc": pred["target_market_cap"],
                    "target_pct": pred["target_percentage"],
                    "predicted_target_pct": pred["target_percentage"],
                    "invalidation_price": pred["invalidation_price"],
                    "invalidation_mc": pred["invalidation_market_cap"],
                    "expected_hold_min": pred["expected_holding_minutes"],
                    # What happened?
                    "status": happened["outcome_status"],
                    "result": happened["result"],
                    "outcome_result": happened["result"],
                    "is_winning": happened["is_winning"],
                    "exit_price": happened["actual_exit_price"],
                    "return_pct": happened["return_percentage"],
                    "outcome_return_pct": happened["return_percentage"],
                    "peak_price": happened["actual_peak_price"],
                    "peak_mc": happened["actual_peak_market_cap"],
                    "mfe_pct": happened["max_favorable_excursion"],
                    "mae_pct": happened["max_adverse_excursion"],
                    "holding_min": happened["holding_time_minutes"],
                    "exit_reason": happened["exit_reason"],
                }
            )

        return flat_rows

    async def export_to_csv(self, filepath: str, limit: int = 10000) -> Path:
        """Export research dataset into a standardized flat CSV file."""
        target_path = Path(filepath)
        rows = await self.get_flat_records(limit=limit)
        if not rows:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with open(target_path, "w", newline="", encoding="utf-8") as f:
                f.write("call_id,timestamp,symbol,score,result,return_pct\n")
            return target_path

        target_path.parent.mkdir(parents=True, exist_ok=True)
        keys = list(rows[0].keys())

        with open(target_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(rows)

        logger.info("Exported %d research records to CSV: %s", len(rows), target_path)
        return target_path

    async def export_to_json(self, filepath: str, limit: int = 10000, indent: int = 2) -> Path:
        """Export structured tripartite research dataset to JSON."""
        target_path = Path(filepath)
        records = await self.get_tripartite_records(limit=limit)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=indent, default=str)

        logger.info("Exported %d research records to JSON: %s", len(records), target_path)
        return target_path

    async def get_dataframe(self, limit: int = 10000) -> pd.DataFrame:
        """Return research observations as a Pandas DataFrame."""
        rows = await self.get_flat_records(limit=limit)
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df

    async def compute_empirical_expectancy(self) -> Dict[str, Any]:
        """Calculate mathematically rigorous expectancy and performance segmented by score tiers and MC."""
        calls = await self.get_all_calls(limit=10000)
        total = len(calls)
        resolved = [c for c in calls if c.outcome_status == CallOutcomeStatus.RESOLVED.value]

        if not resolved:
            return {
                "total_calls": total,
                "resolved_calls": 0,
                "win_rate": 0.0,
                "overall_expectancy": 0.0,
                "profit_factor": 0.0,
                "by_score_bracket": {},
                "by_market_cap_bracket": {},
            }

        def _calc_bracket_stats(cohort: List[StrategyCall]) -> Dict[str, Any]:
            n = len(cohort)
            if n == 0:
                return {"calls": 0, "win_rate": 0.0, "expectancy": 0.0, "avg_mfe": 0.0}

            winners = [c for c in cohort if (c.return_percentage or 0.0) > 0.0]
            losers = [c for c in cohort if (c.return_percentage or 0.0) <= 0.0]

            p_win = len(winners) / n
            p_loss = len(losers) / n

            avg_win = sum(w.return_percentage for w in winners) / len(winners) if winners else 0.0
            avg_loss = abs(sum(l.return_percentage for l in losers) / len(losers)) if losers else 0.0

            expectancy = (p_win * avg_win) - (p_loss * avg_loss)
            avg_mfe = sum(c.max_favorable_excursion for c in cohort) / n

            return {
                "calls": n,
                "resolved_calls": n,
                "win_rate": round(p_win * 100.0, 1),
                "expectancy": round(expectancy, 2),
                "expectancy_pct": round(expectancy, 2),
                "avg_mfe": round(avg_mfe, 2),
                "avg_win_pct": round(avg_win, 2),
                "avg_loss_pct": round(avg_loss, 2),
            }

        overall_stats = _calc_bracket_stats(resolved)

        sum_gains = sum(c.return_percentage for c in resolved if (c.return_percentage or 0.0) > 0)
        sum_losses = abs(sum(c.return_percentage for c in resolved if (c.return_percentage or 0.0) <= 0))
        pf = (sum_gains / sum_losses) if sum_losses > 0 else (99.0 if sum_gains > 0 else 0.0)

        # Segment by score bracket
        score_90_plus = [c for c in resolved if c.momentum_score >= 90.0]
        score_85_89 = [c for c in resolved if 85.0 <= c.momentum_score < 90.0]
        score_under_85 = [c for c in resolved if c.momentum_score < 85.0]

        score_90_stats = _calc_bracket_stats(score_90_plus)
        score_85_stats = _calc_bracket_stats(score_85_89)
        score_under_stats = _calc_bracket_stats(score_under_85)

        # Segment by MC bracket
        mc_sub_150k = [c for c in resolved if (c.entry_market_cap or 0.0) < 150_000.0]
        mc_150_500k = [c for c in resolved if 150_000.0 <= (c.entry_market_cap or 0.0) < 500_000.0]
        mc_over_500k = [c for c in resolved if (c.entry_market_cap or 0.0) >= 500_000.0]

        return {
            "total_calls": total,
            "resolved_calls": len(resolved),
            "winning_calls": len([c for c in resolved if (c.return_percentage or 0.0) > 0]),
            "losing_calls": len([c for c in resolved if (c.return_percentage or 0.0) <= 0]),
            "win_rate": overall_stats["win_rate"],
            "empirical_win_rate": overall_stats["win_rate"],
            "overall_expectancy": overall_stats["expectancy"],
            "mathematical_expectancy_pct": overall_stats["expectancy"],
            "profit_factor": round(pf, 2),
            "avg_win_pct": overall_stats["avg_win_pct"],
            "avg_loss_pct": overall_stats["avg_loss_pct"],
            "by_score_bracket": {
                "Score 90–100": score_90_stats,
                "Score 85–89": score_85_stats,
                "Score <85": score_under_stats,
            },
            "by_score_tier": {
                "90-100 (Strong)": score_90_stats,
                "85-89 (Watch)": score_85_stats,
                "<85 (Conditional/Weak)": score_under_stats,
            },
            "by_market_cap_bracket": {
                "Sub-$150K MC": _calc_bracket_stats(mc_sub_150k),
                "$150K–$500K MC": _calc_bracket_stats(mc_150_500k),
                "$500K+ MC": _calc_bracket_stats(mc_over_500k),
            },
        }
