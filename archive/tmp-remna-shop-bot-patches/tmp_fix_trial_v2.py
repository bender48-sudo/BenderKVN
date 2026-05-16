HANDLERS = "/opt/remna-shop/src/shop_bot/bot/handlers.py"

with open(HANDLERS) as f:
    lines = f.readlines()

# Find the block to replace: from "# Показываем созданный" to the closing ")"
# of the edit_text call with create_main_menu_keyboard
start_idx = None
end_idx = None

for i, line in enumerate(lines):
    if '# Показываем созданный ключ пользователю' in line and start_idx is None:
        start_idx = i
    if start_idx is not None and 'create_main_menu_keyboard' in line and 'reply_markup=' in line:
        # Find the closing )
        for j in range(i, min(i + 5, len(lines))):
            if lines[j].strip() == ')':
                end_idx = j + 1
                break
        if end_idx is None:
            # The ) might be on the same line
            end_idx = i + 1
        break

print(f"Start line: {start_idx + 1 if start_idx else 'NOT FOUND'}")
print(f"End line: {end_idx if end_idx else 'NOT FOUND'}")

if start_idx is not None and end_idx is not None:
    print(f"Replacing lines {start_idx + 1} to {end_idx}")
    print(f"Old block ({end_idx - start_idx} lines):")
    for i in range(start_idx, end_idx):
        print(f"  {i+1}: {lines[i].rstrip()}")

    new_block = [
        '        # Start wizard onboarding\n',
        '        log_action(user_id, "wizard_sub_url", sub_url or uri)\n',
        '        await callback.message.edit_text(\n',
        '            WIZARD_TEXTS["step_1"],\n',
        '            reply_markup=keyboards.create_wizard_step1_keyboard(),\n',
        '            parse_mode="HTML"\n',
        '        )\n',
        '        log_action(user_id, "wizard_step_1", "from_trial")\n',
    ]

    lines[start_idx:end_idx] = new_block

    with open(HANDLERS, 'w') as f:
        f.writelines(lines)

    print(f"\nReplaced with {len(new_block)} lines")

    # Verify
    with open(HANDLERS) as f:
        content = f.read()

    import ast
    try:
        ast.parse(content)
        print("syntax OK")
    except SyntaxError as e:
        print(f"SYNTAX ERROR: {e}")

    print(f"'Как установить' remaining: {content.count('Как установить')}")
    print(f"'from_trial' present: {'from_trial' in content}")
else:
    print("ERROR: Could not find block boundaries")
