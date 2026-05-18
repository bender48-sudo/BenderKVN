"""Bind browser-only web trial account to a real Telegram user."""
from __future__ import annotations

import logging
import sqlite3

import aiohttp

from shop_bot.data_manager.database import DB_FILE, get_user, get_user_keys, register_user_if_not_exists
from shop_bot.modules import remnawave_api
from shop_bot.web_trial_db import (
    format_customer_id,
    get_claim_by_bind_token,
    get_web_trial_claim_by_web_user_id,
    is_web_surrogate_id,
    mark_web_claim_bound,
)

logger = logging.getLogger(__name__)


def merge_web_user_to_telegram(web_uid: int, tg_id: int, username: str) -> dict:
    """Move keys/balance from web surrogate user_id to real Telegram id."""
    if not is_web_surrogate_id(web_uid):
        return {"ok": False, "error": "not_web_user"}
    if tg_id <= 0:
        return {"ok": False, "error": "invalid_telegram"}

    claim = get_web_trial_claim_by_web_user_id(web_uid)
    if not claim:
        return {"ok": False, "error": "not_found"}

    bound_tg = claim.get("telegram_id")
    if bound_tg and int(bound_tg) == tg_id:
        return {
            "ok": True,
            "already_bound": True,
            "customer_id": format_customer_id(web_uid),
        }
    if bound_tg and int(bound_tg) != tg_id:
        return {"ok": False, "error": "already_bound_other"}

    register_user_if_not_exists(tg_id, username or "")
    web_keys = get_user_keys(web_uid)
    tg_keys = get_user_keys(tg_id)
    if tg_keys and web_keys:
        return {"ok": False, "error": "both_have_keys"}

    web_user = get_user(web_uid)
    tg_user = get_user(tg_id)

    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("UPDATE vpn_keys SET user_id = ? WHERE user_id = ?", (tg_id, web_uid))
            conn.execute("UPDATE user_actions SET user_id = ? WHERE user_id = ?", (tg_id, web_uid))

            web_bal = float(web_user["balance"]) if web_user and web_user.get("balance") else 0.0
            tg_bal = float(tg_user["balance"]) if tg_user and tg_user.get("balance") else 0.0
            conn.execute(
                "UPDATE users SET balance = ? WHERE telegram_id = ?",
                (tg_bal + web_bal, tg_id),
            )

            if web_user and web_user.get("trial_used"):
                conn.execute("UPDATE users SET trial_used = 1 WHERE telegram_id = ?", (tg_id,))
            if web_user and web_user.get("agreed_to_terms"):
                conn.execute("UPDATE users SET agreed_to_terms = 1 WHERE telegram_id = ?", (tg_id,))

            web_gen = int(web_user.get("sub_refresh_notified_generation") or 0) if web_user else 0
            tg_gen = int(tg_user.get("sub_refresh_notified_generation") or 0) if tg_user else 0
            conn.execute(
                "UPDATE users SET sub_refresh_notified_generation = ? WHERE telegram_id = ?",
                (max(web_gen, tg_gen), tg_id),
            )

            conn.execute("DELETE FROM users WHERE telegram_id = ?", (web_uid,))
            conn.commit()
    except sqlite3.Error as exc:
        logger.exception("merge_web_user_to_telegram DB failed web=%s tg=%s", web_uid, tg_id)
        return {"ok": False, "error": "merge_failed", "detail": str(exc)[:200]}

    mark_web_claim_bound(web_uid, tg_id)

    return {
        "ok": True,
        "customer_id": format_customer_id(web_uid),
        "panel_email": claim.get("panel_email") or "",
        "keys_moved": len(web_keys),
    }


async def sync_panel_telegram_id(panel_email: str, telegram_id: int) -> bool:
    if not panel_email:
        return True
    try:
        async with aiohttp.ClientSession() as session:
            user = await remnawave_api.get_user_by_email(session, panel_email)
            if not user:
                return True
            uuid = user.get("uuid")
            if not uuid:
                return False
            body = {"uuid": uuid, "telegramId": int(telegram_id)}
            updated = await remnawave_api._fetch_json(session, "PATCH", "/api/users", json=body)
            return bool(updated and updated.get("response"))
    except Exception as exc:
        logger.warning("sync_panel_telegram_id failed %s: %s", panel_email, exc)
        return False


async def bind_web_account_by_token(bind_token: str, telegram_id: int, username: str) -> dict:
    claim = get_claim_by_bind_token(bind_token)
    if not claim:
        return {"ok": False, "error": "invalid_token"}

    web_uid = int(claim["web_user_id"])
    result = merge_web_user_to_telegram(web_uid, telegram_id, username)
    if not result.get("ok"):
        return result

    panel_email = result.get("panel_email") or claim.get("panel_email") or ""
    if panel_email and not result.get("already_bound"):
        result["panel_synced"] = await sync_panel_telegram_id(panel_email, telegram_id)

    return result
