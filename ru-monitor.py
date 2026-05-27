#!/usr/bin/env python3
"""BenderVPN RU Reachability Monitor — orchestrator on Latvia."""

import fcntl
import json
import os
import random
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

# --- Constants ---
VIRTUAL_HOST_UUID = "305ccacd-ab74-42a4-b1a2-f80cdde69a25"
STATE_DIR = "/var/lib/bvpn-ru-monitor"
# monitor.sh пишет alert_* в /var/lib/bvpn-monitor/ (другой путь). Сводка: docs/DEPLOY.md §6.
STATE_FILE = os.path.join(STATE_DIR, "state.json")
LOG_FILE = "/var/log/bvpn-ru-monitor.log"
# Persistent antispam dir (was /tmp/bvpn_states; moved 2026-05-14 so RECOVERED
# markers are not lost on reboot/tmpfiles cleanup, which previously caused
# duplicate ALERTs after a host restart).
ANTISPAM_DIR = "/var/lib/bvpn-monitor"
_LEGACY_ANTISPAM_DIR = "/tmp/bvpn_states"
SSH_TIMEOUT = 120  # seconds, covers ~16 targets x ~5s timeout + overhead
API_TIMEOUT = 15
LOCK_FILE = "/tmp/bvpn-ru-monitor.lock"
# P6-SCALE-06: cron */5 → cycle must stay <300s; jitter capped (was 120).
JITTER_MAX = 60
CYCLE_WARN_SEC = 240  # log WARNING if total cycle exceeds this
# Anti-flap (same idea as monitor.sh): avoid TG spam when relay TLS flaps.
DEFAULT_FAIL_STREAK = 3  # */5 cron → ~15 min sustained fail before DOWN
DEFAULT_OK_STREAK = 2  # ~10 min sustained OK before RECOVERED
DEFAULT_RE_ALERT_COOLDOWN_SEC = 900


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
    """Load KEY=VALUE file into dict. Skip comments and empty lines."""
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
    """Send Telegram message. Never raises — logs errors and returns."""
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
    fname = f"ru_monitor_{event}_{safe_key}_{today}"
    path = os.path.join(ANTISPAM_DIR, fname)
    # Legacy fallback: if a marker for the same key/event/day exists in the
    # old /tmp dir (from before the move), treat as suppressed so we don't
    # re-fire an alert that already went out today.
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
    fname = f"ru_monitor_{event}_{safe_key}_{today}"
    for d in (ANTISPAM_DIR, _LEGACY_ANTISPAM_DIR):
        path = os.path.join(d, fname)
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass


def get_targets(api_url, api_token):
    """Fetch hosts from API, filter, return unique (address, port, sni) list."""
    url = f"{api_url}/api/hosts"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {api_token}")
    try:
        with urllib.request.urlopen(req, timeout=API_TIMEOUT) as resp:
            body = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        log(f"ERROR: API returned HTTP {e.code}")
        return None
    except Exception as e:
        log(f"ERROR: API request failed: {e}")
        return None

    hosts = body.get("response", [])
    if not isinstance(hosts, list):
        log("ERROR: API response.response is not a list")
        return None

    seen = set()
    targets = []
    for h in hosts:
        if h.get("isDisabled"):
            continue
        if h.get("uuid") == VIRTUAL_HOST_UUID:
            continue
        key = (h["address"], h["port"], h["sni"])
        if key not in seen:
            seen.add(key)
            targets.append({
                "address": h["address"],
                "port": h["port"],
                "sni": h["sni"],
            })

    # Hard-coded sanity floor: if we ever see <4 active targets, something
    # likely went wrong with API filters / mass-disable. Otherwise just log
    # the count — it changes legitimately as hosts are added or drained
    # (e.g. P1-ARCH-AMS-DECOM disabled 8 hosts, current=16).
    if len(targets) < 4:
        log(f"WARNING: only {len(targets)} targets fetched (expected >=4)")

    return targets


def run_check(targets, relay_host, relay_port, relay_user, relay_key):
    """SSH to Relay, run check.py with targets on stdin, return parsed JSON."""
    targets_json = json.dumps(targets)
    cmd = [
        "ssh",
        "-p", str(relay_port),
        "-i", relay_key,
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "UserKnownHostsFile=/root/.ssh/known_hosts",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=10",
        f"{relay_user}@{relay_host}",
    ]
    try:
        proc = subprocess.run(
            cmd,
            input=targets_json,
            capture_output=True,
            text=True,
            timeout=SSH_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        log(f"ERROR: SSH to Relay timed out after {SSH_TIMEOUT}s")
        return None

    if proc.returncode != 0:
        stderr = proc.stderr.strip()[:200]
        log(f"ERROR: SSH exit code {proc.returncode}: {stderr}")
        return None

    try:
        data = json.loads(proc.stdout)
    except (json.JSONDecodeError, ValueError) as e:
        log(f"ERROR: invalid JSON from check.py: {e}")
        log(f"  stdout[:200]: {proc.stdout[:200]}")
        return None

    if "results" not in data or not isinstance(data["results"], list):
        log("ERROR: check.py response missing 'results' array")
        return None

    return data


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


def make_target_key(r):
    return f"{r['address']}:{r['port']}/{r['sni']}"


def humanize_since(ts_str):
    """Convert ISO timestamp to human-readable duration like '5 min' / '2h 15m' / '3d 4h'."""
    try:
        then = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = now - then
        total_sec = int(delta.total_seconds())
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


def format_alert_down(r, prev):
    if prev:
        prev_text = f"OK (last change {prev.get('last_change', 'unknown')})"
    else:
        prev_text = "first check"
    if r.get("tcp_connect_ms") is not None:
        tcp_text = f"{r['tcp_connect_ms']}ms (reachable)"
    else:
        tcp_text = "failed"
    error_text = r.get("error") or "unknown"
    return (
        f"\U0001f6a8 <b>RU MONITOR: SNI failure</b>\n\n"
        f"<b>Target:</b> {r['sni']} @ {r['address']}:{r['port']}\n"
        f"<b>Status:</b> TLS handshake failed ({error_text})\n"
        f"<b>TCP connect:</b> {tcp_text}\n"
        f"<b>Previous:</b> {prev_text}\n"
        f"<b>Checked from:</b> Russia Relay (72.56.0.145)\n\n"
        f"Возможные причины:\n"
        f"- ТСПУ блокирует SNI/IP из РФ\n"
        f"- Нода отвалилась (проверь monitor.sh)\n"
        f"- Промежуточная сеть лежит"
    )


def format_alert_recovered(r, prev):
    down_since_raw = prev.get("last_change", "unknown") if prev else "unknown"
    down_since = humanize_since(down_since_raw) if down_since_raw != "unknown" else "unknown"
    return (
        f"\u2705 <b>RU MONITOR: recovered</b>\n\n"
        f"<b>Target:</b> {r['sni']} @ {r['address']}:{r['port']}\n"
        f"<b>Status:</b> TLS handshake OK ({r.get('tls_handshake_ms', '?')}ms)\n"
        f"<b>TCP connect:</b> {r.get('tcp_connect_ms', '?')}ms\n"
        f"<b>Down for:</b> {down_since}\n"
        f"<b>Checked from:</b> Russia Relay (72.56.0.145)"
    )


def format_batch_down(items):
    n = len(items)
    lines = [
        f"\U0001f6a8 <b>RU MONITOR: SNI failures</b> ({n} target{'s' if n != 1 else ''})\n",
        "<b>Checked from:</b> Russia Relay (72.56.0.145)\n",
    ]
    for r in items:
        tcp = r.get("tcp_connect_ms")
        tcp_text = f"{tcp}ms" if tcp is not None else "?"
        err = r.get("error") or "timeout"
        lines.append(
            f"• <b>{r['sni']}</b> @ {r['address']}:{r['port']} "
            f"— TLS failed ({err}), TCP {tcp_text}"
        )
    lines.append(
        "\nВозможные причины:\n"
        "- ТСПУ блокирует SNI/IP из РФ (частый флап — не обязательно падение нод)\n"
        "- Нода отвалилась (проверь monitor.sh)\n"
        "- Промежуточная сеть лежит"
    )
    return "\n".join(lines)


def format_batch_recovered(items):
    n = len(items)
    lines = [
        f"\u2705 <b>RU MONITOR: recovered</b> ({n} target{'s' if n != 1 else ''})\n",
        "<b>Checked from:</b> Russia Relay (72.56.0.145)\n",
    ]
    for r, prev in items:
        down_for = humanize_since(prev.get("last_change", "unknown"))
        tls = r.get("tls_handshake_ms", "?")
        lines.append(
            f"• <b>{r['sni']}</b> @ {r['address']}:{r['port']} "
            f"— OK ({tls}ms), was down ~{down_for}"
        )
    return "\n".join(lines)


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


def format_alert_cert_changed(r, old_fp, new_fp):
    return (
        f"\u26a0\ufe0f <b>RU MONITOR: certificate changed</b>\n\n"
        f"<b>Target:</b> {r['sni']} @ {r['address']}:{r['port']}\n"
        f"<b>Old fingerprint:</b> <code>{old_fp}</code>\n"
        f"<b>New fingerprint:</b> <code>{new_fp}</code>\n"
        f"<b>Checked from:</b> Russia Relay (72.56.0.145)\n\n"
        f"Часто это ротация сертификата апстрима (CDN/магазин), не ваш Caddy. "
        f"Для fingerprinting-узлов на relay — сравните с первым успешным прогоном. MITM не исключайте, но не паникуйте на одном смене."
    )


def main():
    lock_fd = acquire_lock()
    if lock_fd is None:
        return

    cycle_t0 = time.monotonic()
    try:
        # Jitter: random delay to spread cron load
        time.sleep(random.randint(0, JITTER_MAX))

        # Load env
        monitor_env = load_env("/etc/bvpn/ru-monitor.env")
        balancer_env = load_env("/etc/bvpn/balancer.env")

        api_token = monitor_env.get("REMNA_API_TOKEN")
        try:
            sys.path.insert(0, "/opt/scripts")
            from remna_credential_broker import get_panel_token

            api_token = get_panel_token("ru-monitor")
        except Exception as exc:
            log(f"WARN: credential broker fallback: {exc}")
        api_url = monitor_env.get("REMNA_API_URL")
        relay_host = monitor_env.get("RELAY_HOST")
        relay_port = monitor_env.get("RELAY_SSH_PORT", "3344")
        relay_user = monitor_env.get("RELAY_SSH_USER", "bvpncheck")
        relay_key = monitor_env.get("RELAY_SSH_KEY", "/root/.ssh/id_ed25519")
        bot_token = balancer_env.get("BOT_TOKEN")
        chat_id = balancer_env.get("ADMIN_CHAT_ID", "924498094")
        fail_streak_need = int(
            monitor_env.get("RU_FAIL_STREAK_THRESHOLD", DEFAULT_FAIL_STREAK)
        )
        ok_streak_need = int(
            monitor_env.get("RU_OK_STREAK_THRESHOLD", DEFAULT_OK_STREAK)
        )
        re_alert_cooldown_sec = int(
            monitor_env.get("RU_RE_ALERT_COOLDOWN_SEC", DEFAULT_RE_ALERT_COOLDOWN_SEC)
        )

        if not api_token:
            log("FATAL: REMNA_API_TOKEN not found in /etc/bvpn/ru-monitor.env")
            return
        if not api_url:
            log("FATAL: REMNA_API_URL not found in /etc/bvpn/ru-monitor.env")
            return
        if not relay_host:
            log("FATAL: RELAY_HOST not found in /etc/bvpn/ru-monitor.env")
            return
        if not bot_token:
            log("FATAL: BOT_TOKEN not found in /etc/bvpn/balancer.env")
            return

        # Get targets from API
        targets = get_targets(api_url, api_token)
        if targets is None:
            log("FATAL: could not get targets from API, aborting")
            return

        # Run check on Relay
        check_data = run_check(targets, relay_host, relay_port, relay_user, relay_key)
        if check_data is None:
            log("FATAL: check.py on Relay failed, aborting")
            return

        results = check_data["results"]
        now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Load previous state
        prev_state = load_state()
        is_first_run = len(prev_state) == 0

        # Process results with streak anti-flap (monitor.sh-style).
        new_state = {}
        ok_count = 0
        fail_count = 0
        transitions = 0
        pending_down = []
        pending_recovered = []

        for r in results:
            key = make_target_key(r)
            is_ok = r.get("tls_handshake_ok", False)
            status = "ok" if is_ok else "fail"
            cert_fp = r.get("cert_fingerprint")

            prev = prev_state.get(key) or {}
            prev_status = prev.get("status")
            prev_cert = prev.get("last_cert_fp")
            alerting = bool(prev.get("alerting"))
            fail_streak = int(prev.get("fail_streak", prev.get("fail_count", 0)))
            ok_streak = int(prev.get("ok_streak", 0))
            last_change = prev.get("last_change", now_ts)
            cooldown_until = prev.get("cooldown_until")

            if is_ok:
                ok_count += 1
                fail_streak = 0
                ok_streak = ok_streak + 1
            else:
                fail_count += 1
                ok_streak = 0
                fail_streak = fail_streak + 1

            cert_transition = (
                prev_status == "ok" and status == "ok"
                and prev_cert and cert_fp and prev_cert != cert_fp
            )

            opened_down = False
            closed_down = False
            new_cooldown_until = prev.get("cooldown_until")
            last_change = prev.get("last_change", now_ts)

            if not is_ok and not alerting and not is_first_run:
                if (
                    fail_streak >= fail_streak_need
                    and cooldown_allows(prev, re_alert_cooldown_sec)
                    and antispam_check(key, "down")
                ):
                    pending_down.append(r)
                    alerting = True
                    opened_down = True
                    last_change = now_ts
                    transitions += 1
                    log(
                        f"ALERT DOWN queued: {key} streak={fail_streak} "
                        f"-- {r.get('error')}"
                    )
            elif is_ok and alerting:
                if ok_streak >= ok_streak_need:
                    pending_recovered.append((r, prev))
                    alerting = False
                    closed_down = True
                    transitions += 1
                    new_cooldown_until = (
                        datetime.now(timezone.utc)
                        + timedelta(seconds=re_alert_cooldown_sec)
                    ).strftime("%Y-%m-%dT%H:%M:%SZ")
                    antispam_clear(key, "down")
                    log(f"ALERT RECOVERED queued: {key} streak={ok_streak}")
            elif prev_status and prev_status != status:
                last_change = now_ts

            if cert_transition and antispam_check(key, "cert"):
                msg = format_alert_cert_changed(r, prev_cert, cert_fp)
                send_telegram(bot_token, chat_id, msg)
                transitions += 1
                log(f"ALERT CERT CHANGED: {key} {prev_cert} -> {cert_fp}")

            new_state[key] = {
                "status": status,
                "alerting": alerting,
                "fail_streak": fail_streak,
                "ok_streak": ok_streak,
                "last_check": now_ts,
                "last_change": last_change,
                "cooldown_until": new_cooldown_until,
                "last_cert_fp": cert_fp,
                "last_error": r.get("error"),
                "tcp_connect_ms": r.get("tcp_connect_ms"),
                "tls_handshake_ms": r.get("tls_handshake_ms"),
            }

        if pending_down:
            send_telegram(bot_token, chat_id, format_batch_down(pending_down))
        if pending_recovered:
            send_telegram(
                bot_token, chat_id, format_batch_recovered(pending_recovered)
            )

        # Save state atomically
        save_state(new_state)

        # Log summary (P6-SCALE-06: duration for cron */5 budget)
        duration_sec = round(time.monotonic() - cycle_t0, 1)
        log(
            f"total={len(results)} ok={ok_count} fail={fail_count} "
            f"transitions={transitions} duration_sec={duration_sec}"
        )
        if duration_sec > CYCLE_WARN_SEC:
            log(
                f"WARNING: cycle {duration_sec}s > {CYCLE_WARN_SEC}s "
                f"(P6-SCALE-06: target <300s for */5 cron)"
            )

    finally:
        duration_sec = round(time.monotonic() - cycle_t0, 1)
        # Always log cycle time (P6-SCALE-06), including API/SSH abort paths.
        if "results" not in locals():
            log(f"duration_sec={duration_sec} status=aborted")
        try:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
            lock_fd.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
