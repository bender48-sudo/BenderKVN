HANDLERS = "/opt/remna-shop/src/shop_bot/bot/handlers.py"

with open(HANDLERS) as f:
    lines = f.readlines()

# Find line indices for both text assignments in my_account_handler
active_text_idx = None
inactive_text_idx = None

for i, line in enumerate(lines):
    if i > 570 and i < 595:
        if 'активна до' in line:
            active_text_idx = i
            print(f"Active text at line {i+1}")
        if 'не активна' in line:
            inactive_text_idx = i
            print(f"Inactive text at line {i+1}")

if active_text_idx is None or inactive_text_idx is None:
    print("ERROR: text lines not found")
    exit(1)

# Replace active text line - add balance info
# Original: text = f"... Подписка: активна до {exp}... Приглашено друзей: {ref_count}"
# New: add balance line between subscription and referral
lines[active_text_idx] = '        balance = get_balance(user_id)\n        days_left = int(balance / DAILY_RATE) if balance > 0 else 0\n        balance_line = f"\\U0001f4b0 \\u0411\\u0430\\u043b\\u0430\\u043d\\u0441: {balance:.0f} \\u20bd ({days_left} \\u0434\\u043d.)\\n" if balance > 0 else "\\U0001f4b0 \\u0411\\u0430\\u043b\\u0430\\u043d\\u0441: 0 \\u20bd\\n"\n        text = f"\\U0001f464 <b>\\u0412\\u0430\\u0448 \\u0430\\u043a\\u043a\\u0430\\u0443\\u043d\\u0442 BenderVPN</b>\\n\\n\\U0001f4c5 \\u041f\\u043e\\u0434\\u043f\\u0438\\u0441\\u043a\\u0430: \\u0430\\u043a\\u0442\\u0438\\u0432\\u043d\\u0430 \\u0434\\u043e {exp.strftime(\'%d.%m.%Y\')}\\n{balance_line}\\U0001f465 \\u041f\\u0440\\u0438\\u0433\\u043b\\u0430\\u0448\\u0435\\u043d\\u043e \\u0434\\u0440\\u0443\\u0437\\u0435\\u0439: {ref_count}"\n'

# Hmm this is unmaintainable. Let me write it as actual UTF-8 text.
