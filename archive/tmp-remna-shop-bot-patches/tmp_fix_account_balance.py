HANDLERS = "/opt/remna-shop/src/shop_bot/bot/handlers.py"

with open(HANDLERS) as f:
    lines = f.readlines()

# Find the two text= lines in my_account_handler
for i, line in enumerate(lines):
    # Active subscription text (line ~586)
    if 'Подписка: активна до' in line and 'Приглашено друзей' in line:
        # Replace the whole text assignment
        lines[i] = (
            '        balance = get_balance(user_id)\n'
            '        days_left = int(balance / DAILY_RATE) if balance > 0 else 0\n'
            '        text = (f"\\U0001f464 <b>\\u0412\\u0430\\u0448 \\u0430\\u043a\\u043a\\u0430\\u0443\\u043d\\u0442 BenderVPN</b>\\n\\n"\n'
            '               f"\\U0001f4c5 \\u041f\\u043e\\u0434\\u043f\\u0438\\u0441\\u043a\\u0430: \\u0430\\u043a\\u0442\\u0438\\u0432\\u043d\\u0430 \\u0434\\u043e {exp.strftime(chr(37)+chr(100)+chr(46)+chr(37)+chr(109)+chr(46)+chr(37)+chr(89))}\\n"\n'
        )
        # Hmm this is getting messy with escapes. Let me use a different approach.
        break

# Actually, let me just use a clean approach - find and replace the exact text lines
print("Using line-range replacement approach...")
