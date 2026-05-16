SCHEDULER = "/opt/remna-shop/src/shop_bot/data_manager/scheduler.py"

with open(SCHEDULER) as f:
    content = f.read()

# 1. Replace button text and callback (both occurrences)
old_btn = 'InlineKeyboardButton(text="\U0001f4b3 \u041f\u0440\u043e\u0434\u043b\u0438\u0442\u044c \u2014 200 \u20bd/\u043c\u0435\u0441", callback_data="buy_new_key")'
new_btn = 'InlineKeyboardButton(text="\U0001f4b0 \u041f\u043e\u043f\u043e\u043b\u043d\u0438\u0442\u044c \u0431\u0430\u043b\u0430\u043d\u0441", callback_data="show_topup")'

c1 = content.count(old_btn)
print(f"Old button found: {c1}")

if c1 == 0:
    # Try with the actual characters
    old_btn2 = 'Продлить — 200 ₽/мес", callback_data="buy_new_key"'
    c1b = content.count(old_btn2)
    print(f"Trying alt match: {c1b}")
    if c1b > 0:
        content = content.replace(old_btn2, 'Пополнить баланс", callback_data="show_topup"')
        # Also fix emoji
        content = content.replace('text="💳 Пополнить', 'text="💰 Пополнить')
        print(f"Replaced {c1b} via alt match")
else:
    content = content.replace(old_btn, new_btn)
    print(f"Replaced {c1} buttons")

# 2. Update notification texts to mention balance
# Add balance import at top of scheduler
if 'from shop_bot.data_manager import database' in content and 'database.get_balance' not in content:
    # We'll use database.get_balance(user_id) inline since database is already imported
    pass

# For mark > 0 text: add balance info
old_text_mark = 'Через {mark} дн. закончится подписка BenderVPN\\n\\nЧтобы не остаться без VPN — продлите подписку.'
new_text_mark = 'Через {mark} дн. закончится подписка BenderVPN\\n\\n💰 Баланс: {int(database.get_balance(user_id)):.0f} ₽\\n\\nПополните баланс чтобы не остаться без VPN.'

c2 = content.count(old_text_mark)
print(f"Mark>0 text found: {c2}")
if c2 > 0:
    content = content.replace(old_text_mark, new_text_mark)

# For mark == 0 text
old_text_expired = 'Подписка BenderVPN закончилась\\n\\nЧтобы продолжить пользоваться VPN — продлите подписку.'
new_text_expired = 'Подписка BenderVPN закончилась\\n\\n💰 Баланс: {int(database.get_balance(user_id)):.0f} ₽\\n\\nПополните баланс чтобы продолжить.'

c3 = content.count(old_text_expired)
print(f"Expired text found: {c3}")
if c3 > 0:
    content = content.replace(old_text_expired, new_text_expired)

with open(SCHEDULER, 'w') as f:
    f.write(content)

import ast
try:
    ast.parse(content)
    print("syntax OK")
except SyntaxError as e:
    print(f"SYNTAX ERROR: {e}")

print(f"'show_topup' in scheduler: {content.count('show_topup')}")
print(f"'buy_new_key' in scheduler: {content.count('buy_new_key')}")
print(f"'get_balance' in scheduler: {content.count('get_balance')}")
