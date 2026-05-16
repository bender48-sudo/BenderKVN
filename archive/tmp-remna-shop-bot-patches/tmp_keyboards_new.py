from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime
import os


main_reply_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="\U0001f3e0 \u0413\u043b\u0430\u0432\u043d\u043e\u0435 \u043c\u0435\u043d\u044e")]],
    resize_keyboard=True
)


def create_main_menu_keyboard(has_active_sub=False, trial_available=True, is_admin=False, **kwargs):
    builder = InlineKeyboardBuilder()
    if not has_active_sub and trial_available:
        builder.button(text="\U0001f381 \u041f\u043e\u043f\u0440\u043e\u0431\u043e\u0432\u0430\u0442\u044c \u0431\u0435\u0441\u043f\u043b\u0430\u0442\u043d\u043e", callback_data="get_trial")
    elif not has_active_sub:
        builder.button(text="\U0001f4b3 \u041a\u0443\u043f\u0438\u0442\u044c \u043f\u043e\u0434\u043f\u0438\u0441\u043a\u0443", callback_data="buy_new_key")
    else:
        builder.button(text="\U0001f4b3 \u041f\u0440\u043e\u0434\u043b\u0438\u0442\u044c \u043f\u043e\u0434\u043f\u0438\u0441\u043a\u0443", callback_data="buy_new_key")
    builder.button(text="\U0001f464 \u041c\u043e\u0439 \u0430\u043a\u043a\u0430\u0443\u043d\u0442", callback_data="my_account")
    builder.button(text="\U0001f4ac \u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c \u043d\u0430\u043c", callback_data="contact_support")
    builder.adjust(1)
    return builder.as_markup()


def create_trial_success_keyboard(sub_url):
    builder = InlineKeyboardBuilder()
    builder.button(text="\U0001f4cb \u0421\u043a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0441\u0441\u044b\u043b\u043a\u0443 \u043f\u043e\u0434\u043f\u0438\u0441\u043a\u0438", callback_data="copy_sub_url")
    builder.button(text="\U0001f34e App Store", url="https://apps.apple.com/ru/app/happ-proxy-utility-plus/id6746188973")
    builder.button(text="\U0001f916 Google Play", url="https://play.google.com/store/apps/details?id=com.happproxy")
    builder.button(text="\U0001f464 \u041c\u043e\u0439 \u0430\u043a\u043a\u0430\u0443\u043d\u0442", callback_data="my_account")
    builder.button(text="\U0001f4ac \u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c \u043d\u0430\u043c", callback_data="contact_support")
    builder.adjust(1, 2, 1, 1)
    return builder.as_markup()


def create_account_keyboard(sub_url=None):
    builder = InlineKeyboardBuilder()
    if sub_url:
        builder.button(text="\U0001f4cb \u0421\u043a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0441\u0441\u044b\u043b\u043a\u0443 \u043f\u043e\u0434\u043f\u0438\u0441\u043a\u0438", callback_data="copy_sub_url")
    builder.button(text="\U0001f465 \u041f\u0440\u0438\u0433\u043b\u0430\u0441\u0438\u0442\u044c \u0434\u0440\u0443\u0433\u0430", callback_data="invite_friend")
    builder.button(text="\U0001f519 \u041d\u0430\u0437\u0430\u0434", callback_data="back_to_main_menu")
    builder.adjust(1)
    return builder.as_markup()


def create_account_no_sub_keyboard(trial_available):
    builder = InlineKeyboardBuilder()
    if trial_available:
        builder.button(text="\U0001f381 \u041f\u043e\u043f\u0440\u043e\u0431\u043e\u0432\u0430\u0442\u044c \u0431\u0435\u0441\u043f\u043b\u0430\u0442\u043d\u043e", callback_data="get_trial")
    else:
        builder.button(text="\U0001f4b3 \u041a\u0443\u043f\u0438\u0442\u044c \u043f\u043e\u0434\u043f\u0438\u0441\u043a\u0443", callback_data="buy_new_key")
    builder.button(text="\U0001f519 \u041d\u0430\u0437\u0430\u0434", callback_data="back_to_main_menu")
    builder.adjust(1)
    return builder.as_markup()


def create_invite_keyboard(ref_url):
    builder = InlineKeyboardBuilder()
    builder.button(text="\U0001f4cb \u0421\u043a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0440\u0435\u0444\u0435\u0440\u0430\u043b\u044c\u043d\u0443\u044e \u0441\u0441\u044b\u043b\u043a\u0443", callback_data="copy_ref_url")
    builder.button(text="\U0001f519 \u041d\u0430\u0437\u0430\u0434", callback_data="my_account")
    builder.adjust(1)
    return builder.as_markup()


def create_back_to_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="\U0001f519 \u041d\u0430\u0437\u0430\u0434", callback_data="back_to_main_menu")
    return builder.as_markup()


def create_admin_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="\U0001f39f \u041f\u0440\u043e\u043c\u043e\u043a\u043e\u0434\u044b", callback_data="admin_promos")
    builder.button(text="\U0001f4c8 \u0421\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u0430", callback_data="admin_stats")
    builder.button(text="\U0001f4be \u0411\u044d\u043a\u0430\u043f", callback_data="admin_backup")
    builder.button(text="\u2b05\ufe0f \u0412\u044b\u0439\u0442\u0438", callback_data="back_to_main_menu")
    builder.adjust(1)
    return builder.as_markup()

def create_admin_cancel_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="\u274c \u041e\u0442\u043c\u0435\u043d\u0430", callback_data="admin_cancel_edit")
    return builder.as_markup()

def create_admin_promos_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="\u2795 \u0421\u043e\u0437\u0434\u0430\u0442\u044c", callback_data="admin_promo_create")
    builder.button(text="\U0001f4cb \u0421\u043f\u0438\u0441\u043e\u043a", callback_data="admin_promo_list")
    builder.button(text="\u2b05\ufe0f \u041d\u0430\u0437\u0430\u0434", callback_data="open_admin_panel")
    builder.adjust(1)
    return builder.as_markup()

def create_plans_keyboard(plans, action, key_id=0):
    builder = InlineKeyboardBuilder()
    for plan_id, (name, price_rub, _) in plans.items():
        builder.button(text=f"{name} - {float(price_rub):.0f} RUB", callback_data=f"{plan_id}_{action}_{key_id}")
    builder.button(text="\U0001f519 \u041d\u0430\u0437\u0430\u0434", callback_data="back_to_main_menu")
    builder.adjust(1)
    return builder.as_markup()

def create_payment_method_keyboard(payment_methods, plan_id, action, key_id):
    builder = InlineKeyboardBuilder()
    if payment_methods.get("stars"):
        builder.button(text="\u2b50 Telegram Stars", callback_data=f"pay_stars_{plan_id}_{action}_{key_id}")
    if payment_methods.get("yookassa"):
        builder.button(text="\U0001f4b3 \u041a\u0430\u0440\u0442\u0430", callback_data=f"pay_yookassa_{plan_id}_{action}_{key_id}")
    if payment_methods.get("crypto"):
        builder.button(text="\U0001f48e \u041a\u0440\u0438\u043f\u0442\u043e", callback_data=f"pay_crypto_{plan_id}_{action}_{key_id}")
    builder.button(text="\U0001f519 \u041d\u0430\u0437\u0430\u0434", callback_data="back_to_main_menu")
    builder.adjust(1)
    return builder.as_markup()

def create_payment_keyboard(payment_url):
    builder = InlineKeyboardBuilder()
    builder.button(text="\u041f\u0435\u0440\u0435\u0439\u0442\u0438 \u043a \u043e\u043f\u043b\u0430\u0442\u0435", url=payment_url)
    return builder.as_markup()

def create_agreement_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="\u2705 \u041f\u0440\u0438\u043d\u0438\u043c\u0430\u044e", callback_data="agree_to_terms")
    return builder.as_markup()

# Legacy stubs — used by handlers.py, kept for compatibility
def create_keys_management_keyboard(keys): return create_back_to_menu_keyboard()
def create_key_info_keyboard(key_id): return create_back_to_menu_keyboard()
def create_back_to_key_keyboard(key_id): return create_back_to_menu_keyboard()
def create_traffic_keyboard(): return create_back_to_menu_keyboard()
def create_support_keyboard(u): return create_back_to_menu_keyboard()
def create_about_keyboard(t, p): return create_back_to_menu_keyboard()
def create_about_keyboard_terms(t): return create_back_to_menu_keyboard()
def create_about_keyboard_privacy(p): return create_back_to_menu_keyboard()
def create_traffic_packs_keyboard(p, k): return create_back_to_menu_keyboard()
def create_promo_enter_keyboard(): return create_back_to_menu_keyboard()
