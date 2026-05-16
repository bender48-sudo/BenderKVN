KB = "/opt/remna-shop/src/shop_bot/bot/keyboards.py"

with open(KB) as f:
    lines = f.readlines()

replacements = 0
for i, line in enumerate(lines):
    # Main menu: "Купить подписку" → "Пополнить баланс" (line with show_topup, elif branch)
    if 'callback_data="show_topup"' in line and i < 30:
        if 'Купить' in line or '\u041a\u0443\u043f\u0438\u0442\u044c' in line:
            lines[i] = '        builder.button(text="\U0001f4b0 \u041f\u043e\u043f\u043e\u043b\u043d\u0438\u0442\u044c \u0431\u0430\u043b\u0430\u043d\u0441", callback_data="show_topup")\n'
            replacements += 1
            print(f"  Line {i+1}: Купить → Пополнить баланс")
        elif 'Продлить' in line or '\u041f\u0440\u043e\u0434\u043b\u0438\u0442\u044c' in line:
            lines[i] = '        builder.button(text="\U0001f4b0 \u041f\u043e\u043f\u043e\u043b\u043d\u0438\u0442\u044c \u0431\u0430\u043b\u0430\u043d\u0441", callback_data="show_topup")\n'
            replacements += 1
            print(f"  Line {i+1}: Продлить → Пополнить баланс")

    # Account no-sub keyboard (line ~54)
    if 'callback_data="show_topup"' in line and 40 < i < 60:
        if 'Купить' in line or '\u041a\u0443\u043f\u0438\u0442\u044c' in line:
            lines[i] = '        builder.button(text="\U0001f4b0 \u041f\u043e\u043f\u043e\u043b\u043d\u0438\u0442\u044c \u0431\u0430\u043b\u0430\u043d\u0441", callback_data="show_topup")\n'
            replacements += 1
            print(f"  Line {i+1}: account no-sub → Пополнить баланс")

print(f"\nTotal replacements: {replacements}")

with open(KB, 'w') as f:
    f.writelines(lines)

import ast
content = ''.join(lines)
try:
    ast.parse(content)
    print("syntax OK")
except SyntaxError as e:
    print(f"SYNTAX ERROR: {e}")
