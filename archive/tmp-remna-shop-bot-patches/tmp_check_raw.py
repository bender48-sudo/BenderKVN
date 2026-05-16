with open("/opt/remna-shop/src/shop_bot/bot/keyboards.py") as f:
    lines = f.readlines()

for i in [17, 19, 53]:
    if i < len(lines):
        print(f"Line {i+1}: {repr(lines[i][:120])}")
