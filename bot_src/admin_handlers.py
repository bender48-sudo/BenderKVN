import logging
import os
from urllib.parse import urlparse

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from shop_bot.admin_auth import is_admin_telegram
from shop_bot.data_manager.database import get_user, get_user_keys, update_setting
from shop_bot import admin_flow_test
from . import keyboards

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
        "🧪 <b>Тест пользовательских флоу</b>\n\n"
        "Проверки ловят типичные регрессии (порт :2053, 401 панели, кабинет, /setup).\n"
        "«Сценарий» — живое меню или ссылка /setup/; БД не меняется.",
        reply_markup=keyboards.create_admin_flow_test_keyboard(),
    )


@admin_router.callback_query(F.data == "admin_flow_smoke_all")
async def admin_flow_smoke_all(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer("Запускаю проверки…")
    await callback.message.edit_text("⏳ Проверка флоу…")
    text = await admin_flow_test.run_all_smokes(callback.from_user.id)
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.create_admin_flow_test_keyboard(),
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
    await callback.message.edit_text(
        text[:3900],
        reply_markup=keyboards.create_admin_flow_test_keyboard(),
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
    await callback.message.edit_text(
        text[:3900],
        reply_markup=keyboards.create_admin_flow_test_keyboard(),
    )


@admin_router.callback_query(F.data == "admin_flow_smoke_email")
async def admin_flow_smoke_email(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()
    infra = await admin_flow_test.smoke_infrastructure()
    email = admin_flow_test.smoke_email_web()
    text = (
        "🧪 <b>Email / web</b>\n\n"
        + admin_flow_test.format_section("Инфра", infra)
        + "\n\n"
        + admin_flow_test.format_section("Web trial", email)
    )
    await callback.message.edit_text(
        text[:3900],
        reply_markup=keyboards.create_admin_flow_test_keyboard(),
    )


@admin_router.callback_query(F.data == "admin_flow_run_newbie")
async def admin_flow_run_newbie(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()
    tid = callback.from_user.id
    kb = keyboards.create_main_menu_keyboard(
        has_active_sub=False,
        trial_available=True,
        is_admin=False,
        telegram_id=tid,
    )
    await callback.message.edit_text(
        admin_flow_test.sim_newbie_header(),
        reply_markup=keyboards.with_admin_flow_back(kb),
    )


@admin_router.callback_query(F.data == "admin_flow_run_existing")
async def admin_flow_run_existing(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()
    tid = callback.from_user.id
    kb = keyboards.create_main_menu_keyboard(
        has_active_sub=True,
        trial_available=False,
        is_admin=False,
        telegram_id=tid,
    )
    await callback.message.edit_text(
        admin_flow_test.sim_existing_header(tid),
        reply_markup=keyboards.with_admin_flow_back(kb),
    )


@admin_router.callback_query(F.data == "admin_flow_run_email")
async def admin_flow_run_email(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()
    setup_url = f"{admin_flow_test.setup_origin().rstrip('/')}/setup/"
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    rows = [
        [
            InlineKeyboardButton(
                text="\U0001f310 \u041e\u0442\u043a\u0440\u044b\u0442\u044c /setup/ \u0432 \u0431\u0440\u0430\u0443\u0437\u0435\u0440\u0435",
                url=setup_url,
            )
        ],
        [
            InlineKeyboardButton(
                text="\U0001f519 \u041a \u0442\u0435\u0441\u0442\u0430\u043c \u0444\u043b\u043e\u0443",
                callback_data="admin_flow_test_menu",
            )
        ],
    ]
    await callback.message.edit_text(
        admin_flow_test.sim_email_header(),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )