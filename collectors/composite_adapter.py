"""Composite market data provider merging primary market feeds with on-chain enrichment."""

import asyncio
import logging
from typing import List, Optional
from collectors.base import MarketDataProvider
from models.domain import TokenSnapshot

logger = logging.getLogger(__name__)


class CompositeMarketDataProvider(MarketDataProvider):
    """Aggregates a primary market feed (e.g. DexScreener) with on-chain enrichment (e.g. Solana RPC).

    Follows the strict strategy design:
    - Primary provider supplies real-time price, volume, and transaction flow.
    - Secondary provider enriches with holder concentration or security attributes.
    - If a metric cannot be enriched, it remains None. NEVER invent data.
    """

    def __init__(
        self,
        primary_provider: MarketDataProvider,
        enrichment_provider: Optional[MarketDataProvider] = None,
    ):
        self.primary = primary_provider
        self.enricher = enrichment_provider

    @property
    def provider_name(self) -> str:
        if self.enricher:
            return f"composite({self.primary.provider_name}+{self.enricher.provider_name})"
        return self.primary.provider_name

    async def fetch_token_snapshot(self, token_address: str) -> Optional[TokenSnapshot]:
        """Fetch primary snapshot and enrich with secondary provider if available."""
        snapshot = await self.primary.fetch_token_snapshot(token_address)
        if not snapshot or not self.enricher:
            return snapshot

        return await self._enrich_snapshot(snapshot)

    async def fetch_active_tokens(self, limit: int = 50) -> List[TokenSnapshot]:
        """Fetch active tokens from primary and enrich them."""
        snapshots = await self.primary.fetch_active_tokens(limit=limit)
        if not self.enricher or not snapshots:
            return snapshots

        # Enrich concurrently with bounded parallelism
        tasks = [self._enrich_snapshot(s) for s in snapshots]
        enriched = await asyncio.gather(*tasks, return_exceptions=True)

        results: List[TokenSnapshot] = []
        for i, res in enumerate(enriched):
            if isinstance(res, TokenSnapshot):
                results.append(res)
            else:
                # Fallback to unenriched snapshot on exception
                results.append(snapshots[i])

        return results

    async def _enrich_snapshot(self, snapshot: TokenSnapshot) -> TokenSnapshot:
        """Enrich missing metrics in snapshot from secondary provider."""
        if not self.enricher:
            return snapshot

        try:
            extra = await self.enricher.fetch_token_snapshot(snapshot.token_address)
            if not extra:
                return snapshot

            updates = {}
            if snapshot.top10_holder_pct is None and extra.top10_holder_pct is not None:
                updates["top10_holder_pct"] = extra.top10_holder_pct
            if snapshot.holders_count is None and extra.holders_count is not None:
                updates["holders_count"] = extra.holders_count
            if snapshot.change_4h_pct is None and extra.change_4h_pct is not None:
                updates["change_4h_pct"] = extra.change_4h_pct

            if updates:
                updates["provider_source"] = self.provider_name
                return snapshot.model_copy(update=updates)
        except Exception as e:
            logger.debug("Failed enrichment for %s: %s", snapshot.token_address, e)

        return snapshot

    async def get_current_price(self, token_address: str) -> Optional[float]:
        return await self.primary.get_current_price(token_address)

    async def health_check(self) -> bool:
        primary_ok = await self.primary.health_check()
        enricher_ok = await self.enricher.health_check() if self.enricher else True
        return primary_ok and enricher_ok
