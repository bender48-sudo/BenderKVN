KB = "/opt/remna-shop/src/shop_bot/bot/keyboards.py"

with open(KB) as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    # Line with "buy_new_key" in create_main_menu_keyboard area (lines 13-25)
    if 'callback_data="buy_new_key"' in line and i < 25:
        # Replace callback and text
        new_line = line.replace('buy_new_key', 'show_topup')
        # Replace emoji and text - the text is unicode-escaped
        # \U0001f4b3 = 💳, need \U0001f4b0 = 💰
        new_line = new_line.replace('\U0001f4b3', '\U0001f4b0')
        # Replace Russian text (unicode-escaped)
        # "Купить подписку" = \u041a\u0443\u043f\u0438\u0442\u044c \u043f\u043e\u0434\u043f\u0438\u0441\u043a\u0443
        new_line = new_line.replace(
            '\u041a\u0443\u043f\u0438\u0442\u044c \u043f\u043e\u0434\u043f\u0438\u0441\u043a\u0443',
            '\u041f\u043e\u043f\u043e\u043b\u043d\u0438\u0442\u044c \u0431\u0430\u043b\u0430\u043d\u0441'
        )
        # "Продлить подписку" = \u041f\u0440\u043e\u0434\u043b\u0438\u0442\u044c \u043f\u043e\u0434\u043f\u0438\u0441\u043a\u0443
        new_line = new_line.replace(
            '\u041f\u0440\u043e\u0434\u043b\u0438\u0442\u044c \u043f\u043e\u0434\u043f\u0438\u0441\u043a\u0443',
            '\u041f\u043e\u043f\u043e\u043b\u043d\u0438\u0442\u044c \u0431\u0430\u043b\u0430\u043d\u0441'
        )
        if new_line != line:
            print(f"  Fixed line {i+1}")
            lines[i] = new_line

with open(KB, 'w') as f:
    f.writelines(lines)

content = ''.join(lines)
import ast
try:
    ast.parse(content)
    print("syntax OK")
except SyntaxError as e:
    print(f"SYNTAX ERROR: {e}")

print(f"show_topup count: {content.count('show_topup')}")
print(f"buy_new_key count: {content.count('buy_new_key')}")
