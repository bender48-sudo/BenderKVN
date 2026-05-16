

# ==================== Wizard onboarding ====================

WIZARD_TEXTS = {
    "step_1": (
        "\U0001f4f1 <b>Шаг 1 из 4 — Скачай приложение</b>\n\n"
        "Для подключения нужно приложение <b>Happ</b>.\n"
        "Это бесплатный VPN-клиент.\n\n"
        "Скачай для своего устройства \U0001f447\n"
        "Или нажми «Уже скачано» если Happ уже установлен."
    ),
    "step_2": (
        "\U0001f4cb <b>Шаг 2 из 4 — Скопируй ссылку</b>\n\n"
        "Это твой персональный ключ BenderVPN.\n"
        "Нажми кнопку ниже — ссылка скопируется.\n\n"
        "Твоя ссылка:\n"
        "<code>{sub_url}</code>"
    ),
    "step_3": (
        "\U0001f4f2 <b>Шаг 3 из 4 — Добавь подписку в Happ</b>\n\n"
        "1. Открой приложение Happ\n"
        "2. Нажми <b>+</b> в правом верхнем углу\n"
        "3. Выбери <b>«Из буфера обмена»</b>\n\n"
        "Подписка добавится автоматически."
    ),
    "step_4": (
        "\u26a1\ufe0f <b>Шаг 4 из 4 — Подключайся</b>\n\n"
        "Нажми большую кнопку <b>«Подключить»</b> в Happ.\n\n"
        "Лучший сервер выберется автоматически.\n"
        "Когда увидишь \u2705 — всё работает!"
    ),
    "done": (
        "\U0001f389 <b>Готово! VPN подключён.</b>\n\n"
        "Теперь твой интернет защищён и невидим.\n\n"
        "В любой момент:\n"
        "— проверить статус \u2192 «Мой аккаунт»\n"
        "— пригласить друга \u2192 «Мой аккаунт» \u2192 «Пригласить»\n"
        "— нужна помощь \u2192 «Написать нам»"
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
            "У вас пока нет активной подписки.\nСначала активируйте пробный период или купите подписку.",
            reply_markup=keyboards.create_back_to_menu_keyboard(),
            parse_mode="HTML"
        )
