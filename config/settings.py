"""Environment configuration management using Pydantic Settings."""

from functools import lru_cache
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application runtime settings loaded from environment and .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database connection URL
    # PostgreSQL production: postgresql+asyncpg://user:password@localhost:5432/fomo_db
    # Local dev/test fallback: sqlite+aiosqlite:///./fomo_research.db
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./fomo_research.db",
        description="Async SQLAlchemy database connection string",
    )

    # Telegram alerts configuration
    TELEGRAM_BOT_TOKEN: Optional[str] = Field(
        default=None,
        description="Telegram bot token provided by @BotFather",
    )
    TELEGRAM_CHAT_ID: Optional[str] = Field(
        default=None,
        description="Telegram target chat or channel ID for notifications",
    )

    # Strategy thresholds
    MIN_MOMENTUM_SCORE: int = Field(
        default=85,
        ge=0,
        le=100,
        description="Score threshold (0-100) required to trigger an alert candidate",
    )
    MIN_LIQUIDITY_USD: float = Field(
        default=5000.0,
        ge=0.0,
        description="Absolute minimum liquidity in USD to avoid execution failure",
    )
    MIN_MARKET_CAP_USD: float = Field(
        default=10000.0,
        ge=0.0,
        description="Target minimum market cap in USD",
    )
    MAX_MARKET_CAP_USD: float = Field(
        default=10000000.0,
        ge=0.0,
        description="Target maximum market cap in USD",
    )

    # Scanner runtime settings
    SCAN_INTERVAL_SECONDS: int = Field(
        default=10,
        ge=1,
        description="Polling interval between market scans",
    )
    DRY_RUN: bool = Field(
        default=False,
        description="When True, alerts are logged and recorded but not dispatched via network",
    )

    # Logging settings
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    LOG_FILE: str = Field(
        default="logs/fomo_momentum.log",
        description="Path to log file output",
    )


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
