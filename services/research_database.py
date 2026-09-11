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
from services.statistical_engine import StatisticalEngine

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
                "token_age_seconds": call.entry_token_age_seconds,
                "buyer_seller_ratio": call.entry_buyer_seller_ratio,
                "buy_sell_ratio": call.entry_buy_sell_ratio,
                "market_condition": call.entry_market_condition,
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
                    "token_age_seconds": saw.get("token_age_seconds"),
                    "buyer_seller_ratio": saw.get("buyer_seller_ratio"),
                    "buy_sell_ratio": saw.get("buy_sell_ratio"),
                    "market_condition": saw.get("market_condition"),
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
        """Calculate mathematically rigorous expectancy and performance segmented across all dimensions."""
        calls = await self.get_all_calls(limit=10000)
        full_metrics = StatisticalEngine.compute_all_metrics(calls)
        core = full_metrics["core"]
        breakdowns = full_metrics["breakdowns"]

        return {
            "total_calls": core["total_calls_logged"],
            "resolved_calls": core["resolved_calls"],
            "winning_calls": round(core["resolved_calls"] * (core["win_rate"] / 100.0)),
            "losing_calls": round(core["resolved_calls"] * (core["loss_rate"] / 100.0)),
            "win_rate": core["win_rate"],
            "empirical_win_rate": core["win_rate"],
            "loss_rate": core["loss_rate"],
            "avg_win": core["avg_win"],
            "avg_win_pct": core["avg_win"],
            "avg_loss": core["avg_loss"],
            "avg_loss_pct": core["avg_loss"],
            "median_win": core["median_win"],
            "median_loss": core["median_loss"],
            "overall_expectancy": core["expectancy"],
            "mathematical_expectancy_pct": core["expectancy"],
            "profit_factor": core["profit_factor"],
            "avg_holding_time_min": core["avg_holding_time_min"],
            "median_holding_time_min": core["median_holding_time_min"],
            "target_hit_rate": core["target_hit_rate"],
            "invalidation_rate": core["invalidation_rate"],
            "timeout_rate": core["timeout_rate"],
            "avg_mfe": core["avg_mfe"],
            "max_mfe": core["max_mfe"],
            "avg_mae": core["avg_mae"],
            "max_mae": core["max_mae"],
            "max_drawdown": core["max_drawdown"],
            "core": core,
            "breakdowns": breakdowns,
            # Backward-compatible brackets
            "by_score_bracket": {
                "Score 90-100": breakdowns["strategy_score"].get("Score 90-100 (Strong)", {}),
                "Score 85-89": breakdowns["strategy_score"].get("Score 85-89 (Watch)", {}),
                "Score <85": breakdowns["strategy_score"].get("Score 70-84 (Conditional)", {}),
            },
            "by_score_tier": {
                "90-100 (Strong)": breakdowns["strategy_score"].get("Score 90-100 (Strong)", {}),
                "85-89 (Watch)": breakdowns["strategy_score"].get("Score 85-89 (Watch)", {}),
                "<85 (Conditional/Weak)": breakdowns["strategy_score"].get("Score 70-84 (Conditional)", {}),
            },
            "by_market_cap_bracket": {
                "Sub-$150K MC": breakdowns["market_cap"].get("Micro (<$100K)", {}),
                "$150K-$500K MC": breakdowns["market_cap"].get("Mid ($250K-$500K)", {}),
                "$500K+ MC": breakdowns["market_cap"].get("High ($500K+)", {}),
            },
        }
