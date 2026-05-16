KB = "/opt/remna-shop/src/shop_bot/bot/keyboards.py"

with open(KB) as f:
    content = f.read()
    lines = content.split('\n')

# 1. Update main menu: "Купить подписку" → "Пополнить баланс", "Продлить" → "Пополнить баланс"
# Find and replace in create_main_menu_keyboard

# "Купить подписку" with callback buy_new_key → "Пополнить баланс" with show_topup
for i, line in enumerate(lines):
    if 'Купить подписку' in line and 'callback_data="buy_new_key"' in line:
        lines[i] = line.replace('Купить подписку', 'Пополнить баланс').replace('buy_new_key', 'show_topup')
        # Also change emoji from 💳 to 💰
        lines[i] = lines[i].replace('\\U0001f4b3', '\\U0001f4b0')
        if '\U0001f4b3' in lines[i]:
            lines[i] = lines[i].replace('\U0001f4b3', '\U0001f4b0')
        print(f"  Line {i+1}: Купить → Пополнить: {lines[i].rstrip()}")

    if 'Продлить подписку' in line and 'callback_data="buy_new_key"' in line:
        lines[i] = line.replace('Продлить подписку', 'Пополнить баланс').replace('buy_new_key', 'show_topup')
        lines[i] = lines[i].replace('\\U0001f4b3', '\\U0001f4b0')
        if '\U0001f4b3' in lines[i]:
            lines[i] = lines[i].replace('\U0001f4b3', '\U0001f4b0')
        print(f"  Line {i+1}: Продлить → Пополнить: {lines[i].rstrip()}")

content = '\n'.join(lines)

# 2. Add topup keyboards before wizard section
WIZARD_MARKER = '# ==================== Wizard onboarding keyboards ===================='

TOPUP_KBS = '''# ==================== Topup/balance keyboards ====================

def create_topup_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="200 \\u20bd \\u2014 на 30 дней", callback_data="topup_200")
    builder.button(text="500 \\u20bd \\u2014 на 75 дней", callback_data="topup_500")
    builder.button(text="1 000 \\u20bd \\u2014 на 150 дней", callback_data="topup_1000")
    builder.button(text="2 000 \\u20bd \\u2014 на 300 дней", callback_data="topup_2000")
    builder.button(text="\\U0001f4ac Другая сумма", callback_data="topup_custom")
    builder.button(text="\\U0001f519 Назад", callback_data="back_to_main_menu")
    builder.adjust(1)
    return builder.as_markup()

def create_topup_payment_keyboard(amount_rub, topup_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="\\u2b50 Telegram Stars", callback_data=f"pay_stars_topup_{topup_id}")
    builder.button(text="\\U0001f519 Назад", callback_data="show_topup")
    builder.adjust(1)
    return builder.as_markup()

'''

# Hmm the unicode escapes won't render. Let me use actual characters.
TOPUP_KBS = """# ==================== Topup/balance keyboards ====================

def create_topup_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="200 \u20bd \u2014 на 30 дней", callback_data="topup_200")
    builder.button(text="500 \u20bd \u2014 на 75 дней", callback_data="topup_500")
    builder.button(text="1 000 \u20bd \u2014 на 150 дней", callback_data="topup_1000")
    builder.button(text="2 000 \u20bd \u2014 на 300 дней", callback_data="topup_2000")
    builder.button(text="\U0001f4ac Другая сумма", callback_data="topup_custom")
    builder.button(text="\U0001f519 Назад", callback_data="back_to_main_menu")
    builder.adjust(1)
    return builder.as_markup()

def create_topup_payment_keyboard(amount_rub, topup_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="\u2b50 Telegram Stars", callback_data=f"pay_stars_topup_{topup_id}")
    builder.button(text="\U0001f519 Назад", callback_data="show_topup")
    builder.adjust(1)
    return builder.as_markup()

"""

if WIZARD_MARKER in content:
    content = content.replace(WIZARD_MARKER, TOPUP_KBS + WIZARD_MARKER)
    print("Topup keyboards inserted before wizard section")
else:
    content += '\n' + TOPUP_KBS
    print("Topup keyboards appended at end")

with open(KB, 'w') as f:
    f.write(content)

import ast
try:
    ast.parse(content)
    print("syntax OK")
except SyntaxError as e:
    print(f"SYNTAX ERROR: {e}")

print(f"create_topup_keyboard: {'def create_topup_keyboard' in content}")
print(f"create_topup_payment_keyboard: {'def create_topup_payment_keyboard' in content}")
print(f"show_topup in menu: {content.count('show_topup')}")
print(f"buy_new_key in menu: {content.count('buy_new_key')}")
