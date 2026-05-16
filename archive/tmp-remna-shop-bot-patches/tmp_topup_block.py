

# ==================== Topup / balance handlers ====================

@user_router.callback_query(F.data == "show_topup")
async def show_topup_handler(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    balance = get_balance(user_id)
    days_left = int(balance / DAILY_RATE) if balance > 0 else 0

    text = (
        f"\U0001f4b0 <b>Ваш баланс: {balance:.0f} \u20bd</b>\n"
        f"\U0001f4c5 Хватит на: {days_left} дн.\n\n"
        f"Стоимость: {DAILY_RATE:.2f} \u20bd/день\n\n"
        f"Выберите сумму пополнения:"
    )
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.create_topup_keyboard(),
        parse_mode="HTML"
    )


@user_router.callback_query(F.data == "topup_custom")
async def topup_custom_handler(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        CUSTOM_AMOUNT_UNAVAILABLE,
        reply_markup=keyboards.create_topup_keyboard(),
        parse_mode="HTML"
    )


@user_router.callback_query(F.data.in_({"topup_200", "topup_500", "topup_1000", "topup_2000"}))
async def topup_select_handler(callback: types.CallbackQuery):
    await callback.answer()
    topup_id = callback.data

    if topup_id not in TOPUP_PRESETS:
        return

    name, price_str, amount = TOPUP_PRESETS[topup_id]
    days = int(amount / DAILY_RATE)

    text = (
        f"\U0001f4b0 Пополнение на <b>{amount:.0f} \u20bd</b>\n"
        f"\U0001f4c5 Хватит на ~{days} дней\n\n"
        f"Выберите способ оплаты:"
    )
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.create_topup_payment_keyboard(amount, topup_id),
        parse_mode="HTML"
    )


@user_router.callback_query(F.data.startswith("pay_stars_topup_"))
async def pay_stars_topup_handler(callback: types.CallbackQuery, bot: Bot):
    await callback.answer("Создаю счёт...")
    topup_id = callback.data.replace("pay_stars_topup_", "")

    if topup_id not in TOPUP_PRESETS:
        await callback.message.edit_text("Ошибка: пресет не найден.")
        return

    name, price_str, amount_rub = TOPUP_PRESETS[topup_id]
    user_id = callback.from_user.id
    stars_rate = float(os.getenv("STARS_RATE", "1.5"))
    stars_amount = max(1, int(float(price_str) * stars_rate))

    payload_data = json.dumps({
        "uid": user_id,
        "t": "topup",
        "a": amount_rub,
    }, separators=(',', ':'))

    try:
        from aiogram.types import LabeledPrice
        link = await bot.create_invoice_link(
            title=f"Пополнение {amount_rub:.0f} \u20bd",
            description=f"Пополнение баланса BenderVPN на {amount_rub:.0f} \u20bd",
            payload=payload_data,
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label=f"{amount_rub:.0f} RUB", amount=stars_amount)]
        )

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"\U0001f4ab Оплатить {stars_amount} Stars", url=link)]
        ])

        await callback.message.edit_text(
            f"\u2b50 Оплата через Telegram Stars\n\n"
            f"Сумма: {stars_amount} Stars (~{amount_rub:.0f} \u20bd)\n\n"
            f"Нажмите кнопку ниже:",
            reply_markup=kb,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Failed to create Stars topup invoice: {e}", exc_info=True)
        await callback.message.edit_text("\u274c Ошибка создания счёта. Попробуйте позже.")
