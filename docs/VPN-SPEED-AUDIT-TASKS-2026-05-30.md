# Задачи по скорости / аудиту (2026-05-30)

**Контекст:** stealth split (gen≥48), TG upload ~0.3–0.4 MB/s на relay-path — ожидаемо. BBR на relay#1 + LV уже **OK** (фикс не нужен).

**Verify сейчас:** `VPN_BALANCER_PROFILE_OK`, relay probe OK, autotrim на LV синхронизирован со stealth.

---

## Закрыто сегодня

| ID | Что | Статус |
|----|-----|--------|
| VPN-AUD-221 | Stealth split TG/Meta → Intl_Stealth | **DONE** (gen 48) |
| VPN-AUD-310-sync | LV `/opt/scripts` обновлён под stealth + autotrim | **DONE** |
| VPN-AUD-BBR-01 | `ops/audit_bbr_congestion.py` — relay#1 + LV bbr+fq | **DONE** (OK, правок sysctl не нужно) |
| VPN-AUD-DIAG-01 | `ops/diagnose_throughput.py` Phase 2 + stealth Phase 1 | **DONE** (в репо) |

---

## P1 — завтра / ближайшая сессия

| ID | Задача | Done when | Риск |
|----|--------|-----------|------|
| **VPN-AUD-110** | bufferSize 64→128 в template policy | **DONE** (prod bufferSize=128, audit 2026-05-30) |
| **VPN-AUD-430-staging** | Observatory **relay-only** + `leastPing` на Intl_Stealth; probe gstatic/204, не hicloud | staging A/B, нет closed pipe | средний |
| **VPN-AUD-BBR-02** | BBR audit relay#2 (`46.173.28.252`) с LV/bvpncheck | `BBR_AUDIT_OK` 3/3 nodes | низкий — SSH с ПК timeout |
| **VPN-AUD-103-owner** | Smoke владельца: refresh sub → TG/IG/speedtest 10 min | **PARTIAL 2026-06-02** — 2 relay лучше 1; не идеально | — |
| **VPN-AUD-310b** | autotrim синхронизирует **Intl_Stealth** при trim relay | deploy LV + gate | низкий |

---

## P2 — скорость без смены stealth

| ID | Задача | Источник |
|----|--------|----------|
| **VPN-AUD-230** | Split DNS DoH intl | **DONE 2026-06-02** — `patch_dns_split_config.py` live |
| **VPN-AUD-relay-tcpkeep** | `tcpKeepAliveIdle: 90` sockopt на relay inbound | Xray #5828 socket leak |
| **VPN-AUD-throughput-trim** | Autotrim по latency **+** marginal bw (не только TCP connect) | diagnose_throughput |
| **VPN-AUD-140** | Human remarks в injectHosts (не proxy-N) | UX backlog |

---

## P3 — продукт (если нужна скорость «как Amnezia»)

| ID | Задача | Комментарий |
|----|--------|-------------|
| **VPN-AUD-FAST-PROFILE** | Второй профиль 1-hop (AWG или VLESS direct NL) опционально | trade-off stealth vs speed |
| **VPN-AUD-320** | Fragment per-ISP | долгосрок TSPU |

---

## NO-GO (не повторять)

- NL в TG/Meta после stealth split
- observatory hicloud на прод без staging
- mux на Reality+TCP
- `relay_failover` → LV direct на gen≥47

---

## Утренний gate (5 мин)

```bash
python ops/verify_vpn_balancer_profile.py
python ops/probe_subscription.py
python ops/audit_bbr_congestion.py --ssh --ssh-alias bvpn-relay bvpn-lv
ssh bvpn-lv "bash /opt/scripts/run_latency_selector_autotrim.sh"   # no change expected
```

На LV: `tail -5 /var/log/bvpn-latency-autotrim.log` — должно быть `stealth split` + `[autotrim] no selector change`.

---

*Обновлено 2026-05-30 после BBR audit + LV script sync.*
