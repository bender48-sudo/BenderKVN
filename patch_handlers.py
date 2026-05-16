# -*- coding: utf-8 -*-
with open('/opt/remna-shop/src/shop_bot/bot/handlers.py', 'r') as f:
    h = f.read()

with open('/opt/remna-shop/src/shop_bot/bot/handlers.py.bak', 'w') as f:
    f.write(h)

fixes = 0

# --- BUG 1: my_account_handler — duplicate edit_text ---
old = '        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboards.create_account_keyboard(True))\n        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboards.create_account_keyboard(True))'
new = '        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboards.create_account_keyboard(True))'
if old in h:
    h = h.replace(old, new, 1)
    fixes += 1
    print("BUG 1: Fixed duplicate edit_text in my_account_handler")
else:
    print("BUG 1: Pattern not found")

# --- BUG 2: my_account_handler — exp/ref_count not defined in else branch ---
old2 = '''    else:
        trial_available = not (user_db_data and user_db_data.get("trial_used"))
        text = f"\U0001f464 <b>\u0412\u0430\u0448 \u0430\u043a\u043a\u0430\u0443\u043d\u0442 BenderVPN</b>\\n\\n\U0001f4c5 \u041f\u043e\u0434\u043f\u0438\u0441\u043a\u0430: \u0430\u043a\u0442\u0438\u0432\u043d\u0430 \u0434\u043e {exp.strftime('%d.%m.%Y')}\\n\U0001f465 \u041f\u0440\u0438\u0433\u043b\u0430\u0448\u0435\u043d\u043e \u0434\u0440\u0443\u0437\u0435\u0439: {ref_count}"
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboards.create_account_no_sub_keyboard(trial_available))'''

new2 = '''    else:
        trial_available = not (user_db_data and user_db_data.get("trial_used"))
        ref_code = ensure_user_ref_code(user_id)
        ref_count = count_referrals(ref_code)
        text = f"\U0001f464 <b>\u0412\u0430\u0448 \u0430\u043a\u043a\u0430\u0443\u043d\u0442 BenderVPN</b>\\n\\n\U0001f4c5 \u041f\u043e\u0434\u043f\u0438\u0441\u043a\u0430: \u043d\u0435 \u0430\u043a\u0442\u0438\u0432\u043d\u0430\\n\U0001f465 \u041f\u0440\u0438\u0433\u043b\u0430\u0448\u0435\u043d\u043e \u0434\u0440\u0443\u0437\u0435\u0439: {ref_count}"
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboards.create_account_no_sub_keyboard(trial_available))'''

if old2 in h:
    h = h.replace(old2, new2, 1)
    fixes += 1
    print("BUG 2: Fixed exp/ref_count in my_account else branch")
else:
    print("BUG 2: Pattern not found - checking...")
    # Debug: find the else branch
    lines = h.split('\n')
    for i, line in enumerate(lines):
        if 'trial_available = not' in line and 'my_account' not in line:
            for j in range(max(0,i-2), min(len(lines), i+5)):
                print(f"  {j+1}: {repr(lines[j])}")

# --- BUG 3: referrals_handler — ref_text not defined ---
old3 = '    await callback.message.edit_text(ref_text, reply_markup=keyboards.create_back_to_menu_keyboard())'
new3 = '    await callback.message.edit_text(text, reply_markup=keyboards.create_back_to_menu_keyboard())'
if old3 in h:
    h = h.replace(old3, new3, 1)
    fixes += 1
    print("BUG 3: Fixed ref_text -> text in referrals_handler")
else:
    print("BUG 3: Pattern not found")

# --- FEATURE 1: Add new imports ---
old_import = '''    get_promo, apply_promo_usage, ensure_user_ref_code, link_referral, count_referrals,
    set_auto_renew, get_auto_renew, log_action, has_action, add_traffic_extra,
    create_promo, get_all_promos'''
new_import = '''    get_promo, apply_promo_usage, ensure_user_ref_code, link_referral, count_referrals,
    set_auto_renew, get_auto_renew, log_action, has_action, add_traffic_extra,
    create_promo, get_all_promos, has_used_promo, record_promo_usage,
    grant_referrer_bonus, get_user_by_ref_code'''
if old_import in h:
    h = h.replace(old_import, new_import, 1)
    fixes += 1
    print("FEATURE 1: Added new imports")
else:
    print("FEATURE 1: Import pattern not found")

# --- FEATURE 2: Check promo already used by user ---
old_promo = '''    promo = get_promo(code)
    if not promo:
        await message.answer("\u274c \u041f\u0440\u043e\u043c\u043e\u043a\u043e\u0434 \u043d\u0435\u0434\u0435\u0439\u0441\u0442\u0432\u0438\u0442\u0435\u043b\u0435\u043d \u0438\u043b\u0438 \u0438\u0441\u0447\u0435\u0440\u043f\u0430\u043d. \u041f\u043e\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435 \u0434\u0440\u0443\u0433\u043e\u0439.")
        return'''
new_promo = '''    promo = get_promo(code)
    if not promo:
        await message.answer("\u274c \u041f\u0440\u043e\u043c\u043e\u043a\u043e\u0434 \u043d\u0435\u0434\u0435\u0439\u0441\u0442\u0432\u0438\u0442\u0435\u043b\u0435\u043d \u0438\u043b\u0438 \u0438\u0441\u0447\u0435\u0440\u043f\u0430\u043d. \u041f\u043e\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435 \u0434\u0440\u0443\u0433\u043e\u0439.")
        return
    user_id = message.from_user.id
    if has_used_promo(user_id, code):
        await message.answer("\u274c \u0412\u044b \u0443\u0436\u0435 \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u043b\u0438 \u044d\u0442\u043e\u0442 \u043f\u0440\u043e\u043c\u043e\u043a\u043e\u0434.")
        return'''
if old_promo in h:
    h = h.replace(old_promo, new_promo, 1)
    fixes += 1
    print("FEATURE 2: Added promo duplicate check")
else:
    print("FEATURE 2: Promo check pattern not found")

# --- FEATURE 3: Grant referrer bonus on first purchase ---
old_ref = '''        if not has_action(user_id, 'first_purchase'):
            log_action(user_id, 'first_purchase')
            u = get_user(user_id)
            referrer_code = u.get('referred_by') if u else None
            if referrer_code:
                days_to_add += 3
                log_action(user_id, 'ref_bonus_received', referrer_code)'''
new_ref = '''        if not has_action(user_id, 'first_purchase'):
            log_action(user_id, 'first_purchase')
            u = get_user(user_id)
            referrer_code = u.get('referred_by') if u else None
            if referrer_code:
                days_to_add += 3
                log_action(user_id, 'ref_bonus_received', referrer_code)
                referrer = get_user_by_ref_code(referrer_code)
                if referrer:
                    referrer_id = referrer['telegram_id']
                    bonus_granted = grant_referrer_bonus(referrer_id, user_id, 3)
                    if bonus_granted:
                        log_action(referrer_id, 'ref_bonus_granted', str(user_id))
                        try:
                            referrer_keys = get_user_keys(referrer_id)
                            if referrer_keys:
                                ref_email = referrer_keys[0]['key_email']
                                await remnawave_api.provision_key(ref_email, days=3, telegram_id=str(referrer_id))
                                await bot.send_message(referrer_id, "\\U0001f381 <b>\\u0411\\u043e\\u043d\\u0443\\u0441!</b>\\n\\n\\u0412\\u0430\\u0448 \\u0434\\u0440\\u0443\\u0433 \\u043e\\u0444\\u043e\\u0440\\u043c\\u0438\\u043b \\u043f\\u043e\\u0434\\u043f\\u0438\\u0441\\u043a\\u0443 \\u2014 \\u0432\\u044b \\u043f\\u043e\\u043b\\u0443\\u0447\\u0438\\u043b\\u0438 +3 \\u0434\\u043d\\u044f!", parse_mode="HTML")
                        except Exception as ref_err:
                            logger.error(f"Failed to grant referrer bonus days to {referrer_id}: {ref_err}")'''
if old_ref in h:
    h = h.replace(old_ref, new_ref, 1)
    fixes += 1
    print("FEATURE 3: Added referrer bonus on first purchase")
else:
    print("FEATURE 3: Referrer pattern not found")

# --- FEATURE 4: Record promo usage ---
old_apply = '''                apply_promo_usage(promo_code)
                log_action(user_id, 'promo_used', promo_code)'''
new_apply = '''                apply_promo_usage(promo_code)
                record_promo_usage(user_id, promo_code)
                log_action(user_id, 'promo_used', promo_code)'''
if old_apply in h:
    h = h.replace(old_apply, new_apply, 1)
    fixes += 1
    print("FEATURE 4: Added record_promo_usage call")
else:
    print("FEATURE 4: Promo apply pattern not found")

with open('/opt/remna-shop/src/shop_bot/bot/handlers.py', 'w') as f:
    f.write(h)

print(f"\nTotal fixes applied: {fixes}")
