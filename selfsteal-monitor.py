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
from datetime import datetime, timezone

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


def antispam_check(key, event):
    """Return True if this alert should be sent (not suppressed)."""
    os.makedirs(ANTISPAM_DIR, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    safe_key = key.replace("/", "_").replace(":", "_")
    fname = f"selfsteal_monitor_{event}_{safe_key}_{today}"
    path = os.path.join(ANTISPAM_DIR, fname)
    if os.path.exists(path):
        return False
    legacy = os.path.join(_LEGACY_ANTISPAM_DIR, fname)
    if os.path.exists(legacy):
        return False
    try:
        with open(path, "w") as f:
            f.write(today)
    except OSError:
        pass
    return True


def antispam_clear(key, event):
    """Remove antispam marker so the next event of same type can fire."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    safe_key = key.replace("/", "_").replace(":", "_")
    fname = f"selfsteal_monitor_{event}_{safe_key}_{today}"
    for d in (ANTISPAM_DIR, _LEGACY_ANTISPAM_DIR):
        path = os.path.join(d, fname)
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass


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
        f"<i>Short HTTP 0 spikes can be transient (same Caddy handles panel :2053); "
        f"retry before paging.</i>"
    )


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

        # Load env for Telegram
        balancer_env = load_env("/etc/bvpn/balancer.env")
        bot_token = balancer_env.get("BOT_TOKEN")
        chat_id = balancer_env.get("ADMIN_CHAT_ID", "924498094")

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
                sni = r["sni"]
                code = r["code"]
                level = r["level"]
                reason = r["reason"]
                retried = r["retried"]
                key = f"{node_name}:{sni}"

                if level == "ok":
                    ok_count += 1
                elif level == "warning":
                    warning_count += 1
                else:
                    critical_count += 1

                if retried:
                    retried_count += 1

                prev = prev_state.get(key)
                prev_status = prev.get("status") if prev else None

                # Detect transition (only ok <-> critical)
                transition = None
                if prev_status in ("ok", "warning") and level == "critical":
                    transition = "down"
                elif prev_status == "critical" and level in ("ok", "warning"):
                    transition = "recovered"
                elif prev_status is None and level == "critical" and not is_first_run:
                    transition = "down"

                if transition:
                    transitions += 1
                    expected_code = EXPECTATIONS[sni]["expected"]
                    if transition == "down" and antispam_check(key, "critical"):
                        if code == 0:
                            msg = format_alert_down(node_name, sni, code, prev)
                        else:
                            msg = format_alert_drift(node_name, sni, expected_code, code, prev)
                        send_telegram(bot_token, chat_id, msg)
                        log(f"ALERT CRITICAL: {key} -- {reason}")
                    elif transition == "recovered":
                        msg = format_alert_recovered(node_name, sni, code, prev)
                        send_telegram(bot_token, chat_id, msg)
                        log(f"ALERT RECOVERED: {key}")
                        antispam_clear(key, "critical")

                # Warning: only log, no Telegram
                if level == "warning" and prev_status == "ok":
                    log(f"WARNING: {key} code={code} ({reason})")

                # retry_count tracking
                prev_retry_count = prev.get("retry_count", 0) if prev else 0
                if retried:
                    new_retry_count = prev_retry_count + 1
                else:
                    new_retry_count = 0

                if new_retry_count >= RETRY_WARN_THRESHOLD:
                    log(f"WARNING: {key} retried {new_retry_count} times consecutively, check upstream")

                # Build new state entry
                new_state[key] = {
                    "status": level,
                    "last_check": now_ts,
                    "last_change": (
                        now_ts if transition
                        else (prev.get("last_change", now_ts) if prev else now_ts)
                    ),
                    "code": code,
                    "reason": reason,
                    "retried": retried,
                    "retry_count": new_retry_count,
                }

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
