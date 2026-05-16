HANDLERS = "/opt/remna-shop/src/shop_bot/bot/handlers.py"

with open(HANDLERS) as f:
    content = f.read()

# Strategy: replace the entire my_account_handler function body
# Find from "@user_router.callback_query(F.data == "my_account")" to the next handler

OLD_HANDLER = '''@user_router.callback_query(F.data == "my_account")
async def my_account_handler(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    user_db_data = get_user(user_id)
    user_keys = get_user_keys(user_id)
    now = datetime.now()
    active_keys = [k for k in user_keys if datetime.fromisoformat(k["expiry_date"]) > now]
    if active_keys:
        latest = max(active_keys, key=lambda k: datetime.fromisoformat(k["expiry_date"]))
        exp = datetime.fromisoformat(latest["expiry_date"])
        ref_code = ensure_user_ref_code(user_id)
        ref_count = count_referrals(ref_code)
        text = f"\U0001f464 <b>\u0412\u0430\u0448 \u0430\u043a\u043a\u0430\u0443\u043d\u0442 BenderVPN</b>\\n\\n\U0001f4c5 \u041f\u043e\u0434\u043f\u0438\u0441\u043a\u0430: \u0430\u043a\u0442\u0438\u0432\u043d\u0430 \u0434\u043e {exp.strftime('%d.%m.%Y')}\\n\U0001f465 \u041f\u0440\u0438\u0433\u043b\u0430\u0448\u0435\u043d\u043e \u0434\u0440\u0443\u0437\u0435\u0439: {ref_count}"
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboards.create_account_keyboard(True))
    else:
        trial_available = not (user_db_data and user_db_data.get("trial_used"))
        ref_code = ensure_user_ref_code(user_id)
        ref_count = count_referrals(ref_code)
        text = f"\U0001f464 <b>\u0412\u0430\u0448 \u0430\u043a\u043a\u0430\u0443\u043d\u0442 BenderVPN</b>\\n\\n\U0001f4c5 \u041f\u043e\u0434\u043f\u0438\u0441\u043a\u0430: \u043d\u0435 \u0430\u043a\u0442\u0438\u0432\u043d\u0430\\n\U0001f465 \u041f\u0440\u0438\u0433\u043b\u0430\u0448\u0435\u043d\u043e \u0434\u0440\u0443\u0437\u0435\u0439: {ref_count}"
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboards.create_account_no_sub_keyboard(trial_available))'''

# The problem is that the file may have these as actual Unicode chars or as escape sequences.
# Let me just search for key fragments that are definitely there.

# Find using a unique substring that won't have encoding issues
if 'активна до' not in content:
    print("ERROR: 'активна до' not found in content")
    exit(1)

# Replace line by line approach
lines = content.split('\n')
new_lines = []
in_handler = False
handler_replaced = False
skip_until_next_handler = False

for i, line in enumerate(lines):
    if 'F.data == "my_account"' in line:
        in_handler = True
        # Write new handler
        new_lines.append('@user_router.callback_query(F.data == "my_account")')
        new_lines.append('async def my_account_handler(callback: types.CallbackQuery):')
        new_lines.append('    await callback.answer()')
        new_lines.append('    user_id = callback.from_user.id')
        new_lines.append('    user_db_data = get_user(user_id)')
        new_lines.append('    user_keys = get_user_keys(user_id)')
        new_lines.append('    balance = get_balance(user_id)')
        new_lines.append('    days_left = int(balance / DAILY_RATE) if balance > 0 else 0')
        new_lines.append('    now = datetime.now()')
        new_lines.append('    active_keys = [k for k in user_keys if datetime.fromisoformat(k["expiry_date"]) > now]')
        new_lines.append('    ref_code = ensure_user_ref_code(user_id)')
        new_lines.append('    ref_count = count_referrals(ref_code)')
        new_lines.append('    if active_keys:')
        new_lines.append('        latest = max(active_keys, key=lambda k: datetime.fromisoformat(k["expiry_date"]))')
        new_lines.append('        exp = datetime.fromisoformat(latest["expiry_date"])')
        new_lines.append('        balance_text = f"\\U0001f4b0 \u0411\u0430\u043b\u0430\u043d\u0441: {balance:.0f} \u20bd ({days_left} \u0434\u043d.)\\n" if balance > 0 else "\\U0001f4b0 \u0411\u0430\u043b\u0430\u043d\u0441: 0 \u20bd\\n"')
        new_lines.append('        text = f"\\U0001f464 <b>\u0412\u0430\u0448 \u0430\u043a\u043a\u0430\u0443\u043d\u0442 BenderVPN</b>\\n\\n\\U0001f4c5 \u041f\u043e\u0434\u043f\u0438\u0441\u043a\u0430: \u0430\u043a\u0442\u0438\u0432\u043d\u0430 \u0434\u043e {exp.strftime(\'%d.%m.%Y\')}\\n{balance_text}\\U0001f465 \u041f\u0440\u0438\u0433\u043b\u0430\u0448\u0435\u043d\u043e \u0434\u0440\u0443\u0437\u0435\u0439: {ref_count}"')
        new_lines.append('        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboards.create_account_keyboard(True))')
        new_lines.append('    else:')
        new_lines.append('        trial_available = not (user_db_data and user_db_data.get("trial_used"))')
        new_lines.append('        balance_text = f"\\U0001f4b0 \u0411\u0430\u043b\u0430\u043d\u0441: {balance:.0f} \u20bd\\n\\u2139\\ufe0f \u041f\u043e\u043f\u043e\u043b\u043d\u0438\u0442\u0435 \u0431\u0430\u043b\u0430\u043d\u0441 \u0447\u0442\u043e\u0431\u044b \u043f\u0440\u043e\u0434\u043e\u043b\u0436\u0438\u0442\u044c \u043f\u043e\u0441\u043b\u0435 \u043f\u0440\u043e\u0431\u043d\u043e\u0433\u043e \\u043f\u0435\u0440\u0438\u043e\u0434\u0430\\n" if not trial_available else ""')
        new_lines.append('        text = f"\\U0001f464 <b>\u0412\u0430\u0448 \u0430\u043a\u043a\u0430\u0443\u043d\u0442 BenderVPN</b>\\n\\n\\U0001f4c5 \u041f\u043e\u0434\u043f\u0438\u0441\u043a\u0430: \u043d\u0435 \u0430\u043a\u0442\u0438\u0432\u043d\u0430\\n{balance_text}\\U0001f465 \u041f\u0440\u0438\u0433\u043b\u0430\u0448\u0435\u043d\u043e \u0434\u0440\u0443\u0437\u0435\u0439: {ref_count}"')
        new_lines.append('        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboards.create_account_no_sub_keyboard(trial_available))')
        handler_replaced = True
        skip_until_next_handler = True
        continue

    if skip_until_next_handler:
        # Skip old handler lines until we hit next @user_router or non-indented line
        stripped = line.strip()
        if stripped.startswith('@user_router') or (stripped.startswith('async def') and not stripped.startswith('async def my_account')):
            skip_until_next_handler = False
            new_lines.append(line)
        elif stripped == '' and i + 1 < len(lines) and lines[i+1].strip().startswith('@'):
            skip_until_next_handler = False
            new_lines.append(line)
        # else: skip this line (old handler body)
        continue

    new_lines.append(line)

content = '\n'.join(new_lines)

with open(HANDLERS, 'w') as f:
    f.write(content)

import ast
try:
    ast.parse(content)
    print("syntax OK")
except SyntaxError as e:
    print(f"SYNTAX ERROR: {e}")

print(f"handler_replaced: {handler_replaced}")
has_balance = 'Баланс' in content
print(f"has balance text: {has_balance}")
print(f"get_balance in my_account area: {content.count('get_balance')}")
