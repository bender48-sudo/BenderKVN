#!/usr/bin/env python3
"""P1-PRO-RU-BYPASS-01: расширить routing.rules в subscription template
   так, чтобы RU-приложения шли в обход VPN (outboundTag=direct).

Регресс 2026-05 (iOS Streisand / Happ): если из block-rule убрать все домены,
в JSON остаётся ``"domain": []`` + ``outboundTag`` — ядро Xray падает с
``app/router: this rule has no effective fields``.
Патч: при пустом block-rule правило удаляется целиком; см. также
``--strip-degenerate-only`` для hotfix уже сломанных шаблонов.

Что есть СЕЙЧАС в templateJson.routing.rules (`panel-20260515_112116.json`):

  R0  domain=[oneme.ru, max.ru]                        → block  ⚠ MAX-мессенджер VK
  R1  protocol=[bittorrent, utp]                       → block
  R2  ip=[geoip:private]                               → direct
  R3  domain=[avito.st, geosite:category-ru,
              regexp:.*\\.ru$, regexp:.*\\.xn--p1ai$,
              regexp:.*\\.xn--p1acf$, regexp:.*\\.xn--p1ag$]
                                                       → direct
  R4  ip=[geoip:ru]                                    → direct
  R5  network=tcp,udp                                  → balancer:Super_Balancer (VPN)

То есть `.ru`, `.рф`, `.рус`, `.орг.рус` и IP в РФ уже идут direct.
НЕ покрыто (но нужно):
  - max.ru / oneme.ru — заблокированы (а нужны direct, юзер просит MAX)
  - vk.com, vk.me, vkuservideo.com, vkuser.net, userapi.com — VK на .com
  - yandex.com, yandex.net, yastatic.net — Яндекс CDN
  - mts.com, megafon.com, beeline.com — мобильные на .com
  - sber.com, sberbank.com, tinkoff.com, tbank.com, vtb.com — банки на .com
  - avito.com — Авито на .com
  - ozon.com, wildberries.eu — маркетплейсы
  - sbermegamarket.com — Сбер Маркет
  - mybridge.ru — MAX messenger

Что делаем:
  1) Из R0 (block) **удаляем** max.ru и oneme.ru.
  2) В R3 (direct, тот что с geosite:category-ru) **добавляем** EXTRA_DOMAINS.
  3) PATCH /api/subscription-templates с минимальным телом, как в freeze_ams_node.py.
  4) GET-back verify: routing.rules[0].domain не содержит max.ru/oneme.ru;
     routing.rules[3].domain содержит EXTRA_DOMAINS.
  5) Snapshot templateJson сохраняется в .secrets/snapshots/
     перед каждым изменением.

Запуск:
    python ops/ru_bypass_routing.py            # dry-run
    python ops/ru_bypass_routing.py --apply    # реально применить
    python ops/ru_bypass_routing.py --strip-degenerate-only        # сколько правил удалим
    python ops/ru_bypass_routing.py --strip-degenerate-only --apply
                                                # только hotfix без RU-байпас-логики
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from panel_client import PanelClient  # type: ignore

import site_urls  # noqa: E402

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))
from subscription_config_notify import after_template_patch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / ".secrets" / "snapshots"
DEFAULT_TEMPLATE_UUID = site_urls.REMNA_TEMPLATE_UUID

# Xray (incl. iOS/Streisand) rejects routing rules like { "domain": [], "outboundTag": "block" }
# with: app/router: this rule has no effective fields
MATCHER_FIELDS = (
    "domain",
    "domains",
    "ip",
    "port",
    "sourcePort",
    "network",
    "inboundTag",
    "protocol",
    "user",
    "sourceGeoip",
)


def _nonempty_container(v: object) -> bool:
    if v is None:
        return False
    if isinstance(v, (list, tuple, dict, set)):
        return len(v) > 0
    if isinstance(v, str):
        return len(v.strip()) > 0
    return True


def routing_rule_has_matchers(rule: dict) -> bool:
    """True if rule has any supported matching condition (Xray 'field' rule)."""
    return any(_nonempty_container(rule.get(k)) for k in MATCHER_FIELDS)


def strip_degenerate_routing_rules(rules: list[dict]) -> int:
    """Remove rules that route to outbound/balancer but have no matchers (e.g. domain: []).

    Returns how many rules were dropped. Mutates ``rules`` in place.
    """
    removed = 0
    for i in range(len(rules) - 1, -1, -1):
        r = rules[i]
        if (r.get("outboundTag") or r.get("balancerTag")) and not routing_rule_has_matchers(
            r
        ):
            rules.pop(i)
            removed += 1
    return removed

# Домены, которые НЕ покрыты regexp `\.ru$|\.рф$` и должны идти direct.
EXTRA_DIRECT_DOMAINS = [
    # MAX-мессенджер VK (если --unblock-max, добавятся отсюда И из R0)
    "max.ru",
    "oneme.ru",
    "mybridge.ru",

    # VK (соцсеть + CDN, .com / .net не покрыты regexp)
    "vk.com",
    "vk.me",
    "vk.link",
    "vkuservideo.com",
    "vkuservideo.net",
    "vkuser.net",
    "userapi.com",
    "vkontakte.com",

    # Яндекс на .com / .net
    "yandex.com",
    "yandex.net",
    "yandexcloud.net",
    "yastatic.net",
    "ya.com",

    # Мобильные операторы на .com
    "mts.com",
    "megafon.com",
    "beeline.com",
    "tele2.com",

    # Банки на .com / .online
    "sber.com",
    "sberbank.com",
    "sberbank.online",
    "sbermegamarket.com",
    "tinkoff.com",
    "tbank.com",
    "vtb.com",
    "alfabank.com",
    "raiffeisen.com",

    # Маркетплейсы / e-commerce на .com / .eu
    "avito.com",
    "ozon.com",
    "wildberries.eu",
    "aliexpressru.com",

    # Госуслуги / Почта России (на не-.ru если есть)
    "gosuslugi.com",
    "pochta.com",
]


def get_template(c: PanelClient, template_uuid: str) -> dict:
    return c.get_or_raise(f"/api/subscription-templates/{template_uuid}")["response"]


def find_rule(rules: list[dict], match_fn) -> tuple[int, dict | None]:
    for i, r in enumerate(rules):
        if match_fn(r):
            return i, r
    return -1, None


def plan_changes(rules: list[dict], unblock_max: bool):
    """Return (block_rule_idx, direct_rule_idx, current_block_domains,
               domains_to_remove_from_block, current_direct_domains,
               domains_to_add_to_direct)."""
    # R0: block-rule, должен содержать "max.ru" или "oneme.ru"
    block_idx, block_rule = find_rule(
        rules,
        lambda r: r.get("outboundTag") == "block"
        and any(d in (r.get("domain") or []) for d in ("max.ru", "oneme.ru")),
    )
    # R3: direct-rule с geosite:category-ru
    direct_idx, direct_rule = find_rule(
        rules,
        lambda r: r.get("outboundTag") == "direct"
        and "geosite:category-ru" in (r.get("domain") or []),
    )

    block_doms = (block_rule or {}).get("domain", []) if block_rule else []
    direct_doms = (direct_rule or {}).get("domain", []) if direct_rule else []

    will_unblock = []
    if unblock_max and block_rule:
        will_unblock = [d for d in ("max.ru", "oneme.ru") if d in block_doms]

    will_add_direct = [d for d in EXTRA_DIRECT_DOMAINS if d not in direct_doms]

    return {
        "block_idx": block_idx,
        "direct_idx": direct_idx,
        "block_doms": block_doms,
        "will_unblock": will_unblock,
        "direct_doms": direct_doms,
        "will_add_direct": will_add_direct,
    }


def apply_changes(rules: list[dict], plan: dict) -> None:
    """In-place modify rules according to plan.

    Direct-rule updates are applied **before** popping an emptied block-rule so
    list indices stay valid.  After edits, strip any degenerate rules (e.g.
    ``domain: []`` with ``outboundTag``) that crash Xray on iOS.
    """
    if plan["will_add_direct"]:
        di = plan["direct_idx"]
        rules[di]["domain"] = list(rules[di].get("domain", [])) + plan["will_add_direct"]

    if plan["will_unblock"]:
        bi = plan["block_idx"]
        new_dom = [d for d in rules[bi].get("domain", []) if d not in plan["will_unblock"]]
        if new_dom:
            rules[bi]["domain"] = new_dom
        else:
            rules.pop(bi)

    strip_degenerate_routing_rules(rules)


def patch_template(c: PanelClient, tpl: dict, template_uuid: str) -> None:
    minimal = {
        "uuid": tpl.get("uuid") or template_uuid,
        "templateJson": tpl["templateJson"],
        "viewPosition": tpl.get("viewPosition"),
        "templateType": tpl.get("templateType"),
    }
    code, body = c.patch("/api/subscription-templates", body=minimal)
    if code not in (200, 201, 204):
        sys.exit(f"PATCH template HTTP {code}: {str(body)[:500]}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--template-uuid", default=DEFAULT_TEMPLATE_UUID)
    ap.add_argument("--apply", action="store_true",
                    help="actually mutate (default: dry-run)")
    ap.add_argument("--no-unblock-max", action="store_true",
                    help="не вынимать max.ru/oneme.ru из block-rule")
    ap.add_argument(
        "--strip-degenerate-only",
        action="store_true",
        help="только удалить routing rules без матчеров (экстренный hotfix для Xray iOS)",
    )
    ap.add_argument(
        "--no-sub-notify",
        action="store_true",
        help="не bump sub_config_generation / не пушить уведомление в бот",
    )
    args = ap.parse_args()

    unblock_max = not args.no_unblock_max

    c = PanelClient()
    tpl = get_template(c, args.template_uuid)
    rules = tpl["templateJson"]["routing"]["rules"]

    if args.strip_degenerate_only:
        dup = json.loads(json.dumps(rules))
        n = strip_degenerate_routing_rules(dup)
        if n == 0:
            print("nothing to do — template already clean")
            return
        if not args.apply:
            print(f"[strip-degenerate-only] would remove {n} broken routing rule(s)")
            print("Dry-run only. Apply with:")
            print("  python ops/ru_bypass_routing.py --strip-degenerate-only --apply")
            return
        print(f"[strip-degenerate-only] removing {n} broken routing rule(s) on panel")
        ts = time.strftime("%Y%m%d_%H%M%S")
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        backup_path = SNAPSHOT_DIR / f"template-before-strip-degenerate-{ts}.json"
        backup_path.write_text(
            json.dumps({"response": tpl}, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"[backup] {backup_path}")
        n_live = strip_degenerate_routing_rules(rules)
        if n_live != n:
            print(f"WARN: live strip removed {n_live} vs dry-run {n}")
        patch_template(c, tpl, args.template_uuid)
        print("[patch] OK")
        if not args.no_sub_notify:
            try:
                after_template_patch("ru_bypass_strip_degenerate")
            except Exception as exc:
                print(f"[sub-config] WARN: {exc}")
        return

    print(f"current routing rules: {len(rules)}")
    for i, r in enumerate(rules):
        sig = []
        if r.get("domain"):
            sig.append(f"domain={len(r['domain'])}")
        if r.get("ip"):
            sig.append(f"ip={len(r['ip'])}")
        if r.get("protocol"):
            sig.append(f"protocol={r['protocol']}")
        if r.get("network"):
            sig.append(f"network={r['network']}")
        if r.get("balancerTag"):
            sig.append(f"balancer={r['balancerTag']}")
        if r.get("outboundTag"):
            sig.append(f"->{r['outboundTag']}")
        print(f"  R{i}: " + " ".join(sig))

    plan = plan_changes(rules, unblock_max)

    if plan["block_idx"] < 0 and unblock_max:
        sys.exit("FATAL: не нашёл block-rule с max.ru/oneme.ru — структура отличается, прерываюсь.")
    if plan["direct_idx"] < 0:
        sys.exit("FATAL: не нашёл direct-rule с geosite:category-ru — структура отличается, прерываюсь.")

    print()
    if unblock_max:
        print(f"BLOCK rule R{plan['block_idx']} now: {plan['block_doms']}")
        if plan["will_unblock"]:
            print(f"  -> REMOVE from block: {plan['will_unblock']}")
        else:
            print("  -> nothing to unblock (max.ru/oneme.ru already not in block)")
    else:
        print("[--no-unblock-max] block-rule kept as-is")

    print()
    print(f"DIRECT rule R{plan['direct_idx']} now ({len(plan['direct_doms'])} entries): "
          f"{plan['direct_doms']}")
    print(f"  -> ADD to direct ({len(plan['will_add_direct'])}): {plan['will_add_direct']}")

    if not plan["will_unblock"] and not plan["will_add_direct"]:
        print("\nnothing to change — bye.")
        return

    if not args.apply:
        print("\n[dry-run] re-run with --apply to mutate.")
        return

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    backup_path = SNAPSHOT_DIR / f"template-before-ru-bypass-{ts}.json"
    backup_path.write_text(
        json.dumps({"response": tpl}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n[backup] template -> {backup_path}")

    apply_changes(rules, plan)
    patch_template(c, tpl, args.template_uuid)
    print("[patch] OK")

    # Verify
    re_tpl = get_template(c, args.template_uuid)
    re_rules = re_tpl["templateJson"]["routing"]["rules"]
    re_plan = plan_changes(re_rules, unblock_max)
    fail = []
    if re_plan["will_unblock"]:
        fail.append(f"block still has: {re_plan['will_unblock']}")
    if re_plan["will_add_direct"]:
        fail.append(f"direct still missing: {re_plan['will_add_direct']}")
    if fail:
        print("[verify] FAILED:", "; ".join(fail))
        sys.exit(2)
    print("[verify] re-fetch OK: block clean, direct contains all extras")

    degenerate = sum(
        1
        for r in re_rules
        if (r.get("outboundTag") or r.get("balancerTag"))
        and not routing_rule_has_matchers(r)
    )
    print(f"degenerate routing rules (must be 0): {degenerate}")
    if degenerate:
        print("WARN: template still has empty rules — run --strip-degenerate-only --apply")
    new_direct = re_rules[plan["direct_idx"]].get("domain", [])
    print(f"direct-domain count after: {len(new_direct)}")
    if not args.no_sub_notify:
        try:
            after_template_patch("ru_bypass_routing")
        except Exception as exc:
            print(f"[sub-config] WARN: {exc}")
    print("\nDONE")


if __name__ == "__main__":
    main()
