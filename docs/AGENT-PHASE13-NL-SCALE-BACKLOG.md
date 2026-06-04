# Фаза 13 — NL полноценная нода · 3-я prod · отказоустойчивость

**Контекст:** обсуждение 2026-06-04 — симметрия LV/NL, рост 300→10k, 3-я нода.  
**Roadmap:** `docs/CAPACITY-AND-FAILOVER-ROADMAP.md`  
**Очередь:** `docs/BACKLOG-QUEUE.md` (Q174–181).

---

## Verify gate (после каждого Q с PATCH шаблона)

```bash
python ops/vpn_verify_gate.py          # или на LV: python3 /opt/scripts/vpn_verify_gate.py
python ops/nl_node_health_probe.py
python ops/nl_reachability_probe_ru.py
```

Перед `--apply` на template: snapshot в `.secrets/snapshots/`.

---

## Задачи

| Q | ID | P | Done when | Verify |
|---|-----|---|-----------|--------|
| 174 | **VPN-AUD-271** | P1 | `nl_node_health_probe.py` в репо; panel+RU probe; опц. SSH NL | **NL_NODE_HEALTH_OK** |
| 175 | **VPN-AUD-272** | P1 | `happ_geosite_guard` + полный gate на LV (`deploy_lv_vpn_ops.ps1`) | **VPN_VERIFY_GATE_OK** на LV (оба шага) |
| 176 | **VPN-AUD-273** | P2 | Legacy RELAY→NL :9443 hosts `isDisabled=true` в панели | **RELAY_NL_LEGACY_DISABLE_OK** |
| 177 | **VPN-AUD-274** | P2 | BBR/fq на **bvpn-nl** (SSH с LV или alias) | **BBR_AUDIT_OK** включает NL |
| 178 | **VPN-AUD-275** | P1 | Runbook + 6× relay-NL :443 hosts (hidden); **RELAY_NL_443_POC_OK** | inject unchanged; staging only |
| 179 | **VPN-AUD-276** | P1 | **3-я prod-нода:** runbook чеклист в `docs/THIRD-PROD-NODE-ONBOARDING.md` | doc review |
| 180 | **VPN-AUD-277** | P2 | `audit_bbr_congestion` + `nl_node_health` в `deploy_lv_vpn_ops.ps1` | deploy smoke |
| 181 | **VPN-AUD-278** | P1 | Док §12 + `CAPACITY-AND-FAILOVER-ROADMAP` синхрон с очередью | — |

**Владелец (не Q):**

| ID | Задача |
|----|--------|
| **O-VPN-009** | IP + SSH **3-й VPS** (другой DC/AS) → агент `deploy-node.sh` |
| **O-VPN-002** | Smoke телефон РФ после симметрии NL |

---

## NO-GO

1. Вернуть **RELAY→NL :9443** в injectHosts без probe.  
2. NL в **Intl_Stealth** (TG/IG) без staging A/B.  
3. `Super_Balancer` selector `["proxy"]` на все hosts.  
4. `--apply` NL-only failover при живом LV.

---

## Commit (примеры)

| Q | Commit |
|---|--------|
| 174 | `ops: VPN-AUD-271 — NL node health probe` |
| 175 | `ops: VPN-AUD-272 — deploy LV gate scripts` |
| 176 | `ops: VPN-AUD-273 — disable relay-NL legacy hosts` |

**Правило:** один Q → verify → commit → стоп (если не просили «продолжай очередь»).
