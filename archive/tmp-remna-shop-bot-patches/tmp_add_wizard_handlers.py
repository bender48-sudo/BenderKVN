"""Add wizard handlers to the end of handlers.py"""

HANDLERS = "/opt/remna-shop/src/shop_bot/bot/handlers.py"

WIZARD_CODE = '''

# ==================== Wizard onboarding ====================

WIZARD_TEXTS = {
    "step_1": (
        "\\U0001f4f1 <b>\\u0428\\u0430\\u0433 1 \\u0438\\u0437 4 \\u2014 \\u0421\\u043a\\u0430\\u0447\\u0430\\u0439 \\u043f\\u0440\\u0438\\u043b\\u043e\\u0436\\u0435\\u043d\\u0438\\u0435</b>\\n\\n"
        "\\u0414\\u043b\\u044f \\u043f\\u043e\\u0434\\u043a\\u043b\\u044e\\u0447\\u0435\\u043d\\u0438\\u044f \\u043d\\u0443\\u0436\\u043d\\u043e \\u043f\\u0440\\u0438\\u043b\\u043e\\u0436\\u0435\\u043d\\u0438\\u0435 <b>Happ</b>.\\n"
        "\\u042d\\u0442\\u043e \\u0431\\u0435\\u0441\\u043f\\u043b\\u0430\\u0442\\u043d\\u044b\\u0439 VPN-\\u043a\\u043b\\u0438\\u0435\\u043d\\u0442.\\n\\n"
        "\\u0421\\u043a\\u0430\\u0447\\u0430\\u0439 \\u0434\\u043b\\u044f \\u0441\\u0432\\u043e\\u0435\\u0433\\u043e \\u0443\\u0441\\u0442\\u0440\\u043e\\u0439\\u0441\\u0442\\u0432\\u0430 \\U0001f447\\n"
        "\\u0418\\u043b\\u0438 \\u043d\\u0430\\u0436\\u043c\\u0438 \\u00ab\\u0423\\u0436\\u0435 \\u0441\\u043a\\u0430\\u0447\\u0430\\u043d\\u043e\\u00bb \\u0435\\u0441\\u043b\\u0438 Happ \\u0443\\u0436\\u0435 \\u0443\\u0441\\u0442\\u0430\\u043d\\u043e\\u0432\\u043b\\u0435\\u043d."
    ),
'''

# Too complex with unicode escapes. Let me write it properly.

with open(HANDLERS) as f:
    content = f.read()

wizard_block = '''

# ==================== Wizard onboarding ====================

WIZARD_TEXTS = {
    "step_1": (
        "\U0001f4f1 <b>\u0428\u0430\u0433 1 \u0438\u0437 4 \u2014 \u0421\u043a\u0430\u0447\u0430\u0439 \u043f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u0435</b>\\n\\n"
        "\u0414\u043b\u044f \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u044f \u043d\u0443\u0436\u043d\u043e \u043f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u0435 <b>Happ</b>.\\n"
        "\u042d\u0442\u043e \u0431\u0435\u0441\u043f\u043b\u0430\u0442\u043d\u044b\u0439 VPN-\u043a\u043b\u0438\u0435\u043d\u0442.\\n\\n"
        "\u0421\u043a\u0430\u0447\u0430\u0439 \u0434\u043b\u044f \u0441\u0432\u043e\u0435\u0433\u043e \u0443\u0441\u0442\u0440\u043e\u0439\u0441\u0442\u0432\u0430 \U0001f447\\n"
        "\u0418\u043b\u0438 \u043d\u0430\u0436\u043c\u0438 \u00ab\u0423\u0436\u0435 \u0441\u043a\u0430\u0447\u0430\u043d\u043e\u00bb \u0435\u0441\u043b\u0438 Happ \u0443\u0436\u0435 \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d."
    ),
    "step_2": (
        "\U0001f4cb <b>\u0428\u0430\u0433 2 \u0438\u0437 4 \u2014 \u0421\u043a\u043e\u043f\u0438\u0440\u0443\u0439 \u0441\u0441\u044b\u043b\u043a\u0443</b>\\n\\n"
        "\u042d\u0442\u043e \u0442\u0432\u043e\u0439 \u043f\u0435\u0440\u0441\u043e\u043d\u0430\u043b\u044c\u043d\u044b\u0439 \u043a\u043b\u044e\u0447 BenderVPN.\\n"
        "\u041d\u0430\u0436\u043c\u0438 \u043a\u043d\u043e\u043f\u043a\u0443 \u043d\u0438\u0436\u0435 \u2014 \u0441\u0441\u044b\u043b\u043a\u0430 \u0441\u043a\u043e\u043f\u0438\u0440\u0443\u0435\u0442\u0441\u044f.\\n\\n"
        "\u0422\u0432\u043e\u044f \u0441\u0441\u044b\u043b\u043a\u0430:\\n"
        "<code>{sub_url}</code>"
    ),
    "step_3": (
        "\U0001f4f2 <b>\u0428\u0430\u0433 3 \u0438\u0437 4 \u2014 \u0414\u043e\u0431\u0430\u0432\u044c \u043f\u043e\u0434\u043f\u0438\u0441\u043a\u0443 \u0432 Happ</b>\\n\\n"
        "1. \u041e\u0442\u043a\u0440\u043e\u0439 \u043f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u0435 Happ\\n"
        "2. \u041d\u0430\u0436\u043c\u0438 <b>+</b> \u0432 \u043f\u0440\u0430\u0432\u043e\u043c \u0432\u0435\u0440\u0445\u043d\u0435\u043c \u0443\u0433\u043b\u0443\\n"
        "3. \u0412\u044b\u0431\u0435\u0440\u0438 <b>\u00ab\u0418\u0437 \u0431\u0443\u0444\u0435\u0440\u0430 \u043e\u0431\u043c\u0435\u043d\u0430\u00bb</b>\\n\\n"
        "\u041f\u043e\u0434\u043f\u0438\u0441\u043a\u0430 \u0434\u043e\u0431\u0430\u0432\u0438\u0442\u0441\u044f \u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0438."
    ),
    "step_4": (
        "\u26a1\ufe0f <b>\u0428\u0430\u0433 4 \u0438\u0437 4 \u2014 \u041f\u043e\u0434\u043a\u043b\u044e\u0447\u0430\u0439\u0441\u044f</b>\\n\\n"
        "\u041d\u0430\u0436\u043c\u0438 \u0431\u043e\u043b\u044c\u0448\u0443\u044e \u043a\u043d\u043e\u043f\u043a\u0443 <b>\u00ab\u041f\u043e\u0434\u043a\u043b\u044e\u0447\u0438\u0442\u044c\u00bb</b> \u0432 Happ.\\n\\n"
        "\u041b\u0443\u0447\u0448\u0438\u0439 \u0441\u0435\u0440\u0432\u0435\u0440 \u0432\u044b\u0431\u0435\u0440\u0435\u0442\u0441\u044f \u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0438.\\n"
        "\u041a\u043e\u0433\u0434\u0430 \u0443\u0432\u0438\u0434\u0438\u0448\u044c \u2705 \u2014 \u0432\u0441\u0451 \u0440\u0430\u0431\u043e\u0442\u0430\u0435\u0442!"
    ),
    "done": (
        "\U0001f389 <b>\u0413\u043e\u0442\u043e\u0432\u043e! VPN \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0451\u043d.</b>\\n\\n"
        "\u0422\u0435\u043f\u0435\u0440\u044c \u0442\u0432\u043e\u0439 \u0438\u043d\u0442\u0435\u0440\u043d\u0435\u0442 \u0437\u0430\u0449\u0438\u0449\u0451\u043d \u0438 \u043d\u0435\u0432\u0438\u0434\u0438\u043c.\\n\\n"
        "\u0412 \u043b\u044e\u0431\u043e\u0439 \u043c\u043e\u043c\u0435\u043d\u0442:\\n"
        "\u2014 \u043f\u0440\u043e\u0432\u0435\u0440\u0438\u0442\u044c \u0441\u0442\u0430\u0442\u0443\u0441 \u2192 \u00ab\u041c\u043e\u0439 \u0430\u043a\u043a\u0430\u0443\u043d\u0442\u00bb\\n"
        "\u2014 \u043f\u0440\u0438\u0433\u043b\u0430\u0441\u0438\u0442\u044c \u0434\u0440\u0443\u0433\u0430 \u2192 \u00ab\u041c\u043e\u0439 \u0430\u043a\u043a\u0430\u0443\u043d\u0442\u00bb \u2192 \u00ab\u041f\u0440\u0438\u0433\u043b\u0430\u0441\u0438\u0442\u044c\u00bb\\n"
        "\u2014 \u043d\u0443\u0436\u043d\u0430 \u043f\u043e\u043c\u043e\u0449\u044c \u2192 \u00ab\u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c \u043d\u0430\u043c\u00bb"
    ),
}


def _get_wizard_sub_url(user_id):
    """Get stored sub_url from wizard state in user_actions."""
    import sqlite3
    try:
        conn = sqlite3.connect("/app/data/shop_bot.db")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT meta FROM user_actions WHERE user_id=? AND action='wizard_sub_url' ORDER BY id DESC LIMIT 1",
            (user_id,)
        )
        row = cur.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None


def _wizard_step2_text(user_id):
    """Build step 2 text with sub_url."""
    sub_url = _get_wizard_sub_url(user_id)
    return WIZARD_TEXTS["step_2"].replace("{sub_url}", sub_url or "")


@user_router.callback_query(F.data == "wizard_step_2")
async def wizard_step_2_handler(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    text = _wizard_step2_text(user_id)
    await callback.message.edit_text(text, reply_markup=keyboards.create_wizard_step2_keyboard(), parse_mode="HTML")
    log_action(user_id, "wizard_step_2", "")


@user_router.callback_query(F.data == "wizard_step_3")
async def wizard_step_3_handler(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(WIZARD_TEXTS["step_3"], reply_markup=keyboards.create_wizard_step3_keyboard(), parse_mode="HTML")
    log_action(callback.from_user.id, "wizard_step_3", "")


@user_router.callback_query(F.data == "wizard_step_4")
async def wizard_step_4_handler(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(WIZARD_TEXTS["step_4"], reply_markup=keyboards.create_wizard_step4_keyboard(), parse_mode="HTML")
    log_action(callback.from_user.id, "wizard_step_4", "")


@user_router.callback_query(F.data == "wizard_step_5")
async def wizard_done_handler(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(WIZARD_TEXTS["done"], reply_markup=keyboards.create_wizard_done_keyboard(), parse_mode="HTML")
    log_action(callback.from_user.id, "wizard_complete", "")


# Back buttons
@user_router.callback_query(F.data == "wizard_step_1_back")
async def wizard_back_to_1(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(WIZARD_TEXTS["step_1"], reply_markup=keyboards.create_wizard_step1_keyboard(), parse_mode="HTML")


@user_router.callback_query(F.data == "wizard_step_2_back")
async def wizard_back_to_2(callback: types.CallbackQuery):
    await callback.answer()
    text = _wizard_step2_text(callback.from_user.id)
    await callback.message.edit_text(text, reply_markup=keyboards.create_wizard_step2_keyboard(), parse_mode="HTML")


@user_router.callback_query(F.data == "wizard_step_3_back")
async def wizard_back_to_3(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(WIZARD_TEXTS["step_3"], reply_markup=keyboards.create_wizard_step3_keyboard(), parse_mode="HTML")


# Menu entry: setup guide
@user_router.callback_query(F.data == "show_setup_guide")
async def show_setup_guide_handler(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    sub_url = _get_wizard_sub_url(user_id)
    if not sub_url:
        user_keys = get_user_keys(user_id)
        if user_keys:
            # Try to build sub_url from key email
            async with aiohttp.ClientSession() as session:
                remote = await remnawave_api.get_user_by_telegram_id(session, str(user_id))
                if remote:
                    sub_url = remote.get("subscriptionUrl")
                    if sub_url:
                        log_action(user_id, "wizard_sub_url", sub_url)
    if sub_url:
        await callback.message.edit_text(WIZARD_TEXTS["step_1"], reply_markup=keyboards.create_wizard_step1_keyboard(), parse_mode="HTML")
        log_action(user_id, "wizard_step_1", "from_menu")
    else:
        await callback.message.edit_text(
            "\u0423 \u0432\u0430\u0441 \u043f\u043e\u043a\u0430 \u043d\u0435\u0442 \u0430\u043a\u0442\u0438\u0432\u043d\u043e\u0439 \u043f\u043e\u0434\u043f\u0438\u0441\u043a\u0438.\\n\u0421\u043d\u0430\u0447\u0430\u043b\u0430 \u0430\u043a\u0442\u0438\u0432\u0438\u0440\u0443\u0439\u0442\u0435 \u043f\u0440\u043e\u0431\u043d\u044b\u0439 \u043f\u0435\u0440\u0438\u043e\u0434 \u0438\u043b\u0438 \u043a\u0443\u043f\u0438\u0442\u0435 \u043f\u043e\u0434\u043f\u0438\u0441\u043a\u0443.",
            reply_markup=keyboards.create_back_to_menu_keyboard(),
            parse_mode="HTML"
        )
'''

with open(HANDLERS) as f:
    content = f.read()

content += wizard_block

with open(HANDLERS, 'w') as f:
    f.write(content)

# Verify
import ast
try:
    ast.parse(content)
    print("syntax OK")
except SyntaxError as e:
    print(f"SYNTAX ERROR: {e}")

# Count new handlers
print(f"wizard handlers: {content.count('@user_router.callback_query(F.data == \"wizard_')}")
print(f"wizard back handlers: {content.count('wizard_back_to_')}")
print(f"show_setup_guide: {content.count('show_setup_guide')}")
print(f"WIZARD_TEXTS keys: {content.count('step_1'):}")
print(f"_get_wizard_sub_url defined: {'def _get_wizard_sub_url' in content}")
