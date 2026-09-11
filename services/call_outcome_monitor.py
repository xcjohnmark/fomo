"""Call Outcome Monitor service implementing permanent call recording, real-time evaluation, and research analytics."""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from collectors.base import MarketDataProvider
from models.db import StrategyCall
from models.domain import (
    AlertCandidate,
    CallOutcomeStatus,
    CallResult,
    QuickFlipPlan,
    TokenSnapshot,
)
from strategy.trade_planner import QuickFlipTradePlanner

logger = logging.getLogger(__name__)


class CallOutcomeMonitor:
    """Monitors strategy calls continuously without hindsight bias adhering to predefined rules."""

    def __init__(
        self,
        session_factory: Optional[async_sessionmaker[AsyncSession]] = None,
        collector: Optional[MarketDataProvider] = None,
        strategy_version: str = "v1.0",
    ):
        self.session_factory = session_factory
        self.collector = collector
        self.strategy_version = strategy_version
        self._memory_calls: List[StrategyCall] = []
        self._next_id = 1

    async def record_call(
        self,
        candidate: AlertCandidate,
        plan: Optional[QuickFlipPlan] = None,
    ) -> StrategyCall:
        """Record an immutable strategy call from an alert candidate."""
        token = candidate.token
        trade_plan = plan or candidate.plan

        if trade_plan is None:
            trade_plan = QuickFlipTradePlanner.generate_plan(candidate.analysis, token)

        entry_price = trade_plan.entry_price or token.price_usd or 0.0
        entry_mc = trade_plan.entry_market_cap or token.market_cap_usd

        entry_zone_low = trade_plan.entry_zone.low if trade_plan.entry_zone else None
        entry_zone_high = trade_plan.entry_zone.high if trade_plan.entry_zone else None

        target_price = trade_plan.target_price
        target_mc = trade_plan.target_market_cap

        invalidation_price = trade_plan.invalidation_price
        invalidation_mc = trade_plan.invalidation_market_cap

        expected_holding_minutes = trade_plan.expected_holding_minutes or 30

        timestamp = token.timestamp
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        sym = token.symbol or "UNKNOWN"
        short_addr = token.token_address[:8]
        unique_suffix = uuid.uuid4().hex[:6]
        call_id = f"call_{timestamp.strftime('%Y%m%d_%H%M%S')}_{sym}_{short_addr}_{unique_suffix}"

        vol_status = "NORMAL"
        if token.volume_5m_usd and token.volume_1h_usd:
            if token.volume_5m_usd > (token.volume_1h_usd / 12.0) * 1.5:
                vol_status = "ACCELERATING"
            elif token.volume_5m_usd > (token.volume_1h_usd / 12.0):
                vol_status = "EXPANDING"

        call = StrategyCall(
            call_id=call_id,
            timestamp=timestamp,
            token_ca=token.token_address,
            chain=token.chain or "solana",
            pool_address=token.pool_address,
            symbol=sym,
            strategy_version=self.strategy_version,
            momentum_score=candidate.score_result.score,
            # Immutable parameters (What did we see?)
            entry_price=entry_price,
            entry_market_cap=entry_mc,
            entry_liquidity=token.liquidity_usd,
            entry_5m_change_pct=token.change_5m_pct,
            entry_1h_change_pct=token.change_1h_pct,
            entry_volume_5m=token.volume_5m_usd,
            entry_volume_status=vol_status,
            top10_concentration=token.top10_holder_pct,
            # Predictions (What did the strategy predict?)
            entry_zone_low=entry_zone_low,
            entry_zone_high=entry_zone_high,
            target_price=target_price,
            target_market_cap=target_mc,
            target_percentage=trade_plan.target_percentage,
            invalidation_price=invalidation_price,
            invalidation_market_cap=invalidation_mc,
            expected_holding_minutes=expected_holding_minutes,
            setup_state=candidate.confirmation_state.value,
            reasons=list(candidate.reasons),
            risk_flags=list(candidate.risks),
            # Dynamic initial tracking values (What actually happened?)
            outcome_status=CallOutcomeStatus.OPEN.value,
            is_winning=None,
            actual_peak_price=entry_price,
            actual_peak_market_cap=entry_mc,
            actual_low_price=entry_price,
            max_favorable_excursion=0.0,
            max_adverse_excursion=0.0,
            return_percentage=0.0,
            result=None,
        )

        if self.session_factory:
            async with self.session_factory() as session:
                async with session.begin():
                    session.add(call)
                await session.refresh(call)
                logger.info(
                    "Recorded StrategyCall %s for $%s (Target: %s, Invalidation: %s)",
                    call.call_id,
                    sym,
                    target_price,
                    invalidation_price,
                )
                return call
        else:
            call.id = self._next_id
            self._next_id += 1
            self._memory_calls.append(call)
            return call

    def evaluate_tick(
        self,
        call: StrategyCall,
        current_price: float,
        current_market_cap: Optional[float] = None,
        current_time: Optional[datetime] = None,
    ) -> StrategyCall:
        """Evaluate a price tick against an existing call enforcing strict anti-hindsight rules.

        Rule 1: If already RESOLVED, never rewrite history.
        Rule 2: Check invalidation before target if discrete tick hit invalidation level.
        Rule 3: Maintain MFE (max favorable excursion) and MAE (max adverse excursion).
        Rule 4: Timeout if holding window elapsed.
        """
        # Sealed calls are permanent and immutable
        if call.outcome_status == CallOutcomeStatus.RESOLVED.value:
            return call

        if current_price <= 0.0:
            call.result = CallResult.DATA_ERROR.value
            call.outcome_status = CallOutcomeStatus.RESOLVED.value
            call.exit_reason = "Invalid non-positive market price received"
            return call

        # Calculate time elapsed
        call_ts = call.timestamp
        if call_ts.tzinfo is None:
            call_ts = call_ts.replace(tzinfo=timezone.utc)

        now = current_time or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        elapsed_seconds = int(max(0, (now - call_ts).total_seconds()))
        elapsed_minutes = elapsed_seconds / 60.0

        # Update peak / low prices
        if call.actual_peak_price is None or current_price > call.actual_peak_price:
            call.actual_peak_price = current_price
        if current_market_cap and (
            call.actual_peak_market_cap is None or current_market_cap > call.actual_peak_market_cap
        ):
            call.actual_peak_market_cap = current_market_cap

        if call.actual_low_price is None or current_price < call.actual_low_price:
            call.actual_low_price = current_price

        # Update MFE / MAE
        current_return = (
            ((current_price - call.entry_price) / call.entry_price) * 100.0
            if call.entry_price > 0
            else 0.0
        )
        if current_return > call.max_favorable_excursion:
            call.max_favorable_excursion = round(current_return, 2)
        if current_return < call.max_adverse_excursion:
            call.max_adverse_excursion = round(current_return, 2)

        # 1. Check Invalidation First (Strict Discipline: Risk management takes precedence)
        if call.invalidation_price is not None and current_price <= call.invalidation_price:
            call.result = CallResult.INVALIDATED.value
            call.actual_exit_price = current_price
            call.time_to_invalidation = elapsed_seconds
            call.holding_time = elapsed_seconds
            call.return_percentage = round(current_return, 2)
            call.is_winning = False
            call.exit_reason = (
                f"Hit invalidation level at ${current_price:.6f} "
                f"(Threshold: ${call.invalidation_price:.6f}, Return: {call.return_percentage:+.1f}%)"
            )
            call.outcome_status = CallOutcomeStatus.RESOLVED.value
            logger.info("Call %s RESOLVED as INVALIDATED in %ss", call.call_id, elapsed_seconds)
            return call

        # 2. Check Target Hit
        if call.target_price is not None and current_price >= call.target_price:
            call.result = CallResult.TARGET_HIT.value
            call.actual_exit_price = current_price
            call.time_to_target = elapsed_seconds
            call.holding_time = elapsed_seconds
            call.return_percentage = round(current_return, 2)
            call.is_winning = True
            call.exit_reason = (
                f"Reached target level at ${current_price:.6f} "
                f"(Target: ${call.target_price:.6f}, Return: {call.return_percentage:+.1f}%)"
            )
            call.outcome_status = CallOutcomeStatus.RESOLVED.value
            logger.info("Call %s RESOLVED as TARGET_HIT in %ss", call.call_id, elapsed_seconds)
            return call

        # 3. Check Holding Time Expiration (2.0x expected holding window)
        exp_min = call.expected_holding_minutes or 30
        if elapsed_minutes >= (exp_min * 2.0):
            if current_return > 0.0:
                call.result = CallResult.TIME_EXIT.value
                call.is_winning = True
                call.exit_reason = (
                    f"Holding window expired after {elapsed_minutes:.0f}m with partial gain "
                    f"({current_return:+.1f}%)"
                )
            else:
                call.result = CallResult.EXPIRED.value
                call.is_winning = False
                call.exit_reason = (
                    f"Holding window expired after {elapsed_minutes:.0f}m without resolution "
                    f"({current_return:+.1f}%)"
                )
            call.actual_exit_price = current_price
            call.holding_time = elapsed_seconds
            call.return_percentage = round(current_return, 2)
            call.outcome_status = CallOutcomeStatus.RESOLVED.value
            logger.info("Call %s RESOLVED as %s after %dm", call.call_id, call.result, int(elapsed_minutes))
            return call

        return call

    async def monitor_open_calls(self) -> int:
        """Fetch current prices for all open strategy calls and evaluate outcomes."""
        if not self.collector:
            logger.warning("No collector configured for CallOutcomeMonitor; skipping monitoring cycle.")
            return 0

        open_calls: List[StrategyCall] = []
        if self.session_factory:
            async with self.session_factory() as session:
                stmt = select(StrategyCall).where(StrategyCall.outcome_status == CallOutcomeStatus.OPEN.value)
                res = await session.execute(stmt)
                open_calls = list(res.scalars().all())
        else:
            open_calls = [
                c for c in self._memory_calls if c.outcome_status == CallOutcomeStatus.OPEN.value
            ]

        if not open_calls:
            return 0

        updates_count = 0
        now = datetime.now(timezone.utc)

        for call in open_calls:
            current_price = await self.collector.get_current_price(call.token_ca)
            if current_price is None or current_price <= 0.0:
                continue

            # Fetch market cap if available
            snapshot = await self.collector.fetch_token_snapshot(call.token_ca)
            current_mc = snapshot.market_cap_usd if snapshot else None

            if self.session_factory:
                async with self.session_factory() as session:
                    async with session.begin():
                        db_call_stmt = select(StrategyCall).where(StrategyCall.id == call.id)
                        db_call = (await session.execute(db_call_stmt)).scalar_one_or_none()
                        if db_call:
                            self.evaluate_tick(db_call, current_price, current_mc, now)
                            updates_count += 1
            else:
                self.evaluate_tick(call, current_price, current_mc, now)
                updates_count += 1

        return updates_count

    async def get_all_calls(self, limit: int = 100) -> List[StrategyCall]:
        """Retrieve recent strategy calls."""
        if self.session_factory:
            async with self.session_factory() as session:
                stmt = select(StrategyCall).order_by(desc(StrategyCall.id)).limit(limit)
                res = await session.execute(stmt)
                return list(res.scalars().all())
        else:
            return list(reversed(self._memory_calls))[:limit]

    async def get_research_statistics(self) -> Dict[str, Any]:
        """Compute comprehensive statistical metrics across completed strategy calls."""
        calls: List[StrategyCall] = []
        if self.session_factory:
            async with self.session_factory() as session:
                stmt = select(StrategyCall)
                res = await session.execute(stmt)
                calls = list(res.scalars().all())
        else:
            calls = self._memory_calls

        total = len(calls)
        open_count = sum(1 for c in calls if c.outcome_status == CallOutcomeStatus.OPEN.value)
        resolved = [c for c in calls if c.outcome_status == CallOutcomeStatus.RESOLVED.value]
        resolved_count = len(resolved)

        if resolved_count == 0:
            return {
                "total_calls": total,
                "open_calls": open_count,
                "resolved_calls": 0,
                "target_hit_count": 0,
                "invalidated_count": 0,
                "time_exit_count": 0,
                "expired_count": 0,
                "data_error_count": 0,
                "win_rate": 0.0,
                "avg_return_pct": 0.0,
                "avg_winner_pct": 0.0,
                "avg_loser_pct": 0.0,
                "avg_max_favorable_excursion": 0.0,
                "avg_max_adverse_excursion": 0.0,
                "avg_time_to_target_minutes": 0.0,
                "avg_time_to_invalidation_minutes": 0.0,
                "profit_factor": 0.0,
                "expectancy": 0.0,
            }

        target_hits = [c for c in resolved if c.result == CallResult.TARGET_HIT.value]
        invalidated = [c for c in resolved if c.result == CallResult.INVALIDATED.value]
        time_exits = [c for c in resolved if c.result == CallResult.TIME_EXIT.value]
        expired = [c for c in resolved if c.result == CallResult.EXPIRED.value]
        data_errors = [c for c in resolved if c.result == CallResult.DATA_ERROR.value]

        # Winners are target hits and positive time exits
        winners = [c for c in resolved if c.return_percentage > 0.0]
        losers = [c for c in resolved if c.return_percentage <= 0.0]

        win_rate = (len(target_hits) / resolved_count * 100.0) if resolved_count > 0 else 0.0

        avg_return = sum(c.return_percentage for c in resolved) / resolved_count
        avg_winner = sum(c.return_percentage for c in winners) / len(winners) if winners else 0.0
        avg_loser = sum(c.return_percentage for c in losers) / len(losers) if losers else 0.0

        avg_mfe = sum(c.max_favorable_excursion for c in resolved) / resolved_count
        avg_mae = sum(c.max_adverse_excursion for c in resolved) / resolved_count

        time_to_targets = [c.time_to_target for c in target_hits if c.time_to_target is not None]
        avg_time_to_target = (
            (sum(time_to_targets) / len(time_to_targets) / 60.0) if time_to_targets else 0.0
        )

        time_to_invals = [
            c.time_to_invalidation for c in invalidated if c.time_to_invalidation is not None
        ]
        avg_time_to_inval = (
            (sum(time_to_invals) / len(time_to_invals) / 60.0) if time_to_invals else 0.0
        )

        sum_gains = sum(c.return_percentage for c in winners)
        sum_losses = abs(sum(c.return_percentage for c in losers))
        profit_factor = (
            (sum_gains / sum_losses) if sum_losses > 0 else (99.0 if sum_gains > 0 else 0.0)
        )

        p_win = len(winners) / resolved_count
        p_loss = len(losers) / resolved_count
        expectancy = (p_win * avg_winner) - (p_loss * abs(avg_loser))

        return {
            "total_calls": total,
            "open_calls": open_count,
            "resolved_calls": resolved_count,
            "target_hit_count": len(target_hits),
            "invalidated_count": len(invalidated),
            "time_exit_count": len(time_exits),
            "expired_count": len(expired),
            "data_error_count": len(data_errors),
            "win_rate": round(win_rate, 2),
            "avg_return_pct": round(avg_return, 2),
            "avg_winner_pct": round(avg_winner, 2),
            "avg_loser_pct": round(avg_loser, 2),
            "avg_max_favorable_excursion": round(avg_mfe, 2),
            "avg_max_adverse_excursion": round(avg_mae, 2),
            "avg_time_to_target_minutes": round(avg_time_to_target, 1),
            "avg_time_to_invalidation_minutes": round(avg_time_to_inval, 1),
            "profit_factor": round(profit_factor, 2),
            "expectancy": round(expectancy, 2),
        }
