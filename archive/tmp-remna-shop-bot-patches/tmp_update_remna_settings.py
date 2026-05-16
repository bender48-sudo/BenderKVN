import json
import subprocess
import os

TOKEN = os.popen('grep "^PANEL_TOKEN=" /etc/bvpn/balancer.env | cut -d= -f2- | tr -d \'"\' | tr -d "\\n"').read().strip()
BASE = "https://k9x2m1.conntest.xyz:2053/api/subscription-settings"

# GET current
result = subprocess.run(
    ["curl", "-sk", "-H", f"Authorization: Bearer {TOKEN}", BASE],
    capture_output=True, text=True
)
data = json.loads(result.stdout)
settings = data.get("response", data)

print("BEFORE:")
print(f"  profileTitle: {settings.get('profileTitle')}")
print(f"  supportLink: {settings.get('supportLink')}")
print(f"  happAnnounce: {settings.get('happAnnounce')}")

# Modify 3 fields
settings["profileTitle"] = "BenderVPN"
settings["supportLink"] = "https://t.me/Bender_KVN_bot"
settings["happAnnounce"] = "Нажмите «Подключить» — лучший сервер выберется автоматически"

# Try PUT
payload = json.dumps(settings, ensure_ascii=False)
result2 = subprocess.run(
    ["curl", "-sk", "-X", "PUT", "-H", f"Authorization: Bearer {TOKEN}",
     "-H", "Content-Type: application/json", "--data", payload, BASE],
    capture_output=True, text=True
)
print(f"\nPUT status: HTTP {result2.returncode}")
resp = json.loads(result2.stdout) if result2.stdout else {}
updated = resp.get("response", resp)

if "profileTitle" in str(updated):
    print("\nAFTER:")
    print(f"  profileTitle: {updated.get('profileTitle')}")
    print(f"  supportLink: {updated.get('supportLink')}")
    print(f"  happAnnounce: {updated.get('happAnnounce')}")
else:
    print(f"\nRaw response: {result2.stdout[:500]}")
    # Try PATCH as fallback
    print("\nTrying PATCH instead...")
    for key, val in [("profileTitle", "BenderVPN"), ("supportLink", "https://t.me/Bender_KVN_bot"), ("happAnnounce", "Нажмите «Подключить» — лучший сервер выберется автоматически")]:
        r = subprocess.run(
            ["curl", "-sk", "-X", "PATCH", "-H", f"Authorization: Bearer {TOKEN}",
             "-H", "Content-Type: application/json", "--data", json.dumps({key: val}, ensure_ascii=False), BASE],
            capture_output=True, text=True
        )
        print(f"  PATCH {key}: {r.stdout[:100]}")
