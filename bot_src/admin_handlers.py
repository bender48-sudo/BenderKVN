import asyncio
import logging
import os
from html import escape
from urllib.parse import urlparse

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from shop_bot.admin_auth import is_admin_telegram
from shop_bot.data_manager.database import get_user, get_user_keys, update_setting, get_setting
import re

from aiogram.exceptions import TelegramBadRequest

from shop_bot import admin_flow_test, admin_flow_guide
from . import keyboards

_FLOW_STEP_RE = re.compile(r"^admin_flow_g_(nb|ex|web)_(\d+)$")
_FLOW_TOTALS = {"nb": 4, "ex": 3, "web": 4}


def _parse_flow_step(data: str | None) -> tuple[str, int] | None:
    if not data:
        return None
    m = _FLOW_STEP_RE.match(data)
    if not m:
        return None
    return m.group(1), int(m.group(2))

logger = logging.getLogger(__name__)
admin_router = Router()


def _is_admin(user_id: int | None) -> bool:
    return is_admin_telegram(user_id)

class AdminEdit(StatesGroup):
    waiting_for_about_text = State()
    waiting_for_terms_url = State()
    waiting_for_privacy_url = State()
    waiting_for_support_user = State()
    waiting_for_support_text = State()

def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

@admin_router.message(Command("admin"))
async def admin_panel_handler(message: types.Message):
    if not is_admin_telegram(message.from_user.id):
        return
    await message.answer("Добро пожаловать в админ-панель!", reply_markup=keyboards.create_admin_keyboard())

@admin_router.callback_query(F.data.startswith("admin_edit_"))
async def start_editing_handler(callback: types.CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    action = callback.data.removeprefix("admin_edit_") 
    
    logger.info(f"Received callback to edit '{action}'")

    prompts = {
        "about": ("Пришлите новый текст для раздела 'О проекте'.", AdminEdit.waiting_for_about_text),
        "terms": ("Пришлите новую ссылку на Условия использования.", AdminEdit.waiting_for_terms_url),
        "privacy": ("Пришлите новую ссылку на Политику конфиденциальности.", AdminEdit.waiting_for_privacy_url),
        "support_user": ("Пришлите новую ссылку на поддержку.", AdminEdit.waiting_for_support_user),
        "support_text": ("Пришлите новый текст для раздела 'Поддержка'.", AdminEdit.waiting_for_support_text),
    }

    if action in prompts:
        prompt_text, new_state = prompts[action]
        await callback.message.edit_text(prompt_text, reply_markup=keyboards.create_admin_cancel_keyboard())
        await state.set_state(new_state)
    else:
        logger.warning(f"Action '{action}' not found in prompts dictionary.")

    await callback.answer()

@admin_router.callback_query(F.data == "admin_cancel_edit")
async def cancel_editing_handler(callback: types.CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    await callback.message.edit_text("Действие отменено. Вы в админ-панели.", reply_markup=keyboards.create_admin_keyboard())
    await callback.answer()

async def process_new_content(message: types.Message, state: FSMContext, db_key: str):
    if not _is_admin(message.from_user.id):
        await state.clear()
        return
    logger.info(f"Updating setting: {db_key} with value: {message.text}")
    try:
        update_setting(db_key, message.text)
        logger.info(f"Setting '{db_key}' updated successfully.")
    except Exception as e:
        logger.error(f"Error updating setting '{db_key}': {e}")
        await message.answer("❌ Произошла ошибка при обновлении данных. Пожалуйста, попробуйте позже.")
        await state.clear()
        return

    await state.clear()
    logger.info("State cleared.")
    try:
        await message.answer("✅ Успешно обновлено!", reply_markup=keyboards.create_admin_keyboard())
        logger.info("Success message sent.")
    except Exception as e:
        logger.error(f"Error sending success message: {e}")

@admin_router.message(AdminEdit.waiting_for_about_text)
async def process_about_text(message: types.Message, state: FSMContext):
    await process_new_content(message, state, "about_text")

@admin_router.message(AdminEdit.waiting_for_terms_url)
async def process_terms_url(message: types.Message, state: FSMContext):
    if is_valid_url(message.text):
        await process_new_content(message, state, "terms_url")
    else:
        await message.answer("❌ **Ошибка:** Это не похоже на валидную ссылку. Она должна начинаться с `http://` или `https://`. Попробуйте еще раз или нажмите 'Отмена'.")

@admin_router.message(AdminEdit.waiting_for_privacy_url)
async def process_privacy_url(message: types.Message, state: FSMContext):
    if is_valid_url(message.text):
        await process_new_content(message, state, "privacy_url")
    else:
        await message.answer("❌ **Ошибка:** Это не похоже на валидную ссылку. Она должна начинаться с `http://` или `https://`. Попробуйте еще раз или нажмите 'Отмена'.")

@admin_router.message(AdminEdit.waiting_for_support_user)
async def process_support_user(message: types.Message, state: FSMContext):
    logger.info(f"process_support_user called with text: {message.text}")
    if is_valid_url(message.text):
        await process_new_content(message, state, "support_user")
    else:
        await message.answer("❌ **Ошибка:** Это не похоже на валидную ссылку. Она должна начинаться с `http://` или `https://`. Попробуйте еще раз или нажмите 'Отмена'.")

@admin_router.message(AdminEdit.waiting_for_support_text)
async def process_support_text(message: types.Message, state: FSMContext):
    logger.info(f"process_support_text called with text: {message.text}")
    await process_new_content(message, state, "support_text")


@admin_router.callback_query(F.data == "admin_flow_test_menu")
async def admin_flow_test_menu(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(
        "🧪 <b>Тест флоу</b>\n\n"
        "<b>🧭 Гиды</b> — шаг 2+ с <b>реальными</b> кнопками бота (прод-сим). "
        "«Далее» / «Назад»; на web — ссылка в браузер.\n\n"
        "<b>🔧 Диагностика</b> — робот проверяет сервер: панель, :8443, /setup, "
        "ваш аккаунт. Это не сценарий для клиента, а тех. отчёт ✅/❌.",
        reply_markup=keyboards.create_admin_flow_test_keyboard(),
    )


@admin_router.callback_query(F.data == "admin_flow_smoke_all")
async def admin_flow_smoke_all(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer("Диагностика…")
    await _edit_guide_message(
        callback,
        "⏳ <b>Диагностика</b>\n\nПанель, URL :8443, /setup/, ваш Telegram… (до 30 с)",
        keyboards.create_admin_flow_test_keyboard(),
    )
    try:
        text = await asyncio.wait_for(
            admin_flow_test.run_all_smokes(callback.from_user.id),
            timeout=45.0,
        )
    except asyncio.TimeoutError:
        logger.warning("admin_flow_smoke_all timeout uid=%s", callback.from_user.id)
        text = (
            "⏱ <b>Диагностика не уложилась в 30 с</b>\n\n"
            "Часто виноват долгий ответ панели Remna. Повторите через минуту "
            "или смотрите <code>docker logs remna-shop-bot</code> на AMS."
        )
    except Exception as exc:
        logger.exception("admin_flow_smoke_all failed")
        text = (
            "❌ <b>Ошибка диагностики</b>\n\n"
            f"<code>{escape(str(exc)[:240])}</code>"
        )
    await _edit_guide_message(
        callback,
        text,
        keyboards.create_admin_flow_test_keyboard(),
    )


@admin_router.callback_query(F.data == "admin_flow_smoke_existing")
async def admin_flow_smoke_existing(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()
    checks = await admin_flow_test.smoke_existing_user(callback.from_user.id)
    infra = await admin_flow_test.smoke_infrastructure()
    text = (
        "🧪 <b>Существующий пользователь (Telegram)</b>\n\n"
        + admin_flow_test.format_section("Инфра", infra)
        + "\n\n"
        + admin_flow_test.format_section("Ваш аккаунт", checks)
    )
    await _edit_guide_message(
        callback,
        text[:3900],
        keyboards.create_admin_flow_test_keyboard(),
    )


@admin_router.callback_query(F.data == "admin_flow_smoke_newbie")
async def admin_flow_smoke_newbie(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()
    infra = await admin_flow_test.smoke_infrastructure()
    newbie = admin_flow_test.smoke_newbie_logic()
    text = (
        "🧪 <b>Новичок в боте</b>\n\n"
        + admin_flow_test.format_section("Инфра", infra)
        + "\n\n"
        + admin_flow_test.format_section("Логика /start", newbie)
    )
    await _edit_guide_message(
        callback,
        text[:3900],
        keyboards.create_admin_flow_test_keyboard(),
    )


@admin_router.callback_query(F.data == "admin_flow_smoke_email")
async def admin_flow_smoke_email(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()
    infra = await admin_flow_test.smoke_infrastructure()
    email = await admin_flow_test.smoke_email_web()
    text = (
        "🧪 <b>Email / web</b>\n\n"
        + admin_flow_test.format_section("Инфра", infra)
        + "\n\n"
        + admin_flow_test.format_section("Web trial", email)
    )
    await _edit_guide_message(
        callback,
        text[:3900],
        keyboards.create_admin_flow_test_keyboard(),
    )


def _merge_menu_with_nav(menu_markup, nav_markup):
    from aiogram.types import InlineKeyboardMarkup

    return InlineKeyboardMarkup(
        inline_keyboard=list(menu_markup.inline_keyboard) + list(nav_markup.inline_keyboard)
    )


async def _edit_guide_message(
    callback: types.CallbackQuery,
    text: str,
    reply_markup,
    disable_web_page_preview: bool = False,
) -> None:
    try:
        await callback.message.edit_text(
            text,
            reply_markup=reply_markup,
            parse_mode="HTML",
            disable_web_page_preview=disable_web_page_preview,
        )
    except TelegramBadRequest as exc:
        logger.warning("admin flow guide edit failed: %s", exc)
        await callback.message.answer(
            text,
            reply_markup=reply_markup,
            parse_mode="HTML",
            disable_web_page_preview=disable_web_page_preview,
        )


async def _render_admin_flow_guide(
    callback: types.CallbackQuery,
    flow: str,
    step: int,
) -> None:
    tid = callback.from_user.id
    total = _FLOW_TOTALS[flow]
    step = max(1, min(step, total))
    extra = admin_flow_guide.nav_extra(flow, step)
    nav = keyboards.create_admin_flow_nav_keyboard(flow, step, total, extra)

    if flow == "nb":
        if step == 1:
            terms_url = escape((get_setting("terms_url") or "").strip())
            privacy_url = escape((get_setting("privacy_url") or "").strip())
            text = admin_flow_guide.guide_newbie_step(step) + (
                "\n\n<b>Как у пользователя после /start:</b>\n"
                "Экран «Принимаю» (условия и политика — ссылки в настройках бота).\n"
            )
            if terms_url and privacy_url:
                text += (
                    f"\n<a href=\"{terms_url}\">Условия</a> · "
                    f"<a href=\"{privacy_url}\">Политика</a>"
                )
            await _edit_guide_message(
                callback,
                text,
                keyboards.create_admin_guide_nb_step1_keyboard(),
                disable_web_page_preview=True,
            )
            return
        if step == 2:
            user_db = get_user(tid)
            trial_avail = not (user_db and user_db.get("trial_used"))
            menu = keyboards.create_main_menu_keyboard(
                has_active_sub=False,
                trial_available=trial_avail,
                is_admin=True,
                telegram_id=tid,
                for_simulation=False,
            )
            await _edit_guide_message(
                callback,
                admin_flow_guide.guide_newbie_step(step),
                _merge_menu_with_nav(menu, nav),
            )
            return
        if step == 3:
            text = (
                admin_flow_guide.guide_newbie_step(step)
                + "\n\n"
                + admin_flow_guide.demo_trial_success_text()
                + "\n\n<i>Пример экрана. На шаге 2 нажмите «Начать бесплатно» — "
                "увидите свой ключ.</i>"
            )
            await _edit_guide_message(callback, text, nav)
            return
        text = admin_flow_guide.guide_newbie_step(step)
        kb = keyboards.create_admin_guide_nb_step4_keyboard(extra)
        await _edit_guide_message(callback, text, kb)
        return
    elif flow == "ex":
        if step == 1:
            menu = keyboards.create_main_menu_keyboard(
                has_active_sub=True,
                trial_available=False,
                is_admin=True,
                telegram_id=tid,
                for_simulation=False,
            )
            await _edit_guide_message(
                callback,
                admin_flow_guide.guide_existing_step(step),
                _merge_menu_with_nav(menu, nav),
            )
            return
        text = admin_flow_guide.guide_existing_step(step)
    else:
        text = admin_flow_guide.guide_web_step(step)

    await _edit_guide_message(callback, text, nav)


@admin_router.callback_query(F.data == "admin_flow_g_nb_1")
async def admin_flow_g_nb_1(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()
    logger.info("admin guide nb step 1 uid=%s", callback.from_user.id)
    await _render_admin_flow_guide(callback, "nb", 1)


@admin_router.callback_query(F.data == "admin_demo_agree")
async def admin_demo_agree(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer("Шаг 2 — реальное меню новичка", show_alert=False)
    await _render_admin_flow_guide(callback, "nb", 2)


@admin_router.callback_query(F.data == "admin_demo_hint_trial")
async def admin_demo_hint_trial(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer(
        "Нажмите «Начать бесплатно» в меню выше — это реальный get_trial (~3 мес.).",
        show_alert=True,
    )


@admin_router.callback_query(F.data == "admin_demo_hint_help")
async def admin_demo_hint_help(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer(
        "Нажмите «Подключить VPN» в меню выше — мастер настройки как у пользователя.",
        show_alert=True,
    )


@admin_router.callback_query(F.data == "admin_flow_ex_demo_vpn")
async def admin_flow_ex_demo_vpn(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()
    nav = keyboards.create_admin_flow_nav_keyboard("ex", 2, 3)
    await _edit_guide_message(callback, admin_flow_guide.demo_my_vpn_text(), nav)


@admin_router.callback_query(F.data.startswith("admin_flow_g_"))
async def admin_flow_guide_step(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    parsed = _parse_flow_step(callback.data)
    if not parsed:
        await callback.answer("Неизвестная кнопка", show_alert=True)
        return
    await callback.answer()
    flow, step = parsed
    await _render_admin_flow_guide(callback, flow, step)

