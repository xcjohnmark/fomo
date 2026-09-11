"""Automated market-data collector service managing ingestion, deduplication, and persistence."""

import asyncio
from datetime import datetime, timezone
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from collectors.base import MarketDataProvider
from models.db import DataSource, MarketSnapshot, Pool, Token
from models.domain import TokenSnapshot

logger = logging.getLogger(__name__)


def compute_snapshot_hash(snapshot: TokenSnapshot) -> str:
    """Generate deterministic SHA-256 hash of core market metrics for deduplication."""
    payload = {
        "price": snapshot.price_usd,
        "mc": snapshot.market_cap_usd,
        "liq": snapshot.liquidity_usd,
        "vol5m": snapshot.volume_5m_usd,
        "vol1h": snapshot.volume_1h_usd,
        "buys": snapshot.buys,
        "sells": snapshot.sells,
    }
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class AutomatedDataCollector:
    """Resilient automated market-data collector.

    Features:
    - Normalizes token data into TokenSnapshot.
    - Preserves external provider timestamps.
    - Upserts token registries and pool pairs.
    - Deduplicates unchanged observations within a time window.
    - Operates completely independently from the strategy engine (zero alerts).
    """

    def __init__(
        self,
        session_factory,
        provider: MarketDataProvider,
        dedupe_window_seconds: int = 60,
    ):
        self.session_factory = session_factory
        self.provider = provider
        self.dedupe_window_seconds = dedupe_window_seconds
        self._cached_source_id: Optional[int] = None

    async def get_or_create_data_source(self, session: AsyncSession) -> DataSource:
        """Fetch or initialize the DataSource record for the current provider."""
        stmt = select(DataSource).where(DataSource.name == self.provider.provider_name)
        result = await session.execute(stmt)
        source = result.scalar_one_or_none()

        if source is None:
            source = DataSource(
                name=self.provider.provider_name,
                version="v1.0",
                rate_limit_per_minute=300,
                is_active=True,
            )
            session.add(source)
            await session.flush()
            logger.info("Registered new data source: %s (ID: %s)", source.name, source.id)

        self._cached_source_id = source.id
        return source

    async def upsert_token_and_pool(
        self, session: AsyncSession, snapshot: TokenSnapshot
    ) -> Tuple[Token, Optional[Pool]]:
        """Upsert token and associated pool records."""
        # 1. Upsert Token
        stmt_t = select(Token).where(Token.address == snapshot.token_address)
        res_t = await session.execute(stmt_t)
        token = res_t.scalar_one_or_none()

        if token is None:
            token = Token(
                address=snapshot.token_address,
                chain=snapshot.chain,
                symbol=snapshot.symbol,
                name=snapshot.name,
            )
            session.add(token)
            await session.flush()
        else:
            # Update symbol or name if updated or previously unknown
            if snapshot.symbol and token.symbol != snapshot.symbol:
                token.symbol = snapshot.symbol
            if snapshot.name and token.name != snapshot.name:
                token.name = snapshot.name

        # 2. Upsert Pool (if provided)
        pool = None
        if snapshot.pool_address:
            stmt_p = select(Pool).where(Pool.address == snapshot.pool_address)
            res_p = await session.execute(stmt_p)
            pool = res_p.scalar_one_or_none()

            if pool is None:
                pool = Pool(
                    address=snapshot.pool_address,
                    token_id=token.id,
                    chain=snapshot.chain,
                )
                session.add(pool)
                await session.flush()

        return token, pool

    async def store_snapshot(
        self, session: AsyncSession, snapshot: TokenSnapshot
    ) -> Optional[MarketSnapshot]:
        """Store a timestamped snapshot if it represents new data (deduplication)."""
        data_source = await self.get_or_create_data_source(session)
        token, pool = await self.upsert_token_and_pool(session, snapshot)

        # Compute metric hash
        data_hash = compute_snapshot_hash(snapshot)

        # Check most recent snapshot for this token to deduplicate identical observations
        stmt_recent = (
            select(MarketSnapshot)
            .where(MarketSnapshot.token_id == token.id)
            .order_by(MarketSnapshot.id.desc())
            .limit(1)
        )
        res_recent = await session.execute(stmt_recent)
        most_recent = res_recent.scalar_one_or_none()

        captured_at = snapshot.timestamp
        if captured_at.tzinfo is None:
            captured_at = captured_at.replace(tzinfo=timezone.utc)

        if most_recent is not None:
            # Check if metrics are identical
            if most_recent.raw_data_hash == data_hash:
                recent_ts = most_recent.captured_at
                if recent_ts.tzinfo is None:
                    recent_ts = recent_ts.replace(tzinfo=timezone.utc)
                elapsed = (captured_at - recent_ts).total_seconds()

                if elapsed < self.dedupe_window_seconds:
                    logger.debug(
                        "Deduplicated identical observation for %s (Elapsed: %.1fs < %ds)",
                        snapshot.token,
                        elapsed,
                        self.dedupe_window_seconds,
                    )
                    return None

        # Insert new timestamped snapshot
        db_snapshot = MarketSnapshot(
            token_id=token.id,
            pool_id=pool.id if pool else None,
            data_source_id=data_source.id,
            captured_at=captured_at,
            price_usd=snapshot.price_usd,
            market_cap_usd=snapshot.market_cap_usd,
            liquidity_usd=snapshot.liquidity_usd,
            change_5m_pct=snapshot.change_5m_pct,
            change_1h_pct=snapshot.change_1h_pct,
            change_4h_pct=snapshot.change_4h_pct,
            change_24h_pct=snapshot.change_24h_pct,
            volume_5m_usd=snapshot.volume_5m_usd,
            volume_1h_usd=snapshot.volume_1h_usd,
            volume_24h_usd=snapshot.volume_24h_usd,
            buys=snapshot.buys,
            sells=snapshot.sells,
            buy_volume_usd=snapshot.buy_volume_usd,
            sell_volume_usd=snapshot.sell_volume_usd,
            buyers=snapshot.buyers,
            sellers=snapshot.sellers,
            holders_count=snapshot.holders_count,
            top10_holder_pct=snapshot.top10_holder_pct,
            token_age_seconds=snapshot.token_age_seconds,
            raw_data_hash=data_hash,
        )
        session.add(db_snapshot)
        await session.flush()
        return db_snapshot

    async def collect_snapshots_once(
        self, limit: int = 5, target_addresses: Optional[List[str]] = None
    ) -> List[MarketSnapshot]:
        """Execute one controlled collection pass across eligible tokens."""
        snapshots_to_ingest: List[TokenSnapshot] = []

        try:
            if target_addresses:
                logger.info("Collecting snapshots for %d specific tokens...", len(target_addresses))
                for addr in target_addresses:
                    try:
                        snap = await self.provider.fetch_token_snapshot(addr)
                        if snap:
                            snapshots_to_ingest.append(snap)
                    except Exception as e:
                        logger.error("Failed to fetch token snapshot for %s: %s", addr, e)
            else:
                logger.info("Discovering up to %d active tokens via %s...", limit, self.provider.provider_name)
                snapshots_to_ingest = await self.provider.fetch_active_tokens(limit=limit)

        except Exception as e:
            logger.error("Provider collection failure: %s", e, exc_info=True)
            return []

        stored_snapshots: List[MarketSnapshot] = []
        deduped_count = 0

        async with self.session_factory() as session:
            async with session.begin():
                for snap in snapshots_to_ingest:
                    try:
                        saved = await self.store_snapshot(session, snap)
                        if saved is not None:
                            stored_snapshots.append(saved)
                            logger.info(
                                "Stored snapshot for %s | Price: $%s | MC: $%s | Vol5M: $%s",
                                snap.token,
                                f"{snap.price_usd:.8f}" if snap.price_usd else "N/A",
                                f"{snap.market_cap_usd:,.0f}" if snap.market_cap_usd else "N/A",
                                f"{snap.volume_5m_usd:,.0f}" if snap.volume_5m_usd else "N/A",
                            )
                        else:
                            deduped_count += 1
                    except Exception as e:
                        logger.error("Failed to persist snapshot for %s: %s", snap.token, e)

        logger.info(
            "Collection pass complete: %d discovered, %d stored, %d deduplicated.",
            len(snapshots_to_ingest),
            len(stored_snapshots),
            deduped_count,
        )
        return stored_snapshots

    async def run_collection_loop(
        self,
        stop_event: asyncio.Event,
        interval_seconds: int = 30,
        limit: int = 5,
        target_addresses: Optional[List[str]] = None,
    ) -> None:
        """Run continuous background collection loop until stop_event is triggered."""
        logger.info(
            "Starting automated collection loop (Interval: %ds, Limit: %d, Provider: %s)",
            interval_seconds,
            limit,
            self.provider.provider_name,
        )

        while not stop_event.is_set():
            try:
                await self.collect_snapshots_once(limit=limit, target_addresses=target_addresses)
            except Exception as e:
                logger.error("Unexpected error in collection loop: %s", e, exc_info=True)

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
            except asyncio.TimeoutError:
                pass

        logger.info("Automated collection loop stopped gracefully.")

    async def get_stats(self) -> Dict[str, int]:
        """Fetch total counts for tokens, pools, snapshots, and sources."""
        async with self.session_factory() as session:
            t_count = (await session.execute(select(func.count(Token.id)))).scalar() or 0
            p_count = (await session.execute(select(func.count(Pool.id)))).scalar() or 0
            s_count = (await session.execute(select(func.count(MarketSnapshot.id)))).scalar() or 0
            src_count = (await session.execute(select(func.count(DataSource.id)))).scalar() or 0

            return {
                "tokens": t_count,
                "pools": p_count,
                "market_snapshots": s_count,
                "data_sources": src_count,
            }
