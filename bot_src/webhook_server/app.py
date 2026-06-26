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
        ref_code = (data.get("ref_code") or "").strip() or None
        try:
            from shop_bot.portal_web_trial import issue_web_trial

            result = _run_async(issue_web_trial(email, phone, ref_code))
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

    @flask_app.route("/portal-tariff", methods=["POST"])
    def portal_tariff_handler():
        """Mini App balance presets + rate + custom min/max (server is source of truth)."""
        try:
            if not _portal_service_auth():
                return _reject_auth()
            from shop_bot.portal_balance import build_tariff

            return jsonify(build_tariff()), 200
        except Exception as e:
            logger.error("portal-tariff: %s", e, exc_info=True)
            return jsonify({"ok": False, "error": "server_error"}), 500

    @flask_app.route("/portal-transactions", methods=["POST"])
    def portal_transactions_handler():
        """Read-only balance history (top-ups + daily charges) for Mini App."""
        try:
            if not _portal_service_auth():
                return _reject_auth()
            data = request.get_json(silent=True) or {}
            from shop_bot.portal_balance import transactions_snapshot

            raw_tid = data.get("telegram_id")
            try:
                tid = int(raw_tid) if raw_tid is not None else 0
            except (TypeError, ValueError):
                tid = 0
            try:
                limit = int(data.get("limit") or 50)
            except (TypeError, ValueError):
                limit = 50
            doc = transactions_snapshot(
                telegram_id=tid if tid > 0 else None,
                customer_id=(data.get("customer_id") or "").strip(),
                email=(data.get("email") or "").strip(),
                limit=limit,
            )
            code = 200 if doc.get("ok") else 404
            return jsonify(doc), code
        except Exception as e:
            logger.error("portal-transactions: %s", e, exc_info=True)
            return jsonify({"ok": False, "error": "server_error"}), 500

    @flask_app.route("/portal-create-payment", methods=["POST"])
    def portal_create_payment_handler():
        """Create a YooKassa top-up for the Mini App; returns confirmation_url to redirect."""
        try:
            if not _portal_service_auth():
                return _reject_auth()
            data = request.get_json(silent=True) or {}
            from shop_bot.portal_balance import create_topup_payment

            raw_tid = data.get("telegram_id")
            try:
                tid = int(raw_tid) if raw_tid is not None else 0
            except (TypeError, ValueError):
                tid = 0
            doc = create_topup_payment(
                telegram_id=tid if tid > 0 else None,
                customer_id=(data.get("customer_id") or "").strip(),
                email=(data.get("email") or "").strip(),
                amount_rub=data.get("amount_rub"),
            )
            if doc.get("ok"):
                return jsonify(doc), 200
            error = doc.get("error")
            code = 400
            if error == "not_found":
                code = 404
            elif error in ("payments_disabled", "terms_required", "needs_telegram_bind"):
                code = 403
            return jsonify(doc), code
        except Exception as e:
            logger.error("portal-create-payment: %s", e, exc_info=True)
            return jsonify({"ok": False, "error": "server_error"}), 500

    @flask_app.route("/portal-referral", methods=["POST"])
    def portal_referral_handler():
        """Read-only referral snapshot (link, counts, invitees, partner block) for Mini App."""
        try:
            if not _portal_service_auth():
                return _reject_auth()
            data = request.get_json(silent=True) or {}
            from shop_bot.portal_referral import referral_snapshot

            raw_tid = data.get("telegram_id")
            try:
                tid = int(raw_tid) if raw_tid is not None else 0
            except (TypeError, ValueError):
                tid = 0
            doc = referral_snapshot(
                telegram_id=tid if tid > 0 else None,
                customer_id=(data.get("customer_id") or "").strip(),
                email=(data.get("email") or "").strip(),
            )
            code = 200 if doc.get("ok") else 404
            return jsonify(doc), code
        except Exception as e:
            logger.error("portal-referral: %s", e, exc_info=True)
            return jsonify({"ok": False, "error": "server_error"}), 500

    @flask_app.route("/portal-home", methods=["POST"])
    def portal_home_handler():
        """Aggregated home summary (access + balance + referral + capacity/banners)."""
        try:
            if not _portal_service_auth():
                return _reject_auth()
            data = request.get_json(silent=True) or {}
            from shop_bot.portal_home import home_snapshot

            raw_tid = data.get("telegram_id")
            try:
                tid = int(raw_tid) if raw_tid is not None else 0
            except (TypeError, ValueError):
                tid = 0
            doc = home_snapshot(
                telegram_id=tid if tid > 0 else None,
                customer_id=(data.get("customer_id") or "").strip(),
                email=(data.get("email") or "").strip(),
            )
            code = 200 if doc.get("ok") else 404
            return jsonify(doc), code
        except Exception as e:
            logger.error("portal-home: %s", e, exc_info=True)
            return jsonify({"ok": False, "error": "server_error"}), 500

    def _portal_identity(data: dict):
        raw_tid = data.get("telegram_id")
        try:
            tid = int(raw_tid) if raw_tid is not None else 0
        except (TypeError, ValueError):
            tid = 0
        return {
            "telegram_id": tid if tid > 0 else None,
            "customer_id": (data.get("customer_id") or "").strip(),
            "email": (data.get("email") or "").strip(),
        }

    def _support_code(doc: dict) -> int:
        if doc.get("ok"):
            return 200
        err = doc.get("error")
        if err == "not_found":
            return 404
        if err in ("support_disabled", "needs_telegram_bind"):
            return 403
        if err in ("empty_text",):
            return 400
        return 400

    @flask_app.route("/portal-tickets", methods=["POST"])
    def portal_tickets_handler():
        """List the user's support tickets (empty while SUPPORT_TICKETS_LIVE off)."""
        try:
            if not _portal_service_auth():
                return _reject_auth()
            from shop_bot.portal_support import list_tickets

            doc = list_tickets(**_portal_identity(request.get_json(silent=True) or {}))
            return jsonify(doc), 200 if doc.get("ok") else 400
        except Exception as e:
            logger.error("portal-tickets: %s", e, exc_info=True)
            return jsonify({"ok": False, "error": "server_error"}), 500

    @flask_app.route("/portal-unread", methods=["POST"])
    def portal_unread_handler():
        """Unread support messages count for the home bell (0 while gated off)."""
        try:
            if not _portal_service_auth():
                return _reject_auth()
            from shop_bot.portal_support import unread

            doc = unread(**_portal_identity(request.get_json(silent=True) or {}))
            return jsonify(doc), 200
        except Exception as e:
            logger.error("portal-unread: %s", e, exc_info=True)
            return jsonify({"ok": False, "error": "server_error"}), 500

    @flask_app.route("/portal-ticket-get", methods=["POST"])
    def portal_ticket_get_handler():
        """One ticket + its message thread; marks it read."""
        try:
            if not _portal_service_auth():
                return _reject_auth()
            data = request.get_json(silent=True) or {}
            from shop_bot.portal_support import ticket_get

            doc = ticket_get(data.get("ticket_id"), **_portal_identity(data))
            return jsonify(doc), _support_code(doc)
        except Exception as e:
            logger.error("portal-ticket-get: %s", e, exc_info=True)
            return jsonify({"ok": False, "error": "server_error"}), 500

    @flask_app.route("/portal-ticket", methods=["POST"])
    def portal_ticket_create_handler():
        """Create a ticket (subject/text/email) → bridge to TG. Gated by SUPPORT_TICKETS_LIVE."""
        try:
            if not _portal_service_auth():
                return _reject_auth()
            data = request.get_json(silent=True) or {}
            from shop_bot.portal_support import create_ticket

            doc = create_ticket(
                subject=(data.get("subject") or "other"),
                text=(data.get("text") or ""),
                **_portal_identity(data),
            )
            return jsonify(doc), _support_code(doc)
        except Exception as e:
            logger.error("portal-ticket: %s", e, exc_info=True)
            return jsonify({"ok": False, "error": "server_error"}), 500

    @flask_app.route("/portal-ticket-message", methods=["POST"])
    def portal_ticket_message_handler():
        """Append a user message to a ticket → bridge to TG; status → waiting."""
        try:
            if not _portal_service_auth():
                return _reject_auth()
            data = request.get_json(silent=True) or {}
            from shop_bot.portal_support import ticket_message

            doc = ticket_message(data.get("ticket_id"), (data.get("text") or ""), **_portal_identity(data))
            return jsonify(doc), _support_code(doc)
        except Exception as e:
            logger.error("portal-ticket-message: %s", e, exc_info=True)
            return jsonify({"ok": False, "error": "server_error"}), 500

    def _health_authorized() -> bool:
        secret = os.getenv("HEALTH_CHECK_SECRET", "").strip()
        bind = os.getenv("WEBHOOK_BIND_HOST", "127.0.0.1").strip() or "127.0.0.1"
        remote = (request.remote_addr or "").strip()
        if bind in ("127.0.0.1", "localhost", "::1"):
            if remote in ("127.0.0.1", "::1", ""):
                return True
        if secret and request.headers.get("X-Health-Secret", "").strip() == secret:
            return True
        return False

    @flask_app.route("/health", methods=["GET"])
    def health_handler():
        """P2-OPS-BOT-HEALTH-01: liveness + DB + Remna panel API."""
        import time

        if not _health_authorized():
            return jsonify({"ok": False, "error": "forbidden"}), 403

        from shop_bot.data_manager.database import db_connection
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
            with db_connection(timeout=2) as conn:
                conn.execute("SELECT 1")
            checks["db"] = "ok"
        except Exception:
            logger.exception("health db check failed")
            checks["db"] = "error"
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
        except Exception:
            logger.exception("health panel check failed")
            checks["panel"] = "error"
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
