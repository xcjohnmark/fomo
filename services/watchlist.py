"""Watchlist service managing actively monitored tokens."""

import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from models.db import WatchlistToken

logger = logging.getLogger(__name__)


class WatchlistService:
    """Manages persistent list of tokens marked by user for dedicated monitoring."""

    def __init__(self, session_factory: Optional[async_sessionmaker[AsyncSession]] = None):
        self.session_factory = session_factory
        self._memory_watchlist: Dict[str, Dict[str, Any]] = {}

    async def add_token(
        self, token_address: str, symbol: Optional[str] = None, notes: Optional[str] = None
    ) -> bool:
        """Add a token contract address to the watchlist."""
        cleaned_address = token_address.strip()
        if not cleaned_address:
            return False

        if self.session_factory:
            async with self.session_factory() as session:
                async with session.begin():
                    stmt = select(WatchlistToken).where(WatchlistToken.token_address == cleaned_address)
                    existing = (await session.execute(stmt)).scalar_one_or_none()
                    if existing:
                        if symbol:
                            existing.symbol = symbol
                        return True

                    item = WatchlistToken(
                        token_address=cleaned_address,
                        symbol=symbol,
                        notes=notes,
                    )
                    session.add(item)
                logger.info("Added token %s (%s) to watchlist", cleaned_address, symbol)
                return True
        else:
            self._memory_watchlist[cleaned_address] = {
                "token_address": cleaned_address,
                "symbol": symbol,
                "notes": notes,
            }
            return True

    async def remove_token(self, token_address: str) -> bool:
        """Remove a token contract address from the watchlist."""
        cleaned_address = token_address.strip()
        if not cleaned_address:
            return False

        if self.session_factory:
            async with self.session_factory() as session:
                async with session.begin():
                    stmt = delete(WatchlistToken).where(WatchlistToken.token_address == cleaned_address)
                    res = await session.execute(stmt)
                    deleted = res.rowcount > 0
                return deleted
        else:
            return bool(self._memory_watchlist.pop(cleaned_address, None))

    async def is_watched(self, token_address: str) -> bool:
        """Check if a token contract address is actively on the watchlist."""
        cleaned_address = token_address.strip()
        if not cleaned_address:
            return False

        if self.session_factory:
            async with self.session_factory() as session:
                stmt = select(WatchlistToken).where(WatchlistToken.token_address == cleaned_address)
                res = await session.execute(stmt)
                return res.scalar_one_or_none() is not None
        else:
            return cleaned_address in self._memory_watchlist

    async def get_watchlist(self) -> List[Dict[str, Any]]:
        """Retrieve all currently watched tokens."""
        if self.session_factory:
            async with self.session_factory() as session:
                stmt = select(WatchlistToken).order_by(WatchlistToken.id)
                res = await session.execute(stmt)
                items = list(res.scalars().all())
                return [
                    {"token_address": item.token_address, "symbol": item.symbol, "notes": item.notes}
                    for item in items
                ]
        else:
            return list(self._memory_watchlist.values())
