"""Abstract base class defining the Data Provider / Collector contract."""

from abc import ABC, abstractmethod
from typing import List, Optional
from models.domain import NormalizedTokenData


class BaseCollector(ABC):
    """Abstract interface that all exchange / memecoin collectors must implement.

    This abstraction completely isolates the strategy engine and alerting services
    from underlying exchange APIs (Pump.fun, Raydium, DexScreener, Birdeye, etc.).
    """

    @abstractmethod
    async def get_active_tokens(self) -> List[NormalizedTokenData]:
        """Fetch and normalize a list of currently active or newly trending tokens.

        Returns:
            List of NormalizedTokenData snapshots ready for strategy evaluation.
        """
        pass

    @abstractmethod
    async def get_token_snapshot(self, token_address: str) -> Optional[NormalizedTokenData]:
        """Fetch the latest normalized snapshot for a specific token mint/address.

        Args:
            token_address: The contract or mint address of the token.

        Returns:
            NormalizedTokenData if found, None otherwise.
        """
        pass

    @abstractmethod
    async def get_current_price(self, token_address: str) -> Optional[float]:
        """Fetch the real-time spot price in USD for outcome tracking.

        Args:
            token_address: The contract or mint address of the token.

        Returns:
            Current price in USD, or None if unavailable.
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify connectivity and health of the provider's endpoints.

        Returns:
            True if healthy and reachable, False otherwise.
        """
        pass
