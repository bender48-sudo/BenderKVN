"""Who may use admin panel and flow-test menu."""
from __future__ import annotations

import os


def admin_telegram_ids() -> frozenset[str]:
    ids: set[str] = set()
    primary = (os.getenv("ADMIN_TELEGRAM_ID") or "").strip()
    if primary:
        ids.add(primary)
    extra = (os.getenv("ADMIN_TELEGRAM_IDS") or "").strip()
    if extra:
        for part in extra.replace(";", ",").split(","):
            p = part.strip()
            if p:
                ids.add(p)
    return frozenset(ids)


def is_admin_telegram(user_id: int | None) -> bool:
    if user_id is None:
        return False
    allowed = admin_telegram_ids()
    if not allowed:
        return False
    return str(int(user_id)) in allowed
