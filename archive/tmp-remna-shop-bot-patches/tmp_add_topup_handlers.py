HANDLERS = "/opt/remna-shop/src/shop_bot/bot/handlers.py"

with open(HANDLERS) as f:
    content = f.read()

# 1. Add get_balance, add_balance to database imports
OLD_DB_IMPORT = "    grant_referrer_bonus, get_user_by_ref_code\n)"
NEW_DB_IMPORT = "    grant_referrer_bonus, get_user_by_ref_code,\n    get_balance, add_balance\n)"
c1 = content.count(OLD_DB_IMPORT)
print(f"DB import found: {c1}")
if c1 == 1:
    content = content.replace(OLD_DB_IMPORT, NEW_DB_IMPORT)

# 2. Add DAILY_RATE, TOPUP_PRESETS, CUSTOM_AMOUNT_UNAVAILABLE to config imports
OLD_CFG = "    KEY_EMAIL_DOMAIN\n)"
NEW_CFG = "    KEY_EMAIL_DOMAIN,\n    DAILY_RATE, TOPUP_PRESETS, CUSTOM_AMOUNT_UNAVAILABLE\n)"
c2 = content.count(OLD_CFG)
print(f"Config import found: {c2}")
if c2 == 1:
    content = content.replace(OLD_CFG, NEW_CFG)

with open(HANDLERS, 'w') as f:
    f.write(content)

print("Imports updated")

import ast
try:
    ast.parse(content)
    print("syntax OK")
except SyntaxError as e:
    print(f"SYNTAX ERROR: {e}")
