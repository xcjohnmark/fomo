"""Abstract base class defining the MarketDataProvider interface."""

from abc import ABC, abstractmethod
from typing import List, Optional
from models.domain import TokenSnapshot


class MarketDataProvider(ABC):
    """Abstract interface that all exchange and market-data adapters must implement.

    This abstraction completely isolates the strategy engine and alerting services
    from underlying exchange APIs (DexScreener, Birdeye, Solana RPC, Pump.fun, etc.).
    The strategy engine must only consume TokenSnapshot objects.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique identifier of the data provider (e.g. 'dexscreener', 'birdeye', 'solana_rpc')."""
        pass

    @abstractmethod
    async def fetch_active_tokens(self, limit: int = 50) -> List[TokenSnapshot]:
        """Fetch and normalize a list of currently active or newly trending tokens.

        Returns:
            List of normalized TokenSnapshot objects ready for strategy evaluation.
        """
        pass

    @abstractmethod
    async def fetch_token_snapshot(self, token_address: str) -> Optional[TokenSnapshot]:
        """Fetch the latest normalized snapshot for a specific token mint/address.

        Args:
            token_address: The contract or mint address of the token.

        Returns:
            Normalized TokenSnapshot if found, None otherwise.
        """
        pass

    @abstractmethod
    async def get_current_price(self, token_address: str) -> Optional[float]:
        """Fetch real-time spot price in USD for outcome tracking.

        Args:
            token_address: The contract or mint address of the token.

        Returns:
            Current price in USD, or None if unavailable.
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify connectivity and health of the provider endpoints.

        Returns:
            True if healthy and reachable, False otherwise.
        """
        pass

    # Convenience aliases for BaseCollector compatibility
    async def get_active_tokens(self) -> List[TokenSnapshot]:
        return await self.fetch_active_tokens()

    async def get_token_snapshot(self, token_address: str) -> Optional[TokenSnapshot]:
        return await self.fetch_token_snapshot(token_address)


# Backward-compatible alias
BaseCollector = MarketDataProvider
