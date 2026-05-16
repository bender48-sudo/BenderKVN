SCHEDULER = "/opt/remna-shop/src/shop_bot/data_manager/scheduler.py"

with open(SCHEDULER) as f:
    content = f.read()

# The expired text is a regular string, not f-string. Need to add f prefix.
# Find: "❌ Подписка BenderVPN закончилась
# It should be f"❌ ...
old = '                            "❌ Подписка BenderVPN'
new = '                            f"❌ Подписка BenderVPN'

c = content.count(old)
print(f"Found non-fstring expired text: {c}")
if c == 1:
    content = content.replace(old, new)
    print("Fixed: added f-prefix")

with open(SCHEDULER, 'w') as f:
    f.write(content)

import ast
try:
    ast.parse(content)
    print("syntax OK")
except SyntaxError as e:
    print(f"SYNTAX ERROR: {e}")
