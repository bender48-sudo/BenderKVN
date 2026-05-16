import re

SCHEDULER = "/opt/remna-shop/src/shop_bot/data_manager/scheduler.py"

with open(SCHEDULER) as f:
    content = f.read()

# Step 4: Fix dead button choose_plan -> buy_new_key + update button text
content = content.replace(
    'InlineKeyboardButton(text="💳 Оформить подписку", callback_data="choose_plan")',
    'InlineKeyboardButton(text="💳 Продлить — 200 ₽/мес", callback_data="buy_new_key")'
)

# Step 6: Update notification texts
# mark > 0 text (generic for 7, 3, 1 days)
content = content.replace(
    'f"⏰ Ваш бесплатный период заканчивается через {mark} дн.!\\n\\nПонравился BenderVPN? Продолжите пользоваться —\\nоформите подписку прямо здесь 👇"',
    'f"⚠️ Через {mark} дн. закончится подписка BenderVPN\\n\\nЧтобы не остаться без VPN — продлите подписку."'
)

# mark == 0 text (expired)
content = content.replace(
    'f"❗️ Ваш бесплатный период закончился.\\n\\nОформите подписку, чтобы продолжить пользоваться BenderVPN 👇"',
    '"❌ Подписка BenderVPN закончилась\\n\\nЧтобы продолжить пользоваться VPN — продлите подписку."'
)

with open(SCHEDULER, 'w') as f:
    f.write(content)

# Verify
count_choose = content.count('choose_plan')
count_buy = content.count('buy_new_key')
print(f"choose_plan occurrences: {count_choose} (expected 0)")
print(f"buy_new_key occurrences: {count_buy} (expected 2)")
print(f"'Продлить — 200' occurrences: {content.count('Продлить — 200')}")
print(f"Notification text updated: {'Через {mark} дн. закончится' in content}")
print(f"Expired text updated: {'Подписка BenderVPN закончилась' in content}")
