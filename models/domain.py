"""Domain models and Pydantic schemas for research and alerting."""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, computed_field


class SetupClassification(str, Enum):
    """Setup classification according to Section 41."""
    EARLY_MOMENTUM = "Early Momentum"
    CONTINUATION = "Continuation"
    BREAKOUT = "Breakout"
    PULLBACK_CONTINUATION = "Pullback Continuation"
    EXHAUSTION = "Exhaustion / High Risk"


class ConfirmationState(str, Enum):
    """Confirmation state according to Section 33."""
    WATCH = "Watch"
    CONFIRMATION = "Confirmation Candidate"
    CONFIRMED = "Confirmed"
    WEAKENING = "Weakening"
    INVALIDATED = "Invalidated"


class NormalizedTokenData(BaseModel):
    """Strictly normalized token data snapshot independent of data provider."""

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the snapshot",
    )
    token: str = Field(..., description="Token symbol or name (e.g. XYZ)")
    token_address: str = Field(..., description="Contract address / mint address")

    market_cap: float = Field(..., ge=0.0, description="Current market capitalization in USD")
    price: float = Field(..., ge=0.0, description="Current token price in USD")
    liquidity: float = Field(..., ge=0.0, description="Available pool liquidity in USD")

    # Percentage changes
    change_5m: float = Field(..., description="5-minute price change percentage")
    change_1h: float = Field(..., description="1-hour price change percentage")
    change_4h: float = Field(..., description="4-hour price change percentage")
    change_24h: float = Field(..., description="24-hour price change percentage")

    # Volume metrics
    volume_5m: float = Field(..., ge=0.0, description="5-minute trading volume in USD")
    volume_1h: float = Field(..., ge=0.0, description="1-hour trading volume in USD")
    volume_24h: float = Field(..., ge=0.0, description="24-hour trading volume in USD")

    # Order flow counts
    buys: int = Field(default=0, ge=0, description="Number of buy transactions")
    sells: int = Field(default=0, ge=0, description="Number of sell transactions")
    buy_volume: Optional[float] = Field(default=None, ge=0.0, description="Buy volume in USD")
    sell_volume: Optional[float] = Field(default=None, ge=0.0, description="Sell volume in USD")

    # Participant breadth
    buyers: int = Field(default=0, ge=0, description="Unique buyer wallet count")
    sellers: int = Field(default=0, ge=0, description="Unique seller wallet count")

    # Structure & distribution
    holders: int = Field(default=0, ge=0, description="Total holder count")
    top10_percentage: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Supply held by top 10 wallets %"
    )

    # Contextual data
    age: str = Field(default="UNKNOWN", description="Token age (e.g. '2h 14m')")
    age_minutes: Optional[int] = Field(default=None, ge=0, description="Age in minutes if known")
    trader_activity: str = Field(default="UNKNOWN", description="Observed smart/active trader activity")
    narrative: str = Field(default="UNKNOWN", description="Associated meme/catalyst narrative")

    @computed_field
    @property
    def liquidity_ratio(self) -> float:
        """Liquidity to Market Cap ratio (%)."""
        if self.market_cap <= 0:
            return 0.0
        return (self.liquidity / self.market_cap) * 100.0

    @computed_field
    @property
    def buy_tx_ratio(self) -> float:
        """Ratio of buy transactions to total transactions (%)."""
        total = self.buys + self.sells
        if total == 0:
            return 0.0
        return (self.buys / total) * 100.0

    @computed_field
    @property
    def buyer_ratio(self) -> float:
        """Ratio of unique buyers to total active traders (%)."""
        total = self.buyers + self.sellers
        if total == 0:
            return 0.0
        return (self.buyers / total) * 100.0


class ScoreBreakdown(BaseModel):
    """Detailed score breakdown across the 10 strategy dimensions (Section 18)."""
    market_cap_score: float = Field(..., ge=0.0, le=5.0)
    liquidity_score: float = Field(..., ge=0.0, le=15.0)
    volume_score: float = Field(..., ge=0.0, le=15.0)
    price_momentum_score: float = Field(..., ge=0.0, le=20.0)
    buy_sell_pressure_score: float = Field(..., ge=0.0, le=15.0)
    buyer_seller_breadth_score: float = Field(..., ge=0.0, le=10.0)
    holders_score: float = Field(..., ge=0.0, le=5.0)
    top10_score: float = Field(..., ge=0.0, le=5.0)
    trader_activity_score: float = Field(..., ge=0.0, le=5.0)
    narrative_score: float = Field(..., ge=0.0, le=5.0)

    @computed_field
    @property
    def total_score(self) -> float:
        """Calculated total momentum score (0-100)."""
        return round(
            self.market_cap_score
            + self.liquidity_score
            + self.volume_score
            + self.price_momentum_score
            + self.buy_sell_pressure_score
            + self.buyer_seller_breadth_score
            + self.holders_score
            + self.top10_score
            + self.trader_activity_score
            + self.narrative_score,
            2,
        )


class MomentumScoreResult(BaseModel):
    """Scoring evaluation result containing points, breakdown, and notes."""
    score: float = Field(..., ge=0.0, le=100.0)
    breakdown: ScoreBreakdown
    status_summary: str
    reasons: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)


class AlertCandidate(BaseModel):
    """Qualified token candidate ready for dispatch, confirmation, and recording."""
    token: NormalizedTokenData
    score_result: MomentumScoreResult
    classification: SetupClassification
    confirmation_state: ConfirmationState
    alert_reason: str
    reasons: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    confirmation_needed: str
    invalidation_criteria: str
    next_action: str
