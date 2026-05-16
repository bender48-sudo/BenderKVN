import logging
import asyncio
from flask import Flask, request, current_app

logger = logging.getLogger(__name__)

def create_webhook_app(bot, payment_processor):
    flask_app = Flask(__name__)

    @flask_app.route('/yookassa-webhook', methods=['POST'])
    def yookassa_webhook_handler():
        try:
            event_json = request.json
            if event_json.get("event") == "payment.succeeded":
                metadata = event_json.get("object", {}).get("metadata", {})
                obj = event_json.get("object", {})
                if metadata.get("t") == "topup":
                    from shop_bot.bot.handlers import process_topup_payment

                    user_id = int(metadata.get("user_id") or metadata.get("u") or 0)
                    amount_rub = float(metadata.get("amount") or metadata.get("a") or 0)
                    pay_id = obj.get("id") or ""
                    idem = f"topup_yk:{pay_id}" if pay_id else None
                    loop = current_app.config["EVENT_LOOP"]
                    asyncio.run_coroutine_threadsafe(
                        process_topup_payment(
                            bot, user_id, amount_rub, idempotency_key=idem, notify=True
                        ),
                        loop,
                    )
                elif metadata:
                    loop = current_app.config['EVENT_LOOP']
                    asyncio.run_coroutine_threadsafe(payment_processor(bot, metadata), loop)
            return 'OK', 200
        except Exception as e:
            logger.error(f"Error in yookassa webhook handler: {e}")
            return 'Error', 500

    @flask_app.route('/crypto-webhook', methods=['POST'])
    def crypto_webhook_handler():
        try:
            data = request.json
            logger.info(f"Crypto webhook received: {data}")

            if data.get("status") == "paid":
                metadata = data.get("metadata", {})
                if metadata:
                    loop = current_app.config['EVENT_LOOP']
                    asyncio.run_coroutine_threadsafe(payment_processor(bot, metadata), loop)
            
            return 'OK', 200
        except Exception as e:
            logger.error(f"Error in crypto webhook handler: {e}")
            return 'Error', 500
        
    @flask_app.route('/cryptobot-webhook', methods=['GET'])
    def crypto_webhook_get_handler():
        try:
            data = request.args
            logger.info(f"Crypto bot webhook received: {data}")

            if data.get("status") == "paid":
                metadata = data.to_dict()
                loop = current_app.config['EVENT_LOOP']
                asyncio.run_coroutine_threadsafe(payment_processor(bot, metadata), loop)
            
            return 'OK', 200
        except Exception as e:
            logger.error(f"Error in crypto bot webhook handler: {e}")
            return 'Error', 500

    return flask_app