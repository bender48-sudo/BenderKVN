import os
import logging
import sqlite3
import time

from aiogram import Bot, Router, F, types
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest

from shop_bot.data_manager import database
from shop_bot.data_manager.database import (
    cleanup_support_rate_limits,
    get_user,
    register_user_if_not_exists,
    support_rate_limit_check,
)

logger = logging.getLogger(__name__)

SUPPORT_GROUP_ID = int(os.getenv("SUPPORT_GROUP_ID", "0"))
BOT_SUPPORT_ENABLED = os.getenv("BOT_SUPPORT_ENABLED", "1").strip().lower() not in (
    "0",
    "false",
    "no",
    "off",
)
if not BOT_SUPPORT_ENABLED:
    logger.warning(
        "BOT_SUPPORT_ENABLED=0 — user messages will not reach support group"
    )
if os.getenv("BOT_PAYMENTS_LIVE", "").strip() in ("1", "true", "yes") and SUPPORT_GROUP_ID == 0:
    logger.critical(
        "SUPPORT_GROUP_ID is 0 on live bot — support replies from group will not work"
    )
ADMIN_ID = os.getenv("ADMIN_TELEGRAM_ID")
SUPPORT_USER_RL_WINDOW = int(os.getenv("SUPPORT_USER_RL_WINDOW", "60"))
SUPPORT_USER_RL_MAX = int(os.getenv("SUPPORT_USER_RL_MAX", "8"))

MSG_SUPPORT_DISABLED = (
    "Поддержка временно недоступна. Попробуй позже или напиши на @BenderVPN_support."
)


def _db_path():
    return database.DB_FILE

support_router = Router()


def _support_disabled_for_user() -> bool:
    return not BOT_SUPPORT_ENABLED or not SUPPORT_GROUP_ID


def _support_rate_limited(user_id: int) -> bool:
    cleanup_support_rate_limits(SUPPORT_USER_RL_WINDOW * 2)
    return support_rate_limit_check(
        user_id,
        window_sec=SUPPORT_USER_RL_WINDOW,
        max_hits=SUPPORT_USER_RL_MAX,
    )


def _get_support_topic(telegram_id: int):
    with sqlite3.connect(_db_path()) as conn:
        c = conn.cursor()
        c.execute("SELECT support_topic_id FROM users WHERE telegram_id = ?", (telegram_id,))
        row = c.fetchone()
        return row[0] if row and row[0] else None


def _set_support_topic(telegram_id: int, topic_id: int | None) -> None:
    with sqlite3.connect(_db_path()) as conn:
        c = conn.cursor()
        c.execute(
            "UPDATE users SET support_topic_id = ? WHERE telegram_id = ?",
            (topic_id, telegram_id),
        )
        if topic_id is not None and c.rowcount == 0:
            c.execute(
                "INSERT INTO users (telegram_id, support_topic_id) VALUES (?, ?)",
                (telegram_id, topic_id),
            )
        conn.commit()


def _touch_support_user(telegram_id: int) -> None:
    ts = int(time.time())
    with sqlite3.connect(_db_path()) as conn:
        conn.execute(
            "UPDATE users SET support_last_user_at = ? WHERE telegram_id = ?",
            (ts, telegram_id),
        )
        conn.commit()


def _touch_support_staff(topic_id: int) -> None:
    ts = int(time.time())
    with sqlite3.connect(_db_path()) as conn:
        conn.execute(
            "UPDATE users SET support_last_staff_at = ? WHERE support_topic_id = ?",
            (ts, topic_id),
        )
        conn.commit()


def _find_user_by_topic(topic_id: int):
    with sqlite3.connect(_db_path()) as conn:
        c = conn.cursor()
        c.execute("SELECT telegram_id FROM users WHERE support_topic_id = ?", (topic_id,))
        row = c.fetchone()
        return row[0] if row else None


async def _create_topic(bot: Bot, user_id: int, full_name: str):
    """Create a new forum topic and save it to DB."""
    name = f"{full_name} | {user_id}"
    result = await bot.create_forum_topic(
        chat_id=SUPPORT_GROUP_ID,
        name=name[:128],
    )
    topic_id = result.message_thread_id
    _set_support_topic(user_id, topic_id)
    logger.info(f"Created support topic {topic_id} for user {user_id}")
    return topic_id


async def _relay_user_message_to_topic(
    bot: Bot, message: types.Message, topic_id: int
) -> None:
    """Copy user message into support forum topic (more reliable than forward)."""
    await bot.copy_message(
        chat_id=SUPPORT_GROUP_ID,
        from_chat_id=message.chat.id,
        message_id=message.message_id,
        message_thread_id=topic_id,
    )


@support_router.message(F.chat.type == "private", ~F.text.startswith("/"), ~F.successful_payment)
async def user_message_to_support(message: types.Message, bot: Bot):
    """Forward user messages to support group topic."""
    if _support_disabled_for_user():
        await message.answer(MSG_SUPPORT_DISABLED, parse_mode="HTML")
        return

    user_id = message.from_user.id
    register_user_if_not_exists(
        user_id, message.from_user.username or message.from_user.full_name or ""
    )
    user_data = get_user(user_id)
    if not user_data or not user_data.get("agreed_to_terms"):
        await message.answer(
            "Сначала прими <b>Условия использования</b>:\n"
            "отправь /start и нажми кнопку <b>«Принимаю»</b>.\n\n"
            "Если кнопка «загружается» — закрой чат и снова /start, "
            "затем нажми «Принимаю» на <b>новом</b> сообщении.",
            parse_mode="HTML",
        )
        return

    if _support_rate_limited(user_id):
        await message.answer(
            "Слишком много сообщений подряд. Подожди минуту и напиши снова."
        )
        return
    topic_id = _get_support_topic(user_id)
    is_new_topic = False

    if not topic_id:
        try:
            topic_id = await _create_topic(bot, user_id, message.from_user.full_name)
            is_new_topic = True
        except Exception as e:
            logger.error(f"Failed to create support topic for {user_id}: {e}")
            await message.answer("\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0441\u043e\u0437\u0434\u0430\u0442\u044c \u043e\u0431\u0440\u0430\u0449\u0435\u043d\u0438\u0435. \u041f\u043e\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435 \u043f\u043e\u0437\u0436\u0435.")
            return

    try:
        await _relay_user_message_to_topic(bot, message, topic_id)
        _touch_support_user(user_id)
        if is_new_topic:
            await message.answer("\u041f\u043e\u043b\u0443\u0447\u0438\u043b\u0438 \u0432\u0430\u0448\u0435 \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435! \u041e\u0442\u0432\u0435\u0442\u0438\u043c \u0432 \u0441\u0430\u043c\u043e\u0435 \u0431\u043b\u0438\u0436\u0430\u0439\u0448\u0435\u0435 \u0432\u0440\u0435\u043c\u044f \U0001f64f")
    except TelegramBadRequest as e:
        err = str(e).lower()
        if "thread not found" in err or "topic not found" in err:
            logger.warning("Support topic %s missing for user %s, recreating once", topic_id, user_id)
            try:
                topic_id = await _create_topic(bot, user_id, message.from_user.full_name)
                await _relay_user_message_to_topic(bot, message, topic_id)
                _touch_support_user(user_id)
                if is_new_topic:
                    await message.answer(
                        "\u041f\u043e\u043b\u0443\u0447\u0438\u043b\u0438 \u0432\u0430\u0448\u0435 \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435! "
                        "\u041e\u0442\u0432\u0435\u0442\u0438\u043c \u0432 \u0441\u0430\u043c\u043e\u0435 \u0431\u043b\u0438\u0436\u0430\u0439\u0448\u0435\u0435 \u0432\u0440\u0435\u043c\u044f \U0001f64f"
                    )
            except Exception as e2:
                logger.error("Failed to recreate support topic for %s: %s", user_id, e2)
                await message.answer(
                    "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043e\u0442\u043f\u0440\u0430\u0432\u0438\u0442\u044c \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435 \u0432 \u043f\u043e\u0434\u0434\u0435\u0440\u0436\u043a\u0443. "
                    "\u041f\u043e\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435 \u043f\u043e\u0437\u0436\u0435."
                )
        else:
            logger.error("Failed to relay message to topic %s: %s", topic_id, e)
            await message.answer(
                "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043e\u0442\u043f\u0440\u0430\u0432\u0438\u0442\u044c \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435 \u0432 \u043f\u043e\u0434\u0434\u0435\u0440\u0436\u043a\u0443. "
                "\u041f\u043e\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435 \u043f\u043e\u0437\u0436\u0435."
            )
    except Exception as e:
        logger.error("Failed to relay message to topic %s: %s", topic_id, e)
        await message.answer(
            "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043e\u0442\u043f\u0440\u0430\u0432\u0438\u0442\u044c \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435 \u0432 \u043f\u043e\u0434\u0434\u0435\u0440\u0436\u043a\u0443. "
            "\u041f\u043e\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435 \u043f\u043e\u0437\u0436\u0435."
        )


def _user_id_from_reply(message: types.Message) -> int | None:
    """Resolve client from reply-to forwarded user message in support topic."""
    ref = message.reply_to_message
    if not ref:
        return None
    if ref.forward_from and not ref.forward_from.is_bot:
        return int(ref.forward_from.id)
    origin = getattr(ref, "forward_origin", None)
    if origin is not None:
        sender = getattr(origin, "sender_user", None)
        if sender and not getattr(sender, "is_bot", False):
            return int(sender.id)
    if ref.from_user and not ref.from_user.is_bot and ref.chat.type == "private":
        return int(ref.from_user.id)
    return None


@support_router.message(F.chat.id == SUPPORT_GROUP_ID, F.message_thread_id)
async def admin_reply_in_topic(message: types.Message, bot: Bot):
    """Forward admin replies from support group topic back to user."""
    thread_id = message.message_thread_id
    if not thread_id:
        return

    if not is_authorized_support_staff(message.from_user):
        logger.warning(
            "Ignored support reply from unauthorized tg_id=%s in topic=%s",
            getattr(message.from_user, "id", None),
            thread_id,
        )
        return

    user_id = _find_user_by_topic(thread_id)
    if not user_id:
        user_id = _user_id_from_reply(message)
        if user_id:
            _set_support_topic(user_id, thread_id)
            logger.info(
                "Support topic %s remapped to user %s via reply_to forward",
                thread_id,
                user_id,
            )
    if not user_id:
        logger.warning(
            "Support reply dropped: unknown topic=%s staff=%s (reply in thread or remap DB)",
            thread_id,
            message.from_user.id,
        )
        await message.reply(
            f"⚠️ Сообщение не доставлено клиенту: топик {thread_id} не привязан к user_id. "
            "Ответьте *реплаем* на пересланное сообщение клиента или попросите его написать боту снова.",
            parse_mode="Markdown",
        )
        return

    try:
        _touch_support_staff(thread_id)
        if message.text:
            await bot.send_message(chat_id=user_id, text=message.text)
        elif message.photo:
            await bot.send_photo(chat_id=user_id, photo=message.photo[-1].file_id, caption=message.caption)
        elif message.document:
            await bot.send_document(chat_id=user_id, document=message.document.file_id, caption=message.caption)
        elif message.video:
            await bot.send_video(chat_id=user_id, video=message.video.file_id, caption=message.caption)
        elif message.sticker:
            await bot.send_sticker(chat_id=user_id, sticker=message.sticker.file_id)
        else:
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
            )
        logger.info(
            "Support reply delivered to user %s from staff %s topic=%s",
            user_id,
            message.from_user.id,
            thread_id,
        )
    except Exception as e:
        logger.error(
            "Failed to deliver support reply to user %s topic=%s: %s",
            user_id,
            thread_id,
            e,
        )
        await message.reply(
            f"\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043e\u0442\u043f\u0440\u0430\u0432\u0438\u0442\u044c \u043e\u0442\u0432\u0435\u0442 \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044e ({e})."
        )
