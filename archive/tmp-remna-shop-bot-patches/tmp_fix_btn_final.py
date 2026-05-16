KB = "/opt/remna-shop/src/shop_bot/bot/keyboards.py"

with open(KB) as f:
    content = f.read()

NEW_BTN = '        builder.button(text="\\U0001f4b0 \\u041f\\u043e\\u043f\\u043e\\u043b\\u043d\\u0438\\u0442\\u044c \\u0431\\u0430\\u043b\\u0430\\u043d\\u0441", callback_data="show_topup")'

# Line 18: elif not has_active_sub → "Купить подписку" → show_topup
OLD_18 = '        builder.button(text="\\U0001f4b3 \\u041a\\u0443\\u043f\\u0438\\u0442\\u044c \\u043f\\u043e\\u0434\\u043f\\u0438\\u0441\\u043a\\u0443", callback_data="show_topup")'
# Line 20: else → "Продлить подписку" → show_topup
OLD_20 = '        builder.button(text="\\U0001f4b3 \\u041f\\u0440\\u043e\\u0434\\u043b\\u0438\\u0442\\u044c \\u043f\\u043e\\u0434\\u043f\\u0438\\u0441\\u043a\\u0443", callback_data="show_topup")'
# Line 54: account no-sub → "Купить подписку" → show_topup (same as OLD_18)

for old, label in [(OLD_18, "Купить→Пополнить"), (OLD_20, "Продлить→Пополнить")]:
    c = content.count(old)
    print(f"  '{label}': found {c}")
    content = content.replace(old, NEW_BTN)

with open(KB, 'w') as f:
    f.write(content)

import ast
try:
    ast.parse(content)
    print("syntax OK")
except SyntaxError as e:
    print(f"SYNTAX ERROR: {e}")

# Count
search = 'u0431\\u0430\\u043b\\u0430\\u043d\\u0441'
print(f"balance text count: {content.count(search)}")
