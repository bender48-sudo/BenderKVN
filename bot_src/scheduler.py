import asyncio
import logging
import time as _time
from datetime import datetime, timezone
import shutil
from pathlib import Path
from aiogram import Bot
from shop_bot.data_manager import database
from shop_bot.modules import remnawave_api
from shop_bot.modules.remnawave_api import remna_client_session
from shop_bot.config import BOT_PAYMENTS_LIVE, DAILY_RATE, SCHEDULER_CONCURRENT_API_CALLS
from shop_bot.auto_renew_billing import balance_covers_renew, plan_renew_cost
from shop_bot.utils.logger import bot_logger
from shop_bot.bot.subscription_refresh import run_sub_refresh_notify_batch

CHECK_INTERVAL_SECONDS = 300
EXPIRY_NOTIFY_DAYS = [7, 3, 1, 0]
logger = logging.getLogger(__name__)

THRESHOLDS = [50, 80, 90, 100]

BACKUP_INTERVAL_HOURS = 6  # Продакшн значение - бэкап каждые 6 часов
BACKUP_CHECK_INTERVAL_SECONDS = 3600  # не решать «пора ли бэкап» каждые 5 мин
async def _poll_vpn_user(bot: Bot, session, user_entry: dict) -> tuple[int, bool]:
    """Poll one VPN user; returns (notifications_sent, had_error)."""
    notifications_sent = 0
    user_id = user_entry["user_id"]
    user_profile = database.get_user(user_id)
    auto_renew = user_profile.get("auto_renew") if user_profile else 0
    user_keys = database.get_user_keys(user_id)

    if not user_keys:
        return 0, False

    remote = await remnawave_api.get_user_by_telegram_id(session, str(user_id))
    if not remote:
        return 0, False

    expire_iso = remote.get("expireAt")
    if not expire_iso:
        return 0, False

    try:
        remote_dt = datetime.fromisoformat(expire_iso.replace("Z", "+00:00"))
        remote_ms = int(remote_dt.timestamp() * 1000)

        for key in user_keys:
            key_email = key["key_email"]
            local_dt = datetime.fromisoformat(key["expiry_date"])
            if local_dt.tzinfo is None:
                local_dt = local_dt.replace(tzinfo=timezone.utc)
            local_ms = int(local_dt.timestamp() * 1000)

            if abs(remote_ms - local_ms) > 1000:

                class _Obj:
                    pass

                o = _Obj()
                o.expiry_time = remote_ms
                o.id = remote.get("vlessUuid")
                database.update_key_status_from_server(key_email, o)

        if remote_dt.tzinfo is None:
            remote_dt = remote_dt.replace(tzinfo=timezone.utc)
        now_utc = datetime.now(timezone.utc)
        days_left = (remote_dt - now_utc).days
        hours_left = (remote_dt - now_utc).total_seconds() / 3600
        last_days_notified = database.get_last_expiry_notified_days(user_id)

        if (
            0 < hours_left <= 6
            and not database.was_expiry_hour_notified(user_id)
        ):
            try:
                hrs = max(1, int(hours_left))
                txt = (
                    f"⏰ Доступ заканчивается примерно через {hrs} ч.\n\n"
                    "Пополните баланс или продлите подписку, чтобы не потерять VPN."
                )
                await bot.send_message(user_id, txt)
                bot_logger.notification(user_id, "EXPIRY_6H", True)
                notifications_sent += 1
            except Exception:
                bot_logger.notification(user_id, "EXPIRY_6H", False)
            database.mark_expiry_hour_notified(user_id)

        for mark in EXPIRY_NOTIFY_DAYS:
            if days_left <= mark and last_days_notified > mark:
                try:
                    if BOT_PAYMENTS_LIVE:
                        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

                        kb = InlineKeyboardMarkup(
                            inline_keyboard=[
                                [
                                    InlineKeyboardButton(
                                        text="💰 Пополнить баланс",
                                        callback_data="show_topup",
                                    )
                                ]
                            ]
                        )
                        bal = database.get_balance(user_id)
                        if mark > 0:
                            txt = (
                                f"⏰ Доступ заканчивается через {mark} дн.\n\n"
                                f"💰 Баланс: {bal:.0f} ₽\n\n"
                                f"Пополните баланс ({DAILY_RATE:.2f} ₽/день), "
                                f"чтобы не остаться без VPN 👇"
                            )
                        else:
                            txt = (
                                "❗️ Срок доступа истёк.\n\n"
                                f"💰 Баланс: {bal:.0f} ₽\n\n"
                                "Пополните баланс, чтобы продолжить пользоваться BenderVPN 👇"
                            )
                        await bot.send_message(user_id, txt, reply_markup=kb)
                    else:
                        if mark > 0:
                            txt = (
                                f"⏰ Бесплатный доступ по пробному тарифу заканчивается через {mark} дн.\n\n"
                                "Оплата через бота пока подключается. Напишите сюда в чат поддержки — поможем с продлением."
                            )
                        else:
                            txt = (
                                "❗️ Истёк срок бесплатного пробного доступа.\n\n"
                                "Оплата через бота пока недоступна. Напишите в этот чат — согласуем продление."
                            )
                        await bot.send_message(user_id, txt)
                    tag = "EXPIRED" if mark == 0 else f"EXPIRY_{mark}D"
                    bot_logger.notification(user_id, tag, True)
                    notifications_sent += 1
                except Exception:
                    bot_logger.notification(user_id, f"EXPIRY_{mark}D", False)
                database.update_last_expiry_notified_days(user_id, mark)
                break

        if auto_renew and BOT_PAYMENTS_LIVE and days_left <= 0 and user_keys:
            key = user_keys[0]
            from shop_bot.data_manager.database import (
                add_balance,
                get_balance,
                log_action,
                try_deduct_balance,
                update_key_info,
                update_user_stats,
            )

            try:
                plan = key.get("subscription_plan") or "buy_1_month"
                cost_rub, months, extend_days = plan_renew_cost(plan)
                bal = get_balance(user_id)
                if not balance_covers_renew(bal, cost_rub):
                    log_action(
                        user_id,
                        "auto_renew_skip",
                        f"insufficient:{bal:.2f}:{cost_rub:.2f}",
                    )
                    logger.info(
                        "auto_renew skip user=%s days_left=%s balance=%.2f need=%.2f",
                        user_id,
                        days_left,
                        bal,
                        cost_rub,
                    )
                    try:
                        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

                        kb = InlineKeyboardMarkup(
                            inline_keyboard=[
                                [
                                    InlineKeyboardButton(
                                        text="💰 Пополнить баланс",
                                        callback_data="show_topup",
                                    )
                                ]
                            ]
                        )
                        await bot.send_message(
                            user_id,
                            (
                                "⚠️ <b>Автопродление не выполнено</b>\n\n"
                                f"На балансе: {bal:.0f} ₽\n"
                                f"Нужно: {cost_rub:.0f} ₽ ({months} мес.)\n\n"
                                "Пополните баланс — продление включится при следующей проверке."
                            ),
                            parse_mode="HTML",
                            reply_markup=kb,
                        )
                        bot_logger.vpn_action(
                            user_id,
                            "AUTO_RENEW_SKIP",
                            f"balance {bal:.0f} < {cost_rub:.0f}",
                        )
                    except Exception:
                        pass
                elif try_deduct_balance(user_id, cost_rub):
                    key_email = key["key_email"]
                    logger.info(
                        "auto_renew trigger user=%s days_left=%s plan=%s",
                        user_id,
                        days_left,
                        plan,
                    )
                    uri, new_expire_iso, new_uuid = await remnawave_api.provision_key(
                        key_email,
                        days=extend_days,
                        telegram_id=str(user_id),
                    )
                    if uri and new_expire_iso and new_uuid:
                        new_dt = datetime.fromisoformat(
                            new_expire_iso.replace("Z", "+00:00")
                        )
                        for user_key in user_keys:
                            update_key_info(
                                user_key["key_id"],
                                new_uuid,
                                int(new_dt.timestamp() * 1000),
                            )
                        update_user_stats(user_id, cost_rub, months)
                        log_action(
                            user_id,
                            "auto_renew_success",
                            f"{key['key_id']}:{months}:{cost_rub:.2f}",
                        )
                        database.clear_expiry_hour_notified(user_id)
                        try:
                            await bot.send_message(
                                user_id,
                                (
                                    f"🔁 Подписка автоматически продлена на {months} мес. "
                                    f"до {new_dt.strftime('%d.%m.%Y %H:%M')}\n\n"
                                    f"Списано с баланса: {cost_rub:.0f} ₽"
                                ),
                            )
                            bot_logger.vpn_action(
                                user_id, "AUTO_RENEW", f"{months} months"
                            )
                        except Exception:
                            pass
                    else:
                        add_balance(user_id, cost_rub)
                        log_action(user_id, "auto_renew_fail", str(key["key_id"]))
                        try:
                            await bot.send_message(
                                user_id,
                                "⚠️ Автопродление: оплата списана, но сервер не ответил. "
                                "Баланс возвращён — напишите в поддержку.",
                            )
                            bot_logger.vpn_action(
                                user_id,
                                "AUTO_RENEW_FAILED",
                                "provision failed, refunded",
                            )
                        except Exception:
                            pass
                else:
                    log_action(user_id, "auto_renew_skip", "deduct_race")
            except Exception as e:
                bot_logger.error(
                    f"💥 Auto renew error for user {user_id}: {e}",
                    exc_info=True,
                )

        if remote and user_keys:
            first_key_email = user_keys[0]["key_email"]
            limit = remote.get("trafficLimitBytes", 0)
            used = remote.get("usedTrafficBytes", 0)
            if limit and limit > 0:
                percent = int((used / limit) * 100)
                last_notified = database.get_key_last_notified_percent(first_key_email)
                for th in THRESHOLDS:
                    if percent >= th and last_notified < th:
                        try:
                            human_used = used / 1024 / 1024 / 1024
                            human_limit = limit / 1024 / 1024 / 1024
                            await bot.send_message(
                                chat_id=user_id,
                                text=(
                                    f"⚠️ Трафик ключа {first_key_email} достиг {th}%\n"
                                    f"Использовано: {human_used:.1f} ГБ из {human_limit:.0f} ГБ."
                                ),
                            )
                            bot_logger.notification(user_id, f"TRAFFIC_{th}%", True)
                        except Exception:
                            bot_logger.notification(user_id, f"TRAFFIC_{th}%", False)
                        database.update_key_last_notified_percent(first_key_email, th)
                if percent < 5 and used < 1_000_000 and last_notified >= 50:
                    database.update_key_last_notified_percent(first_key_email, 0)

    except Exception as e:
        bot_logger.error(f"Error processing user {user_id}: {e}", exc_info=True)
        return notifications_sent, True

    return notifications_sent, False


async def start_subscription_monitor(bot: Bot):
    bot_logger.system("MONITOR", "Subscription monitor started", "OK")
    last_backup_decision_at = 0.0
    while True:
        try:
            sub_ok, sub_fail = await run_sub_refresh_notify_batch(bot)
            if sub_ok or sub_fail:
                bot_logger.system(
                    "SUB_REFRESH",
                    f"notify batch ok={sub_ok} fail={sub_fail}",
                    "OK" if sub_fail == 0 else "WARNING",
                )

            vpn_users = database.get_all_vpn_users()
            if not vpn_users:
                bot_logger.system(
                    "SCHEDULER_CYCLE",
                    f"sub_ok={sub_ok} sub_fail={sub_fail} vpn_users=0 interval={CHECK_INTERVAL_SECONDS}s",
                    "OK",
                )
                await asyncio.sleep(CHECK_INTERVAL_SECONDS)
                continue
            async with remna_client_session() as session:
                users_processed = len(vpn_users)
                notifications_sent = 0
                errors_count = 0
                sem = asyncio.Semaphore(SCHEDULER_CONCURRENT_API_CALLS)
                batch_t0 = _time.monotonic()

                async def _run_poll(entry):
                    async with sem:
                        return await _poll_vpn_user(bot, session, entry)

                outcomes = await asyncio.gather(
                    *(_run_poll(entry) for entry in vpn_users),
                    return_exceptions=True,
                )
                batch_sec = _time.monotonic() - batch_t0
                for outcome in outcomes:
                    if isinstance(outcome, Exception):
                        errors_count += 1
                        bot_logger.error(f"Poll user batch error: {outcome}", exc_info=outcome)
                    else:
                        n_sent, had_err = outcome
                        notifications_sent += n_sent
                        if had_err:
                            errors_count += 1

                bot_logger.system(
                    "MONITOR",
                    f"Poll batch {users_processed} users in {batch_sec:.1f}s "
                    f"(concurrency={SCHEDULER_CONCURRENT_API_CALLS})",
                    "OK",
                )

                # Итоговая статистика цикла мониторинга
                if users_processed > 0:
                    bot_logger.system("MONITOR", f"Cycle: {users_processed} users, {notifications_sent} notifications, {errors_count} errors", "OK" if errors_count == 0 else "WARNING")
                bot_logger.system(
                    "SCHEDULER_CYCLE",
                    f"sub_ok={sub_ok} sub_fail={sub_fail} vpn_users={users_processed} "
                    f"notifications={notifications_sent} errors={errors_count} "
                    f"batch_sec={batch_sec:.1f} interval={CHECK_INTERVAL_SECONDS}s",
                    "OK" if errors_count == 0 else "WARNING",
                )

        except Exception as e:
            bot_logger.error(f"Monitor loop critical error: {e}", exc_info=True)

        # 💾 Автоматический бэкап (решение раз в час, не каждые 5 мин)
        try:
            import os
            import time as _time

            now_mono = _time.monotonic()
            if now_mono - last_backup_decision_at >= BACKUP_CHECK_INTERVAL_SECONDS:
                last_backup_decision_at = now_mono
                now = datetime.now(timezone.utc)
                last_backup_iso = database.get_last_backup_timestamp()
                should_backup = not last_backup_iso

                if last_backup_iso:
                    try:
                        raw = last_backup_iso.replace("Z", "+00:00")
                        last_backup_dt = datetime.fromisoformat(raw)
                        if last_backup_dt.tzinfo is None:
                            last_backup_dt = last_backup_dt.replace(tzinfo=timezone.utc)
                        hours_since_backup = (now - last_backup_dt).total_seconds() / 3600
                        if hours_since_backup < 1:
                            time_str = f"{int(hours_since_backup * 60)} мин"
                        elif hours_since_backup < 24:
                            time_str = f"{hours_since_backup:.1f} ч"
                        else:
                            time_str = f"{hours_since_backup / 24:.1f} дн"
                        should_backup = hours_since_backup >= BACKUP_INTERVAL_HOURS
                        if should_backup:
                            bot_logger.backup(
                                "SCHEDULED", f"Time for backup (last: {time_str} ago)"
                            )
                    except ValueError:
                        bot_logger.backup(
                            "PARSE_ERROR",
                            f"Invalid timestamp (skip run): {last_backup_iso}",
                            "ERROR",
                        )
                        should_backup = False
                else:
                    bot_logger.backup("FIRST_BACKUP", "No previous backup found")

                if should_backup:
                    from shop_bot.bot.handlers import create_backup_and_send

                    admin_id = os.getenv("ADMIN_TELEGRAM_ID")
                    if admin_id:
                        success = await create_backup_and_send(
                            bot, admin_id, is_auto=True
                        )
                        if success:
                            bot_logger.backup(
                                "AUTO_COMPLETE", "Backup saved on disk (silent)", "OK"
                            )
                        else:
                            bot_logger.backup(
                                "AUTO_FAILED", "Failed to create backup", "ERROR"
                            )
                    else:
                        bot_logger.backup(
                            "NO_ADMIN", "ADMIN_TELEGRAM_ID not configured", "WARNING"
                        )

                    backups_dir = Path(database.DB_FILE.parent) / "backups"
                    if backups_dir.exists():
                        archives = sorted(backups_dir.glob("backup_*.tar.gz"))
                        if len(archives) > 20:
                            cleaned_count = 0
                            for old in archives[:-20]:
                                try:
                                    old.unlink()
                                    cleaned_count += 1
                                except Exception as exc:
                                    logger.warning("backup prune failed %s: %s", old, exc)
                            if cleaned_count > 0:
                                bot_logger.backup(
                                    "CLEANUP",
                                    f"Pruned {cleaned_count} old backup_*.tar.gz archives",
                                    "OK",
                                )
        except Exception as e:
            bot_logger.backup("SYSTEM_ERROR", str(e), "ERROR")
        
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
