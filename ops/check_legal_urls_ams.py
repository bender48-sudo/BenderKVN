#!/usr/bin/env python3
"""Print bot legal/settings URLs from SQLite (run in remna-shop-bot container)."""
from shop_bot.data_manager.database import get_setting
from shop_bot.config import TERMS_URL, PRIVACY_URL, SUPPORT_USER, CHANNEL_URL

STUB_MARKERS = ("не установлена", "не установлен", "Установите её")

keys = ("terms_url", "privacy_url", "support_user", "support_text", "channel_url", "about_text")
for k in keys:
    v = get_setting(k) or ""
    print(f"{k}={v!r}")

print("--- defaults (config stubs) ---")
for name, val in [
    ("TERMS_URL", TERMS_URL),
    ("PRIVACY_URL", PRIVACY_URL),
    ("SUPPORT_USER", SUPPORT_USER),
    ("CHANNEL_URL", CHANNEL_URL),
]:
    print(f"{name}_stub={any(m in val for m in STUB_MARKERS)}")

terms = get_setting("terms_url") or ""
privacy = get_setting("privacy_url") or ""
support = get_setting("support_user") or ""
channel = get_setting("channel_url") or ""

def ok(url: str) -> bool:
    if not url or any(m in url for m in STUB_MARKERS):
        return False
    return url.startswith("http") or url.startswith("@") or "t.me/" in url

# P2-COM-MONETIZE-03: terms + privacy before pay; support for help (channel optional in UI)
ok_all = ok(terms) and ok(privacy) and ok(support)
print(f"LEGAL_OK={ok_all}")
if channel:
    print(f"channel_url_optional={ok(channel)}")
