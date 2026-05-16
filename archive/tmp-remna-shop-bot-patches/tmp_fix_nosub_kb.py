KB = "/opt/remna-shop/src/shop_bot/bot/keyboards.py"

with open(KB) as f:
    lines = f.readlines()

# Line 54 (0-indexed 53) - create_account_no_sub_keyboard
for i, line in enumerate(lines):
    if 'callback_data="buy_new_key"' in line and i > 40 and i < 60:
        new_line = line.replace('buy_new_key', 'show_topup')
        new_line = new_line.replace('\U0001f4b3', '\U0001f4b0')
        new_line = new_line.replace(
            '\u041a\u0443\u043f\u0438\u0442\u044c \u043f\u043e\u0434\u043f\u0438\u0441\u043a\u0443',
            '\u041f\u043e\u043f\u043e\u043b\u043d\u0438\u0442\u044c \u0431\u0430\u043b\u0430\u043d\u0441'
        )
        lines[i] = new_line
        print(f"Fixed line {i+1}")

with open(KB, 'w') as f:
    f.writelines(lines)

content = ''.join(lines)
print(f"buy_new_key remaining: {content.count('buy_new_key')}")
print(f"show_topup total: {content.count('show_topup')}")
