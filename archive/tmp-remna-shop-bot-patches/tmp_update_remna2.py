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
uuid = settings["uuid"]

print(f"UUID: {uuid}")
print(f"BEFORE: profileTitle={settings['profileTitle']}, supportLink={settings['supportLink']}, happAnnounce={settings['happAnnounce']}")

# PATCH with uuid included
payload = {
    "uuid": uuid,
    "profileTitle": "BenderVPN",
    "supportLink": "https://t.me/Bender_KVN_bot",
    "happAnnounce": "\u041d\u0430\u0436\u043c\u0438\u0442\u0435 \u00ab\u041f\u043e\u0434\u043a\u043b\u044e\u0447\u0438\u0442\u044c\u00bb \u2014 \u043b\u0443\u0447\u0448\u0438\u0439 \u0441\u0435\u0440\u0432\u0435\u0440 \u0432\u044b\u0431\u0435\u0440\u0435\u0442\u0441\u044f \u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0438",
    "profileUpdateInterval": settings["profileUpdateInterval"],
    "serveJsonAtBaseSubscription": settings["serveJsonAtBaseSubscription"],
    "isProfileWebpageUrlEnabled": settings["isProfileWebpageUrlEnabled"],
    "isShowCustomRemarks": settings["isShowCustomRemarks"],
    "customRemarks": settings["customRemarks"],
    "customResponseHeaders": settings["customResponseHeaders"],
    "randomizeHosts": settings["randomizeHosts"],
    "responseRules": settings["responseRules"],
    "hwidSettings": settings["hwidSettings"],
}

if "happRouting" in settings:
    payload["happRouting"] = settings["happRouting"]

body = json.dumps(payload, ensure_ascii=False)
result2 = subprocess.run(
    ["curl", "-sk", "-X", "PATCH", "-H", f"Authorization: Bearer {TOKEN}",
     "-H", "Content-Type: application/json", "--data", body, BASE],
    capture_output=True, text=True
)

try:
    resp = json.loads(result2.stdout)
    updated = resp.get("response", resp)
    if "profileTitle" in updated:
        print(f"\nAFTER:")
        print(f"  profileTitle: {updated.get('profileTitle')}")
        print(f"  supportLink: {updated.get('supportLink')}")
        print(f"  happAnnounce: {updated.get('happAnnounce')}")
    else:
        print(f"\nResponse: {result2.stdout[:500]}")
except:
    print(f"\nRaw: {result2.stdout[:500]}")
