HANDLERS = "/opt/remna-shop/src/shop_bot/bot/handlers.py"

with open(HANDLERS) as f:
    lines = f.readlines()

# Find "logger.info(f"Converted metadata: {metadata}")" line
# and "await process_successful_payment(bot, metadata)" line
# Insert topup check between them

target_idx = None
for i, line in enumerate(lines):
    if 'logger.info(f"Converted metadata:' in line:
        target_idx = i
        print(f"Found metadata log at line {i+1}")
        break

if target_idx is None:
    print("ERROR: metadata log line not found")
    exit(1)

# The next line should be "await process_successful_payment(bot, metadata)"
# We insert BEFORE that line, adding topup check

# Find the process_successful_payment call after target_idx
call_idx = None
for i in range(target_idx, min(target_idx + 5, len(lines))):
    if 'await process_successful_payment(bot, metadata)' in lines[i]:
        call_idx = i
        print(f"Found process_successful_payment call at line {i+1}")
        break

if call_idx is None:
    print("ERROR: process_successful_payment call not found")
    exit(1)

# Replace the two lines (metadata log + process call) with topup-aware version
indent = '        '  # 8 spaces (inside try block)
new_lines = [
    f'{indent}logger.info(f"Converted metadata: {{metadata}}")\n',
    f'\n',
    f'{indent}# Handle topup payments (balance model)\n',
    f'{indent}if payload_data.get("t") == "topup":\n',
    f'{indent}    amount_rub = float(payload_data.get("a", 0))\n',
    f'{indent}    if amount_rub > 0:\n',
    f'{indent}        add_balance(user_id, amount_rub)\n',
    f'{indent}        new_balance = get_balance(user_id)\n',
    f'{indent}        days_left = int(new_balance / DAILY_RATE) if new_balance > 0 else 0\n',
    f'{indent}        # Create key if user has none\n',
    f'{indent}        user_keys = get_user_keys(user_id)\n',
    f'{indent}        if not user_keys:\n',
    f'{indent}            key_number = get_next_key_number(user_id)\n',
    f'{indent}            email = f"user{{user_id}}-key{{key_number}}@{{KEY_EMAIL_DOMAIN}}"\n',
    f'{indent}            uri, expire_iso, vless_uuid, sub_url = await remnawave_api.provision_key(email, days=30, telegram_id=str(user_id))\n',
    f'{indent}            if uri and expire_iso and vless_uuid:\n',
    f'{indent}                expiry_dt = datetime.fromisoformat(expire_iso.replace("Z", "+00:00"))\n',
    f'{indent}                expiry_ms = int(expiry_dt.timestamp() * 1000)\n',
    f'{indent}                add_new_key(user_id, vless_uuid, email, expiry_ms)\n',
    f'{indent}                log_action(user_id, "wizard_sub_url", sub_url or uri)\n',
    f'{indent}                # Show wizard for first-time users\n',
    f'{indent}                if not has_action(user_id, "wizard_complete"):\n',
    f'{indent}                    await bot.send_message(\n',
    f'{indent}                        chat_id=user_id,\n',
    f'{indent}                        text=WIZARD_TEXTS["step_1"],\n',
    f'{indent}                        reply_markup=keyboards.create_wizard_step1_keyboard(),\n',
    f'{indent}                        parse_mode="HTML"\n',
    f'{indent}                    )\n',
    f'{indent}                    log_action(user_id, "wizard_step_1", "from_topup")\n',
    f'{indent}                    bot_logger.payment(user_id, "TELEGRAM_STARS", payment.total_amount, "SUCCESS")\n',
    f'{indent}                    return\n',
    f'{indent}        await bot.send_message(\n',
    f'{indent}            chat_id=user_id,\n',
    f'{indent}            text=(\n',
    f'{indent}                f"\\u2705 Баланс пополнен на {{amount_rub:.0f}} \\u20bd\\n\\n"\n',
    f'{indent}                f"\\U0001f4b0 Текущий баланс: {{new_balance:.0f}} \\u20bd\\n"\n',
    f'{indent}                f"\\U0001f4c5 Хватит на: {{days_left}} дн."\n',
    f'{indent}            ),\n',
    f'{indent}            parse_mode="HTML"\n',
    f'{indent}        )\n',
    f'{indent}        log_action(user_id, "topup", f"{{amount_rub}}")\n',
    f'{indent}        bot_logger.payment(user_id, "TELEGRAM_STARS", payment.total_amount, "SUCCESS")\n',
    f'{indent}        return\n',
    f'\n',
    f'{indent}await process_successful_payment(bot, metadata)\n',
]

lines[target_idx:call_idx + 1] = new_lines

with open(HANDLERS, 'w') as f:
    f.writelines(lines)

print(f"Replaced {call_idx - target_idx + 1} lines with {len(new_lines)} lines")

content = ''.join(lines)
import ast
try:
    ast.parse(content)
    print("syntax OK")
except SyntaxError as e:
    print(f"SYNTAX ERROR: {e}")

print(f"'topup' in handlers: {content.count('topup')}")
print(f"add_balance calls: {content.count('add_balance')}")
