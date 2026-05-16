HANDLERS = "/opt/remna-shop/src/shop_bot/bot/handlers.py"

with open(HANDLERS) as f:
    content = f.read()

old = '            _sub_url = sub_url if "sub_url" in dir() else uri'
new = '            _sub_url = sub_url or uri'

count = content.count(old)
print(f"Found: {count}")
content = content.replace(old, new)

with open(HANDLERS, 'w') as f:
    f.write(content)

print(f"Replaced. 'sub_url in dir' remaining: {content.count('sub_url in dir')}")
