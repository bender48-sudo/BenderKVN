HANDLERS = "/opt/remna-shop/src/shop_bot/bot/handlers.py"

with open(HANDLERS) as f:
    lines = f.readlines()

# Find the block:
#     if user_data and user_data.get('agreed_to_terms'):
#         await message.answer("👋 Снова здравствуйте..."...)
#         await show_main_menu(message)

# We need to insert wizard check between the greeting and show_main_menu
target_idx = None
for i, line in enumerate(lines):
    if 'await show_main_menu(message)' in line and i > 190 and i < 230:
        target_idx = i
        print(f"Found show_main_menu at line {i+1}: {line.rstrip()}")
        break

if target_idx is None:
    print("ERROR: show_main_menu not found in start handler")
else:
    # Replace the single show_main_menu line with wizard check + fallback
    indent = '        '  # 8 spaces
    new_lines = [
        f'{indent}# Check if wizard was started but not completed\n',
        f'{indent}if has_action(user_id, "wizard_step_1") and not has_action(user_id, "wizard_complete"):\n',
        f'{indent}    sub_url = _get_wizard_sub_url(user_id)\n',
        f'{indent}    if sub_url:\n',
        f'{indent}        last_step = 1\n',
        f'{indent}        for s in [4, 3, 2]:\n',
        f'{indent}            if has_action(user_id, f"wizard_step_{{s}}"):\n',
        f'{indent}                last_step = s\n',
        f'{indent}                break\n',
        f'{indent}        next_step = min(last_step + 1, 4)\n',
        f'{indent}        from aiogram.utils.keyboard import InlineKeyboardBuilder\n',
        f'{indent}        wb = InlineKeyboardBuilder()\n',
        f'{indent}        wb.button(text=f"\\u27a1\\ufe0f \\u041f\\u0440\\u043e\\u0434\\u043e\\u043b\\u0436\\u0438\\u0442\\u044c \\u043d\\u0430\\u0441\\u0442\\u0440\\u043e\\u0439\\u043a\\u0443 (\\u0448\\u0430\\u0433 {{next_step}})", callback_data=f"wizard_step_{{next_step}}" if next_step > 1 else "wizard_step_1_back")\n',
        f'{indent}        wb.button(text="\\U0001f3e0 \\u0412 \\u0433\\u043b\\u0430\\u0432\\u043d\\u043e\\u0435 \\u043c\\u0435\\u043d\\u044e", callback_data="back_to_main_menu")\n',
        f'{indent}        wb.adjust(1)\n',
        f'{indent}        await message.answer(\n',
        f'{indent}            "\\U0001f44b \\u0421 \\u0432\\u043e\\u0437\\u0432\\u0440\\u0430\\u0449\\u0435\\u043d\\u0438\\u0435\\u043c!\\n\\n\\u0412\\u044b \\u043d\\u0435 \\u0437\\u0430\\u0432\\u0435\\u0440\\u0448\\u0438\\u043b\\u0438 \\u043d\\u0430\\u0441\\u0442\\u0440\\u043e\\u0439\\u043a\\u0443 VPN. \\u041f\\u0440\\u043e\\u0434\\u043e\\u043b\\u0436\\u0438\\u043c?",\n',
        f'{indent}            reply_markup=wb.as_markup(),\n',
        f'{indent}            parse_mode="HTML"\n',
        f'{indent}        )\n',
        f'{indent}        return\n',
        f'{indent}await show_main_menu(message)\n',
    ]

    lines[target_idx:target_idx + 1] = new_lines

    with open(HANDLERS, 'w') as f:
        f.writelines(lines)

    print(f"Replaced 1 line with {len(new_lines)} lines")

    with open(HANDLERS) as f:
        content = f.read()

    import ast
    try:
        ast.parse(content)
        print("syntax OK")
    except SyntaxError as e:
        print(f"SYNTAX ERROR: {e}")

    print(f"'wizard_complete' checks: {content.count('wizard_complete')}")
    print(f"'С возвращением' present: {chr(1057) + chr(32) + chr(1074) + chr(1086) + chr(1079) + chr(1074) + chr(1088) + chr(1072) + chr(1097) + chr(1077) + chr(1085) + chr(1080) + chr(1077) + chr(1084) in content}")
