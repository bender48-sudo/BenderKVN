import asyncio
import logging
import os

from flask import Flask, jsonify, request

from shop_bot.webhook_server.auth import (
    assert_prod_webhook_hardening,
    is_client_allowed,
    verify_crypto_shared_secret,
    verify_yookassa_notification,
)
from shop_bot.webhook_server.payment_queue import (
    PaymentWebhookQueue,
    idempotency_key_crypto,
    idempotency_key_cryptobot,
    idempotency_key_yookassa,
)

logger = logging.getLogger(__name__)


def create_webhook_app(bot, payment_processor):
    assert_prod_webhook_hardening()
    flask_app = Flask(__name__)
    pay_queue: PaymentWebhookQueue | None = None

    def _queue() -> PaymentWebhookQueue:
        nonlocal pay_queue
        if pay_queue is None:
            loop = flask_app.config["EVENT_LOOP"]
            pay_queue = PaymentWebhookQueue(bot, payment_processor, loop)
        return pay_queue

    def _run_async(coro, timeout: float = 30):
        """Run coroutine on bot EVENT_LOOP (P2-RED-WEBHOOK-ASYNC-01)."""
        loop = flask_app.config.get("EVENT_LOOP")
        if loop is None:
            raise RuntimeError("EVENT_LOOP not configured on webhook app")
        fut = asyncio.run_coroutine_threadsafe(coro, loop)
        return fut.result(timeout=timeout)

    def _reject_auth() -> tuple[str, int]:
        return "forbidden", 403

    def _accept(key: str | None, source: str, payload: dict) -> tuple[str, int]:
        if not key:
            logger.warning("Webhook without idempotency key from %s", source)
            return "missing idempotency key", 400
        result = _queue().submit(key, source, payload)
        if result == "duplicate":
            return "duplicate", 200
        return "OK", 200

    @flask_app.route("/yookassa-webhook", methods=["POST"])
    def yookassa_webhook_handler():
        try:
            if not is_client_allowed(request):
                return _reject_auth()
            event_json = request.json or {}
            if event_json.get("event") == "payment.succeeded":
                if not verify_yookassa_notification(event_json):
                    return _reject_auth()
            key = idempotency_key_yookassa(event_json)
            if event_json.get("event") != "payment.succeeded":
                return "ignored", 200
            body, code = _accept(key, "yookassa", event_json)
            return body, code
        except Exception as e:
            logger.error("yookassa webhook: %s", e, exc_info=True)
            return "Error", 500

    @flask_app.route("/crypto-webhook", methods=["POST"])
    def crypto_webhook_handler():
        try:
            if not is_client_allowed(request) or not verify_crypto_shared_secret(request):
                return _reject_auth()
            data = request.json or {}
            logger.info("Crypto webhook received: %s", data.get("status"))
            if data.get("status") != "paid":
                return "ignored", 200
            key = idempotency_key_crypto(data)
            body, code = _accept(key, "crypto", data)
            return body, code
        except Exception as e:
            logger.error("crypto webhook: %s", e, exc_info=True)
            return "Error", 500

    @flask_app.route("/portal-web-trial", methods=["POST"])
    def portal_web_trial_handler():
        """Browser signup: new user without Telegram (localhost only)."""
        secret = os.getenv("PORTAL_WEB_TRIAL_SECRET", "").strip()
        if not secret or request.headers.get("X-Portal-Web-Trial-Key") != secret:
            return _reject_auth()
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip()
        phone = (data.get("phone") or "").strip() or None
        try:
            from shop_bot.portal_web_trial import issue_web_trial

            result = _run_async(issue_web_trial(email, phone))
            code = 200 if result.get("ok") else 400
            if result.get("error") == "trial_already_claimed":
                code = 409
            return jsonify(result), code
        except Exception as e:
            logger.error("portal-web-trial: %s", e, exc_info=True)
            return jsonify({"ok": False, "error": "server_error"}), 500

    @flask_app.route("/portal-web-trial-recover", methods=["POST"])
    def portal_web_trial_recover_handler():
        secret = os.getenv("PORTAL_WEB_TRIAL_SECRET", "").strip()
        if not secret or request.headers.get("X-Portal-Web-Trial-Key") != secret:
            return _reject_auth()
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip()
        try:
            from shop_bot.portal_web_trial import recover_web_trial

            result = _run_async(recover_web_trial(email))
            code = 200 if result.get("ok") else 404
            if result.get("error") == "invalid_email":
                code = 400
            return jsonify(result), code
        except Exception as e:
            logger.error("portal-web-trial-recover: %s", e, exc_info=True)
            return jsonify({"ok": False, "error": "server_error"}), 500

    @flask_app.route("/cryptobot-webhook", methods=["POST"])
    def crypto_webhook_post_handler():
        try:
            if not is_client_allowed(request) or not verify_crypto_shared_secret(request):
                return _reject_auth()
            data = request.get_json(silent=True) or {}
            logger.info("Crypto bot webhook received: %s", data.get("status"))
            if data.get("status") != "paid":
                return "ignored", 200
            key = idempotency_key_cryptobot(data)
            body, code = _accept(key, "cryptobot", data)
            return body, code
        except Exception as e:
            logger.error("cryptobot webhook: %s", e, exc_info=True)
            return "Error", 500

    def _portal_lookup_auth() -> bool:
        secret = os.getenv("PORTAL_BROWSER_LOOKUP_SECRET", "").strip()
        if not secret:
            return False
        return request.headers.get("X-Portal-Lookup-Key", "") == secret

    def _portal_service_auth() -> bool:
        """LV setup_verify uses PORTAL_WEB_TRIAL_SECRET; optional separate lookup key."""
        trial = os.getenv("PORTAL_WEB_TRIAL_SECRET", "").strip()
        if trial and request.headers.get("X-Portal-Web-Trial-Key") == trial:
            return True
        return _portal_lookup_auth()

    @flask_app.route("/portal-telegram-setup", methods=["POST"])
    def portal_telegram_setup_handler():
        """Mini App / portal: signed /setup/?t= for Telegram user (not email trial)."""
        secret = os.getenv("PORTAL_WEB_TRIAL_SECRET", "").strip()
        if not secret or request.headers.get("X-Portal-Web-Trial-Key") != secret:
            return _reject_auth()
        try:
            data = request.get_json(silent=True) or {}
            raw_tid = data.get("telegram_id")
            try:
                tid = int(raw_tid)
            except (TypeError, ValueError):
                tid = 0
            if tid <= 0:
                return jsonify({"ok": False, "error": "missing_telegram_id"}), 400
            from shop_bot.portal_telegram_setup import telegram_setup_for_user

            result = _run_async(telegram_setup_for_user(tid))
            code = 200 if result.get("ok") else 404
            if result.get("error") in ("invalid_telegram", "missing_telegram_id"):
                code = 400
            return jsonify(result), code
        except Exception as e:
            logger.error("portal-telegram-setup: %s", e, exc_info=True)
            return jsonify({"ok": False, "error": "server_error"}), 500

    @flask_app.route("/portal-cabinet", methods=["POST"])
    def portal_cabinet_handler():
        """Read-only balance for web trial (BVPN-ID or email)."""
        try:
            if not _portal_service_auth():
                return _reject_auth()
            data = request.get_json(silent=True) or {}
            from shop_bot.portal_cabinet import cabinet_snapshot

            raw_tid = data.get("telegram_id")
            try:
                tid = int(raw_tid) if raw_tid is not None else 0
            except (TypeError, ValueError):
                tid = 0
            doc = cabinet_snapshot(
                customer_id=(data.get("customer_id") or "").strip(),
                email=(data.get("email") or "").strip(),
                telegram_id=tid if tid > 0 else None,
            )
            code = 200 if doc.get("ok") else 404
            return jsonify(doc), code
        except Exception as e:
            logger.error("portal-cabinet: %s", e, exc_info=True)
            return jsonify({"ok": False, "error": "server_error"}), 500

    @flask_app.route("/health", methods=["GET"])
    def health_handler():
        """P2-OPS-BOT-HEALTH-01: liveness + DB + Remna panel API."""
        import time

        import sqlite3

        from shop_bot.data_manager.database import DB_FILE
        from shop_bot.modules.remnawave_api import (
            _fetch_json,
            remna_client_session,
            reset_global_backoff,
        )

        reset_global_backoff()
        started = time.perf_counter()
        checks: dict[str, str] = {}
        panel_ms: int | None = None
        ok = True

        try:
            with sqlite3.connect(DB_FILE, timeout=2) as conn:
                conn.execute("SELECT 1")
            checks["db"] = "ok"
        except Exception as exc:
            checks["db"] = str(exc)
            ok = False

        async def _panel_probe():
            async with remna_client_session() as session:
                return await _fetch_json(session, "GET", "/api/users?limit=1&start=0")

        try:
            t_panel = time.perf_counter()
            panel_data = _run_async(_panel_probe())
            panel_ms = int((time.perf_counter() - t_panel) * 1000)
            if panel_data is None:
                checks["panel"] = "unreachable"
                ok = False
            else:
                checks["panel"] = "ok"
        except Exception as exc:
            checks["panel"] = str(exc)
            ok = False

        body = {
            "ok": ok,
            "checks": checks,
            "panel_ms": panel_ms,
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
        }
        return jsonify(body), 200 if ok else 503

    @flask_app.route("/portal-setup-resolve", methods=["POST"])
    def portal_setup_resolve_handler():
        """Browser setup: resolve @username / telegram id → subscription URL."""
        try:
            if not _portal_service_auth():
                return _reject_auth()
            data = request.get_json(silent=True) or {}
            username = (data.get("username") or "").strip()
            raw_tid = data.get("telegram_id")
            telegram_id = None
            if raw_tid is not None and str(raw_tid).strip().isdigit():
                telegram_id = int(raw_tid)
            from shop_bot.portal_browser_resolve import resolve_browser_setup

            doc = _run_async(
                resolve_browser_setup(username=username, telegram_id=telegram_id)
            )
            code = 200 if doc.get("ok") else 404
            return jsonify(doc), code
        except Exception as e:
            logger.error("portal-setup-resolve: %s", e, exc_info=True)
            return jsonify({"ok": False, "error": "server_error"}), 500

    return flask_app
