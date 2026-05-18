"""Support group reply authorization (P3-RED-SUP-01)."""
from __future__ import annotations

import os

from aiogram.types import User


def support_staff_ids() -> set[int]:
    """Telegram user ids allowed to reply from SUPPORT_GROUP_ID topics."""
    ids: set[int] = set()
    admin = (os.getenv("ADMIN_TELEGRAM_ID") or "").strip()
    if admin.isdigit():
        ids.add(int(admin))
    raw = (os.getenv("SUPPORT_STAFF_IDS") or "").strip()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            ids.add(int(part))
    return ids


def is_authorized_support_staff(user: User | None) -> bool:
    if user is None:
        return False
    if user.is_bot:
        return False
    allowed = support_staff_ids()
    if not allowed:
        return False
    return user.id in allowed
