import asyncio
import logging
from datetime import datetime, timezone
import shutil
from pathlib import Path
from aiogram import Bot
from shop_bot.data_manager import database
from shop_bot.modules import remnawave_api
from shop_bot.config import PLANS, BOT_PAYMENTS_LIVE, DAILY_RATE
from shop_bot.utils.logger import bot_logger
import aiohttp

CHECK_INTERVAL_SECONDS = 300
EXPIRY_NOTIFY_DAYS = [7, 3, 1, 0]
logger = logging.getLogger(__name__)

THRESHOLDS = [50, 80, 90, 100]

BACKUP_INTERVAL_HOURS = 6  # Продакшн значение - бэкап каждые 6 часов

async def start_subscription_monitor(bot: Bot):
    bot_logger.system("MONITOR", "Subscription monitor started", "OK")
    while True:
        try:
            vpn_users = database.get_all_vpn_users()
            if not vpn_users:
                await asyncio.sleep(CHECK_INTERVAL_SECONDS)
                continue
            async with aiohttp.ClientSession() as session:
                users_processed = 0
                notifications_sent = 0
                errors_count = 0
                
                for user_entry in vpn_users:
                    users_processed += 1
                    user_id = user_entry['user_id']
                    user_profile = database.get_user(user_id)
                    auto_renew = user_profile.get('auto_renew') if user_profile else 0
                    user_keys = database.get_user_keys(user_id)
                    
                    if not user_keys:
                        continue
                        
                    # Получаем общую информацию о пользователе (теперь все ключи в одном профиле)
                    remote = await remnawave_api.get_user_by_telegram_id(session, str(user_id))
                    if not remote:
                        continue
                        
                    expire_iso = remote.get('expireAt')
                    if not expire_iso:
                        continue
                        
                    try:
                        remote_dt = datetime.fromisoformat(expire_iso.replace('Z', '+00:00'))
                        remote_ms = int(remote_dt.timestamp() * 1000)
                        
                        # Обновляем дату истечения для всех ключей пользователя
                        for key in user_keys:
                            key_email = key['key_email']
                            local_dt = datetime.fromisoformat(key['expiry_date'])
                            local_ms = int(local_dt.timestamp() * 1000)
                            
                            if abs(remote_ms - local_ms) > 1000:
                                class _Obj: pass
                                o = _Obj()
                                o.expiry_time = remote_ms
                                o.id = remote.get('vlessUuid')
                                database.update_key_status_from_server(key_email, o)
                        
                        # Уведомления об истечении (отправляем только один раз для пользователя)
                        # Конвертируем remote_dt в локальное время для корректного сравнения
                        now_local = datetime.now()
                        remote_local = remote_dt.replace(tzinfo=None)  # убираем timezone info
                        days_left = (remote_local - now_local).days
                        last_days_notified = database.get_last_expiry_notified_days(user_id)
                        for mark in EXPIRY_NOTIFY_DAYS:
                            if days_left <= mark and last_days_notified > mark:
                                try:
                                    if BOT_PAYMENTS_LIVE:
                                        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                                        kb = InlineKeyboardMarkup(inline_keyboard=[
                                            [InlineKeyboardButton(text="💰 Пополнить баланс", callback_data="show_topup")]
                                        ])
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
                                                f"Оплата через бота пока подключается. Напишите сюда в чат поддержки — поможем с продлением."
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
                        
                        # Auto renew placeholder (применяем к первому ключу)
                        if auto_renew and BOT_PAYMENTS_LIVE and days_left == 0 and user_keys:
                            key = user_keys[0]  # Берем первый ключ для автопродления
                            try:
                                plan = key.get('subscription_plan') or 'buy_1_month'
                                name, price_rub, months = PLANS.get(plan, (None, None, 1))
                                extend_days = months * 30
                                key_email = key['key_email']
                                uri, new_expire_iso, new_uuid = await remnawave_api.provision_key(key_email, days=extend_days, telegram_id=str(user_id))
                                if uri and new_expire_iso and new_uuid:
                                    new_dt = datetime.fromisoformat(new_expire_iso.replace('Z', '+00:00'))
                                    # обновим локально для всех ключей пользователя
                                    from shop_bot.data_manager.database import update_key_info, log_action, update_user_stats
                                    for user_key in user_keys:
                                        update_key_info(user_key['key_id'], new_uuid, int(new_dt.timestamp()*1000))
                                    update_user_stats(user_id, float(price_rub) if price_rub else 0.0, months)
                                    log_action(user_id, 'auto_renew_success', f"{key['key_id']}:{months}")
                                    try:
                                        await bot.send_message(user_id, f"🔁 Подписка автоматически продлена на {months} мес. до {new_dt.strftime('%d.%m.%Y %H:%M')}")
                                        bot_logger.vpn_action(user_id, "AUTO_RENEW", f"{months} months")
                                    except Exception:
                                        pass
                                else:
                                    from shop_bot.data_manager.database import log_action
                                    log_action(user_id, 'auto_renew_fail', str(key['key_id']))
                                    try:
                                        await bot.send_message(user_id, f"⚠️ Автопродление не удалось. Продлите вручную.")
                                        bot_logger.vpn_action(user_id, "AUTO_RENEW_FAILED", "Payment failed")
                                    except Exception:
                                        pass
                            except Exception as e:
                                bot_logger.error(f"💥 Auto renew error for user {user_id}: {e}", exc_info=True)
                    
                    except Exception as e:
                        bot_logger.error(f"Error processing user {user_id}: {e}", exc_info=True)
                        errors_count += 1
                        continue
                        
                    # Проверка лимитов трафика
                    if remote and user_keys:  # Добавляем проверку user_keys
                        # Используем первый ключ для уведомлений о трафике
                        first_key_email = user_keys[0]['key_email']
                        limit = remote.get('trafficLimitBytes', 0)
                        used = remote.get('usedTrafficBytes', 0)
                        if not limit or limit <= 0:
                            continue
                        percent = int((used / limit) * 100)
                        last_notified = database.get_key_last_notified_percent(first_key_email)
                        for th in THRESHOLDS:
                            if percent >= th and last_notified < th:
                                try:
                                    human_used = used/1024/1024/1024
                                    human_limit = limit/1024/1024/1024
                                    await bot.send_message(
                                        chat_id=user_id,
                                        text=(f"⚠️ Трафик ключа {first_key_email} достиг {th}%\n"
                                              f"Использовано: {human_used:.1f} ГБ из {human_limit:.0f} ГБ.")
                                    )
                                    bot_logger.notification(user_id, f"TRAFFIC_{th}%", True)
                                except Exception as e:
                                    bot_logger.notification(user_id, f"TRAFFIC_{th}%", False)
                                database.update_key_last_notified_percent(first_key_email, th)
                        if percent < 5 and used < 1_000_000 and last_notified >= 50:
                            database.update_key_last_notified_percent(first_key_email, 0)
                
                # Итоговая статистика цикла мониторинга
                if users_processed > 0:
                    bot_logger.system("MONITOR", f"Cycle: {users_processed} users, {notifications_sent} notifications, {errors_count} errors", "OK" if errors_count == 0 else "WARNING")
                
        except Exception as e:
            bot_logger.error(f"Monitor loop critical error: {e}", exc_info=True)
        
        # 💾 Автоматический бэкап системы
        try:
            now = datetime.utcnow()
            
            # Получаем время последнего бэкапа из базы данных
            last_backup_iso = database.get_last_backup_timestamp()
            should_backup = True
            
            if last_backup_iso:
                try:
                    last_backup_dt = datetime.fromisoformat(last_backup_iso.replace('Z', ''))
                    hours_since_backup = (now - last_backup_dt).total_seconds() / 3600
                    
                    # Красивое форматирование времени
                    if hours_since_backup < 1:
                        time_str = f"{int(hours_since_backup * 60)} мин"
                    elif hours_since_backup < 24:
                        time_str = f"{hours_since_backup:.1f} ч"
                    else:
                        time_str = f"{hours_since_backup/24:.1f} дн"
                    
                    should_backup = hours_since_backup >= BACKUP_INTERVAL_HOURS
                    
                    if should_backup:
                        bot_logger.backup("SCHEDULED", f"Time for backup (last: {time_str} ago)")
                except ValueError as e:
                    bot_logger.backup("PARSE_ERROR", f"Invalid timestamp: {last_backup_iso}", "ERROR")
                    should_backup = True
            else:
                bot_logger.backup("FIRST_BACKUP", "No previous backup found")
            
            if should_backup:
                # Используем универсальную функцию для создания и отправки бэкапа
                from shop_bot.bot.handlers import create_backup_and_send
                import os
                
                admin_id = os.getenv("ADMIN_TELEGRAM_ID")
                if admin_id:
                    success = await create_backup_and_send(bot, admin_id, is_auto=True)
                    if success:
                        bot_logger.backup("AUTO_COMPLETE", "Backup created and sent to admin", "OK")
                    else:
                        bot_logger.backup("AUTO_FAILED", "Failed to create backup", "ERROR")
                else:
                    bot_logger.backup("NO_ADMIN", "ADMIN_TELEGRAM_ID not configured", "WARNING")
                
                # Очистка старых бэкапов (оставляем только файлы, не tar.gz)
                backups_dir = Path(database.DB_FILE.parent) / 'backups'
                if backups_dir.exists():
                    files = sorted(backups_dir.glob('shop_bot_*.db'))
                    if len(files) > 20:
                        cleaned_count = 0
                        for old in files[:-20]:
                            try: 
                                old.unlink()
                                cleaned_count += 1
                            except Exception: 
                                pass
                        if cleaned_count > 0:
                            bot_logger.backup("CLEANUP", f"Removed {cleaned_count} old backup files", "OK")
        except Exception as e:
            bot_logger.backup("SYSTEM_ERROR", str(e), "ERROR")
        
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)