"""Database engine initialization and async session context managers."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config.settings import Settings, get_settings
from database.base import Base

_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def create_db_engine(database_url: Optional[str] = None) -> AsyncEngine:
    """Create and configure the async database engine."""
    url = database_url or get_settings().DATABASE_URL
    is_sqlite = url.startswith("sqlite")

    engine_kwargs = {
        "echo": False,
        "pool_pre_ping": True,
    }

    if is_sqlite:
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    else:
        # PostgreSQL connection pooling optimizations
        engine_kwargs["pool_size"] = 10
        engine_kwargs["max_overflow"] = 20

    return create_async_engine(url, **engine_kwargs)


def get_engine() -> AsyncEngine:
    """Get or lazily initialize the shared database engine singleton."""
    global _engine
    if _engine is None:
        _engine = create_db_engine()
    return _engine


def async_session_factory(engine: Optional[AsyncEngine] = None) -> async_sessionmaker[AsyncSession]:
    """Get or initialize the async session factory."""
    global _session_factory
    eng = engine or get_engine()
    if _session_factory is None or engine is not None:
        factory = async_sessionmaker(
            bind=eng,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        if engine is None:
            _session_factory = factory
        return factory
    return _session_factory


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional async database session context."""
    factory = async_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db(engine: Optional[AsyncEngine] = None) -> None:
    """Create all database tables defined on Base and apply non-destructive column additions."""
    eng = engine or get_engine()
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        def _ensure_columns(sync_conn):
            from sqlalchemy import inspect, text
            inspector = inspect(sync_conn)
            if "strategy_calls" in inspector.get_table_names():
                existing_cols = {c["name"] for c in inspector.get_columns("strategy_calls")}
                cols_to_add = [
                    ("target_percentage", "FLOAT"),
                    ("entry_liquidity", "FLOAT"),
                    ("entry_5m_change_pct", "FLOAT"),
                    ("entry_1h_change_pct", "FLOAT"),
                    ("entry_volume_5m", "FLOAT"),
                    ("entry_volume_status", "VARCHAR(32)"),
                    ("top10_concentration", "FLOAT"),
                    ("is_winning", "BOOLEAN"),
                ]
                for col_name, col_type in cols_to_add:
                    if col_name not in existing_cols:
                        sync_conn.execute(text(f"ALTER TABLE strategy_calls ADD COLUMN {col_name} {col_type}"))

        await conn.run_sync(_ensure_columns)


async def close_db() -> None:
    """Dispose of the database engine connection pool."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
