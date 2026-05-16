HANDLERS = "/opt/remna-shop/src/shop_bot/bot/handlers.py"

with open(HANDLERS) as f:
    content = f.read()

OLD_TEXT = '👥 <b>Пригласите друга</b>\\n\\nКогда друг активирует подписку —\\nвы оба получите +3 дня 🎁'
NEW_TEXT = '👥 <b>Приглашайте друзей в BenderVPN</b>\\n\\nДелитесь ссылкой — бонусы для вас\\nи вашего друга при подключении 🎁'

count = content.count(OLD_TEXT)
print(f"Old text found: {count} times")

if count == 0:
    print("ERROR: old text not found! Checking partial...")
    print(f"  'Пригласите друга' count: {content.count('Пригласите друга')}")
    print(f"  '+3 дня' count: {content.count('+3 дня')}")
else:
    content = content.replace(OLD_TEXT, NEW_TEXT)
    with open(HANDLERS, 'w') as f:
        f.write(content)
    print(f"Replaced: {count} occurrences")

# Verify
print(f"\n+3 дня remaining: {content.count('+3 дня')}")
print(f"бонусы для вас count: {content.count('бонусы для вас')}")
