# Digest pins (P2-OPS-IMAGE-PIN-01)

Immutable image references for supply-chain stability. Prod digests captured **2026-05-16** from AMS/LV.

| Component | Image reference | Where |
|-----------|-----------------|--------|
| **Postgres** | `postgres:17.6@sha256:00bc86618629af00d2937fdc5a5d63db3ff8450acf52f0636ec813c7f4902929` | `compose/ams/remnawave/docker-compose.yml.tmpl` |
| **Valkey** | `valkey/valkey:8.1-alpine@sha256:b027235326507cfdade9b6684056ec1d0b0c0757412e628245129b5d7b788618` | same |
| **AdGuard** | `adguard/adguardhome:latest@sha256:7fbf01d73ecb7a32d2d9e6cef8bf88e64bd787889ca80a1e8bce30cd4c084442` | `compose/ams/adguard/`, `compose/lv/adguard/` |
| **Caddy (host)** | **v2.11.2** + `mholt/caddy-ratelimit` | **не** в compose; **`ops/lv-install-caddy-ratelimit.sh`** |

Already pinned (P0-OPS-02): `remnawave/backend`, `subscription-page`, `remnanode` — см. compose `remnanode` / `remnawave-sub`.

**Verify:** `python ops/check_compose_image_pins.py`

**Обновление digest:** на целевом хосте `docker pull <image>` → `docker images --digests`, затем правка tmpl + safe-deploy.
