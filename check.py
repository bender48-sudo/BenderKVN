#!/usr/bin/env python3
"""BenderVPN RU Reachability Check Agent — stateless, runs on Relay."""

import json
import hashlib
import socket
import ssl
import sys
import time
from datetime import datetime, timezone

TIMEOUT = 5


def check_target(target):
    addr = target["address"]
    port = target["port"]
    sni = target["sni"]

    result = {
        "address": addr,
        "port": port,
        "sni": sni,
        "tcp_connect_ms": None,
        "tls_handshake_ok": False,
        "tls_handshake_ms": None,
        "cert_fingerprint": None,
        "error": None,
    }

    sock = None
    ssock = None
    try:
        # TCP connect
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        t0 = time.monotonic()
        sock.connect((addr, port))
        t1 = time.monotonic()
        result["tcp_connect_ms"] = round((t1 - t0) * 1000, 1)

        # TLS handshake
        # NOTE: CERT_NONE is INTENTIONAL here. This probe runs from the RU relay
        # against arbitrary public SNIs (microsoft.com, apple.com, …) where the
        # only thing we care about is "did the handshake succeed and what does
        # the cert look like" — not whether the local CA bundle trusts it.
        # Do NOT replace this with strict verification; it will break the probe
        # on relays without an up-to-date CA store.
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        remaining = TIMEOUT - (t1 - t0)
        if remaining <= 0:
            result["error"] = "timeout before TLS (TCP took too long)"
            return result

        sock.settimeout(remaining)
        t2 = time.monotonic()
        ssock = ctx.wrap_socket(sock, server_hostname=sni)
        t3 = time.monotonic()
        result["tls_handshake_ok"] = True
        result["tls_handshake_ms"] = round((t3 - t2) * 1000, 1)

        # Certificate fingerprint
        cert_bin = ssock.getpeercert(binary_form=True)
        if cert_bin:
            fp = hashlib.sha256(cert_bin).hexdigest()[:32]
            result["cert_fingerprint"] = fp

    except socket.timeout:
        result["error"] = "timeout"
    except ConnectionRefusedError:
        result["error"] = "connection refused"
    except ConnectionResetError:
        result["error"] = "connection reset"
    except ssl.SSLError as e:
        result["error"] = f"ssl: {e.reason}"
    except OSError as e:
        result["error"] = f"os: {e}"
    except Exception as e:
        result["error"] = f"unexpected: {e}"
    finally:
        if ssock:
            try:
                ssock.close()
            except Exception:
                pass
        if sock:
            try:
                sock.close()
            except Exception:
                pass

    return result


def main():
    try:
        raw = sys.stdin.read()
        targets = json.loads(raw)
    except (json.JSONDecodeError, ValueError) as e:
        output = {"error": f"invalid input JSON: {e}", "results": []}
        print(json.dumps(output))
        return

    results = []
    for t in targets:
        results.append(check_target(t))

    output = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "results": results,
    }
    print(json.dumps(output))


if __name__ == "__main__":
    main()
