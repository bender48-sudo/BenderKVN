#!/usr/bin/env python3
"""Fix scheduler.py notification text: replace old expiry messages with trial-friendly text + buy button."""

SCHEDULER_PATH = "/opt/remna-shop/src/shop_bot/data_manager/scheduler.py"

with open(SCHEDULER_PATH, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
i = 0
skip_until_notifications_sent = False

while i < len(lines):
    line = lines[i]

    # Detect the start of the block we want to replace
    if "if mark > 0:" in line and "days_left" not in line and not skip_until_notifications_sent:
        indent = "                                    "
        ind2 = indent + "    "
        ind3 = ind2 + "    "

        # -- mark > 0 branch --
        new_lines.append(indent + "if mark > 0:\n")
        new_lines.append(ind2 + "from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton\n")
        new_lines.append(ind2 + "kb = InlineKeyboardMarkup(inline_keyboard=[\n")
        new_lines.append(ind3 + "[InlineKeyboardButton(text=\"\U0001f4b3 \u041e\u0444\u043e\u0440\u043c\u0438\u0442\u044c \u043f\u043e\u0434\u043f\u0438\u0441\u043a\u0443\", callback_data=\"choose_plan\")]\n")
        new_lines.append(ind2 + "])\n")
        new_lines.append(ind2 + "await bot.send_message(\n")
        new_lines.append(ind3 + "user_id,\n")
        # f-string with explicit \n inside
        msg1 = (
            'f"\u23f0 \u0412\u0430\u0448 \u0431\u0435\u0441\u043f\u043b\u0430\u0442\u043d\u044b\u0439 '
            '\u043f\u0435\u0440\u0438\u043e\u0434 \u0437\u0430\u043a\u0430\u043d\u0447\u0438\u0432\u0430\u0435\u0442\u0441\u044f '
            '\u0447\u0435\u0440\u0435\u0437 {mark} \u0434\u043d.!'
            '\\n\\n'
            '\u041f\u043e\u043d\u0440\u0430\u0432\u0438\u043b\u0441\u044f BenderVPN? '
            '\u041f\u0440\u043e\u0434\u043e\u043b\u0436\u0438\u0442\u0435 \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u044c\u0441\u044f \u2014'
            '\\n'
            '\u043e\u0444\u043e\u0440\u043c\u0438\u0442\u0435 \u043f\u043e\u0434\u043f\u0438\u0441\u043a\u0443 '
            '\u043f\u0440\u044f\u043c\u043e \u0437\u0434\u0435\u0441\u044c \U0001f447"'
        )
        new_lines.append(ind3 + msg1 + ",\n")
        new_lines.append(ind3 + "reply_markup=kb\n")
        new_lines.append(ind2 + ")\n")
        new_lines.append(ind2 + "bot_logger.notification(user_id, f\"EXPIRY_{mark}D\", True)\n")

        # -- else (mark == 0, expired) --
        new_lines.append(indent + "else:\n")
        new_lines.append(ind2 + "from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton\n")
        new_lines.append(ind2 + "kb = InlineKeyboardMarkup(inline_keyboard=[\n")
        new_lines.append(ind3 + "[InlineKeyboardButton(text=\"\U0001f4b3 \u041e\u0444\u043e\u0440\u043c\u0438\u0442\u044c \u043f\u043e\u0434\u043f\u0438\u0441\u043a\u0443\", callback_data=\"choose_plan\")]\n")
        new_lines.append(ind2 + "])\n")
        new_lines.append(ind2 + "await bot.send_message(\n")
        new_lines.append(ind3 + "user_id,\n")
        msg2 = (
            'f"\u2757\ufe0f \u0412\u0430\u0448 \u0431\u0435\u0441\u043f\u043b\u0430\u0442\u043d\u044b\u0439 '
            '\u043f\u0435\u0440\u0438\u043e\u0434 \u0437\u0430\u043a\u043e\u043d\u0447\u0438\u043b\u0441\u044f.'
            '\\n\\n'
            '\u041e\u0444\u043e\u0440\u043c\u0438\u0442\u0435 \u043f\u043e\u0434\u043f\u0438\u0441\u043a\u0443, '
            '\u0447\u0442\u043e\u0431\u044b \u043f\u0440\u043e\u0434\u043e\u043b\u0436\u0438\u0442\u044c '
            '\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u044c\u0441\u044f BenderVPN \U0001f447"'
        )
        new_lines.append(ind3 + msg2 + ",\n")
        new_lines.append(ind3 + "reply_markup=kb\n")
        new_lines.append(ind2 + ")\n")
        new_lines.append(ind2 + "bot_logger.notification(user_id, \"EXPIRED\", True)\n")

        # Skip old lines until "notifications_sent += 1"
        i += 1
        while i < len(lines) and "notifications_sent += 1" not in lines[i]:
            i += 1
        # i now at "notifications_sent += 1", continue to append it normally
        continue
    else:
        new_lines.append(line)
    i += 1

with open(SCHEDULER_PATH, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

# Verify syntax
import ast
with open(SCHEDULER_PATH, "r", encoding="utf-8") as f:
    source = f.read()
try:
    ast.parse(source)
    print("SUCCESS: scheduler.py updated and syntax OK")
except SyntaxError as e:
    print(f"SYNTAX ERROR: {e}")
