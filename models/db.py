"""SQLAlchemy ORM models for research database and outcome tracking."""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, TimestampMixin


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
