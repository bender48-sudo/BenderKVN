KEYBOARDS = "/opt/remna-shop/src/shop_bot/bot/keyboards.py"

with open(KEYBOARDS) as f:
    lines = f.readlines()

# Find the line with "Продлить подписку" in create_main_menu_keyboard
insert_after = None
for i, line in enumerate(lines):
    if 'callback_data="buy_new_key"' in line and i > 10 and i < 30:
        # This is in create_main_menu_keyboard (the else: Продлить branch)
        # Check it's the right one (in the else block)
        if 'else' in lines[i-1] or lines[i].strip().startswith('builder.button'):
            insert_after = i
            print(f"Found 'Продлить' line at {i+1}: {line.rstrip()}")

if insert_after is not None:
    # Check if guide button already exists
    already = any('show_setup_guide' in l for l in lines[insert_after:insert_after+3])
    if already:
        print("Guide button already present, skipping")
    else:
        new_line = '        builder.button(text="\U0001f4d6 \u041a\u0430\u043a \u043d\u0430\u0441\u0442\u0440\u043e\u0438\u0442\u044c", callback_data="show_setup_guide")\n'
        lines.insert(insert_after + 1, new_line)
        print(f"Inserted guide button after line {insert_after + 1}")

        with open(KEYBOARDS, 'w') as f:
            f.writelines(lines)

        import ast
        with open(KEYBOARDS) as f:
            content = f.read()
        try:
            ast.parse(content)
            print("syntax OK")
        except SyntaxError as e:
            print(f"SYNTAX ERROR: {e}")

        print(f"show_setup_guide count: {content.count('show_setup_guide')}")
else:
    print("ERROR: Could not find insertion point")
