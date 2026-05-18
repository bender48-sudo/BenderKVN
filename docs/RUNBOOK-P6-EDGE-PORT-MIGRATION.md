# Runbook: публичный edge **2053 → 8443** (P2-RED-EDGE-PORT-01)

**Зачем:** убрать сигнатуру дефолтного порта 3X-UI; канонические URL в репо → **`:8443`**.  
**Grace:** **7–14 дней** — **`:2053`** и **`:8443`** параллельно; затем редирект или отключение **2053** (владелец).

## Репозиторий (готово в Q051)

- `ops/site_urls.py`, `ops/site.env.example` — defaults **8443**
- `Caddyfile-latvia-full.txt` — блоки **`p4n7q:8443`**, **`k9x2m1:8443`**
- `compose/ams/remnawave/panel.env.tmpl`, `bot_src/config.py`, `bot_src/portal_links.py`

## LV (bvpn-lv)

```bash
# На хосте root
bash ops/patch-caddy-edge-port-8443-lv.sh
ufw allow 8443/tcp comment 'BenderVPN edge HTTPS' || true
```

Проверка:

```bash
curl -fsSI https://k9x2m1.conntest.xyz:8443/portal/ | head -1
curl -fsSI "https://p4n7q.conntest.xyz:8443/${SUB_MONITOR_PROBE_SUFFIX}" | head -1
python ops/smoke_sub_edge_port.py
```

## AMS panel env

После правки `panel.env.tmpl` на сервере — `FRONT_END_DOMAIN` / `SUB_PUBLIC_DOMAIN` с **:8443**, recreate backend при необходимости (см. `RUNBOOK-AMS-SAFE-DEPLOY.md`).

## Владелец (ручное)

- [ ] **BotFather** — Menu Button / Web App URL → `https://k9x2m1.conntest.xyz:8443/portal/`
- [ ] Сообщение пользователям: «обновите подписку / ссылку» (старый **2053** ещё работает в grace)
- [ ] Через 7–14 дней: редирект **2053→8443** в Caddy или закрыть **2053** в firewall

## Smoke

`SUB_EDGE_PORT_OK` — `ops/smoke_sub_edge_port.py` (repo defaults + optional live curl).

## Откат

Восстановить `Caddyfile` из backup `Caddyfile.bak-pre-edge-8443-*`; вернуть `PANEL_URL` / `site.env` на **2053**.
