"""Mock Pump.fun data provider simulating realistic token market data feeds."""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from collectors.base import BaseCollector
from models.domain import NormalizedTokenData


class MockPumpCollector(BaseCollector):
    """Reference collector implementation providing realistic test and development feeds."""

    def __init__(self, initial_tokens: Optional[List[NormalizedTokenData]] = None):
        self._tokens: Dict[str, NormalizedTokenData] = {}
        if initial_tokens:
            for t in initial_tokens:
                self._tokens[t.token_address] = t
        else:
            self._load_default_scenarios()

    def _load_default_scenarios(self) -> None:
        """Load standard test tokens representing key scenarios from STRATEGY.md."""
        now = datetime.now(timezone.utc)

        # 1. High Score Candidate (Scenario 1 & Section 38 template: Score ~88+)
        xyz = NormalizedTokenData(
            timestamp=now,
            token="XYZ",
            token_address="XYZpump11111111111111111111111111111111111",
            market_cap=180000.0,
            price=0.00018,
            liquidity=42000.0,
            change_5m=7.2,
            change_1h=18.4,
            change_4h=11.2,
            change_24h=45.8,
            volume_5m=14000.0,
            volume_1h=91000.0,
            volume_24h=420000.0,
            buys=182,
            sells=97,
            buy_volume=10200.0,
            sell_volume=3800.0,
            buyers=141,
            sellers=72,
            holders=1842,
            top10_percentage=18.4,
            age="2h 14m",
            age_minutes=134,
            trader_activity="Increasing smart trader volume",
            narrative="AI meme trend breakout",
        )

        # 2. Pump already reversing (Scenario 2: high 24h, negative 5m/1h)
        dump = NormalizedTokenData(
            timestamp=now,
            token="DUMP",
            token_address="DUMPpump22222222222222222222222222222222222",
            market_cap=350000.0,
            price=0.00035,
            liquidity=25000.0,
            change_5m=-12.0,
            change_1h=-25.0,
            change_4h=180.0,
            change_24h=900.0,
            volume_5m=30000.0,
            volume_1h=120000.0,
            volume_24h=950000.0,
            buys=45,
            sells=210,
            buyers=35,
            sellers=180,
            holders=950,
            top10_percentage=45.0,
            age="6h 00m",
            age_minutes=360,
            trader_activity="Major sellers exiting",
            narrative="Old pump",
        )

        # 3. Dangerous Thin Liquidity (Scenario 5)
        thin = NormalizedTokenData(
            timestamp=now,
            token="THIN",
            token_address="THINpump33333333333333333333333333333333333",
            market_cap=150000.0,
            price=0.00015,
            liquidity=4000.0,  # low liquidity!
            change_5m=18.0,
            change_1h=45.0,
            change_4h=60.0,
            change_24h=80.0,
            volume_5m=12000.0,
            volume_1h=35000.0,
            volume_24h=80000.0,
            buys=60,
            sells=20,
            buyers=45,
            sellers=15,
            holders=300,
            top10_percentage=60.0,
            age="30m",
            age_minutes=30,
            trader_activity="Single whale",
            narrative="Low cap hype",
        )

        self._tokens[xyz.token_address] = xyz
        self._tokens[dump.token_address] = dump
        self._tokens[thin.token_address] = thin

    def set_token(self, token: NormalizedTokenData) -> None:
        """Insert or update a token in the mock feed."""
        self._tokens[token.token_address] = token

    async def get_active_tokens(self) -> List[NormalizedTokenData]:
        """Return all simulated tokens."""
        return list(self._tokens.values())

    async def get_token_snapshot(self, token_address: str) -> Optional[NormalizedTokenData]:
        """Fetch snapshot for specified address."""
        return self._tokens.get(token_address)

    async def get_current_price(self, token_address: str) -> Optional[float]:
        """Return simulated spot price."""
        token = self._tokens.get(token_address)
        return token.price if token else None

    async def health_check(self) -> bool:
        """Mock collector is always healthy."""
        return True
