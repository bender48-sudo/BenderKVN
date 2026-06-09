"""Portal/web referral attribution (P1-REF-001).

Links portal ``ref_code`` / ``?ref=`` values to ``users.referred_by`` via the
same ``link_referral`` path as Telegram ``/start ref_*``.
"""
from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

_REF_CODE_RE = re.compile(r"^[A-Za-z0-9_-]{4,64}$")


def normalize_portal_ref_code(raw: str | None) -> str | None:
    """Accept raw portal ref or ``ref_<token>`` deep-link form."""
    if raw is None:
        return None
    code = str(raw).strip()
    if not code:
        return None
    if code.lower().startswith("ref_"):
        code = code[4:].strip()
    if not code or not _REF_CODE_RE.match(code):
        return None
    return code


def apply_web_referral(ref_code: str | None, user_id: int) -> bool:
    """Set ``referred_by`` when code is valid and user is not already attributed."""
    from shop_bot.data_manager.database import get_user, link_referral, log_action

    norm = normalize_portal_ref_code(ref_code)
    if not norm:
        return False

    user = get_user(user_id)
    if not user or user.get("referred_by"):
        return False

    if not link_referral(norm, user_id):
        return False

    log_action(user_id, "referral_linked", f"web:{norm}")
    return True
