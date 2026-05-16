HANDLERS = "/opt/remna-shop/src/shop_bot/bot/handlers.py"

with open(HANDLERS) as f:
    content = f.read()

OLD_BLOCK = '''        # Показываем созданный ключ пользователю
        from .keyboards import create_main_menu_keyboard
        expiry_str = expiry_dt.strftime("%d.%m.%Y %H:%M")
        message_text = f"\\u2705 Готово! Вот твоя личная ссылка BenderVPN:\\n\\n"
        message_text += f"`{sub_url or uri}`\\n\\n"
        message_text += "\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\n"
        message_text += "\\U0001f4f1 Как установить:\\n\\n"
        message_text += "1\\ufe0f\\u20e3 Скачай приложение Happ (кнопка ниже)\\n\\n"
        message_text += "2\\ufe0f\\u20e3 Открой Happ\\n\\n"
        message_text += "3\\ufe0f\\u20e3 Нажми + в правом верхнем углу\\n\\n"
        message_text += \'4\\ufe0f\\u20e3 Выбери "Из буфера обмена"\\n\\n\'
        message_text += "5\\ufe0f\\u20e3 Нажми кнопку питания \\u2014 готово! \\U0001f389\\n"
        message_text += "\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\n"
        message_text += "Что-то не так? Напиши нам \\U0001f447"

        # Получаем данные пользователя для клавиатуры
        user_keys = get_user_keys(user_id)
        user_data = get_user(user_id)
        is_admin = str(user_id) == ADMIN_ID
        auto_renew = user_data.get(\'auto_renew\', False) if user_data else False

        await callback.message.edit_text(
            message_text,
            parse_mode="Markdown",
            reply_markup=create_main_menu_keyboard(user_keys, trial_available=False, is_admin=is_admin, auto_renew=auto_renew)
        )'''

NEW_BLOCK = '''        # Start wizard onboarding
        log_action(user_id, "wizard_sub_url", sub_url or uri)
        await callback.message.edit_text(
            WIZARD_TEXTS["step_1"],
            reply_markup=keyboards.create_wizard_step1_keyboard(),
            parse_mode="HTML"
        )
        log_action(user_id, "wizard_step_1", "from_trial")'''

count = content.count(OLD_BLOCK)
print(f"Old block found: {count} times")

if count == 1:
    content = content.replace(OLD_BLOCK, NEW_BLOCK)
    with open(HANDLERS, 'w') as f:
        f.write(content)
    print("Replaced OK")
    print(f"'Как установить' remaining: {content.count('Как установить')}")
    print(f"'wizard_step_1' in trial area: {'from_trial' in content}")
elif count == 0:
    print("ERROR: old block not found. Trying line-by-line search...")
    # Show context around "Показываем"
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'Показываем созданный' in line:
            print(f"Found at line {i+1}: {line.rstrip()}")
            for j in range(i, min(i+5, len(lines))):
                print(f"  {j+1}: {lines[j].rstrip()}")
