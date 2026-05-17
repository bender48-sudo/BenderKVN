"""AMS hot-patch webhook app: prod baseline + /portal-web-trial (no payment_queue refactor)."""
import asyncio
import logging
import os

from flask import Flask, jsonify, request, current_app

logger = logging.getLogger(__name__)


def create_webhook_app(bot, payment_processor):
    flask_app = Flask(__name__)

    @flask_app.route("/yookassa-webhook", methods=["POST"])
    def yookassa_webhook_handler():
        try:
            event_json = request.json
            if event_json.get("event") == "payment.succeeded":
                metadata = event_json.get("object", {}).get("metadata", {})
                if metadata:
                    loop = current_app.config["EVENT_LOOP"]
                    asyncio.run_coroutine_threadsafe(payment_processor(bot, metadata), loop)
            return "OK", 200
        except Exception as e:
            logger.error("Error in yookassa webhook handler: %s", e)
            return "Error", 500

    @flask_app.route("/crypto-webhook", methods=["POST"])
    def crypto_webhook_handler():
        try:
            data = request.json
            logger.info("Crypto webhook received: %s", data.get("status") if data else None)
            if data.get("status") == "paid":
                metadata = data.get("metadata", {})
                if metadata:
                    loop = current_app.config["EVENT_LOOP"]
                    asyncio.run_coroutine_threadsafe(payment_processor(bot, metadata), loop)
            return "OK", 200
        except Exception as e:
            logger.error("Error in crypto webhook handler: %s", e)
            return "Error", 500

    @flask_app.route("/cryptobot-webhook", methods=["GET"])
    def crypto_webhook_get_handler():
        try:
            data = request.args
            logger.info("Crypto bot webhook received: %s", data.get("status"))
            if data.get("status") == "paid":
                metadata = data.to_dict()
                loop = current_app.config["EVENT_LOOP"]
                asyncio.run_coroutine_threadsafe(payment_processor(bot, metadata), loop)
            return "OK", 200
        except Exception as e:
            logger.error("Error in crypto bot webhook handler: %s", e)
            return "Error", 500

    @flask_app.route("/portal-web-trial", methods=["POST"])
    def portal_web_trial_handler():
        secret = os.getenv("PORTAL_WEB_TRIAL_SECRET", "").strip()
        if not secret or request.headers.get("X-Portal-Web-Trial-Key") != secret:
            return "forbidden", 403
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip()
        phone = (data.get("phone") or "").strip() or None
        try:
            from shop_bot.portal_web_trial import issue_web_trial

            result = asyncio.run(issue_web_trial(email, phone))
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
            return "forbidden", 403
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip()
        try:
            from shop_bot.portal_web_trial import recover_web_trial

            result = asyncio.run(recover_web_trial(email))
            code = 200 if result.get("ok") else 404
            if result.get("error") == "invalid_email":
                code = 400
            return jsonify(result), code
        except Exception as e:
            logger.error("portal-web-trial-recover: %s", e, exc_info=True)
            return jsonify({"ok": False, "error": "server_error"}), 500

    return flask_app
