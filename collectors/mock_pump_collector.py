"""Mock market data provider for deterministic testing and synthetic feeds."""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from collectors.base import MarketDataProvider
from models.domain import TokenSnapshot


class MockPumpCollector(MarketDataProvider):
    """Reference mock provider satisfying MarketDataProvider returning TokenSnapshot objects."""

    def __init__(self, initial_tokens: Optional[List[TokenSnapshot]] = None):
        self._tokens: Dict[str, TokenSnapshot] = {}
        if initial_tokens:
            for t in initial_tokens:
                self._tokens[t.token_address] = t
        else:
            self._load_default_scenarios()

    @property
    def provider_name(self) -> str:
        return "mock_pump_provider"

    def _load_default_scenarios(self) -> None:
        """Load standard test tokens representing key scenarios from STRATEGY.md."""
        now = datetime.now(timezone.utc)

        # 1. High Score Candidate (Scenario 1 & Section 38 template: Score ~88+)
        xyz = TokenSnapshot(
            timestamp=now,
            provider_source=self.provider_name,
            symbol="XYZ",
            name="XYZ Token",
            token_address="XYZpump11111111111111111111111111111111111",
            chain="solana",
            market_cap_usd=180000.0,
            price_usd=0.00018,
            liquidity_usd=42000.0,
            change_5m_pct=7.2,
            change_1h_pct=18.4,
            change_4h_pct=11.2,
            change_24h_pct=45.8,
            volume_5m_usd=14000.0,
            volume_1h_usd=91000.0,
            volume_24h_usd=420000.0,
            buys=182,
            sells=97,
            buy_volume_usd=10200.0,
            sell_volume_usd=3800.0,
            buyers=141,
            sellers=72,
            holders_count=1842,
            top10_holder_pct=18.4,
            token_age_seconds=8040,
            token_age_formatted="2h 14m",
            trader_activity_summary="Increasing smart trader volume",
            narrative="AI meme trend breakout",
        )

        # 2. Pump already reversing (Scenario 2: high 24h, negative 5m/1h)
        dump = TokenSnapshot(
            timestamp=now,
            provider_source=self.provider_name,
            symbol="DUMP",
            name="Dump Token",
            token_address="DUMPpump22222222222222222222222222222222222",
            chain="solana",
            market_cap_usd=350000.0,
            price_usd=0.00035,
            liquidity_usd=25000.0,
            change_5m_pct=-12.0,
            change_1h_pct=-25.0,
            change_4h_pct=180.0,
            change_24h_pct=900.0,
            volume_5m_usd=30000.0,
            volume_1h_usd=120000.0,
            volume_24h_usd=950000.0,
            buys=45,
            sells=210,
            buyers=35,
            sellers=180,
            holders_count=950,
            top10_holder_pct=45.0,
            token_age_seconds=21600,
            token_age_formatted="6h 00m",
            trader_activity_summary="Major sellers exiting",
            narrative="Old pump",
        )

        # 3. Dangerous Thin Liquidity (Scenario 5)
        thin = TokenSnapshot(
            timestamp=now,
            provider_source=self.provider_name,
            symbol="THIN",
            name="Thin Liquidity Token",
            token_address="THINpump33333333333333333333333333333333333",
            chain="solana",
            market_cap_usd=150000.0,
            price_usd=0.00015,
            liquidity_usd=4000.0,  # low liquidity!
            change_5m_pct=18.0,
            change_1h_pct=45.0,
            change_4h_pct=60.0,
            change_24h_pct=80.0,
            volume_5m_usd=12000.0,
            volume_1h_usd=35000.0,
            volume_24h_usd=80000.0,
            buys=60,
            sells=20,
            buyers=45,
            sellers=15,
            holders_count=300,
            top10_holder_pct=60.0,
            token_age_seconds=1800,
            token_age_formatted="30m",
            trader_activity_summary="Single whale",
            narrative="Low cap hype",
        )

        self._tokens[xyz.token_address] = xyz
        self._tokens[dump.token_address] = dump
        self._tokens[thin.token_address] = thin

    def set_token(self, token: TokenSnapshot) -> None:
        """Insert or update a token in the mock feed."""
        self._tokens[token.token_address] = token

    async def fetch_active_tokens(self, limit: int = 50) -> List[TokenSnapshot]:
        """Return simulated active tokens."""
        return list(self._tokens.values())[:limit]

    async def fetch_token_snapshot(self, token_address: str) -> Optional[TokenSnapshot]:
        """Fetch snapshot for specified address."""
        return self._tokens.get(token_address)

    async def get_current_price(self, token_address: str) -> Optional[float]:
        """Return simulated spot price."""
        token = self._tokens.get(token_address)
        return token.price_usd if token else None

    async def health_check(self) -> bool:
        """Mock collector is always healthy."""
        return True


# Alias for compatibility
MockMarketDataProvider = MockPumpCollector
