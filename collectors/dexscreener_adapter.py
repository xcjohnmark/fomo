"""DexScreener market data adapter normalizing public REST API responses."""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import httpx

from collectors.base import MarketDataProvider
from collectors.resilience import AsyncRateLimiter, execute_with_retry
from models.domain import TokenSnapshot

logger = logging.getLogger(__name__)


class DexScreenerAdapter(MarketDataProvider):
    """Adapter for DexScreener's public DEX API (https://api.dexscreener.com).

    Availability Notes:
    - Provides real-time Price, Market Cap, Liquidity, 5M/1H/24H Price Changes, 5M/1H/24H Volumes, and Buy/Sell Tx counts.
    - 4H change is UNAVAILABLE (DexScreener provides 6H instead). It is strictly set to None.
    - Unique buyer/seller wallets and holder distribution are UNAVAILABLE and strictly set to None.
    """

    BASE_URL = "https://api.dexscreener.com/latest/dex"

    def __init__(
        self,
        http_client: Optional[httpx.AsyncClient] = None,
        timeout_seconds: float = 10.0,
        rate_limiter: Optional[AsyncRateLimiter] = None,
    ):
        self._client = http_client
        self._timeout = timeout_seconds
        self._rate_limiter = rate_limiter or AsyncRateLimiter(max_rate_per_minute=300)

    @property
    def provider_name(self) -> str:
        return "dexscreener"

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    async def _fetch_url(self, url: str) -> httpx.Response:
        """Fetch URL with rate limiting and exponential retry on 429/5xx."""
        async with self._rate_limiter:
            client = await self._get_client()

            async def _do_req() -> httpx.Response:
                resp = await client.get(url)
                if resp.status_code in {429, 500, 502, 503, 504}:
                    resp.raise_for_status()
                return resp

            return await execute_with_retry(_do_req)

    def normalize_pair(self, pair: Dict[str, Any]) -> Optional[TokenSnapshot]:
        """Convert a raw DexScreener pair dictionary into a standardized TokenSnapshot."""
        if not pair:
            return None

        base_token = pair.get("baseToken", {})
        token_address = base_token.get("address")
        if not token_address:
            return None

        symbol = base_token.get("symbol")
        name = base_token.get("name")
        chain = pair.get("chainId", "solana")
        pool_address = pair.get("pairAddress")

        # Price
        price_str = pair.get("priceUsd")
        price_usd = float(price_str) if price_str is not None else None

        # Market Cap & Liquidity
        mc = pair.get("marketCap") or pair.get("fdv")
        market_cap_usd = float(mc) if mc is not None else None

        liq_obj = pair.get("liquidity") or {}
        liq_val = liq_obj.get("usd")
        liquidity_usd = float(liq_val) if liq_val is not None else None

        # Rolling percentage price changes
        price_change = pair.get("priceChange") or {}
        change_5m = float(price_change["m5"]) if "m5" in price_change and price_change["m5"] is not None else None
        change_1h = float(price_change["h1"]) if "h1" in price_change and price_change["h1"] is not None else None
        # DexScreener has "h6", NOT "h4". Strategy Rule 1: Never invent data. Set to None.
        change_4h = None
        change_24h = float(price_change["h24"]) if "h24" in price_change and price_change["h24"] is not None else None

        # Volume
        volume = pair.get("volume") or {}
        volume_5m = float(volume["m5"]) if "m5" in volume and volume["m5"] is not None else None
        volume_1h = float(volume["h1"]) if "h1" in volume and volume["h1"] is not None else None
        volume_24h = float(volume["h24"]) if "h24" in volume and volume["h24"] is not None else None

        # Transactions (Flow) - prioritize 1h txns for broader context, fallback to m5
        txns = pair.get("txns") or {}
        h1_txns = txns.get("h1") or {}
        m5_txns = txns.get("m5") or {}

        buys = h1_txns.get("buys") if "buys" in h1_txns else m5_txns.get("buys")
        sells = h1_txns.get("sells") if "sells" in h1_txns else m5_txns.get("sells")

        # Token Age
        pair_created_at = pair.get("pairCreatedAt")  # epoch milliseconds
        age_seconds: Optional[int] = None
        age_formatted: Optional[str] = None
        if pair_created_at:
            created_dt = datetime.fromtimestamp(pair_created_at / 1000.0, tz=timezone.utc)
            now_dt = datetime.now(timezone.utc)
            diff_secs = max(int((now_dt - created_dt).total_seconds()), 0)
            age_seconds = diff_secs
            hours = diff_secs // 3600
            minutes = (diff_secs % 3600) // 60
            if hours > 0:
                age_formatted = f"{hours}h {minutes}m"
            else:
                age_formatted = f"{minutes}m"

        return TokenSnapshot(
            token_address=token_address,
            chain=chain,
            pool_address=pool_address,
            symbol=symbol,
            name=name,
            timestamp=datetime.now(timezone.utc),
            provider_source=self.provider_name,
            price_usd=price_usd,
            market_cap_usd=market_cap_usd,
            liquidity_usd=liquidity_usd,
            change_5m_pct=change_5m,
            change_1h_pct=change_1h,
            change_4h_pct=change_4h,
            change_24h_pct=change_24h,
            volume_5m_usd=volume_5m,
            volume_1h_usd=volume_1h,
            volume_24h_usd=volume_24h,
            buys=int(buys) if buys is not None else None,
            sells=int(sells) if sells is not None else None,
            # Explicitly UNAVAILABLE from DexScreener:
            buy_volume_usd=None,
            sell_volume_usd=None,
            buyers=None,
            sellers=None,
            holders_count=None,
            top10_holder_pct=None,
            token_age_seconds=age_seconds,
            token_age_formatted=age_formatted,
            trader_activity_summary=None,
            narrative=None,
            raw_metadata=pair,
        )

    async def fetch_token_snapshot(self, token_address: str) -> Optional[TokenSnapshot]:
        """Fetch real-time snapshot for a token CA from DexScreener."""
        url = f"{self.BASE_URL}/tokens/{token_address}"
        try:
            resp = await self._fetch_url(url)
            if resp.status_code != 200:
                logger.warning("DexScreener token query returned %s for %s", resp.status_code, token_address)
                return None
            data = resp.json()
            pairs = data.get("pairs") or []
            if not pairs:
                return None
            # Select the most liquid Solana pair
            solana_pairs = [p for p in pairs if p.get("chainId") == "solana"]
            target_pairs = solana_pairs or pairs
            best_pair = max(
                target_pairs,
                key=lambda p: (p.get("liquidity") or {}).get("usd") or 0.0,
            )
            return self.normalize_pair(best_pair)
        except Exception as e:
            logger.error("Failed to fetch DexScreener token %s: %s", token_address, e)
            return None

    async def fetch_active_tokens(self, limit: int = 50) -> List[TokenSnapshot]:
        """Fetch trending / active tokens via DexScreener search."""
        url = f"{self.BASE_URL}/search?q=solana"
        try:
            resp = await self._fetch_url(url)
            if resp.status_code != 200:
                logger.warning("DexScreener search query returned %s", resp.status_code)
                return []
            data = resp.json()
            pairs = data.get("pairs") or []
            snapshots: List[TokenSnapshot] = []
            seen_tokens = set()
            for pair in pairs:
                if pair.get("chainId") != "solana":
                    continue
                snapshot = self.normalize_pair(pair)
                if snapshot and snapshot.token_address not in seen_tokens:
                    seen_tokens.add(snapshot.token_address)
                    snapshots.append(snapshot)
                    if len(snapshots) >= limit:
                        break
            return snapshots
        except Exception as e:
            logger.error("Failed to fetch active tokens from DexScreener: %s", e)
            return []

    async def get_current_price(self, token_address: str) -> Optional[float]:
        """Get latest spot price."""
        snapshot = await self.fetch_token_snapshot(token_address)
        return snapshot.price_usd if snapshot else None

    async def health_check(self) -> bool:
        """Verify DexScreener connectivity."""
        try:
            # Query a known stable Solana token (USDC)
            url = f"{self.BASE_URL}/tokens/EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
            resp = await self._fetch_url(url)
            return resp.status_code == 200
        except Exception as e:
            logger.warning("DexScreener health check failed: %s", e)
            return False

    async def close(self) -> None:
        """Close underlying HTTP client session."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
