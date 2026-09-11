"""Internal domain schema: TokenSnapshot and strategy evaluation models."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, computed_field


class SetupClassification(str, Enum):
    """Setup classification according to Section 41."""
    EARLY_MOMENTUM = "Early Momentum"
    CONTINUATION = "Continuation"
    BREAKOUT = "Breakout"
    PULLBACK_CONTINUATION = "Pullback Continuation"
    EXHAUSTION = "Exhaustion / High Risk"
    NONE = "None"


class ScoreTier(str, Enum):
    """Score classification tiers according to Section 29."""
    STRONG = "STRONG"          # 85–100
    WATCH = "WATCH"            # 70–84
    CONDITIONAL = "CONDITIONAL"# 55–69
    WEAK = "WEAK"              # 40–54
    REJECT = "REJECT"          # 0–39


class ConfirmationState(str, Enum):
    """Confirmation state according to Section 33."""
    CONFIRMED = "CONFIRMED"
    DEVELOPING = "DEVELOPING"
    WEAKENING = "WEAKENING"
    INVALIDATED = "INVALIDATED"
    # Aliases for backward compatibility
    WATCH = "DEVELOPING"
    CONFIRMATION = "DEVELOPING"


class TokenSnapshot(BaseModel):
    """Normalized internal market snapshot strictly decoupled from external providers.

    STRICT STRATEGY RULE:
    If a field is not available from an external provider, it is represented as None.
    NEVER invent, estimate, or default missing metrics to zero.
    """

    model_config = ConfigDict(extra="ignore")

    # Identifiers
    token_address: str = Field(..., description="Token contract / mint address (CA)")
    chain: str = Field(default="solana", description="Blockchain network (e.g. 'solana')")
    pool_address: Optional[str] = Field(default=None, description="Liquidity pool / pair address")
    symbol: Optional[str] = Field(default=None, description="Token ticker symbol")
    name: Optional[str] = Field(default=None, description="Token name")

    # Timestamp & Data Provenance
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when snapshot was captured/normalized",
    )
    provider_source: str = Field(
        default="unknown",
        description="Name of the adapter/provider that produced this snapshot",
    )

    # Core Pricing & Liquidity (USD)
    price_usd: Optional[float] = Field(default=None, ge=0.0, description="Current price in USD")
    market_cap_usd: Optional[float] = Field(default=None, ge=0.0, description="Market cap in USD")
    liquidity_usd: Optional[float] = Field(default=None, ge=0.0, description="Pool liquidity in USD")

    # Percentage Price Changes
    change_5m_pct: Optional[float] = Field(default=None, description="5-minute price change %")
    change_1h_pct: Optional[float] = Field(default=None, description="1-hour price change %")
    change_4h_pct: Optional[float] = Field(default=None, description="4-hour price change %")
    change_24h_pct: Optional[float] = Field(default=None, description="24-hour price change %")

    # Trading Volumes (USD)
    volume_5m_usd: Optional[float] = Field(default=None, ge=0.0, description="5-minute volume in USD")
    volume_1h_usd: Optional[float] = Field(default=None, ge=0.0, description="1-hour volume in USD")
    volume_24h_usd: Optional[float] = Field(default=None, ge=0.0, description="24-hour volume in USD")

    # Flow & Transaction Counts
    buys: Optional[int] = Field(default=None, ge=0, description="Buy transaction count")
    sells: Optional[int] = Field(default=None, ge=0, description="Sell transaction count")
    buy_volume_usd: Optional[float] = Field(default=None, ge=0.0, description="Buy volume in USD")
    sell_volume_usd: Optional[float] = Field(default=None, ge=0.0, description="Sell volume in USD")

    # Participant Breadth
    buyers: Optional[int] = Field(default=None, ge=0, description="Unique buyer wallet count")
    sellers: Optional[int] = Field(default=None, ge=0, description="Unique seller wallet count")

    # Distribution & Holders
    holders_count: Optional[int] = Field(default=None, ge=0, description="Total token holders count")
    top10_holder_pct: Optional[float] = Field(
        default=None, ge=0.0, le=100.0, description="Percentage of supply held by top 10 wallets"
    )

    # Token Age
    token_age_seconds: Optional[int] = Field(default=None, ge=0, description="Token age in seconds")
    token_age_formatted: Optional[str] = Field(default=None, description="Formatted age (e.g. '2h 14m')")

    # Qualitative & Smart Money Signals
    trader_activity_summary: Optional[str] = Field(
        default=None, description="Observed smart/active trader activity summary"
    )
    narrative: Optional[str] = Field(
        default=None, description="Associated meme/catalyst narrative if identified"
    )

    # Raw Payload (for debugging / audit)
    raw_metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Raw provider payload for audit and research"
    )

    @computed_field
    @property
    def liquidity_ratio(self) -> Optional[float]:
        """Liquidity to Market Cap ratio (%). Returns None if either metric is missing."""
        if self.liquidity_usd is None or self.market_cap_usd is None or self.market_cap_usd <= 0:
            return None
        return (self.liquidity_usd / self.market_cap_usd) * 100.0

    @computed_field
    @property
    def buy_tx_ratio(self) -> Optional[float]:
        """Ratio of buy transactions to total transactions (%). Returns None if missing."""
        if self.buys is None or self.sells is None:
            return None
        total = self.buys + self.sells
        if total == 0:
            return None
        return (self.buys / total) * 100.0

    @computed_field
    @property
    def buyer_ratio(self) -> Optional[float]:
        """Ratio of unique buyers to total active traders (%). Returns None if missing."""
        if self.buyers is None or self.sellers is None:
            return None
        total = self.buyers + self.sellers
        if total == 0:
            return None
        return (self.buyers / total) * 100.0

    @property
    def token(self) -> str:
        """Compatibility property returning symbol or short address."""
        return self.symbol or self.token_address[:8]

    def is_available(self, field_name: str) -> bool:
        """Check if a specific field has a valid, non-None value."""
        return getattr(self, field_name, None) is not None

    def get_missing_fields(self) -> List[str]:
        """Return list of all strategy fields that are unavailable (None)."""
        core_fields = [
            "price_usd",
            "market_cap_usd",
            "liquidity_usd",
            "change_5m_pct",
            "change_1h_pct",
            "change_4h_pct",
            "change_24h_pct",
            "volume_5m_usd",
            "volume_1h_usd",
            "volume_24h_usd",
            "buys",
            "sells",
            "buyers",
            "sellers",
            "holders_count",
            "top10_holder_pct",
            "token_age_seconds",
            "trader_activity_summary",
            "narrative",
        ]
        return [f for f in core_fields if getattr(self, f) is None]


# Alias for backward-compatibility during transition
NormalizedTokenData = TokenSnapshot


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

    # Missing dimension tracking
    unavailable_dimensions: List[str] = Field(
        default_factory=list,
        description="Dimensions that could not be evaluated due to missing provider data",
    )

    def to_dict(self) -> Dict[str, float]:
        """Dictionary of component scores matching strategy names."""
        return {
            "market_cap": self.market_cap_score,
            "liquidity": self.liquidity_score,
            "volume": self.volume_score,
            "price_momentum": self.price_momentum_score,
            "buy_sell_pressure": self.buy_sell_pressure_score,
            "buyer_seller_breadth": self.buyer_seller_breadth_score,
            "holder_growth": self.holders_score,
            "top_10_concentration": self.top10_score,
            "trader_activity": self.trader_activity_score,
            "narrative": self.narrative_score,
        }

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
    missing_metrics: List[str] = Field(default_factory=list)


class MomentumAnalysis(BaseModel):
    """Deterministic momentum analysis output for research, alerting, and strategy evaluation."""
    model_config = ConfigDict(extra="ignore")

    token_address: str
    symbol: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    score: float = Field(..., ge=0.0, le=100.0, description="Total momentum score (0-100)")
    score_breakdown: Dict[str, float] = Field(
        ..., description="Scores for each of the 10 strategy dimensions"
    )
    score_tier: ScoreTier = Field(
        ..., description="STRONG, WATCH, CONDITIONAL, WEAK, or REJECT"
    )
    classification: SetupClassification = Field(
        ..., description="Setup classification profile"
    )
    setup_state: ConfirmationState = Field(
        ..., description="CONFIRMED, DEVELOPING, WEAKENING, or INVALIDATED"
    )

    reasons: List[str] = Field(
        default_factory=list, description="2-4 factual objective reasons supporting setup"
    )
    warnings: List[str] = Field(
        default_factory=list, description="Objective risks, distribution hazards, or divergences"
    )
    confirmation_needed: List[str] = Field(
        default_factory=list, description="Conditions required before trade consideration"
    )
    invalidation_conditions: List[str] = Field(
        default_factory=list, description="Events that falsify the momentum thesis"
    )
    next_action: str = Field(
        default="Ignore", description="Recommended next action (e.g. Watch, Confirm, Ignore)"
    )
    is_overextended: bool = Field(
        default=False, description="Flag indicating vertical price move poses bad entry"
    )
    raw_breakdown: Optional[ScoreBreakdown] = None


class AlertCandidate(BaseModel):
    """Qualified token candidate ready for dispatch, confirmation, and recording."""
    token: TokenSnapshot
    score_result: MomentumScoreResult
    classification: SetupClassification
    confirmation_state: ConfirmationState
    alert_reason: str
    reasons: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    confirmation_needed: str
    invalidation_criteria: str
    next_action: str
    analysis: Optional[MomentumAnalysis] = None
