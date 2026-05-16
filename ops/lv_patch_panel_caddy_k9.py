#!/usr/bin/env python3
"""Patch LV /etc/caddy/Caddyfile — панель k9x2m1 на :2053.

- Редирект с http://k9x2m1.conntest.xyz (порт 80) на https://…:2053
- header_up Host {host} перед X-Forwarded-Proto у reverse_proxy на AMS :3000
  только внутри блока k9x2m1.conntest.xyz:2053.

После патча на LV:
  caddy validate --config /etc/caddy/Caddyfile && systemctl restart caddy
(reload через systemd может падать при admin off — см. журнал.)
"""
from __future__ import annotations

from pathlib import Path

CADDYFILE = Path("/etc/caddy/Caddyfile")
SITE = "k9x2m1.conntest.xyz:2053 {"
HTTP_BLOCK = """http://k9x2m1.conntest.xyz {
    redir https://k9x2m1.conntest.xyz:2053{uri} permanent
}

"""
PROXY_NEEDLE = (
    "    reverse_proxy http://168.100.11.140:3000 {\n"
    "        header_up X-Forwarded-Proto"
)
HOST_LINE = "        header_up Host {host}"


def main() -> None:
    full = CADDYFILE.read_text(encoding="utf-8")
    orig = full

    if "http://k9x2m1.conntest.xyz {" not in full:
        if SITE not in full:
            raise SystemExit(f"missing site {SITE!r}")
        full = full.replace(SITE, HTTP_BLOCK + SITE, 1)

    if SITE not in full:
        raise SystemExit("internal error: site marker lost")

    before, site_and_tail = full.split(SITE, 1)
    idx = site_and_tail.find(PROXY_NEEDLE)
    if idx == -1:
        raise SystemExit("reverse_proxy needle not found inside k9 site")
    chunk = site_and_tail[idx : idx + len(PROXY_NEEDLE) + 80]
    if HOST_LINE in chunk:
        print("Host header already present after proxy open.")
    else:
        site_and_tail = site_and_tail.replace(
            PROXY_NEEDLE,
            "    reverse_proxy http://168.100.11.140:3000 {\n"
            + HOST_LINE
            + "\n        header_up X-Forwarded-Proto",
            1,
        )
    full = before + SITE + site_and_tail

    if full != orig:
        CADDYFILE.write_text(full, encoding="utf-8")
        print(f"Updated {CADDYFILE}")
    else:
        print("No changes written.")


if __name__ == "__main__":
    main()
