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
    token_symbol: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    token_address: Mapped[str] = mapped_column(String(128), index=True, nullable=False)

    alert_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )

    # Core market metrics
    market_cap: Mapped[float] = mapped_column(Float, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    liquidity: Mapped[float] = mapped_column(Float, nullable=False)

    # Momentum timeframes
    change_5m: Mapped[float] = mapped_column(Float, nullable=False)
    change_1h: Mapped[float] = mapped_column(Float, nullable=False)
    change_4h: Mapped[float] = mapped_column(Float, nullable=False)
    change_24h: Mapped[float] = mapped_column(Float, nullable=False)

    # Volumes
    volume_5m: Mapped[float] = mapped_column(Float, nullable=False)
    volume_1h: Mapped[float] = mapped_column(Float, nullable=False)
    volume_24h: Mapped[float] = mapped_column(Float, nullable=False)

    # Flow & breadth
    buys: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sells: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    buyers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sellers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Distribution
    holders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    top10_percentage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

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
