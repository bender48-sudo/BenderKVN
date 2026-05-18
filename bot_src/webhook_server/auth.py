"""Webhook auth helpers (P6-RED-PAY-02)."""
from __future__ import annotations

import ipaddress
import logging
import os
from typing import Any

from flask import Request

logger = logging.getLogger(__name__)


def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, "1" if default else "0").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _allowed_networks() -> list[ipaddress._BaseNetwork]:  # type: ignore[name-defined]
    raw = os.getenv(
        "WEBHOOK_ALLOWED_IPS",
        "127.0.0.1/32,::1/128",
    )
    nets: list[ipaddress._BaseNetwork] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "/" not in part:
            part = f"{part}/32"
        try:
            nets.append(ipaddress.ip_network(part, strict=False))
        except ValueError:
            logger.warning("Invalid WEBHOOK_ALLOWED_IPS entry: %s", part)
    return nets


def client_ip(req: Request) -> str:
    """Client IP; X-Forwarded-For only when behind trusted reverse proxy."""
    if _env_bool("WEBHOOK_TRUST_PROXY_HEADERS", False):
        xff = (req.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
        if xff:
            return xff
    x_real = (req.headers.get("X-Real-IP") or "").strip()
    if x_real and _env_bool("WEBHOOK_TRUST_PROXY_HEADERS", False):
        return x_real
    return req.remote_addr or ""


def is_client_allowed(req: Request) -> bool:
    """Allow loopback peers (nginx on AMS) without trusting X-Forwarded-For."""
    peer = (req.remote_addr or "").strip()
    if peer in ("127.0.0.1", "::1"):
        return True
    ip_s = peer or client_ip(req)
    if not ip_s:
        return False
    try:
        ip = ipaddress.ip_address(ip_s)
    except ValueError:
        return False
    for net in _allowed_networks():
        if ip in net:
            return True
    logger.warning("Webhook rejected IP %s (peer=%s)", ip_s, peer)
    return False


def verify_crypto_shared_secret(req: Request) -> bool:
    import hmac

    expected = os.getenv("CRYPTO_WEBHOOK_SECRET", "").strip()
    if not expected:
        return _env_bool("WEBHOOK_ALLOW_OPEN_CRYPTO", False)
    got = (req.headers.get("X-Webhook-Secret") or req.args.get("secret") or "").strip()
    return hmac.compare_digest(got, expected)


def verify_yookassa_notification(event_json: dict[str, Any]) -> bool:
    """Optional API round-trip: confirm payment.succeeded with YooKassa API."""
    if event_json.get("event") != "payment.succeeded":
        return True
    obj = event_json.get("object") or {}
    payment_id = obj.get("id")
    if not payment_id:
        logger.warning("YooKassa webhook missing object.id")
        return False
    if _env_bool("YOOKASSA_WEBHOOK_SKIP_API_VERIFY", False):
        logger.critical(
            "YOOKASSA_WEBHOOK_SKIP_API_VERIFY is enabled — webhook API verify disabled"
        )
        return True
    shop = os.getenv("YOOKASSA_SHOP_ID", "").strip()
    secret = os.getenv("YOOKASSA_SECRET_KEY", "").strip()
    if not shop or not secret:
        logger.warning("YooKassa API verify skipped: missing shop credentials")
        return False
    try:
        from yookassa import Configuration, Payment

        Configuration.account_id = shop
        Configuration.secret_key = secret
        payment = Payment.find_one(payment_id)
        ok = getattr(payment, "status", None) == "succeeded"
        if not ok:
            logger.warning(
                "YooKassa API verify failed for %s status=%s",
                payment_id,
                getattr(payment, "status", None),
            )
        return ok
    except Exception as exc:
        logger.error("YooKassa API verify error: %s", exc)
        return False
