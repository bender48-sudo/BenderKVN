import logging

from flask import Flask, request

from shop_bot.webhook_server.auth import (
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
    flask_app = Flask(__name__)
    pay_queue: PaymentWebhookQueue | None = None

    def _queue() -> PaymentWebhookQueue:
        nonlocal pay_queue
        if pay_queue is None:
            loop = flask_app.config["EVENT_LOOP"]
            pay_queue = PaymentWebhookQueue(bot, payment_processor, loop)
        return pay_queue

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

    @flask_app.route("/cryptobot-webhook", methods=["GET"])
    def crypto_webhook_get_handler():
        try:
            if not is_client_allowed(request) or not verify_crypto_shared_secret(request):
                return _reject_auth()
            data = request.args.to_dict()
            logger.info("Crypto bot webhook received: %s", data.get("status"))
            if data.get("status") != "paid":
                return "ignored", 200
            key = idempotency_key_cryptobot(data)
            body, code = _accept(key, "cryptobot", data)
            return body, code
        except Exception as e:
            logger.error("cryptobot webhook: %s", e, exc_info=True)
            return "Error", 500

    return flask_app
