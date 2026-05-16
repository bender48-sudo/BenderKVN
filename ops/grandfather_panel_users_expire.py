#!/usr/bin/env python3
"""Разовое продление пользователям Remnawave, созданным до cut-off (`createdAt` в панели).

Зачем:
  После перехода на пробный период 90 дней для новых клиентов, текущую базу
  «праймим» до `expireAt` ≈ 2099. Пользователи с createdAt ≥ cut-off не трогаем
  (им бот уже выдаёт нужный TTL).

Examples:
  python ops/grandfather_panel_users_expire.py --dry-run
  python ops/grandfather_panel_users_expire.py --apply

Токен: как PanelClient (`.secrets/panel-token.txt` или `PANEL_TOKEN`).
До `--apply` обязательно `--dry-run` и проверка списка почт.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "ops"))

import site_urls  # noqa: F401 — site.env defaults
from panel_client import PanelClient, PanelError  # noqa: E402


def _parse_created(raw: object) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return datetime.fromtimestamp(raw / 1000.0, tz=timezone.utc)
    if isinstance(raw, str):
        s = raw.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(s)
        except ValueError:
            return None
    return None


def _iter_users(client: PanelClient) -> list[dict]:
    out: list[dict] = []
    size = 100
    start = 0
    while True:
        code, data = client.get(f"/api/users?size={size}&start={start}")
        if code != 200:
            raise PanelError(code, data)
        resp = data.get("response") if isinstance(data, dict) else {}
        items = resp.get("users") or []
        out.extend(items)
        if len(items) < size:
            break
        start += len(items)
    return out


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _patch_body(target_expire: str, u: dict) -> dict | None:
    uuid = u.get("uuid")
    email = u.get("email")
    if not uuid or not email:
        return None
    body: dict = {
        "uuid": uuid,
        "email": email,
        "expireAt": target_expire,
    }
    tid = u.get("telegramId")
    if tid is not None:
        body["telegramId"] = int(tid)
    if u.get("trafficLimitBytes") is not None:
        body["trafficLimitBytes"] = u["trafficLimitBytes"]
        body["trafficLimitStrategy"] = u.get("trafficLimitStrategy") or "MONTH"
    return body


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--cutoff",
        default=os.environ.get("GRANDFATHER_CUTOFF", "2026-05-16T00:00:00+03:00"),
        help="Legacy if panel createdAt < this (ISO8601). По умолчанию 16.05.2026 00:00 МСК.",
    )
    ap.add_argument(
        "--expire",
        default=os.environ.get("GRANDFATHER_EXPIRE", "2099-12-31T23:59:59Z"),
        help="Новое expireAt для legacy-пользователей.",
    )
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    cutoff_utc = _utc(datetime.fromisoformat(args.cutoff.replace("Z", "+00:00")))
    client = PanelClient()
    rows = _iter_users(client)
    patched: list[dict] = []
    skipped_new: list[object] = []
    skipped_no_created: list[object] = []

    for u in rows:
        created = _parse_created(u.get("createdAt"))
        if created is None:
            skipped_no_created.append(u.get("email") or u.get("uuid"))
            continue
        if _utc(created) >= cutoff_utc:
            skipped_new.append(u.get("email"))
            continue
        body = _patch_body(args.expire, u)
        if body:
            patched.append(body)

    print(json.dumps({"total_users": len(rows), "would_patch": len(patched)}, ensure_ascii=False, indent=2))
    print(f"# skipped (createdAt >= cutoff): {len(skipped_new)}")
    print(f"# skipped (no parsable createdAt): {len(skipped_no_created)}")

    if not args.apply:
        for b in patched[:20]:
            print("DRY_PATCH", b.get("email"), "->", b.get("expireAt"))
        if len(patched) > 20:
            print(f"... and {len(patched) - 20} more.")
        print("Dry-run OK. Repeat with --apply to PATCH.")
        return 0

    errors = 0
    for b in patched:
        try:
            client.patch_or_raise("/api/users", body=b)
            print("OK", b["email"])
        except PanelError as e:
            errors += 1
            print("FAIL", b.get("email"), e, file=sys.stderr)
    print(f"# done patched={len(patched) - errors} errors={errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
