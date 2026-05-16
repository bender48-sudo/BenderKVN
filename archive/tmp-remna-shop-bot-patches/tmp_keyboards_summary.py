import re

with open("/opt/remna-shop/src/shop_bot/bot/keyboards.py") as f:
    content = f.read()

lines = content.split("\n")
in_function = None
current_func = []

for line in lines:
    m = re.match(r"^def (\w+)\(", line)
    if m:
        if in_function and current_func:
            print(f"--- {in_function} ---")
            for l in current_func:
                print(l)
            print()
        in_function = m.group(1)
        current_func = [line]
    elif in_function:
        if line.startswith(" ") or line.strip() == "":
            current_func.append(line)
        else:
            print(f"--- {in_function} ---")
            for l in current_func:
                print(l)
            print()
            in_function = None
            current_func = []

if in_function and current_func:
    print(f"--- {in_function} ---")
    for l in current_func:
        print(l)
