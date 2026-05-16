import os
import logging
import sqlite3
from pathlib import Path

from aiogram import Bot, Router, F, types
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest

logger = logging.getLogger(__name__)

SUPPORT_GROUP_ID = int(os.getenv("SUPPORT_GROUP_ID", "0"))
ADMIN_ID = os.getenv("ADMIN_TELEGRAM_ID")
DB_FILE = Path("/app/data/shop_bot.db")

support_router = Router()


def _get_support_topic(telegram_id: int):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT support_topic_id FROM users WHERE telegram_id = ?", (telegram_id,))
        row = c.fetchone()
        return row[0] if row and row[0] else None


def _set_support_topic(telegram_id: int, topic_id):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO users (telegram_id, support_topic_id) VALUES (?, ?) "
            "ON CONFLICT(telegram_id) DO UPDATE SET support_topic_id = excluded.support_topic_id",
            (telegram_id, topic_id),
        )
        conn.commit()


def _find_user_by_topic(topic_id: int):
    with sqlite3.connect(DB_FILE) as conn:
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


@support_router.message(F.chat.type == "private", ~F.text.startswith("/"), ~F.successful_payment)
async def user_message_to_support(message: types.Message, bot: Bot):
    """Forward user messages to support group topic."""
    if not SUPPORT_GROUP_ID:
        return

    user_id = message.from_user.id
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
        await bot.forward_message(
            chat_id=SUPPORT_GROUP_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
            message_thread_id=topic_id,
        )
        if is_new_topic:
            await message.answer("\u041f\u043e\u043b\u0443\u0447\u0438\u043b\u0438 \u0432\u0430\u0448\u0435 \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435! \u041e\u0442\u0432\u0435\u0442\u0438\u043c \u0432 \u0441\u0430\u043c\u043e\u0435 \u0431\u043b\u0438\u0436\u0430\u0439\u0448\u0435\u0435 \u0432\u0440\u0435\u043c\u044f \U0001f64f")
    except TelegramBadRequest as e:
        if "thread not found" in str(e).lower():
            # Topic was deleted from the group — create a new one
            logger.warning(f"Topic {topic_id} not found for user {user_id}, recreating")
            _set_support_topic(user_id, None)
            try:
                topic_id = await _create_topic(bot, user_id, message.from_user.full_name)
                await bot.forward_message(
                    chat_id=SUPPORT_GROUP_ID,
                    from_chat_id=message.chat.id,
                    message_id=message.message_id,
                    message_thread_id=topic_id,
                )
                await message.answer("\u041f\u043e\u043b\u0443\u0447\u0438\u043b\u0438 \u0432\u0430\u0448\u0435 \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435! \u041e\u0442\u0432\u0435\u0442\u0438\u043c \u0432 \u0441\u0430\u043c\u043e\u0435 \u0431\u043b\u0438\u0436\u0430\u0439\u0448\u0435\u0435 \u0432\u0440\u0435\u043c\u044f \U0001f64f")
            except Exception as e2:
                logger.error(f"Failed to recreate topic for {user_id}: {e2}")
                await message.answer("\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043e\u0442\u043f\u0440\u0430\u0432\u0438\u0442\u044c \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435 \u0432 \u043f\u043e\u0434\u0434\u0435\u0440\u0436\u043a\u0443. \u041f\u043e\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435 \u043f\u043e\u0437\u0436\u0435.")
        else:
            logger.error(f"Failed to forward message to topic {topic_id}: {e}")
            await message.answer("\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043e\u0442\u043f\u0440\u0430\u0432\u0438\u0442\u044c \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435 \u0432 \u043f\u043e\u0434\u0434\u0435\u0440\u0436\u043a\u0443. \u041f\u043e\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435 \u043f\u043e\u0437\u0436\u0435.")
    except Exception as e:
        logger.error(f"Failed to forward message to topic {topic_id}: {e}")
        await message.answer("\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043e\u0442\u043f\u0440\u0430\u0432\u0438\u0442\u044c \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435 \u0432 \u043f\u043e\u0434\u0434\u0435\u0440\u0436\u043a\u0443. \u041f\u043e\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435 \u043f\u043e\u0437\u0436\u0435.")


@support_router.message(F.chat.id == SUPPORT_GROUP_ID, F.message_thread_id)
async def admin_reply_in_topic(message: types.Message, bot: Bot):
    """Forward admin replies from support group topic back to user."""
    if not message.message_thread_id:
        return

    user_id = _find_user_by_topic(message.message_thread_id)
    if not user_id:
        return

    try:
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
    except Exception as e:
        logger.error(f"Failed to forward reply to user {user_id}: {e}")
        await message.reply("\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043e\u0442\u043f\u0440\u0430\u0432\u0438\u0442\u044c \u043e\u0442\u0432\u0435\u0442 \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044e.")
