"""Birdeye DeFi market data adapter normalizing authenticated REST API responses."""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import httpx

from collectors.base import MarketDataProvider
from models.domain import TokenSnapshot

logger = logging.getLogger(__name__)


class BirdeyeAdapter(MarketDataProvider):
    """Adapter for Birdeye DeFi API (https://public-api.birdeye.so).

    Availability Notes:
    - Provides Price, MC, Liquidity, 5M/1H/4H/24H Price Changes, 5M/1H/4H/24H Volumes, Buy/Sell Flow, and Token Security.
    - Security endpoint provides total holder count and exact top-10 concentration % (top10UserPercent).
    - Requires an X-API-KEY header from Birdeye Data Services.
    """

    BASE_URL = "https://public-api.birdeye.so"

    def __init__(
        self,
        api_key: Optional[str] = None,
        http_client: Optional[httpx.AsyncClient] = None,
        timeout_seconds: float = 10.0,
    ):
        self.api_key = api_key
        self._client = http_client
        self._timeout = timeout_seconds

    @property
    def provider_name(self) -> str:
        return "birdeye"

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {"X-API-KEY": self.api_key} if self.api_key else {}
            self._client = httpx.AsyncClient(timeout=self._timeout, headers=headers)
        return self._client

    def normalize_birdeye_payload(
        self,
        overview: Dict[str, Any],
        security: Optional[Dict[str, Any]] = None,
    ) -> Optional[TokenSnapshot]:
        """Convert raw Birdeye overview and security payloads into a TokenSnapshot."""
        if not overview:
            return None

        data = overview.get("data") or overview
        sec_data = (security.get("data") or security) if security else {}

        token_address = data.get("address")
        if not token_address:
            return None

        symbol = data.get("symbol")
        name = data.get("name")

        price_usd = float(data["price"]) if data.get("price") is not None else None
        market_cap_usd = float(data["mc"]) if data.get("mc") is not None else (
            float(data["realMc"]) if data.get("realMc") is not None else None
        )
        liquidity_usd = float(data["liquidity"]) if data.get("liquidity") is not None else None

        # Price changes
        change_5m = float(data["priceChange5mPercent"]) if data.get("priceChange5mPercent") is not None else None
        change_1h = float(data["priceChange1hPercent"]) if data.get("priceChange1hPercent") is not None else None
        change_4h = float(data["priceChange4hPercent"]) if data.get("priceChange4hPercent") is not None else None
        change_24h = float(data["priceChange24hPercent"]) if data.get("priceChange24hPercent") is not None else None

        # Volume
        v5m = data.get("v5mUSD") or data.get("volume5mUSD")
        v1h = data.get("v1hUSD") or data.get("volume1hUSD")
        v24h = data.get("v24hUSD") or data.get("volume24hUSD")

        volume_5m = float(v5m) if v5m is not None else None
        volume_1h = float(v1h) if v1h is not None else None
        volume_24h = float(v24h) if v24h is not None else None

        # Flow
        buys = data.get("buy1h") or data.get("buy5m")
        sells = data.get("sell1h") or data.get("sell5m")
        buy_vol = data.get("buyVolume1h") or data.get("buyVolume5m")
        sell_vol = data.get("sellVolume1h") or data.get("sellVolume5m")

        # Security & Holder distribution
        holders_count = sec_data.get("holder") or data.get("holder")
        top10_val = sec_data.get("top10UserPercent")
        top10_pct: Optional[float] = None
        if top10_val is not None:
            # Birdeye top10UserPercent is sometimes 0.18 for 18% or 18.0
            top10_float = float(top10_val)
            top10_pct = top10_float * 100.0 if top10_float <= 1.0 else top10_float

        return TokenSnapshot(
            token_address=token_address,
            chain="solana",
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
            buy_volume_usd=float(buy_vol) if buy_vol is not None else None,
            sell_volume_usd=float(sell_vol) if sell_vol is not None else None,
            buyers=None,
            sellers=None,
            holders_count=int(holders_count) if holders_count is not None else None,
            top10_holder_pct=top10_pct,
            token_age_seconds=None,
            token_age_formatted=None,
            trader_activity_summary=None,
            narrative=None,
            raw_metadata={"overview": overview, "security": security},
        )

    async def fetch_token_snapshot(self, token_address: str) -> Optional[TokenSnapshot]:
        """Fetch overview and security data from Birdeye API."""
        if not self.api_key:
            logger.debug("Birdeye API key not configured; skipping live fetch.")
            return None

        client = await self._get_client()
        overview_url = f"{self.BASE_URL}/defi/token_overview?address={token_address}"
        security_url = f"{self.BASE_URL}/defi/token_security?address={token_address}"

        try:
            resp_ov = await client.get(overview_url)
            if resp_ov.status_code != 200:
                return None
            overview_data = resp_ov.json()

            security_data = None
            try:
                resp_sec = await client.get(security_url)
                if resp_sec.status_code == 200:
                    security_data = resp_sec.json()
            except Exception:
                pass

            return self.normalize_birdeye_payload(overview_data, security_data)
        except Exception as e:
            logger.error("Failed to fetch Birdeye data for %s: %s", token_address, e)
            return None

    async def fetch_active_tokens(self, limit: int = 50) -> List[TokenSnapshot]:
        """Fetch trending tokens from Birdeye token list."""
        if not self.api_key:
            return []
        client = await self._get_client()
        url = f"{self.BASE_URL}/defi/tokenlist?sort_by=v24hUSD&sort_type=desc&offset=0&limit={limit}"
        try:
            resp = await client.get(url)
            if resp.status_code != 200:
                return []
            data = resp.json().get("data", {}).get("tokens", [])
            snapshots = []
            for item in data:
                snapshot = self.normalize_birdeye_payload(item)
                if snapshot:
                    snapshots.append(snapshot)
            return snapshots
        except Exception as e:
            logger.error("Failed to fetch active tokens from Birdeye: %s", e)
            return []

    async def get_current_price(self, token_address: str) -> Optional[float]:
        snapshot = await self.fetch_token_snapshot(token_address)
        return snapshot.price_usd if snapshot else None

    async def health_check(self) -> bool:
        if not self.api_key:
            # Considered healthy in unconfigured/dry-run mode
            return True
        client = await self._get_client()
        try:
            url = f"{self.BASE_URL}/defi/price?address=So11111111111111111111111111111111111111112"
            resp = await client.get(url)
            return resp.status_code == 200
        except Exception as e:
            logger.warning("Birdeye health check failed: %s", e)
            return False

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
