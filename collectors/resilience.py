"""Resilience utilities: rate limiting and exponential backoff retry handlers."""

import asyncio
from functools import wraps
import logging
import time
from typing import Any, Callable, Coroutine, Optional, Set, Type, Union
import httpx

logger = logging.getLogger(__name__)


class AsyncRateLimiter:
    """Async Token-Bucket Rate Limiter to enforce provider request quotas."""

    def __init__(self, max_rate_per_minute: int = 300, burst_size: Optional[int] = None):
        self.rate_per_second = max_rate_per_minute / 60.0
        self.capacity = float(burst_size or max(int(self.rate_per_second * 2), 5))
        self.tokens = self.capacity
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until a token is available, then consume one."""
        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self.last_update
                self.last_update = now
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate_per_second)

                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return

                # Calculate wait time until 1 token is available
                needed = 1.0 - self.tokens
                wait_time = max(needed / self.rate_per_second, 0.05)
                await asyncio.sleep(wait_time)

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


async def execute_with_retry(
    coro_fn: Callable[..., Coroutine[Any, Any, Any]],
    *args,
    max_retries: int = 3,
    initial_delay: float = 0.5,
    backoff_factor: float = 2.0,
    retry_exceptions: Union[Type[Exception], tuple] = (
        httpx.RequestError,
        httpx.HTTPStatusError,
        asyncio.TimeoutError,
    ),
    retry_status_codes: Set[int] = {429, 500, 502, 503, 504},
    **kwargs,
) -> Any:
    """Execute async function with exponential backoff on transient errors."""
    delay = initial_delay
    last_exception = None

    for attempt in range(1, max_retries + 1):
        try:
            return await coro_fn(*args, **kwargs)
        except httpx.HTTPStatusError as e:
            last_exception = e
            if e.response.status_code in retry_status_codes:
                if attempt == max_retries:
                    logger.error(
                        "Request failed with status %s after %d retries.",
                        e.response.status_code,
                        max_retries,
                    )
                    raise
                logger.warning(
                    "HTTP %s encounter (attempt %d/%d). Retrying in %.2fs...",
                    e.response.status_code,
                    attempt,
                    max_retries,
                    delay,
                )
            else:
                # Non-retryable status (e.g. 400, 404)
                raise
        except retry_exceptions as e:
            last_exception = e
            if attempt == max_retries:
                logger.error("Operation failed after %d retries: %s", max_retries, e)
                raise
            logger.warning(
                "Transient error: %s (attempt %d/%d). Retrying in %.2fs...",
                e,
                attempt,
                max_retries,
                delay,
            )

        await asyncio.sleep(delay)
        delay *= backoff_factor

    if last_exception:
        raise last_exception
