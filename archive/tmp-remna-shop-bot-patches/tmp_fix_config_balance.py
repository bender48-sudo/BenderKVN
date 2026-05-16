CONFIG = "/opt/remna-shop/src/shop_bot/config.py"

with open(CONFIG) as f:
    content = f.read()

# 1. Add DAILY_RATE and TOPUP_PRESETS after TRAFFIC_PACKS block
OLD = '''WELCOME_MESSAGE = ('''
NEW = '''DAILY_RATE = 6.67  # рублей в день за 1 устройство

TOPUP_PRESETS = {
    "topup_200": ("200 \\u20bd \\u2014 на 30 дней", "200.00", 200),
    "topup_500": ("500 \\u20bd \\u2014 на 75 дней", "500.00", 500),
    "topup_1000": ("1 000 \\u20bd \\u2014 на 150 дней", "1000.00", 1000),
    "topup_2000": ("2 000 \\u20bd \\u2014 на 300 дней", "2000.00", 2000),
}

WELCOME_MESSAGE = ('''

# Hmm, the ruble sign escapes won't be right. Let me use actual characters.
# Rewrite:
OLD = 'WELCOME_MESSAGE = ('
NEW_BLOCK = """DAILY_RATE = 6.67  # рублей в день за 1 устройство

TOPUP_PRESETS = {
    "topup_200": ("200 ₽ — на 30 дней", "200.00", 200),
    "topup_500": ("500 ₽ — на 75 дней", "500.00", 500),
    "topup_1000": ("1 000 ₽ — на 150 дней", "1000.00", 1000),
    "topup_2000": ("2 000 ₽ — на 300 дней", "2000.00", 2000),
}

WELCOME_MESSAGE = ("""

count = content.count(OLD)
print(f"WELCOME_MESSAGE found: {count}")
if count == 1:
    content = content.replace(OLD, NEW_BLOCK, 1)

# 2. Update CHOOSE_PLAN_MESSAGE
content = content.replace(
    'CHOOSE_PLAN_MESSAGE = "Выберите подходящий тариф:"',
    'CHOOSE_PLAN_MESSAGE = "Выберите сумму пополнения:"'
)

# 3. Add new messages after CHOOSE_PAYMENT_METHOD_MESSAGE
content = content.replace(
    'CHOOSE_PAYMENT_METHOD_MESSAGE = "Выберите удобный способ оплаты:"',
    'CHOOSE_PAYMENT_METHOD_MESSAGE = "Выберите удобный способ оплаты:"\n'
    'CHOOSE_TOPUP_MESSAGE = "Выберите сумму пополнения:"\n'
    'CUSTOM_AMOUNT_UNAVAILABLE = "⏳ Произвольная сумма будет доступна после подключения оплаты картой или криптой."'
)

with open(CONFIG, 'w') as f:
    f.write(content)

import ast
try:
    ast.parse(content)
    print("syntax OK")
except SyntaxError as e:
    print(f"SYNTAX ERROR: {e}")

print(f"DAILY_RATE present: {'DAILY_RATE' in content}")
print(f"TOPUP_PRESETS present: {'TOPUP_PRESETS' in content}")
print(f"PLANS still present: {'PLANS' in content}")
print(f"CHOOSE_TOPUP_MESSAGE present: {'CHOOSE_TOPUP_MESSAGE' in content}")
print(f"CUSTOM_AMOUNT_UNAVAILABLE present: {'CUSTOM_AMOUNT_UNAVAILABLE' in content}")
