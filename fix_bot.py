# -*- coding: utf-8 -*-
import sys

filepath = '/opt/remna-shop/src/shop_bot/bot/handlers.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

with open(filepath + '.bak', 'w', encoding='utf-8') as f:
    f.write(content)

lines = content.split('\n')
new_lines = []
fixes = 0
i = 0

while i < len(lines):
    line = lines[i]

    # FIX 1: Trial success message block
    if 'Ваша подписка BenderVPN активна на 30 дней' in line:
        indent = '        '
        new_lines.append(indent + 'message_text = f"\\u2705 Готово! Вот твоя личная ссылка BenderVPN:\\n\\n"')
        new_lines.append(indent + 'message_text += f"`{sub_url or uri}`\\n\\n"')
        new_lines.append(indent + 'message_text += "\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\n"')
        new_lines.append(indent + 'message_text += "\\U0001f4f1 Как установить:\\n\\n"')
        new_lines.append(indent + 'message_text += "1\\ufe0f\\u20e3 Скачай приложение Happ (кнопка ниже)\\n\\n"')
        new_lines.append(indent + 'message_text += "2\\ufe0f\\u20e3 Открой Happ\\n\\n"')
        new_lines.append(indent + 'message_text += "3\\ufe0f\\u20e3 Нажми + в правом верхнем углу\\n\\n"')
        new_lines.append(indent + "message_text += '4\\ufe0f\\u20e3 Выбери \"Из буфера обмена\"\\n\\n'")
        new_lines.append(indent + 'message_text += "5\\ufe0f\\u20e3 Нажми кнопку питания \\u2014 готово! \\U0001f389\\n"')
        new_lines.append(indent + 'message_text += "\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\u2501\\n"')
        new_lines.append(indent + 'message_text += "Что-то не так? Напиши нам \\U0001f447"')
        # Skip old block until великолепны
        while i < len(lines) and 'великолепны' not in lines[i]:
            i += 1
        i += 1
        fixes += 1
        print("FIX 1: Trial message updated")
        continue

    # FIX 2: Instruction handler
    if 'instruction_text = (' in line and i + 1 < len(lines) and 'Как подключиться' in lines[i+1]:
        indent = '    '
        new_lines.append(indent + 'instruction_text = (')
        new_lines.append(indent + '    "<b>\\U0001f4f1 Как установить:</b>\\n\\n"')
        new_lines.append(indent + '    "1\\ufe0f\\u20e3 Скачай приложение Happ (кнопка ниже)\\n\\n"')
        new_lines.append(indent + '    "2\\ufe0f\\u20e3 Открой Happ\\n\\n"')
        new_lines.append(indent + '    "3\\ufe0f\\u20e3 Нажми + в правом верхнем углу\\n\\n"')
        new_lines.append(indent + "    '4\\ufe0f\\u20e3 Выбери \"Из буфера обмена\"\\n\\n'")
        new_lines.append(indent + '    "5\\ufe0f\\u20e3 Нажми кнопку питания \\u2014 готово! \\U0001f389\\n\\n"')
        new_lines.append(indent + '    "Что-то не так? Напиши нам \\U0001f447"')
        new_lines.append(indent + ')')
        # Skip old instruction_text block until closing paren after "ниже"
        while i < len(lines) and not (lines[i].strip() == ')' and i > 0 and 'ниже' in lines[i-1]):
            i += 1
        i += 1
        fixes += 1
        print("FIX 2: Instruction handler updated")
        continue

    # FIX 3: Referral URL handler
    if 'Ваша реферальная ссылка' in line and 'await callback.message.answer' in line:
        indent = '    '
        new_lines.append(indent + 'await callback.message.answer(')
        new_lines.append(indent + '    f"\\U0001f465 Твоя реферальная ссылка \\u2014 нажми чтобы скопировать:\\n\\n"')
        new_lines.append(indent + '    f"`{ref_url}`",')
        new_lines.append(indent + '    parse_mode="Markdown"')
        new_lines.append(indent + ')')
        i += 1
        if i < len(lines) and 'await callback.message.answer(ref_url)' in lines[i]:
            i += 1
        fixes += 1
        print("FIX 3: Referral URL formatted as monospace")
        continue

    # FIX 4: Subscription URL handler
    if 'Ваша ссылка подписки' in line and 'await callback.message.answer' in line and 'copy_sub' not in line:
        indent = '                '
        new_lines.append(indent + 'await callback.message.answer(')
        new_lines.append(indent + '    f"\\U0001f4cb Твоя ссылка подписки \\u2014 нажми чтобы скопировать:\\n\\n"')
        new_lines.append(indent + '    f"`{sub_url}`",')
        new_lines.append(indent + '    parse_mode="Markdown"')
        new_lines.append(indent + ')')
        i += 1
        if i < len(lines) and 'await callback.message.answer(sub_url)' in lines[i]:
            i += 1
        fixes += 1
        print("FIX 4: Subscription URL formatted as monospace")
        continue

    new_lines.append(line)
    i += 1

content = '\n'.join(new_lines)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\nTotal fixes applied: {fixes}")
if fixes < 4:
    print("WARNING: Not all fixes applied!")
