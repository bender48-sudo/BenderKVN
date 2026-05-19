"""Browser-only free trial (no Telegram). Runs on AMS inside remna-shop-bot."""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone

from shop_bot.config import KEY_EMAIL_DOMAIN

REMNA_TRIAL_DAYS = int(
    os.getenv("REMNA_TRIAL_DAYS", os.getenv("TRIAL_DAYS", os.getenv("REMNA_DEFAULT_DAYS", "90")))
)
from shop_bot.data_manager.database import (
    add_new_key,
    get_next_key_number,
    get_user,
    register_user_if_not_exists,
    reset_trial_used,
    set_terms_agreed,
    set_trial_used,
)
from shop_bot.config import telegram_bind_url
from shop_bot.web_trial_db import (
    ensure_bind_token,
    format_customer_id,
    get_web_trial_claim,
    is_valid_contact_email,
    normalize_contact_email,
    record_web_trial_claim,
    release_web_trial_email,
    reserve_web_trial_email,
    web_user_id_from_email,
)
from shop_bot.modules import remnawave_api
import aiohttp

logger = logging.getLogger(__name__)


async def issue_web_trial(
    contact_email: str,
    contact_phone: str | None = None,
) -> dict:
    """Create panel user + trial subscription for a new web-only customer."""
    em = normalize_contact_email(contact_email)
    if not is_valid_contact_email(em):
        return {"ok": False, "error": "invalid_email"}

    web_uid = web_user_id_from_email(em)
    if not reserve_web_trial_email(em, web_uid):
        return {"ok": False, "error": "trial_already_claimed"}

    register_user_if_not_exists(web_uid, em.split("@")[0][:32])
    set_terms_agreed(web_uid)

    user_row = get_user(web_uid)
    if user_row and user_row.get("trial_used"):
        return {"ok": False, "error": "trial_already_claimed"}

    set_trial_used(web_uid)

    key_number = get_next_key_number(web_uid)
    panel_email = f"web{abs(web_uid)}-key{key_number}-trial@{KEY_EMAIL_DOMAIN}"

    try:
        uri, expire_iso, vless_uuid, sub_url = await remnawave_api.provision_key(
            panel_email,
            days=REMNA_TRIAL_DAYS,
            telegram_id=None,
        )
    except Exception as exc:
        logger.exception("provision_key failed for web trial %s", em)
        reset_trial_used(web_uid)
        release_web_trial_email(em)
        return {"ok": False, "error": "provision_failed", "detail": str(exc)[:200]}

    if not uri or not expire_iso or not vless_uuid or not sub_url:
        reset_trial_used(web_uid)
        release_web_trial_email(em)
        return {"ok": False, "error": "provision_failed"}

    expiry_dt = datetime.fromisoformat(expire_iso.replace("Z", "+00:00"))
    expiry_ms = int(expiry_dt.timestamp() * 1000)
    add_new_key(web_uid, vless_uuid, panel_email, expiry_ms)
    record_web_trial_claim(em, web_uid, panel_email, contact_phone)
    bind_token = ensure_bind_token(web_uid)

    return {
        "ok": True,
        "sub_url": sub_url,
        "expire_at": expiry_dt.strftime("%d.%m.%Y"),
        "days": REMNA_TRIAL_DAYS,
        "customer_id": format_customer_id(web_uid),
        "web_user_id": web_uid,
        "bind_token": bind_token,
        "bind_url": telegram_bind_url(bind_token),
        "telegram_bound": False,
    }


async def recover_web_trial(contact_email: str) -> dict:
    """Return existing subscription for a web customer (same panel user, fresh sub URL)."""
    em = normalize_contact_email(contact_email)
    if not is_valid_contact_email(em):
        return {"ok": False, "error": "invalid_email"}

    claim = get_web_trial_claim(em)
    if not claim:
        return {"ok": False, "error": "not_found"}

    web_uid = int(claim["web_user_id"])
    bind_token = ensure_bind_token(web_uid)
    bind_extra = {
        "bind_token": bind_token,
        "bind_url": telegram_bind_url(bind_token),
        "telegram_bound": bool(claim.get("telegram_id")),
    }
    panel_email = claim["panel_email"]
    if not panel_email:
        return {"ok": False, "error": "not_found"}

    try:
        async with aiohttp.ClientSession() as session:
            inbound = await remnawave_api.get_inbound(session)
            if not inbound:
                return {"ok": False, "error": "provision_failed"}

            user = await remnawave_api.get_user_by_email(session, panel_email)
            if not user:
                user = await remnawave_api.get_user_by_telegram_id(session, str(web_uid))

            if user:
                sub_url = user.get("subscriptionUrl") or ""
                expire_iso = user.get("expireAt") or ""
                if sub_url and expire_iso:
                    expiry_dt = datetime.fromisoformat(expire_iso.replace("Z", "+00:00"))
                    return {
                        "ok": True,
                        "sub_url": sub_url,
                        "expire_at": expiry_dt.strftime("%d.%m.%Y"),
                        "customer_id": format_customer_id(web_uid),
                        "recovered": True,
                        **bind_extra,
                    }

            uri, expire_iso, vless_uuid, sub_url = await remnawave_api.provision_key(
                panel_email,
                days=REMNA_TRIAL_DAYS,
                telegram_id=str(web_uid),
            )
    except Exception as exc:
        logger.exception("recover_web_trial failed for %s", em)
        return {"ok": False, "error": "provision_failed", "detail": str(exc)[:200]}

    if not sub_url or not expire_iso:
        return {"ok": False, "error": "provision_failed"}

    expiry_dt = datetime.fromisoformat(expire_iso.replace("Z", "+00:00"))
    return {
        "ok": True,
        "sub_url": sub_url,
        "expire_at": expiry_dt.strftime("%d.%m.%Y"),
        "customer_id": format_customer_id(web_uid),
        "recovered": True,
        "reprovisioned": True,
        **bind_extra,
    }


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    ap = argparse.ArgumentParser(description="Issue browser web trial")
    ap.add_argument("--email", required=True)
    ap.add_argument("--phone", default="")
    args = ap.parse_args()
    result = asyncio.run(issue_web_trial(args.email, args.phone or None))
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
