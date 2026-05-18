"""AMS deploy entry: secured webhook app (auth, queue, portal trial routes)."""
from shop_bot.webhook_server.app import create_webhook_app

__all__ = ["create_webhook_app"]
