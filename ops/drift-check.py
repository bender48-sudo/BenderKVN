#!/usr/bin/env python3
"""Walk through every (repo, prod) pair and md5-diff.

Optimised to use ONE ssh connection per host (avoids LV sshd rate-limit).

Two kinds of pairs:
  - "file"   — bash/python script in repo root or ops/, compared as-is.
  - "tmpl"   — sanitized template in compose/; see PAIRS tmpl_only_keys and
               docs/DEPLOY.md §7.
"""
import hashlib
import re
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ops"))

# Readable progress when stdout is fully buffered (pipes / agents).
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass

import render_compose  # type: ignore  # noqa: E402  # uses load_vault + render_file


def md5_hex_norm(blob: bytes) -> str:
    """Prod is LF; workspace copies or editors may use CRLF."""
    blob = blob.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.md5(blob).hexdigest()


# Sanitize rules MUST stay in sync with .secrets/sanitize-compose.py.
# Drift-check uses them to derive a "what would the template look like
# rendered with vault values" version of the prod file: actually,
# the other direction — we render the template via render_compose +
# vault and compare to prod md5.  These rules are kept here only as
# a sanity check and could be removed if sanitize-compose.py is invoked
# in-process; we keep a copy to keep drift-check.py standalone.
SANITIZE_RULES_REF = [
    r'(SECRET_KEY=)("?eyJ[A-Za-z0-9+/=_\\-]+"?)',
    r'(JWT_AUTH_SECRET=)([a-f0-9]{32,})',
    r'(JWT_API_TOKENS_SECRET=)([a-f0-9]{32,})',
    r'(DATABASE_URL=)"?postgresql://([^:@]+):([^@/]+)@([^"\s]+)"?',
    r'(POSTGRES_PASSWORD=)([^\s"]+)',
    r'((?:REMNA_API_TOKEN|REMNAWAVE_API_TOKEN|PANEL_TOKEN)=)("?eyJ[A-Za-z0-9._\\-]+"?)',
    r'((?:TELEGRAM_BOT_TOKEN|BOT_TOKEN)=)("?[0-9]{6,}:[A-Za-z0-9_\\-]+"?)',
    r'(METRICS_PASS=)([a-f0-9A-F]{16,})',
    r'(WEBHOOK_SECRET_HEADER=)([A-Za-z0-9._\\-]{16,})',
    r'(CLOUDFLARE_TOKEN=)([A-Za-z0-9._\\-]{8,})',
    r'^\s*[0-9]{6,}:[A-Za-z0-9_\-]{20,}\s*$',
]
_ = re  # keep import in case future work needs it

# (kind, repo-path, host-alias, remote-path, tmpl_only_keys)
# tmpl_only_keys:
#   None  = expand every ${KEY} that exists in vault (typical .env)
#   frozenset() = expand nothing (compose files that are already prod-shaped)
#   frozenset({'X'}) = expand only listed keys (YAML with a single secret)
PAIRS: list[tuple[str, str, str, str, frozenset[str] | None]] = [
    # scripts
    ("file", "monitor.sh",                     "bvpn-lv",  "/opt/scripts/monitor.sh", None),
    ("file", "daily-report.sh",                "bvpn-lv",  "/opt/scripts/daily-report.sh", None),
    ("file", "ops/count_users_with_ams_sub.py","bvpn-lv",  "/opt/scripts/count_users_with_ams_sub.py", None),
    ("file", "balancer.sh",                    "bvpn-lv",  "/opt/scripts/balancer.sh", None),
    ("file", "backup-remnawave.sh",            "bvpn-lv",  "/opt/scripts/backup-remnawave.sh", None),
    ("file", "ru-monitor.py",                  "bvpn-lv",  "/opt/scripts/ru-monitor.py", None),
    ("file", "selfsteal-monitor.py",           "bvpn-lv",  "/opt/scripts/selfsteal-monitor.py", None),
    ("file", "deploy-node.sh",                 "bvpn-lv",  "/opt/scripts/deploy-node.sh", None),
    ("file", "deploy-node.sh",                 "bvpn-ams", "/opt/scripts/deploy-node.sh", None),
    ("file", "ops/bvpn-watchdog-probe.sh",     "bvpn-lv",  "/usr/local/sbin/bvpn-watchdog-probe", None),
    ("file", "ops/bvpn-docker-firewall.sh",    "bvpn-ams", "/usr/local/sbin/bvpn-docker-firewall.sh", None),
    ("file", "ops/watchdog.sh",                "bvpn-nl",  "/opt/scripts/watchdog.sh", None),

    # compose + env — see docs/SECRETS.md
    ("tmpl", "compose/lv/remnanode/docker-compose.yml.tmpl",          "bvpn-lv",  "/opt/remnanode/docker-compose.yml", frozenset()),
    ("tmpl", "compose/lv/remnanode/node.env.tmpl",                    "bvpn-lv",  "/opt/remnanode/.env",
     frozenset({"SECRET_KEY_NODE_LV"})),
    ("tmpl", "compose/lv/adguard/docker-compose.yml.tmpl",            "bvpn-lv",  "/opt/adguard/docker-compose.yml", frozenset()),
    ("tmpl", "compose/ams/remnanode/docker-compose.yml.tmpl",         "bvpn-ams", "/opt/remnanode/docker-compose.yml",
     frozenset()),
    ("tmpl", "compose/ams/remnanode/node.env.tmpl",                  "bvpn-ams", "/opt/remnanode/.env",
     frozenset({"SECRET_KEY_NODE_AMS"})),
    ("tmpl", "compose/ams/remnawave/docker-compose.yml.tmpl",           "bvpn-ams", "/opt/remnawave/docker-compose.yml", frozenset()),
    ("tmpl", "compose/ams/remnawave/panel.env.tmpl",                  "bvpn-ams", "/opt/remnawave/.env", None),
    ("tmpl", "compose/ams/remnawave-sub/docker-compose.yml.tmpl",     "bvpn-ams", "/opt/remnawave/sub/docker-compose.yml",
     frozenset({"REMNA_API_TOKEN"})),
    ("tmpl", "compose/ams/remna-shop/docker-compose.yml.tmpl",        "bvpn-ams", "/opt/remna-shop/docker-compose.yml", frozenset()),
    ("tmpl", "compose/ams/remna-shop/bot.env.tmpl",                   "bvpn-ams", "/opt/remna-shop/.env", None),
    ("tmpl", "compose/ams/adguard/docker-compose.yml.tmpl",           "bvpn-ams", "/opt/adguard/docker-compose.yml", frozenset()),
    ("tmpl", "compose/nl/remnanode/docker-compose.yml.tmpl",          "bvpn-nl",  "/opt/remnanode/docker-compose.yml",
     frozenset()),
    ("tmpl", "compose/nl/remnanode/node.env.tmpl",                    "bvpn-nl",  "/opt/remnanode/.env",
     frozenset({"SECRET_KEY_NODE_NL"})),
    ("tmpl", "compose/_shared/etc-bvpn-lv/balancer.env.tmpl",         "bvpn-lv",  "/etc/bvpn/balancer.env", None),
    ("tmpl", "compose/_shared/etc-bvpn-lv/ru-monitor.env.tmpl",       "bvpn-lv",  "/etc/bvpn/ru-monitor.env", None),
    ("tmpl", "compose/_shared/etc-bvpn-nl/bot-token.tmpl",            "bvpn-nl",  "/etc/bvpn/bot-token",
     frozenset({"BOT_TOKEN"})),
]


def md5_local_file(p: str) -> str:
    return md5_hex_norm(Path(p).read_bytes())


def md5_local_tmpl(p: str, vault: dict[str, str], missing: set[str],
                   only_substitute: frozenset[str] | None) -> str:
    rendered = render_compose.render_file(ROOT / p, vault, missing,
                                          only_substitute=only_substitute)
    return md5_hex_norm(rendered)


def md5_local(kind: str, p: str, vault, missing, only_substitute) -> str:
    if kind == "file":
        return md5_local_file(p)
    return md5_local_tmpl(p, vault, missing, only_substitute)


by_host: dict[str, list[str]] = defaultdict(list)
for _, _, host, path, _ in PAIRS:
    if path not in by_host[host]:
        by_host[host].append(path)

remote_md5: dict[tuple[str, str], str] = {}
for host, paths in by_host.items():
    # LV: rate-limit / latency — smaller chunks + longer idle between rounds.
    if host == "bvpn-lv":
        chunk_sz, run_timeout, nap_s = 3, 270, 1.25
    else:
        chunk_sz, run_timeout, nap_s = 4, 180, 0.0
    for i in range(0, len(paths), chunk_sz):
        if i > 0 and nap_s:
            time.sleep(nap_s)
        chunk = paths[i : i + chunk_sz]
        print(f"[drift-check] ssh {host} md5 ({len(chunk)} paths)…", flush=True)
        cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=40",
               "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=4", host,
               "md5sum " + " ".join(chunk) + " 2>&1 || true"]
        stdout_text = ""
        ok = False
        max_attempts = 4 if host == "bvpn-lv" else 2
        for attempt in range(max_attempts):
            extra = attempt * (45 if host == "bvpn-lv" else 30)
            try:
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=run_timeout + extra,
                )
                stdout_text = proc.stdout or ""
                ok = True
                break
            except subprocess.TimeoutExpired:
                print(
                    f"[drift-check] timeout ssh {host} chunk starting {chunk[0]!r} "
                    f"attempt {attempt + 1}/{max_attempts} (+{extra}s deadline)",
                    flush=True,
                )
                if attempt + 1 < max_attempts:
                    time.sleep(4.0 + attempt * 6.0)
        if not ok:
            for p in chunk:
                remote_md5[(host, p)] = "TIMEOUT"
            continue
        for line in stdout_text.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0] not in ("md5sum:",):
                remote_md5[(host, parts[1])] = parts[0]
        for p in chunk:
            remote_md5.setdefault((host, p), "MISSING")

# Vault is only needed when there are tmpl pairs.
vault: dict[str, str] = {}
missing_vault: set[str] = set()
if any(k == "tmpl" for k, *_ in PAIRS):
    vault = render_compose.load_vault()

results = []
for kind, repo, host, path, only_keys in PAIRS:
    try:
        local = md5_local(kind, repo, vault, missing_vault, only_keys)
    except FileNotFoundError:
        local = "MISSING"
    remote = remote_md5.get((host, path), "MISSING")
    if remote == local:
        status = "OK"
    elif remote in ("MISSING", "TIMEOUT"):
        status = remote
    else:
        status = "DRIFT"
    results.append((status, kind, repo, host, path, local, remote))

print(f"{'STATUS':8s}  {'KIND':4s}  {'REPO':50s}  {'HOST':10s}  {'PATH':40s}  {'REPO-MD5':10s} {'PROD-MD5':10s}")
print("-" * 145)
for status, kind, repo, host, path, l, r in results:
    print(f"{status:8s}  {kind:4s}  {repo:50s}  {host:10s}  {path:40s}  {l[:8]}     {r[:8]}")

bad = [r for r in results if r[0] != "OK"]
print()
print(f"Total: {len(results)}, OK: {len(results) - len(bad)}, problems: {len(bad)}")
if missing_vault:
    print(f"[note] vault missing values for: {sorted(missing_vault)}", file=sys.stderr)
sys.exit(0 if not bad else 1)
