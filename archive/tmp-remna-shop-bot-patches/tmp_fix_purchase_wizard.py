HANDLERS = "/opt/remna-shop/src/shop_bot/bot/handlers.py"

with open(HANDLERS) as f:
    lines = f.readlines()

# Find the two lines: final_text = get_purchase_success_text... and the send_message after it
target_idx = None
for i, line in enumerate(lines):
    if 'final_text = get_purchase_success_text(' in line:
        target_idx = i
        break

if target_idx is None:
    print("ERROR: get_purchase_success_text line not found")
else:
    print(f"Found at line {target_idx + 1}: {lines[target_idx].rstrip()}")
    print(f"Next line {target_idx + 2}: {lines[target_idx + 1].rstrip()}")

    # Get indentation level
    indent = '        '  # 8 spaces, same as the existing block

    # Replace the two lines with conditional wizard + fallback
    old_lines = lines[target_idx:target_idx + 2]

    new_lines = [
        f'{indent}# Wizard for first-time new key purchases\n',
        f'{indent}if action == "new" and not has_action(user_id, "wizard_complete"):\n',
        f'{indent}    _sub_url = sub_url if "sub_url" in dir() else uri\n',
        f'{indent}    log_action(user_id, "wizard_sub_url", _sub_url)\n',
        f'{indent}    await bot.send_message(\n',
        f'{indent}        chat_id=user_id,\n',
        f'{indent}        text=WIZARD_TEXTS["step_1"],\n',
        f'{indent}        reply_markup=keyboards.create_wizard_step1_keyboard(),\n',
        f'{indent}        parse_mode="HTML"\n',
        f'{indent}    )\n',
        f'{indent}    log_action(user_id, "wizard_step_1", "from_purchase")\n',
        f'{indent}else:\n',
        f'{indent}    final_text = get_purchase_success_text(action=action, key_number=key_number, expiry_date=expiry_dt, connection_string=uri)\n',
        f'{indent}    await bot.send_message(chat_id=user_id, text=final_text, reply_markup=keyboards.create_key_info_keyboard(key_id))\n',
    ]

    lines[target_idx:target_idx + 2] = new_lines

    with open(HANDLERS, 'w') as f:
        f.writelines(lines)

    print(f"\nReplaced 2 lines with {len(new_lines)} lines")

    with open(HANDLERS) as f:
        content = f.read()

    import ast
    try:
        ast.parse(content)
        print("syntax OK")
    except SyntaxError as e:
        print(f"SYNTAX ERROR: {e}")

    print(f"'from_purchase' present: {'from_purchase' in content}")
    print(f"'wizard_complete' check present: {content.count('wizard_complete')}")
