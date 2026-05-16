"""Read prod compose/env files from .secrets/prod-compose/, write sanitized
templates into compose/ in repo root.

Replacements are conservative — keep public values (METRICS_USER, NODE_PORT, etc.)
unchanged but replace anything secret-looking with ${PLACEHOLDER}.

⚠ Перезаписывает весь каталог compose/ только файлами из MAP.

Run from repo root:
  python ops/sanitize_compose_templates.py
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / ".secrets" / "prod-compose"
DST = ROOT / "compose"

# (pattern, replacement) — applied in order, each line at a time.
RULES = [
    (re.compile(r'(JWT_AUTH_SECRET=)([a-f0-9]{32,})'),
     r'\1${JWT_AUTH_SECRET}'),
    (re.compile(r'(JWT_API_TOKENS_SECRET=)([a-f0-9]{32,})'),
     r'\1${JWT_API_TOKENS_SECRET}'),
    (re.compile(r'(DATABASE_URL=)"?postgresql://([^:@]+):([^@/]+)@([^"\s]+)"?'),
     r'\1"postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@\4"'),
    (re.compile(r'(POSTGRES_PASSWORD=)([^\s"]+)'),
     r'\1${POSTGRES_PASSWORD}'),
    # REMNA API JWT — applied per-file in sanitize() as
    # ${REMNA_API_TOKEN_AMS} vs ${REMNA_API_TOKEN_LV}.
    (re.compile(r'((?:TELEGRAM_BOT_TOKEN|BOT_TOKEN)=)("?[0-9]{6,}:[A-Za-z0-9_\\-]+"?)'),
     r'\1${BOT_TOKEN}'),
    (re.compile(r'(METRICS_PASS=)([a-f0-9A-F]{16,})'),
     r'\1${METRICS_PASS}'),
    (re.compile(r'(WEBHOOK_SECRET_HEADER=)([A-Za-z0-9._\\-]{16,})'),
     r'\1${WEBHOOK_SECRET_HEADER}'),
    (re.compile(r'(CLOUDFLARE_TOKEN=)([A-Za-z0-9._\\-]{8,})'),
     r'\1${CLOUDFLARE_TOKEN}'),
    (re.compile(r'^\s*[0-9]{6,}:[A-Za-z0-9_\-]{20,}\s*$', re.MULTILINE),
     '${BOT_TOKEN}\n'),
]

LEAK_PATTERNS = [
    (re.compile(r'\beyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{10,}'),
     "JWT (token starting with eyJ.*.*.* )"),
    (re.compile(r'BEGIN (?:PRIVATE|RSA PRIVATE|EC PRIVATE) KEY'),
     "PEM private key marker"),
    (re.compile(r'\b[0-9]{6,}:[A-Za-z0-9_\-]{20,}\b'),
     "Telegram bot-token style number:secret"),
    (re.compile(r'(?<!sha256:)\b[a-f0-9]{64,}\b'),
     "Long hex blob (likely secret)"),
]


MAP = [
    ("lv/remnanode-compose.yml",     "lv", "remnanode",       "docker-compose.yml.tmpl"),
    ("lv/remnanode.env",             "lv", "remnanode",       "node.env.tmpl"),
    ("lv/adguard-compose.yml",       "lv", "adguard",         "docker-compose.yml.tmpl"),
    ("lv/remnawave-legacy-compose.yml", "_archive", "lv-remnawave-2026-04", "docker-compose.yml.tmpl"),
    ("lv/remnawave-legacy.env",         "_archive", "lv-remnawave-2026-04", "panel.env.tmpl"),
    ("ams/remnanode-compose.yml",    "ams", "remnanode",      "docker-compose.yml.tmpl"),
    ("ams/remnawave-compose.yml",    "ams", "remnawave",      "docker-compose.yml.tmpl"),
    ("ams/remnawave.env",            "ams", "remnawave",      "panel.env.tmpl"),
    ("ams/sub-compose.yml",          "ams", "remnawave-sub",  "docker-compose.yml.tmpl"),
    ("ams/remna-shop-compose.yml",   "ams", "remna-shop",     "docker-compose.yml.tmpl"),
    ("ams/remna-shop.env",           "ams", "remna-shop",     "bot.env.tmpl"),
    ("ams/adguard-compose.yml",      "ams", "adguard",        "docker-compose.yml.tmpl"),
    ("nl/remnanode-compose.yml",     "nl", "remnanode",       "docker-compose.yml.tmpl"),
    ("lv/etc-bvpn-balancer.env",      "_shared", "etc-bvpn-lv", "balancer.env.tmpl"),
    ("lv/etc-bvpn-ru-monitor.env",    "_shared", "etc-bvpn-lv", "ru-monitor.env.tmpl"),
    ("nl/etc-bvpn-bot-token.env",     "_shared", "etc-bvpn-nl", "bot-token.tmpl"),
]


def host_specific_rules(host: str) -> list:
    suffix = {"lv": "LV", "ams": "AMS", "nl": "NL"}.get(host)
    if not suffix:
        return []
    return [
        (re.compile(r'(SECRET_KEY=)("?eyJ[A-Za-z0-9+/=_\\-]+"?)'),
         rf'\1${{SECRET_KEY_NODE_{suffix}}}'),
    ]


def remna_var_for_rel(rel: str) -> str:
    if rel.startswith("lv/etc-bvpn"):
        return "REMNA_API_TOKEN_LV"
    if rel in ("ams/remna-shop.env", "ams/sub-compose.yml"):
        return "REMNA_API_TOKEN_AMS"
    if rel.startswith("lv/remnawave-legacy"):
        return "REMNA_API_TOKEN_LV"
    return "REMNA_API_TOKEN_AMS"


def sanitize(text: str, host: str, rel: str) -> tuple[str, list[str]]:
    rem = remna_var_for_rel(rel)
    remna_rules = [
        (re.compile(r'((?:REMNA_API_TOKEN|REMNAWAVE_API_TOKEN|PANEL_TOKEN)=)("?eyJ[A-Za-z0-9._\\-]+"?)'),
         rf'\1${{{rem}}}'),
    ]
    out_lines = []
    matches = []
    rules = host_specific_rules(host) + RULES + remna_rules
    for line in text.splitlines(keepends=True):
        new = line
        for pat, repl in rules:
            new2, n = pat.subn(repl, new)
            if n:
                matches.append(f"   • {pat.pattern[:60]}…")
                new = new2
        out_lines.append(new)
    return "".join(out_lines), matches


def main() -> None:
    if DST.exists():
        shutil.rmtree(DST)
    DST.mkdir()

    total_changes = 0
    leaks: list[tuple[Path, str, str]] = []
    for rel, host, svc, name in MAP:
        src = SRC / rel
        if not src.exists():
            print(f"SKIP {rel} (no src)")
            continue
        dst_dir = DST / host / svc
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / name

        raw = src.read_text(encoding="utf-8")
        out, matches = sanitize(raw, host, rel)
        for pat, label in LEAK_PATTERNS:
            for m in pat.finditer(out):
                snippet = m.group(0)[:40]
                leaks.append((dst, label, snippet))

        dst.write_text(out, encoding="utf-8")
        delta = len(raw) - len(out)
        print(f"{rel}  ->  compose/{host}/{svc}/{name}")
        print(f"    {len(matches)} substitution(s)  (size delta: {delta:+d})")
        for m in matches[:8]:
            print(m)
        total_changes += len(matches)

    print(f"\nTOTAL substitutions across all files: {total_changes}")

    if leaks:
        print(f"\n!!!  POTENTIAL LEAK in {len(leaks)} place(s)  !!!")
        for path, label, snippet in leaks:
            print(f"  {path.relative_to(ROOT)}  [{label}]  {snippet!r}")
        print("\nREMOVING compose/ — fix sanitize rules and re-run.")
        shutil.rmtree(DST)
        raise SystemExit(2)
    print("[leak-scan] clean — all templates are safe to commit.")


if __name__ == "__main__":
    main()
