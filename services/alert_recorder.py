"""Database persistence service for storing every detected alert candidate."""

import logging
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from models.db import SetupOutcome, TokenAlert
from models.domain import AlertCandidate

logger = logging.getLogger(__name__)


class AlertRecorder:
    """Persists alert candidates and initializes research outcome tracking (Section 60)."""

    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def record_alert(self, candidate: AlertCandidate) -> TokenAlert:
        """Persist a newly triggered alert candidate to the database."""
        token = candidate.token

        alert = TokenAlert(
            token_symbol=token.token,
            token_address=token.token_address,
            alert_timestamp=token.timestamp,
            market_cap=token.market_cap,
            price=token.price,
            liquidity=token.liquidity,
            change_5m=token.change_5m,
            change_1h=token.change_1h,
            change_4h=token.change_4h,
            change_24h=token.change_24h,
            volume_5m=token.volume_5m,
            volume_1h=token.volume_1h,
            volume_24h=token.volume_24h,
            buys=token.buys,
            sells=token.sells,
            buyers=token.buyers,
            sellers=token.sellers,
            holders=token.holders,
            top10_percentage=token.top10_percentage,
            age=token.age,
            trader_activity=token.trader_activity,
            narrative=token.narrative,
            momentum_score=candidate.score_result.score,
            classification=candidate.classification.value,
            confirmation_state=candidate.confirmation_state.value,
            alert_reason=candidate.alert_reason,
        )

        async with self.session_factory() as session:
            async with session.begin():
                session.add(alert)
                await session.flush()

                # Initialize tracking outcome record
                outcome = SetupOutcome(
                    alert_id=alert.id,
                    is_winning=None,
                    max_favorable_excursion=0.0,
                    max_adverse_excursion=0.0,
                    final_return_percentage=0.0,
                    status="OPEN",
                )
                session.add(outcome)

            await session.refresh(alert)
            logger.info(
                "Persisted alert ID %s for %s (%s)",
                alert.id,
                alert.token_symbol,
                alert.token_address,
            )
            return alert

    async def get_recent_alerts(self, limit: int = 50) -> List[TokenAlert]:
        """Fetch the most recent alerts with observations and outcome loaded."""
        async with self.session_factory() as session:
            stmt = (
                select(TokenAlert)
                .options(
                    selectinload(TokenAlert.observations),
                    selectinload(TokenAlert.outcome),
                )
                .order_by(TokenAlert.id.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())
