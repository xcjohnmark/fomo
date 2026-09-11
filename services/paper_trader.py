"""Paper trading ledger and simulation execution engine."""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from models.db import PaperTrade
from models.domain import QuickFlipPlan, TokenSnapshot

logger = logging.getLogger(__name__)


class PaperTraderService:
    """Simulates disciplined trade entries, targets, stop-losses, and records performance metrics."""

    def __init__(self, session_factory: Optional[async_sessionmaker[AsyncSession]] = None):
        self.session_factory = session_factory
        # In-memory fallback if session factory is not provided (e.g. lightweight unit tests)
        self._memory_trades: List[PaperTrade] = []
        self._next_id = 1

    async def open_trade(
        self,
        token_address: str,
        symbol: Optional[str],
        entry_price: float,
        entry_market_cap: Optional[float] = None,
        target_price: Optional[float] = None,
        target_market_cap: Optional[float] = None,
        invalidation_price: Optional[float] = None,
        invalidation_market_cap: Optional[float] = None,
        expected_holding_minutes: Optional[int] = 30,
        notes: Optional[str] = None,
        entry_timestamp: Optional[datetime] = None,
    ) -> PaperTrade:
        """Execute a simulated buy trade and record paper entry parameters."""
        now = entry_timestamp or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        trade = PaperTrade(
            token_address=token_address,
            symbol=symbol,
            paper_entry_timestamp=now,
            paper_entry_price=entry_price,
            paper_entry_mc=entry_market_cap,
            target_price=target_price,
            target_market_cap=target_market_cap,
            invalidation_price=invalidation_price,
            invalidation_market_cap=invalidation_market_cap,
            status="OPEN",
            expected_holding_minutes=expected_holding_minutes,
            notes=notes,
        )

        if self.session_factory:
            async with self.session_factory() as session:
                async with session.begin():
                    session.add(trade)
                await session.refresh(trade)
                logger.info(
                    "Opened simulated paper trade for %s: Entry Price $%s, MC $%s at %s",
                    symbol or token_address,
                    entry_price,
                    entry_market_cap,
                    now.strftime("%H:%M:%S UTC"),
                )
                return trade
        else:
            trade.id = self._next_id
            self._next_id += 1
            self._memory_trades.append(trade)
            return trade

    async def open_from_plan(
        self, plan: QuickFlipPlan, current_snapshot: TokenSnapshot
    ) -> PaperTrade:
        """Execute a simulated buy entry from a QuickFlipPlan."""
        entry_price = plan.entry_price or current_snapshot.price_usd or 0.0
        return await self.open_trade(
            token_address=plan.token_address,
            symbol=plan.symbol or current_snapshot.symbol,
            entry_price=entry_price,
            entry_market_cap=plan.entry_market_cap or current_snapshot.market_cap_usd,
            target_price=plan.target_price,
            target_market_cap=plan.target_market_cap,
            invalidation_price=plan.invalidation_price,
            invalidation_market_cap=plan.invalidation_market_cap,
            expected_holding_minutes=plan.expected_holding_minutes or 30,
            notes=plan.plan_reason,
        )

    def evaluate_paper_tick(
        self,
        trade: PaperTrade,
        current_price: float,
        current_market_cap: Optional[float] = None,
        current_time: Optional[datetime] = None,
    ) -> PaperTrade:
        """Evaluate market price against an open paper trade adhering to strict discipline."""
        if trade.status not in ("OPEN",):
            return trade

        now = current_time or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        entry_ts = trade.paper_entry_timestamp
        if entry_ts.tzinfo is None:
            entry_ts = entry_ts.replace(tzinfo=timezone.utc)

        elapsed_minutes = (now - entry_ts).total_seconds() / 60.0
        pnl_pct = (
            ((current_price - trade.paper_entry_price) / trade.paper_entry_price) * 100.0
            if trade.paper_entry_price > 0
            else 0.0
        )

        # 1. Invalidation First
        if trade.invalidation_price is not None and current_price <= trade.invalidation_price:
            trade.status = "INVALIDATED"
            trade.paper_exit_price = current_price
            trade.paper_exit_mc = current_market_cap
            trade.paper_exit_timestamp = now
            trade.paper_exit_reason = "INVALIDATED"
            trade.paper_pnl_pct = round(pnl_pct, 2)
            logger.info("Paper trade for %s hit invalidation (%s%%)", trade.symbol, trade.paper_pnl_pct)
            return trade

        # 2. Target Hit
        if trade.target_price is not None and current_price >= trade.target_price:
            trade.status = "TARGET_HIT"
            trade.paper_exit_price = current_price
            trade.paper_exit_mc = current_market_cap
            trade.paper_exit_timestamp = now
            trade.paper_exit_reason = "TARGET_HIT"
            trade.paper_pnl_pct = round(pnl_pct, 2)
            logger.info("Paper trade for %s reached target (+%s%%)", trade.symbol, trade.paper_pnl_pct)
            return trade

        # 3. Expiration Check
        exp_min = trade.expected_holding_minutes or 30
        if elapsed_minutes >= (exp_min * 2.0):
            trade.status = "TIME_EXIT" if pnl_pct > 0 else "EXPIRED"
            trade.paper_exit_price = current_price
            trade.paper_exit_mc = current_market_cap
            trade.paper_exit_timestamp = now
            trade.paper_exit_reason = trade.status
            trade.paper_pnl_pct = round(pnl_pct, 2)
            logger.info("Paper trade for %s closed on time (%s%%)", trade.symbol, trade.paper_pnl_pct)
            return trade

        return trade

    async def close_trade(
        self,
        token_address: str,
        exit_price: float,
        reason: str = "CLOSED_MANUAL",
    ) -> Optional[PaperTrade]:
        """Close an open paper trade and compute return percentage."""
        if self.session_factory:
            async with self.session_factory() as session:
                async with session.begin():
                    stmt = (
                        select(PaperTrade)
                        .where(PaperTrade.token_address == token_address, PaperTrade.status == "OPEN")
                        .order_by(desc(PaperTrade.id))
                        .limit(1)
                    )
                    res = await session.execute(stmt)
                    trade = res.scalar_one_or_none()
                    if not trade:
                        return None

                    pnl_pct = (
                        ((exit_price - trade.paper_entry_price) / trade.paper_entry_price) * 100.0
                        if trade.paper_entry_price > 0
                        else 0.0
                    )
                    trade.status = reason
                    trade.paper_exit_price = exit_price
                    trade.paper_exit_timestamp = datetime.now(timezone.utc)
                    trade.paper_exit_reason = reason
                    trade.paper_pnl_pct = round(pnl_pct, 2)
                await session.refresh(trade)
                return trade
        else:
            for trade in reversed(self._memory_trades):
                if trade.token_address == token_address and trade.status == "OPEN":
                    pnl_pct = (
                        ((exit_price - trade.paper_entry_price) / trade.paper_entry_price) * 100.0
                        if trade.paper_entry_price > 0
                        else 0.0
                    )
                    trade.status = reason
                    trade.paper_exit_price = exit_price
                    trade.paper_exit_timestamp = datetime.now(timezone.utc)
                    trade.paper_exit_reason = reason
                    trade.paper_pnl_pct = round(pnl_pct, 2)
                    return trade
            return None

    async def monitor_open_paper_trades(self, collector) -> int:
        """Evaluate all open paper trades against current market prices."""
        if not collector:
            return 0

        open_trades: List[PaperTrade] = []
        if self.session_factory:
            async with self.session_factory() as session:
                stmt = select(PaperTrade).where(PaperTrade.status == "OPEN")
                res = await session.execute(stmt)
                open_trades = list(res.scalars().all())
        else:
            open_trades = [t for t in self._memory_trades if t.status == "OPEN"]

        if not open_trades:
            return 0

        now = datetime.now(timezone.utc)
        resolved_count = 0

        for trade in open_trades:
            price = await collector.get_current_price(trade.token_address)
            if price is None or price <= 0:
                continue

            snapshot = await collector.fetch_token_snapshot(trade.token_address)
            mc = snapshot.market_cap_usd if snapshot else None

            if self.session_factory:
                async with self.session_factory() as session:
                    async with session.begin():
                        db_stmt = select(PaperTrade).where(PaperTrade.id == trade.id)
                        db_trade = (await session.execute(db_stmt)).scalar_one_or_none()
                        if db_trade:
                            self.evaluate_paper_tick(db_trade, price, mc, now)
                            if db_trade.status != "OPEN":
                                resolved_count += 1
            else:
                self.evaluate_paper_tick(trade, price, mc, now)
                if trade.status != "OPEN":
                    resolved_count += 1

        return resolved_count

    async def get_open_trades(self) -> List[Dict[str, Any]]:
        """Retrieve all active open paper positions."""
        trades: List[PaperTrade] = []
        if self.session_factory:
            async with self.session_factory() as session:
                stmt = select(PaperTrade).where(PaperTrade.status == "OPEN").order_by(desc(PaperTrade.id))
                res = await session.execute(stmt)
                trades = list(res.scalars().all())
        else:
            trades = [t for t in self._memory_trades if t.status == "OPEN"]

        return [
            {
                "id": t.id,
                "token_address": t.token_address,
                "symbol": t.symbol,
                "entry_price": t.paper_entry_price,
                "entry_market_cap": t.paper_entry_mc,
                "entry_timestamp": t.paper_entry_timestamp,
                "target_price": t.target_price,
                "target_market_cap": t.target_market_cap,
                "invalidation_price": t.invalidation_price,
                "invalidation_market_cap": t.invalidation_market_cap,
                "status": t.status,
                "unrealized_pnl_pct": 0.0,
            }
            for t in trades
        ]

    async def get_recent_closed(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recently resolved simulated trades."""
        trades: List[PaperTrade] = []
        if self.session_factory:
            async with self.session_factory() as session:
                stmt = (
                    select(PaperTrade)
                    .where(PaperTrade.status != "OPEN")
                    .order_by(desc(PaperTrade.paper_exit_timestamp), desc(PaperTrade.id))
                    .limit(limit)
                )
                res = await session.execute(stmt)
                trades = list(res.scalars().all())
        else:
            trades = [t for t in self._memory_trades if t.status != "OPEN"][-limit:]

        return [
            {
                "id": t.id,
                "token_address": t.token_address,
                "symbol": t.symbol,
                "status": t.status,
                "pnl_pct": t.paper_pnl_pct or 0.0,
                "entry_price": t.paper_entry_price,
                "entry_mc": t.paper_entry_mc,
                "exit_price": t.paper_exit_price,
                "exit_mc": t.paper_exit_mc,
                "exit_time": t.paper_exit_timestamp,
                "exit_reason": t.paper_exit_reason,
            }
            for t in trades
        ]

    async def get_performance_stats(self) -> Dict[str, Any]:
        """Compute aggregate simulation metrics across closed paper trades."""
        trades: List[PaperTrade] = []
        if self.session_factory:
            async with self.session_factory() as session:
                stmt = select(PaperTrade).where(PaperTrade.status != "OPEN")
                res = await session.execute(stmt)
                trades = list(res.scalars().all())
        else:
            trades = [t for t in self._memory_trades if t.status != "OPEN"]

        total = len(trades)
        if total == 0:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "avg_gain_pct": 0.0,
                "avg_loss_pct": 0.0,
                "profit_factor": 0.0,
                "invalidation_rate": 0.0,
            }

        wins = [t.paper_pnl_pct for t in trades if (t.paper_pnl_pct or 0.0) > 0]
        losses = [t.paper_pnl_pct for t in trades if (t.paper_pnl_pct or 0.0) <= 0]
        invalidated = [t for t in trades if t.paper_exit_reason == "INVALIDATED"]

        avg_gain = sum(wins) / len(wins) if wins else 0.0
        avg_loss = sum(losses) / len(losses) if losses else 0.0
        sum_wins = sum(wins)
        sum_losses = abs(sum(losses))
        profit_factor = (sum_wins / sum_losses) if sum_losses > 0 else (99.0 if sum_wins > 0 else 0.0)
        invalidation_rate = (len(invalidated) / total) * 100.0

        return {
            "total_trades": total,
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "avg_gain_pct": avg_gain,
            "avg_loss_pct": avg_loss,
            "profit_factor": profit_factor,
            "invalidation_rate": invalidation_rate,
        }
