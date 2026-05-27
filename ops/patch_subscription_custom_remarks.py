#!/usr/bin/env python3
"""Fix subscription-page UI labels (customRemarks) showing as ?????.

Panel stores customRemarks with literal '?' where UTF-8 symbols (→, ⌛, 🚧)
were lost. subscription-page renders these strings when isShowCustomRemarks=true.

Uses plain Russian + ASCII punctuation (same policy as patch_happ_announce.py).

Usage:
    python ops/patch_subscription_custom_remarks.py
    python ops/patch_subscription_custom_remarks.py --apply
"""
from __future__ import annotations

import argparse
import copy
import io
import json
import sys
import time
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from panel_client import PanelClient  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / ".secrets" / "snapshots"

# Remnawave schema (backend CustomRemarksSchema); no emoji / guillemets.
TARGET_CUSTOM_REMARKS = {
    "emptyHosts": [
        "BenderVPN",
        "Обновите подписку в приложении (кнопка обновления)",
        "Сервер выбирается автоматически — вручную переключать не нужно",
        "Поддержка: t.me/Bender_KVN_bot",
    ],
    "emptyInternalSquads": [
        "BenderVPN",
        "Нет назначенного squad - напишите в поддержку",
        "t.me/Bender_KVN_bot",
    ],
    "expiredUsers": [
        "Подписка истекла",
        "Напишите в поддержку: t.me/Bender_KVN_bot",
    ],
    "limitedUsers": [
        "Подписка ограничена",
        "Напишите в поддержку: t.me/Bender_KVN_bot",
    ],
    "disabledUsers": [
        "Подписка отключена",
        "Напишите в поддержку: t.me/Bender_KVN_bot",
    ],
    "HWIDNotSupported": [
        "Это приложение не поддерживается",
        "Используйте Happ, Clash или v2rayN",
    ],
    "HWIDMaxDevicesExceeded": [
        "Достигнут лимит устройств",
        "Отключите лишнее устройство или напишите в поддержку",
    ],
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    c = PanelClient()
    settings = c.get_or_raise("/api/subscription-settings")["response"]
    before = settings.get("customRemarks") or {}
    print("current customRemarks:")
    print(json.dumps(before, ensure_ascii=False, indent=2))
    print("\ntarget customRemarks:")
    print(json.dumps(TARGET_CUSTOM_REMARKS, ensure_ascii=False, indent=2))

    if before == TARGET_CUSTOM_REMARKS:
        print("OK: already patched")
        return 0

    if not args.apply:
        print("dry-run: pass --apply to PATCH subscription-settings")
        return 0

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    snap = SNAPSHOT_DIR / f"subscription-settings-before-custom-remarks-{ts}.json"
    snap.write_text(
        json.dumps({"response": settings}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"snapshot: {snap}")

    payload = copy.deepcopy(settings)
    payload["customRemarks"] = TARGET_CUSTOM_REMARKS
    code, body = c.patch("/api/subscription-settings", body=payload)
    if code not in (200, 201):
        raise SystemExit(f"PATCH failed HTTP {code}: {body!s}"[:500])
    after = c.get_or_raise("/api/subscription-settings")["response"].get("customRemarks") or {}
    for key, want in TARGET_CUSTOM_REMARKS.items():
        if key == "emptyInternalSquads":
            continue  # panel may omit if unused
        got = after.get(key)
        if got != want:
            raise SystemExit(
                f"verify failed {key}: {json.dumps(got, ensure_ascii=False)[:200]}"
            )
    if "?" in json.dumps(after, ensure_ascii=False):
        raise SystemExit("verify failed: customRemarks still contain '?'")
    print("OK: customRemarks patched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
