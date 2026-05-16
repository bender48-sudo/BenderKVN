HANDLERS = "/opt/remna-shop/src/shop_bot/bot/handlers.py"

with open(HANDLERS) as f:
    content = f.read()

# 1. Add KEY_EMAIL_DOMAIN to the config import
content = content.replace(
    "    PLANS, get_profile_text, get_vpn_active_text, VPN_INACTIVE_TEXT, VPN_NO_DATA_TEXT,\n"
    "    get_key_info_text, CHOOSE_PAYMENT_METHOD_MESSAGE, get_purchase_success_text, ABOUT_TEXT, TERMS_URL, PRIVACY_URL, SUPPORT_USER, SUPPORT_TEXT\n"
    ")",
    "    PLANS, get_profile_text, get_vpn_active_text, VPN_INACTIVE_TEXT, VPN_NO_DATA_TEXT,\n"
    "    get_key_info_text, CHOOSE_PAYMENT_METHOD_MESSAGE, get_purchase_success_text, ABOUT_TEXT, TERMS_URL, PRIVACY_URL, SUPPORT_USER, SUPPORT_TEXT,\n"
    "    KEY_EMAIL_DOMAIN\n"
    ")"
)

# 2. Replace trial email
content = content.replace(
    'email = f"user{user_id}-key{key_number}-trial@kitsura.fun"',
    'email = f"user{user_id}-key{key_number}-trial@{KEY_EMAIL_DOMAIN}"'
)

# 3. Replace paid email
content = content.replace(
    'email = f"user{user_id}-key{key_number}@kitsura.fun"',
    'email = f"user{user_id}-key{key_number}@{KEY_EMAIL_DOMAIN}"'
)

with open(HANDLERS, 'w') as f:
    f.write(content)

# Verify
kitsura_count = content.count('kitsura')
domain_count = content.count('KEY_EMAIL_DOMAIN')
print(f"kitsura occurrences: {kitsura_count} (expected 0)")
print(f"KEY_EMAIL_DOMAIN occurrences: {domain_count} (expected 3 — 1 import + 2 usages)")
