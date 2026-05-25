"""In-memory subscription URL cache (P2-RED-SUB-URL-CACHE-01)."""
from __future__ import annotations

import asyncio
import logging
import time

logger = logging.getLogger(__name__)

SUBSCRIPTION_URL_TTL_SEC = 60

_cache: dict[int, tuple[str, float]] = {}
_lock = asyncio.Lock()


def invalidate_subscription_url_cache(telegram_id: int) -> None:
    tid = int(telegram_id)
    _cache.pop(tid, None)


async def get_subscription_url_cached(telegram_id: int) -> str | None:
    tid = int(telegram_id)
    now = time.monotonic()
    async with _lock:
        entry = _cache.get(tid)
        if entry and (now - entry[1]) < SUBSCRIPTION_URL_TTL_SEC:
            logger.debug("subscription url cache hit tid=%s", tid)
            return entry[0]

    from shop_bot.subscription_resolve import resolve_subscription_url

    url = await resolve_subscription_url(tid)
    if url:
        async with _lock:
            _cache[tid] = (url, now)
    return url
