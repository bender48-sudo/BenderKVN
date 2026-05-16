import re

with open("/opt/remna-shop/src/shop_bot/bot/handlers.py") as f:
    content = f.read()

lines = content.split("\n")
handlers = []
current = None

for i, line in enumerate(lines):
    m = re.match(r"^@user_router\.(callback_query|message|pre_checkout_query)\((.*)?\)", line.strip())
    if m:
        if current:
            handlers.append(current)
        current = {
            "line": i + 1,
            "decorator": line.strip(),
            "type": m.group(1),
            "filter": m.group(2) if m.group(2) else "",
            "handler_name": None,
            "first_actions": []
        }
        continue

    if current and current["handler_name"] is None:
        m2 = re.match(r"^async def (\w+)\(", line.strip())
        if m2:
            current["handler_name"] = m2.group(1)
            continue

    if current and current["handler_name"]:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and len(current["first_actions"]) < 8:
            current["first_actions"].append(line.rstrip())
        elif len(current["first_actions"]) >= 8:
            handlers.append(current)
            current = None

if current:
    handlers.append(current)

for h in handlers:
    print(f"--- L{h['line']}: {h['handler_name']}")
    print(f"    Filter: {h['filter']}")
    for a in h["first_actions"][:6]:
        print(f"    {a}")
    print()
