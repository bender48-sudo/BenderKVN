"""Deploy alias: copied to shop_bot/webhook_server/app.py on AMS (see ops/deploy-bot-payment-webhook-ams.ps1)."""
from shop_bot.webhook_server.app import create_webhook_app

__all__ = ["create_webhook_app"]
