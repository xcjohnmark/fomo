"""Solana JSON-RPC / Helius adapter for authoritative on-chain holder distribution."""

import logging
from typing import Any, Dict, List, Optional
import httpx

from collectors.base import MarketDataProvider
from models.domain import TokenSnapshot

logger = logging.getLogger(__name__)


class HeliusRpcAdapter(MarketDataProvider):
    """Adapter querying Solana JSON-RPC methods (e.g. via Helius, QuickNode, or public RPC).

    Capabilities:
    - Queries `getTokenLargestAccounts` to calculate authoritative Top-10 concentration %.
    - Queries `getTokenSupply` to verify token supply and decimals.
    """

    def __init__(
        self,
        rpc_url: str = "https://api.mainnet-beta.solana.com",
        api_key: Optional[str] = None,
        http_client: Optional[httpx.AsyncClient] = None,
        timeout_seconds: float = 10.0,
    ):
        if api_key and "helius.xyz" in rpc_url and "api-key" not in rpc_url:
            self.rpc_url = f"{rpc_url}?api-key={api_key}"
        else:
            self.rpc_url = rpc_url
        self._client = http_client
        self._timeout = timeout_seconds

    @property
    def provider_name(self) -> str:
        return "solana_rpc"

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    async def get_top10_concentration(self, token_mint: str) -> Optional[float]:
        """Calculate top 10 holder concentration % using getTokenLargestAccounts and getTokenSupply."""
        client = await self._get_client()

        supply_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTokenSupply",
            "params": [token_mint],
        }

        largest_payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "getTokenLargestAccounts",
            "params": [token_mint],
        }

        try:
            resp_sup = await client.post(self.rpc_url, json=supply_payload)
            resp_lar = await client.post(self.rpc_url, json=largest_payload)

            if resp_sup.status_code != 200 or resp_lar.status_code != 200:
                return None

            sup_res = resp_sup.json().get("result", {}).get("value", {})
            lar_res = resp_lar.json().get("result", {}).get("value", [])

            total_supply_raw = float(sup_res.get("amount", 0))
            if total_supply_raw <= 0 or not lar_res:
                return None

            # Sum top 10 accounts
            top10_sum = sum(float(acc.get("amount", 0)) for acc in lar_res[:10])
            concentration_pct = (top10_sum / total_supply_raw) * 100.0
            return round(concentration_pct, 2)
        except Exception as e:
            logger.debug("Failed to calculate top 10 concentration for %s: %s", token_mint, e)
            return None

    async def fetch_token_snapshot(self, token_address: str) -> Optional[TokenSnapshot]:
        """RPC adapter returns partial on-chain snapshot containing holder concentration."""
        top10 = await self.get_top10_concentration(token_address)
        return TokenSnapshot(
            token_address=token_address,
            chain="solana",
            provider_source=self.provider_name,
            top10_holder_pct=top10,
        )

    async def fetch_active_tokens(self, limit: int = 50) -> List[TokenSnapshot]:
        """Standard JSON-RPC does not index active market pools natively without Geyser."""
        return []

    async def get_current_price(self, token_address: str) -> Optional[float]:
        return None

    async def health_check(self) -> bool:
        client = await self._get_client()
        payload = {"jsonrpc": "2.0", "id": 1, "method": "getHealth"}
        try:
            resp = await client.post(self.rpc_url, json=payload)
            return resp.status_code == 200
        except Exception as e:
            logger.warning("Solana RPC health check failed: %s", e)
            return False

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
