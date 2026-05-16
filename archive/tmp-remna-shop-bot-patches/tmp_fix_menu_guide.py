KEYBOARDS = "/opt/remna-shop/src/shop_bot/bot/keyboards.py"

with open(KEYBOARDS) as f:
    content = f.read()

# Add "Как настроить" button after the "Продлить" else branch, before "Мой аккаунт"
OLD = '''    else:
        builder.button(text="\\U0001f4b3 \\u041f\\u0440\\u043e\\u0434\\u043b\\u0438\\u0442\\u044c \\u043f\\u043e\\u0434\\u043f\\u0438\\u0441\\u043a\\u0443", callback_data="buy_new_key")
    builder.button(text="\\U0001f464 \\u041c\\u043e\\u0439 \\u0430\\u043a\\u043a\\u0430\\u0443\\u043d\\u0442", callback_data="my_account")'''

NEW = '''    else:
        builder.button(text="\\U0001f4b3 \\u041f\\u0440\\u043e\\u0434\\u043b\\u0438\\u0442\\u044c \\u043f\\u043e\\u0434\\u043f\\u0438\\u0441\\u043a\\u0443", callback_data="buy_new_key")
        builder.button(text="\\U0001f4d6 \\u041a\\u0430\\u043a \\u043d\\u0430\\u0441\\u0442\\u0440\\u043e\\u0438\\u0442\\u044c", callback_data="show_setup_guide")
    builder.button(text="\\U0001f464 \\u041c\\u043e\\u0439 \\u0430\\u043a\\u043a\\u0430\\u0443\\u043d\\u0442", callback_data="my_account")'''

count = content.count(OLD)
print(f"Old block found: {count}")

if count == 0:
    # Unicode might be stored differently, try raw approach
    print("Trying raw search...")
    # Find the exact lines
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'Продлить' in line or '\\u041f\\u0440\\u043e\\u0434\\u043b\\u0438\\u0442\\u044c' in line:
            print(f"  Line {i+1}: {line.rstrip()}")
