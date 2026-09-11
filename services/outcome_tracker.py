"""Outcome tracking and performance metrics calculation service (Sections 60, 61)."""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from collectors.base import BaseCollector, MarketDataProvider
from models.db import PriceObservation, SetupOutcome, TokenAlert

logger = logging.getLogger(__name__)


class OutcomeTracker:
    """Tracks post-alert price points (5m, 10m, 20m, 30m, 60m) and computes statistical metrics."""

    TARGET_INTERVALS = [5, 10, 20, 30, 60]

    def __init__(self, session_factory, collector: MarketDataProvider):
        self.session_factory = session_factory
        self.collector = collector

    async def track_open_alerts(self) -> int:
        """Evaluate all open alerts and record price observations where due."""
        now = datetime.now(timezone.utc)
        updates_count = 0

        async with self.session_factory() as session:
            stmt = (
                select(TokenAlert)
                .join(SetupOutcome)
                .where(SetupOutcome.status == "OPEN")
                .options(selectinload(TokenAlert.observations), selectinload(TokenAlert.outcome))
            )
            result = await session.execute(stmt)
            open_alerts = list(result.scalars().all())

        for alert in open_alerts:
            if alert.price is None or alert.price <= 0:
                continue

            current_price = await self.collector.get_current_price(alert.token_address)
            if current_price is None or current_price <= 0:
                continue

            # Calculate minutes elapsed since alert
            alert_ts = alert.alert_timestamp
            if alert_ts.tzinfo is None:
                alert_ts = alert_ts.replace(tzinfo=timezone.utc)
            elapsed_seconds = (now - alert_ts).total_seconds()
            elapsed_minutes = int(elapsed_seconds // 60)

            # Check if any observation intervals have been reached
            existing_intervals = {obs.interval_minutes for obs in alert.observations}

            async with self.session_factory() as session:
                async with session.begin():
                    outcome_stmt = select(SetupOutcome).where(SetupOutcome.alert_id == alert.id)
                    outcome_res = await session.execute(outcome_stmt)
                    outcome = outcome_res.scalar_one_or_none()
                    if not outcome:
                        continue

                    current_return = ((current_price - alert.price) / alert.price) * 100.0

                    # Update MFE and MAE
                    if current_return > outcome.max_favorable_excursion:
                        outcome.max_favorable_excursion = round(current_return, 2)
                    if current_return < outcome.max_adverse_excursion:
                        outcome.max_adverse_excursion = round(current_return, 2)

                    # Check for invalidation (e.g. sharp drop > 15% against setup)
                    if current_return <= -15.0 and not outcome.invalidation_triggered:
                        outcome.invalidation_triggered = True
                        outcome.invalidation_reason = f"Drop of {current_return:.1f}% exceeded invalidation threshold"
                        outcome.status = "INVALIDATED"
                        logger.warning("Alert ID %s for %s invalidated!", alert.id, alert.token_symbol)

                    for interval in self.TARGET_INTERVALS:
                        if elapsed_minutes >= interval and interval not in existing_intervals:
                            obs = PriceObservation(
                                alert_id=alert.id,
                                interval_minutes=interval,
                                observed_at=now,
                                price=current_price,
                                return_percentage=round(current_return, 2),
                            )
                            session.add(obs)
                            updates_count += 1
                            logger.info(
                                "Recorded %sm observation for %s (Alert ID: %s, Return: %s%%)",
                                interval,
                                alert.token_symbol,
                                alert.id,
                                round(current_return, 2),
                            )

                    # Close outcome after 60 minutes
                    if elapsed_minutes >= 60 and outcome.status == "OPEN":
                        outcome.final_return_percentage = round(current_return, 2)
                        outcome.is_winning = current_return > 0.0
                        outcome.status = "CLOSED"
                        logger.info(
                            "Closed outcome for %s (Final Return: %s%%)",
                            alert.token_symbol,
                            outcome.final_return_percentage,
                        )

        return updates_count

    async def calculate_research_statistics(self) -> Dict[str, Any]:
        """Compute aggregate performance statistics following Section 61."""
        async with self.session_factory() as session:
            stmt = select(SetupOutcome).where(SetupOutcome.status.in_(["CLOSED", "INVALIDATED"]))
            result = await session.execute(stmt)
            outcomes = list(result.scalars().all())

        if not outcomes:
            return {
                "total_completed_alerts": 0,
                "win_rate": 0.0,
                "average_winner_pct": 0.0,
                "average_loser_pct": 0.0,
                "expectancy": 0.0,
                "invalidated_count": 0,
            }

        total = len(outcomes)
        winners = [o for o in outcomes if o.is_winning is True]
        losers = [o for o in outcomes if o.is_winning is False or o.invalidation_triggered]
        invalidated = [o for o in outcomes if o.invalidation_triggered]

        win_rate = (len(winners) / total) if total > 0 else 0.0
        loss_rate = 1.0 - win_rate

        avg_win = (
            sum(w.final_return_percentage for w in winners) / len(winners)
            if winners
            else 0.0
        )
        avg_loss = (
            abs(sum(l.final_return_percentage for l in losers) / len(losers))
            if losers
            else 0.0
        )

        expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)

        return {
            "total_completed_alerts": total,
            "win_rate": round(win_rate * 100.0, 2),
            "average_winner_pct": round(avg_win, 2),
            "average_loser_pct": round(avg_loss, 2),
            "expectancy": round(expectancy, 2),
            "invalidated_count": len(invalidated),
        }
