import asyncio
import json
import logging
import os
import ssl
import time
from urllib.parse import urlparse

import aiohttp
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from shop_bot.data_manager.database import update_setting
from . import keyboards

ADMIN_ID = os.getenv("ADMIN_TELEGRAM_ID")
logger = logging.getLogger(__name__)
admin_router = Router()

# /status: lightweight infra probe ------------------------------------------
REMNA_BASE_URL = os.getenv("REMNA_BASE_URL", "").rstrip("/")
REMNA_API_TOKEN = os.getenv("REMNA_API_TOKEN")
# Subscription edge probe (mirror monitor.sh — path is public smoke URL).
_sub = os.getenv("SUB_PUBLIC_ORIGIN", "https://p4n7q.conntest.xyz:2053").rstrip("/")
_sub_path = os.getenv(
    "SUB_MONITOR_PROBE_SUFFIX", "api/sub/JLCF43RGjyq4ML78Qcsbq7Kf2"
).lstrip("/")
SUB_PROBE_URL = os.getenv("SUB_MONITOR_PROBE_URL") or f"{_sub}/{_sub_path}"
# Nodes whose disconnected state is *expected* (e.g. drained during decom).
DECOM_NODE_NAMES = {"Amsterdam-01"}
STATUS_TIMEOUT = 8


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
    except Exception:
        return False


async def _fetch_panel(session: aiohttp.ClientSession, path: str) -> dict | None:
    """GET ${REMNA_BASE_URL}${path} with bearer token. Returns parsed JSON or None."""
    if not REMNA_BASE_URL or not REMNA_API_TOKEN:
        return None
    url = REMNA_BASE_URL + path
    headers = {"Authorization": f"Bearer {REMNA_API_TOKEN}"}
    try:
        async with session.get(url, headers=headers, timeout=STATUS_TIMEOUT) as r:
            if r.status != 200:
                return None
            return await r.json(content_type=None)
    except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError):
        return None


async def _probe_sub(session: aiohttp.ClientSession) -> int:
    """Return HTTP status code from subscription endpoint (0 on connect error)."""
    try:
        async with session.get(SUB_PROBE_URL, timeout=STATUS_TIMEOUT) as r:
            return r.status
    except (aiohttp.ClientError, asyncio.TimeoutError):
        return 0


def _render_status(nodes_payload, hosts_payload, sub_code: int) -> str:
    lines = ["🛰 <b>BenderVPN — Live Status</b>"]
    lines.append(f"🕐 {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}")
    lines.append("")

    lines.append("🖥 <b>Nodes:</b>")
    if not nodes_payload:
        lines.append("  ⚠️ couldn't reach panel API")
    else:
        nodes = (nodes_payload or {}).get("response") or []
        for n in nodes:
            name = n.get("name", "?")
            is_conn = bool(n.get("isConnected"))
            if name in DECOM_NODE_NAMES:
                icon, note = "🟡", " (decom, expected)"
            elif is_conn:
                icon, note = "🟢", ""
            else:
                icon, note = "🔴", " — disconnected"
            lines.append(f"  {icon} {name}{note}")
    lines.append("")

    lines.append("📦 <b>Hosts:</b>")
    if not hosts_payload:
        lines.append("  ⚠️ couldn't reach panel API")
    else:
        hosts = (hosts_payload or {}).get("response") or []
        total = len(hosts)
        # hidden and disabled overlap (e.g. AMS during decom is both), so we
        # show visible = !hidden && !disabled separately rather than subtracting.
        visible = sum(1 for h in hosts if not h.get("isHidden") and not h.get("isDisabled"))
        hidden = sum(1 for h in hosts if h.get("isHidden"))
        disabled = sum(1 for h in hosts if h.get("isDisabled"))
        lines.append(f"  total={total}  visible={visible}  hidden={hidden}  disabled={disabled}")
    lines.append("")

    lines.append("🌐 <b>Subscription endpoint:</b>")
    if sub_code == 200:
        lines.append(f"  🟢 HTTP {sub_code}")
    elif sub_code == 0:
        lines.append("  🔴 connect failed")
    else:
        lines.append(f"  🟡 HTTP {sub_code}")

    lines.append("")
    lines.append("<i>(monitor.sh / ru-monitor.py liveness is covered by the NL watchdog — silent if healthy.)</i>")
    return "\n".join(lines)


async def _gather_status() -> str:
    conn = aiohttp.TCPConnector(ssl=ssl.create_default_context())
    async with aiohttp.ClientSession(connector=conn) as session:
        nodes_t = _fetch_panel(session, "/api/nodes")
        hosts_t = _fetch_panel(session, "/api/hosts")
        sub_t = _probe_sub(session)
        nodes_p, hosts_p, sub_c = await asyncio.gather(nodes_t, hosts_t, sub_t)
    return _render_status(nodes_p, hosts_p, sub_c)


@admin_router.message(Command("status"))
async def status_handler(message: types.Message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    try:
        text = await _gather_status()
    except Exception as e:
        logger.exception("status handler failed: %s", e)
        text = f"⚠️ /status failed: {e}"
    await message.answer(text)


@admin_router.message(Command("admin"))
async def admin_panel_handler(message: types.Message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    await message.answer("Добро пожаловать в админ-панель!", reply_markup=keyboards.create_admin_keyboard())

@admin_router.callback_query(F.data.startswith("admin_edit_"))
async def start_editing_handler(callback: types.CallbackQuery, state: FSMContext):
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
    await state.clear()
    await callback.message.edit_text("Действие отменено. Вы в админ-панели.", reply_markup=keyboards.create_admin_keyboard())
    await callback.answer()

async def process_new_content(message: types.Message, state: FSMContext, db_key: str):
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
