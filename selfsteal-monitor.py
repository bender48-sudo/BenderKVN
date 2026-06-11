#!/usr/bin/env python3
"""BenderVPN Selfsteal Fingerprint Monitor — checks Caddy reverse_proxy on both nodes."""

import fcntl
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

# Strict DNS-label whitelist for SNIs that we pipe into a remote shell.
# Anything outside this set must be rejected before going near `bash -s`.
SNI_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9.-]{0,253}[A-Za-z0-9])?$")

# --- Constants ---
LOCK_FILE = "/tmp/bvpn-selfsteal-monitor.lock"
STATE_DIR = "/var/lib/bvpn-selfsteal-monitor"
STATE_FILE = os.path.join(STATE_DIR, "state.json")
LOG_FILE = "/var/log/bvpn-selfsteal-monitor.log"
# Persistent antispam dir (was /tmp/bvpn_states; moved 2026-05-14, same reason
# as monitor.sh / ru-monitor.py: /tmp got cleaned on reboot and recover msgs
# disappeared).
ANTISPAM_DIR = "/var/lib/bvpn-monitor"
_LEGACY_ANTISPAM_DIR = "/tmp/bvpn_states"
CURL_TIMEOUT = 8
SSH_TIMEOUT = 90
JITTER_MAX = 120
RETRY_DELAY = 0.5
RETRY_WARN_THRESHOLD = 5
# When curl returns 0 (timeout/refused), retry before alerting — same Caddy serves
# heavy panel traffic; brief contention is not necessarily "probe dead".
HTTP_ZERO_RETRIES = 3
HTTP_ZERO_BACKOFF_BASE = 1.0

# Anti-flap (aligned with monitor.sh / ru-monitor.py). Override via /etc/bvpn/balancer.env.
DEFAULT_FAIL_STREAK = 3
DEFAULT_OK_STREAK = 2
DEFAULT_RE_ALERT_COOLDOWN_SEC = 900
DEFAULT_RECOVER_NOTIFY_MIN_SEC = 3600
QUORUM_MIN_BAD = 2

# CDN-heavy decoy SNIs: brief HTTP 0 is warning/log-only until sustained or quorum.
CDN_HEAVY_SNIS = frozenset({
    "www.microsoft.com",
    "www.apple.com",
    "www.bing.com",
})

# RU/edge baseline SNIs: sustained failure pages faster (still respects streak).
CRITICAL_BASELINE_SNIS = frozenset({
    "ads.x5.ru",
    "eh.vk.com",
    "ir-3.ozone.ru",
    "sun6-21.userapi.com",
    "id.x5.ru",
    "5post-gate.x5.ru",
})

# --- Amsterdam ---
AMSTERDAM_HOST = "168.100.11.140"
AMSTERDAM_SSH_PORT = 3344
AMSTERDAM_SSH_KEY = "/root/.ssh/id_ed25519"

# --- Nodes ---
# Amsterdam is currently in drain (P1-ARCH-AMS-DECOM): caddy-selfsteal still
# runs there but reverse_proxy for some SNI goes through the stopped remnanode
# and returns 500. Re-enable when AMS xray is restored, or remove this comment
# entirely once AMS is fully decommissioned (step 4c).
NODES = [
    ("latvia", None),
    # ("amsterdam", AMSTERDAM_HOST),  # disabled 2026-05-14 — AMS xray drain
]

# Display names for Telegram (flag + label)
NODE_LABELS = {
    "latvia": "\U0001f1fb\U0001f1f7 Latvia",
    "amsterdam": "\U0001f1f3\U0001f1f1 Amsterdam",
}


def node_label(node: str) -> str:
    return NODE_LABELS.get(node, node)

# --- Expectations (from doc section 5.6) ---
# Baseline verification: проверены руками `curl -sk --resolve sni:9443:127.0.0.1
# https://sni:9443/` против Caddy reality на каждой ноде (дата округления —
# перед Monitor-block/P1-selfsteal-01). Если upstream меняет ответ —
# править строку здесь и дату в docs/COMMERCIAL-BACKLOG.
# WWW/CDN строки ниже допускают редиректы там, где иначе много шума при смене геодансинга edge.
EXPECTATIONS = {
    "www.microsoft.com":    {"expected": 200, "tolerate": [200, 301, 302, 304]},
    "www.apple.com":        {"expected": 200, "tolerate": [200, 301, 302, 304]},
    "api.github.com":       {"expected": 200, "tolerate": [200, 304]},
    "www.bing.com":         {"expected": 200, "tolerate": [200, 301, 302]},
    # ads.x5.ru: 2026-05-14 upstream сменил поведение, теперь 302 → x5media.ru
    # (раньше 503). Tolerate сохраняет старые 5xx — если X5 вернёт сервис, не алертим.
    "ads.x5.ru":            {"expected": 302, "tolerate": [302, 301, 503, 502, 504]},
    "eh.vk.com":            {"expected": 400, "tolerate": [400, 401, 403]},
    "ir-3.ozone.ru":        {"expected": 403, "tolerate": [403, 401]},
    "sun6-21.userapi.com":  {"expected": 403, "tolerate": [403, 401]},
    "google-analytics.com": {"expected": 301, "tolerate": [301, 302, 200]},
    "pimg.mycdn.me":        {"expected": 404, "tolerate": [404, 403]},
    "fonts.googleapis.com": {"expected": 404, "tolerate": [404, 403, 200]},
    "id.x5.ru":             {"expected": 200, "tolerate": [200, 301, 302]},
    "5post-gate.x5.ru":     {"expected": 404, "tolerate": [404, 403]},
}


def acquire_lock():
    """Acquire exclusive lock. Return lock fd or None if another instance is running."""
    try:
        fd = open(LOCK_FILE, "w")
        fcntl.flock(fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except (IOError, OSError):
        return None


def log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"[{ts}] {msg}"
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except OSError:
        pass


def load_env(path):
    """Load KEY=VALUE file into dict. Strip wrapping quotes."""
    env = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    v = v.strip()
                    if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
                        v = v[1:-1]
                    env[k.strip()] = v
    except FileNotFoundError:
        log(f"ERROR: env file not found: {path}")
    return env


def send_telegram(bot_token, chat_id, text):
    """Send Telegram message. Never raises."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "parse_mode": "HTML",
        "text": text,
    }).encode()
    req = urllib.request.Request(url, data=data)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
    except Exception as e:
        log(f"WARNING: Telegram send failed: {e}")


def cooldown_allows(prev, cooldown_sec):
    """True if we may open a new DOWN after a recent RECOVERED."""
    if not prev:
        return True
    until = prev.get("cooldown_until")
    if not until:
        return True
    try:
        end = datetime.fromisoformat(until.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) >= end
    except (ValueError, TypeError):
        return True


def recover_notify_allows(prev, recover_notify_min_sec):
    """True if RECOVERED Telegram may fire (rate limit per key)."""
    if not prev:
        return True
    last = prev.get("last_recover_notify")
    if not last:
        return True
    try:
        then = datetime.fromisoformat(last.replace("Z", "+00:00"))
        elapsed = (datetime.now(timezone.utc) - then).total_seconds()
        return elapsed >= recover_notify_min_sec
    except (ValueError, TypeError):
        return True


def normalize_prev_entry(prev):
    """Migrate legacy state entries (pre anti-flap) without crashing."""
    if not prev:
        return {}
    out = dict(prev)
    if "fail_streak" not in out:
        out["fail_streak"] = 1 if out.get("status") == "critical" else 0
    if "ok_streak" not in out:
        out["ok_streak"] = 0
    if "alerting" not in out:
        out["alerting"] = out.get("status") == "critical"
    return out


def is_bad_probe(level):
    return level == "critical"


def evaluate_paging_down(
    sni,
    level,
    code,
    fail_streak,
    fail_streak_need,
    node_bad_count,
    prev,
    re_alert_cooldown_sec,
):
    """Return (should_page: bool, log_reason: str)."""
    if not is_bad_probe(level):
        return False, ""

    quorum = node_bad_count >= QUORUM_MIN_BAD
    is_cdn = sni in CDN_HEAVY_SNIS
    is_baseline = sni in CRITICAL_BASELINE_SNIS
    http_zero = code == 0

    if not cooldown_allows(prev, re_alert_cooldown_sec):
        return False, (
            f"suppressed: cooldown active fail_streak {fail_streak}/{fail_streak_need}"
        )

    if quorum and fail_streak >= 1:
        return True, "paging: quorum fail"

    if is_baseline and fail_streak >= fail_streak_need:
        return True, "paging: sustained fail (baseline)"

    if is_cdn and http_zero:
        if fail_streak >= fail_streak_need:
            return True, "paging: sustained fail"
        return False, (
            f"warning: CDN SNI degraded; suppressed: fail_streak "
            f"{fail_streak}/{fail_streak_need}"
        )

    if fail_streak >= fail_streak_need:
        return True, "paging: sustained fail"

    return False, f"suppressed: fail_streak {fail_streak}/{fail_streak_need}"


def process_node_checks(
    node_name,
    results,
    prev_state,
    now_ts,
    is_first_run,
    *,
    fail_streak_need,
    ok_streak_need,
    re_alert_cooldown_sec,
    recover_notify_min_sec,
):
    """Apply anti-flap to one node's probe results.

    Returns (new_state, pending_down, pending_recovered, log_lines).
    """
    node_bad_count = sum(1 for r in results if is_bad_probe(r["level"]))
    new_state = {}
    pending_down = []
    pending_recovered = []
    log_lines = []

    for r in results:
        sni = r["sni"]
        code = r["code"]
        level = r["level"]
        reason = r["reason"]
        retried = r["retried"]
        key = f"{node_name}:{sni}"

        prev = normalize_prev_entry(prev_state.get(key))
        alerting = bool(prev.get("alerting"))
        fail_streak = int(prev.get("fail_streak", 0))
        ok_streak = int(prev.get("ok_streak", 0))
        last_change = prev.get("last_change", now_ts)
        cooldown_until = prev.get("cooldown_until")
        last_recover_notify = prev.get("last_recover_notify")

        if is_bad_probe(level):
            fail_streak += 1
            ok_streak = 0
        else:
            ok_streak += 1
            fail_streak = 0

        opened_down = False
        closed_down = False
        new_cooldown_until = cooldown_until

        if (
            is_bad_probe(level)
            and not alerting
            and not is_first_run
        ):
            should_page, page_reason = evaluate_paging_down(
                sni,
                level,
                code,
                fail_streak,
                fail_streak_need,
                node_bad_count,
                prev,
                re_alert_cooldown_sec,
            )
            if should_page:
                alerting = True
                opened_down = True
                last_change = now_ts
                expected_code = EXPECTATIONS[sni]["expected"]
                pending_down.append({
                    "sni": sni,
                    "code": code,
                    "reason": reason,
                    "prev": prev,
                    "expected": expected_code,
                    "page_reason": page_reason,
                })
                log_lines.append(f"ALERT DOWN queued: {key} {page_reason} -- {reason}")
            elif page_reason:
                log_lines.append(f"{page_reason}: {key} code={code}")

        elif not is_bad_probe(level) and alerting:
            if ok_streak >= ok_streak_need:
                if recover_notify_allows(prev, recover_notify_min_sec):
                    alerting = False
                    closed_down = True
                    last_change = now_ts
                    last_recover_notify = now_ts
                    new_cooldown_until = (
                        datetime.now(timezone.utc)
                        + timedelta(seconds=re_alert_cooldown_sec)
                    ).strftime("%Y-%m-%dT%H:%M:%SZ")
                    pending_recovered.append({
                        "sni": sni,
                        "code": code,
                        "prev": prev,
                    })
                    log_lines.append(
                        f"ALERT RECOVERED queued: {key} ok_streak={ok_streak}"
                    )
                else:
                    log_lines.append(
                        f"suppressed: recover notify cooldown {key} ok_streak={ok_streak}"
                    )
            else:
                log_lines.append(
                    f"suppressed: ok_streak {ok_streak}/{ok_streak_need} {key}"
                )

        elif prev.get("status") and prev.get("status") != level:
            last_change = now_ts

        if level == "warning" and prev.get("status") == "ok":
            log_lines.append(f"WARNING: {key} code={code} ({reason})")

        prev_retry_count = int(prev.get("retry_count", 0))
        new_retry_count = prev_retry_count + 1 if retried else 0
        if new_retry_count >= RETRY_WARN_THRESHOLD:
            log_lines.append(
                f"WARNING: {key} retried {new_retry_count} times consecutively"
            )

        new_state[key] = {
            "status": level,
            "alerting": alerting,
            "fail_streak": fail_streak,
            "ok_streak": ok_streak,
            "last_check": now_ts,
            "last_change": last_change,
            "cooldown_until": new_cooldown_until,
            "last_recover_notify": last_recover_notify,
            "code": code,
            "reason": reason,
            "retried": retried,
            "retry_count": new_retry_count,
        }

    return new_state, pending_down, pending_recovered, log_lines


def load_state():
    """Load previous state. Returns empty dict if file missing or corrupted."""
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError) as e:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        corrupted_path = f"{STATE_FILE}.corrupted.{ts}"
        try:
            os.rename(STATE_FILE, corrupted_path)
        except OSError:
            pass
        log(f"WARNING: state.json corrupted ({e}), renamed to {corrupted_path}")
        return {}
    except OSError as e:
        log(f"ERROR: could not read state.json: {e}")
        return {}


def save_state(state):
    """Atomically save state: write to tmp, fsync, rename."""
    os.makedirs(STATE_DIR, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=STATE_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(state, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.rename(tmp_path, STATE_FILE)
    except Exception as e:
        log(f"ERROR: failed to save state: {e}")
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def humanize_since(ts_str):
    """Convert ISO timestamp to human-readable duration."""
    try:
        then = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        total_sec = int((now - then).total_seconds())
        if total_sec < 0:
            return ts_str
        if total_sec < 60:
            return f"{total_sec}s"
        if total_sec < 3600:
            return f"{total_sec // 60} min"
        if total_sec < 86400:
            h = total_sec // 3600
            m = (total_sec % 3600) // 60
            return f"{h}h {m}m"
        d = total_sec // 86400
        h = (total_sec % 86400) // 3600
        return f"{d}d {h}h"
    except (ValueError, TypeError):
        return ts_str


def curl_local(sni):
    """Run curl to localhost:9443 for one SNI. Return HTTP code as int (0 on error)."""
    cmd = [
        "curl", "-sk",
        "--resolve", f"{sni}:9443:127.0.0.1",
        "--max-time", str(CURL_TIMEOUT),
        "-o", "/dev/null",
        "-w", "%{http_code}",
        f"https://{sni}:9443/",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=CURL_TIMEOUT + 5)
        return int(proc.stdout.strip())
    except (subprocess.TimeoutExpired, ValueError):
        return 0


def ssh_batch_check(ssh_host, sni_list):
    """SSH to remote host, run curl for each SNI, return dict {sni: code}.

    Hardening (P0-SEC-02): the SNI list is NEVER interpolated into the remote
    bash script. Defense in depth:
      1) Reject any SNI that does not match a strict DNS label regex — drops
         anything like `foo; rm -rf /` before it gets near a shell.
      2) Pass the surviving SNIs through stdin as a `\\n`-separated list. The
         remote script reads them with `while IFS= read -r`, so word splitting
         and metacharacters in stdin can't escape into the shell.
    """
    safe = [s for s in sni_list if SNI_RE.match(s)]
    rejected = [s for s in sni_list if not SNI_RE.match(s)]
    if rejected:
        log(f"WARN: dropping {len(rejected)} SNIs failing whitelist: {rejected[:5]}")
    if not safe:
        log("ERROR: no valid SNIs left after whitelist")
        return None

    # Fixed script body — no caller-controlled data is interpolated into it.
    # The list of SNIs travels as a here-doc payload after the script, so
    # arbitrary characters in stdin can never escape into shell syntax.
    payload = (
        "#!/bin/bash\n"
        "set -u\n"
        f"CURL_TIMEOUT={int(CURL_TIMEOUT)}\n"
        'while IFS= read -r sni; do\n'
        '  [ -z "$sni" ] && continue\n'
        '  case "$sni" in *[!A-Za-z0-9.-]*) continue ;; esac\n'
        '  code=$(curl -sk --resolve "$sni:9443:127.0.0.1" '
        '--max-time "$CURL_TIMEOUT" -o /dev/null -w "%{http_code}" '
        '"https://$sni:9443/" 2>/dev/null)\n'
        '  printf "%s %s\\n" "$sni" "$code"\n'
        "done <<'__SNI_EOF__'\n"
        + "\n".join(safe) + "\n"
        "__SNI_EOF__\n"
    )

    cmd = [
        "ssh",
        "-p", str(AMSTERDAM_SSH_PORT),
        "-i", AMSTERDAM_SSH_KEY,
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "UserKnownHostsFile=/root/.ssh/known_hosts",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=10",
        f"root@{ssh_host}",
        "bash", "-s",
    ]
    try:
        proc = subprocess.run(
            cmd, input=payload,
            capture_output=True, text=True, timeout=SSH_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        log(f"ERROR: SSH to {ssh_host} timed out after {SSH_TIMEOUT}s")
        return None

    if proc.returncode != 0:
        stderr = proc.stderr.strip()[:200]
        log(f"ERROR: SSH to {ssh_host} exit code {proc.returncode}: {stderr}")
        return None

    results = {}
    for line in proc.stdout.strip().splitlines():
        parts = line.strip().split()
        if len(parts) == 2:
            sni, code_str = parts
            try:
                results[sni] = int(code_str)
            except ValueError:
                results[sni] = 0
    return results


def classify_result(code, exp_entry):
    """Classify HTTP code: 'ok', 'warning', or 'critical'."""
    expected = exp_entry["expected"]
    tolerate = exp_entry["tolerate"]
    if code == 0:
        return "critical", "no response (HTTP 000)"
    if code == expected:
        return "ok", None
    if code in tolerate:
        return "warning", f"tolerated ({code} instead of {expected})"
    return "critical", f"fingerprint drift ({code} instead of {expected})"


def run_checks_local():
    """Run all 13 SNI checks on Latvia localhost. Return list of result dicts."""
    results = []
    for sni, exp in EXPECTATIONS.items():
        code = curl_local(sni)
        retried = False
        if code == 0:
            for attempt in range(HTTP_ZERO_RETRIES):
                time.sleep(HTTP_ZERO_BACKOFF_BASE + attempt * 0.5)
                code = curl_local(sni)
                retried = True
                if code != 0:
                    break
        if code not in exp["tolerate"]:
            if not retried:
                time.sleep(RETRY_DELAY)
            code = curl_local(sni)
            retried = True
        level, reason = classify_result(code, exp)
        results.append({
            "sni": sni,
            "code": code,
            "level": level,
            "reason": reason,
            "retried": retried,
        })
    return results


def run_checks_remote(ssh_host):
    """Run all 13 SNI checks on remote node via SSH. Return list of result dicts."""
    sni_list = list(EXPECTATIONS.keys())

    # First batch: all 13 SNI
    batch = ssh_batch_check(ssh_host, sni_list)
    if batch is None:
        # SSH failed entirely — all critical
        results = []
        for sni in sni_list:
            results.append({
                "sni": sni,
                "code": 0,
                "level": "critical",
                "reason": "SSH to node failed",
                "retried": False,
            })
        return results

    # Identify SNI needing retry
    needs_retry = []
    for sni in sni_list:
        code = batch.get(sni, 0)
        if code not in EXPECTATIONS[sni]["tolerate"]:
            needs_retry.append(sni)

    # Retry batch (only failed SNI)
    retry_results = {}
    if needs_retry:
        time.sleep(RETRY_DELAY)
        retry_results = ssh_batch_check(ssh_host, needs_retry)
        if retry_results is None:
            retry_results = {}

    # Build final results
    results = []
    for sni in sni_list:
        if sni in needs_retry:
            code = retry_results.get(sni, 0)
            retried = True
        else:
            code = batch.get(sni, 0)
            retried = False
        level, reason = classify_result(code, EXPECTATIONS[sni])
        results.append({
            "sni": sni,
            "code": code,
            "level": level,
            "reason": reason,
            "retried": retried,
        })
    return results


def format_alert_down(node, sni, code, prev):
    node = node_label(node)
    """Format CRITICAL alert: Caddy not responding (HTTP 000)."""
    if prev:
        prev_text = f"OK (last change {prev.get('last_change', 'unknown')})"
    else:
        prev_text = "first check"
    return (
        f"\U0001f6a8 <b>SELFSTEAL: Caddy not responding</b>\n\n"
        f"<b>Node:</b> {node}\n"
        f"<b>SNI:</b> {sni}\n"
        f"<b>Status:</b> no response (HTTP {code})\n"
        f"<b>Previous:</b> {prev_text}\n\n"
        f"Critical: active probing protection is broken.\n"
        f"Caddy on this node is either down or not proxying this SNI.\n\n"
        f"Check:\n"
        f"- systemctl status caddy (Latvia)\n"
        f"- docker ps caddy-selfsteal (Amsterdam)\n"
        f"- tail /var/log/caddy/...\n\n"
        f"<i>Sustained failure or quorum required before paging (anti-flap).</i>"
    )


def format_batch_alert_down(node, items):
    """Batch DOWN alert for multiple SNIs on one node."""
    n = len(items)
    label = node_label(node)
    lines = [
        f"\U0001f6a8 <b>SELFSTEAL: probe failure</b> ({n} SNI on {label})\n",
    ]
    for item in items:
        sni = item["sni"]
        code = item["code"]
        page_reason = item.get("page_reason", "paging")
        if code == 0:
            status = f"no response (HTTP {code})"
        else:
            status = f"HTTP {code} (expected {item.get('expected', '?')})"
        lines.append(f"• <b>{sni}</b> — {status} [{page_reason}]")
    lines.append(
        "\nCheck Caddy selfsteal on this node.\n"
        "<i>CDN SNI single blips are suppressed until sustained or quorum.</i>"
    )
    return "\n".join(lines)


def format_batch_alert_recovered(node, items):
    """Batch RECOVERED alert for multiple SNIs on one node."""
    n = len(items)
    label = node_label(node)
    lines = [
        f"\u2705 <b>SELFSTEAL: recovered</b> ({n} SNI on {label})\n",
    ]
    for item in items:
        sni = item["sni"]
        code = item["code"]
        prev = item.get("prev") or {}
        down_since_raw = prev.get("last_change", "unknown")
        down_since = (
            humanize_since(down_since_raw)
            if down_since_raw != "unknown"
            else "unknown"
        )
        lines.append(f"• <b>{sni}</b> — HTTP {code} OK (was down ~{down_since})")
    return "\n".join(lines)


def format_alert_drift(node, sni, expected, got, prev):
    node = node_label(node)
    """Format CRITICAL alert: fingerprint drift."""
    if prev:
        prev_text = f"OK (last seen {prev.get('last_change', 'unknown')})"
    else:
        prev_text = "first check"
    return (
        f"\U0001f6a8 <b>SELFSTEAL: fingerprint drift</b>\n\n"
        f"<b>Node:</b> {node}\n"
        f"<b>SNI:</b> {sni}\n"
        f"<b>Expected:</b> {expected}\n"
        f"<b>Got:</b> {got}\n"
        f"<b>Previous:</b> {prev_text}\n\n"
        f"Active probe protection compromised.\n"
        f"Upstream may be down, or Caddy reverse_proxy misconfigured."
    )


def format_alert_recovered(node, sni, code, prev):
    node = node_label(node)
    """Format OK alert: recovered."""
    down_since_raw = prev.get("last_change", "unknown") if prev else "unknown"
    down_since = humanize_since(down_since_raw) if down_since_raw != "unknown" else "unknown"
    return (
        f"\u2705 <b>SELFSTEAL: recovered</b>\n\n"
        f"<b>Node:</b> {node}\n"
        f"<b>SNI:</b> {sni}\n"
        f"<b>Status:</b> HTTP {code} (expected)\n"
        f"<b>Down for:</b> {down_since}\n"
    )


def main():
    lock_fd = acquire_lock()
    if lock_fd is None:
        return

    try:
        time.sleep(random.randint(0, JITTER_MAX))

        # Load env for Telegram + anti-flap thresholds
        balancer_env = load_env("/etc/bvpn/balancer.env")
        bot_token = balancer_env.get("BOT_TOKEN")
        chat_id = balancer_env.get("ADMIN_CHAT_ID", "924498094")
        fail_streak_need = int(
            balancer_env.get("SELFSTEAL_FAIL_STREAK_THRESHOLD", DEFAULT_FAIL_STREAK)
        )
        ok_streak_need = int(
            balancer_env.get("SELFSTEAL_OK_STREAK_THRESHOLD", DEFAULT_OK_STREAK)
        )
        re_alert_cooldown_sec = int(
            balancer_env.get("SELFSTEAL_RE_ALERT_COOLDOWN_SEC", DEFAULT_RE_ALERT_COOLDOWN_SEC)
        )
        recover_notify_min_sec = int(
            balancer_env.get(
                "SELFSTEAL_RECOVER_NOTIFY_MIN_SEC", DEFAULT_RECOVER_NOTIFY_MIN_SEC
            )
        )

        if not bot_token:
            log("FATAL: BOT_TOKEN not found in /etc/bvpn/balancer.env")
            return

        # Load previous state
        prev_state = load_state()
        is_first_run = len(prev_state) == 0

        now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        new_state = {}
        ok_count = 0
        warning_count = 0
        critical_count = 0
        retried_count = 0
        transitions = 0

        for node_name, ssh_host in NODES:
            if ssh_host is None:
                results = run_checks_local()
            else:
                results = run_checks_remote(ssh_host)

            for r in results:
                if r["level"] == "ok":
                    ok_count += 1
                elif r["level"] == "warning":
                    warning_count += 1
                else:
                    critical_count += 1
                if r["retried"]:
                    retried_count += 1

            node_state, pending_down, pending_recovered, log_lines = process_node_checks(
                node_name,
                results,
                prev_state,
                now_ts,
                is_first_run,
                fail_streak_need=fail_streak_need,
                ok_streak_need=ok_streak_need,
                re_alert_cooldown_sec=re_alert_cooldown_sec,
                recover_notify_min_sec=recover_notify_min_sec,
            )
            new_state.update(node_state)
            transitions += len(pending_down) + len(pending_recovered)

            for line in log_lines:
                log(line)

            if pending_down:
                send_telegram(
                    bot_token, chat_id, format_batch_alert_down(node_name, pending_down)
                )
            if pending_recovered:
                send_telegram(
                    bot_token,
                    chat_id,
                    format_batch_alert_recovered(node_name, pending_recovered),
                )

        # Save state atomically
        save_state(new_state)

        # Log summary
        log(f"total={ok_count + warning_count + critical_count} "
            f"ok={ok_count} critical={critical_count} warning={warning_count} "
            f"retried={retried_count} transitions={transitions}")

    finally:
        try:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
            lock_fd.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
