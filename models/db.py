"""SQLAlchemy ORM models for research database, historical snapshots, and outcome tracking."""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, TimestampMixin


# =====================================================================
# Phase 3 Market Data & Historical Snapshot Storage
# =====================================================================

class DataSource(Base, TimestampMixin):
    """Metadata registry of legitimate external market-data providers."""

    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    version: Mapped[str] = mapped_column(String(32), default="v1.0", nullable=False)
    base_url: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    rate_limit_per_minute: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    snapshots: Mapped[List["MarketSnapshot"]] = relationship("MarketSnapshot", back_populates="data_source")


class Token(Base, TimestampMixin):
    """Normalized registry of discovered tokens across chains."""

    __tablename__ = "tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    address: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    chain: Mapped[str] = mapped_column(String(32), default="solana", index=True, nullable=False)
    symbol: Mapped[Optional[str]] = mapped_column(String(32), index=True, nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    decimals: Mapped[Optional[int]] = mapped_column(Integer, default=6, nullable=True)

    pools: Mapped[List["Pool"]] = relationship("Pool", back_populates="token", cascade="all, delete-orphan")
    snapshots: Mapped[List["MarketSnapshot"]] = relationship(
        "MarketSnapshot", back_populates="token", cascade="all, delete-orphan"
    )


class Pool(Base, TimestampMixin):
    """Liquidity pool or pair address associated with a token."""

    __tablename__ = "pools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    address: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    token_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tokens.id", ondelete="CASCADE"), index=True, nullable=False
    )
    chain: Mapped[str] = mapped_column(String(32), default="solana", nullable=False)
    dex_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # raydium, pumpfun, etc.
    quote_token_address: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    quote_token_symbol: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    token: Mapped["Token"] = relationship("Token", back_populates="pools")
    snapshots: Mapped[List["MarketSnapshot"]] = relationship("MarketSnapshot", back_populates="pool")


class MarketSnapshot(Base, TimestampMixin):
    """Historical timestamped market micro-structure observation for a token."""

    __tablename__ = "market_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tokens.id", ondelete="CASCADE"), index=True, nullable=False
    )
    pool_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("pools.id", ondelete="SET NULL"), index=True, nullable=True
    )
    data_source_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("data_sources.id", ondelete="RESTRICT"), index=True, nullable=False
    )

    # Provider timestamp preserved
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)

    # Pricing & Liquidity (USD)
    price_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    market_cap_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    liquidity_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Price Changes (%)
    change_5m_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    change_1h_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    change_4h_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    change_24h_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Volumes (USD)
    volume_5m_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    volume_1h_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    volume_24h_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Flow & Counts
    buys: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sells: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    buy_volume_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sell_volume_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Breadth & Distribution
    buyers: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sellers: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    holders_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    top10_holder_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    token_age_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Deduplication Hash: SHA-256 of (price, mc, liq, vol5m, buys, sells)
    raw_data_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    # Relationships
    token: Mapped["Token"] = relationship("Token", back_populates="snapshots")
    pool: Mapped[Optional["Pool"]] = relationship("Pool", back_populates="snapshots")
    data_source: Mapped["DataSource"] = relationship("DataSource", back_populates="snapshots")


# =====================================================================
# Strategy Alerts & Performance Research
# =====================================================================

class TokenAlert(Base, TimestampMixin):
    """Stores every detected momentum alert candidate snapshot (Section 60)."""

    __tablename__ = "token_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token_symbol: Mapped[str] = mapped_column(String(32), index=True, default="UNKNOWN", nullable=False)
    token_address: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    provider_source: Mapped[str] = mapped_column(String(64), default="unknown", nullable=False)

    alert_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )

    # Core market metrics (nullable if unavailable from a specific provider)
    market_cap: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    liquidity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Momentum timeframes
    change_5m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    change_1h: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    change_4h: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    change_24h: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Volumes
    volume_5m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    volume_1h: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    volume_24h: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Flow & breadth
    buys: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sells: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    buyers: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sellers: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Distribution
    holders: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    top10_percentage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Qualitative context
    age: Mapped[str] = mapped_column(String(64), default="UNKNOWN", nullable=False)
    trader_activity: Mapped[str] = mapped_column(String(128), default="UNKNOWN", nullable=False)
    narrative: Mapped[str] = mapped_column(String(256), default="UNKNOWN", nullable=False)

    # Strategy outputs
    momentum_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    classification: Mapped[str] = mapped_column(String(64), nullable=False)
    confirmation_state: Mapped[str] = mapped_column(String(64), default="Confirmation Candidate", nullable=False)
    alert_reason: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    observations: Mapped[List["PriceObservation"]] = relationship(
        "PriceObservation",
        back_populates="alert",
        cascade="all, delete-orphan",
        order_by="PriceObservation.interval_minutes",
    )
    outcome: Mapped[Optional["SetupOutcome"]] = relationship(
        "SetupOutcome",
        back_populates="alert",
        uselist=False,
        cascade="all, delete-orphan",
    )


class PriceObservation(Base, TimestampMixin):
    """Tracks post-alert price points (e.g. 5m, 10m, 20m, 30m, 60m) for statistical analysis."""

    __tablename__ = "price_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("token_alerts.id", ondelete="CASCADE"), index=True, nullable=False
    )

    interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    return_percentage: Mapped[float] = mapped_column(Float, nullable=False)

    alert: Mapped["TokenAlert"] = relationship("TokenAlert", back_populates="observations")


class SetupOutcome(Base, TimestampMixin):
    """Final recorded trade outcome for research and ML optimization (Section 61)."""

    __tablename__ = "setup_outcomes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("token_alerts.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )

    is_winning: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    max_favorable_excursion: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    max_adverse_excursion: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    final_return_percentage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    optimal_holding_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    invalidation_triggered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    invalidation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="OPEN", nullable=False)

    alert: Mapped["TokenAlert"] = relationship("TokenAlert", back_populates="outcome")


# =====================================================================
# Phase 6 Paper Trading & Watchlist Models
# =====================================================================

class PaperTrade(Base, TimestampMixin):
    """Simulated paper trade execution record for performance tracking."""

    __tablename__ = "paper_trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token_address: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    symbol: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # Simulated Entry Recording (Explicit user fields)
    paper_entry_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    paper_entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    paper_entry_mc: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Simulated Targets & Stops
    target_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    target_market_cap: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    invalidation_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    invalidation_market_cap: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Simulated Exit & Resolution
    status: Mapped[str] = mapped_column(String(32), default="OPEN", index=True, nullable=False)
    paper_exit_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    paper_exit_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    paper_exit_mc: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    paper_exit_reason: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    paper_pnl_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    expected_holding_minutes: Mapped[Optional[int]] = mapped_column(Integer, default=30, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Aliases for backward compatibility
    @property
    def entry_price(self) -> float:
        return self.paper_entry_price

    @entry_price.setter
    def entry_price(self, val: float) -> None:
        self.paper_entry_price = val

    @property
    def entry_market_cap(self) -> Optional[float]:
        return self.paper_entry_mc

    @entry_market_cap.setter
    def entry_market_cap(self, val: Optional[float]) -> None:
        self.paper_entry_mc = val

    @property
    def exit_price(self) -> Optional[float]:
        return self.paper_exit_price

    @exit_price.setter
    def exit_price(self, val: Optional[float]) -> None:
        self.paper_exit_price = val

    @property
    def exit_time(self) -> Optional[datetime]:
        return self.paper_exit_timestamp

    @exit_time.setter
    def exit_time(self, val: Optional[datetime]) -> None:
        self.paper_exit_timestamp = val

    @property
    def pnl_pct(self) -> Optional[float]:
        return self.paper_pnl_pct

    @pnl_pct.setter
    def pnl_pct(self, val: Optional[float]) -> None:
        self.paper_pnl_pct = val


class WatchlistToken(Base, TimestampMixin):
    """Dedicated tokens actively monitored on user watchlist."""

    __tablename__ = "watchlist_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token_address: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    symbol: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


# =====================================================================
# Phase 7 & 8 Strategy Call Research Ledger & Outcome Records
# =====================================================================

class StrategyCall(Base, TimestampMixin):
    """Permanent immutable research observation for every generated Quick Flip setup."""

    __tablename__ = "strategy_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    call_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True, nullable=False
    )
    token_ca: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    chain: Mapped[str] = mapped_column(String(32), default="solana", nullable=False)
    pool_address: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    symbol: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    strategy_version: Mapped[str] = mapped_column(String(32), default="v1.0", nullable=False)
    momentum_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Immutable initial call plan parameters
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    entry_market_cap: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    entry_liquidity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    entry_5m_change_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    entry_1h_change_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    entry_volume_5m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    entry_volume_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    top10_concentration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    entry_zone_low: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    entry_zone_high: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    target_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    target_market_cap: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    target_percentage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    invalidation_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    invalidation_market_cap: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    expected_holding_minutes: Mapped[Optional[int]] = mapped_column(Integer, default=30, nullable=True)
    setup_state: Mapped[str] = mapped_column(String(64), default="CONFIRMED", nullable=False)

    reasons: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    risk_flags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    # Dynamic observation and outcome resolution fields
    outcome_status: Mapped[str] = mapped_column(String(32), default="OPEN", index=True, nullable=False)
    is_winning: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    actual_peak_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actual_peak_market_cap: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actual_low_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actual_exit_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    time_to_target: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    time_to_invalidation: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    max_favorable_excursion: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    max_adverse_excursion: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    return_percentage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    holding_time: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    exit_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result: Mapped[Optional[str]] = mapped_column(String(32), index=True, nullable=True)


