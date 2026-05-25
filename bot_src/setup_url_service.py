"""Shared setup page URL resolution (P2-RED-SETUP-URL-DEDUP-01)."""
from __future__ import annotations

import logging

from shop_bot.bot import portal_links
from shop_bot.subscription_cache import get_subscription_url_cached

logger = logging.getLogger(__name__)


async def get_setup_url_for_user(telegram_id: int) -> tuple[str | None, str | None]:
    """Return (setup_page_url, error_reason). reason is set when url is None."""
    tid = int(telegram_id)
    try:
        sub_url = await get_subscription_url_cached(tid)
    except Exception as exc:
        logger.warning("get_setup_url_for_user tid=%s: %s", tid, exc)
        return None, "upstream_failed"

    if not sub_url:
        return None, "no_subscription"

    try:
        setup_url = portal_links.setup_url_for_sub(sub_url)
    except Exception as exc:
        logger.warning("setup_url_for_sub tid=%s: %s", tid, exc)
        return None, "token_failed"

    if not setup_url:
        return None, "token_failed"

    return setup_url, None
