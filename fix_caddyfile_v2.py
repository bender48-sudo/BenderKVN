#!/usr/bin/env python3
"""Generate sanitized Caddyfile — OPSEC Stage 2 v2.
Uses site-level 'header' directive to strip Via/Alt-Svc/Server
since header_down inside reverse_proxy doesn't catch Caddy's own Via."""

import sys

input_path = sys.argv[1] if len(sys.argv) > 1 else "/etc/caddy/Caddyfile"
output_path = sys.argv[2] if len(sys.argv) > 2 else "/tmp/Caddyfile.new"

with open(input_path, "r") as f:
    original = f.read()

# Remove any existing global block or header_down we may have added
content = original

# Remove old global block if present
if content.startswith("{"):
    # Find matching closing brace
    depth = 0
    end = 0
    for i, ch in enumerate(content):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    content = content[end:].lstrip("\n")

# Remove any header_down lines we previously added
lines = content.split("\n")
lines = [l for l in lines if "header_down -Via" not in l
         and "header_down -Alt-Svc" not in l
         and "header_down -Server" not in l]
content = "\n".join(lines)

# Build new Caddyfile
new_lines = []

# Global options
new_lines.append("{")
new_lines.append("    admin off")
new_lines.append("    servers {")
new_lines.append("        protocols h1 h2")
new_lines.append("    }")
new_lines.append("}")
new_lines.append("")

# Process each site block
# Add header stripping to :9443 selfsteal blocks and proxy blocks
in_site = False
site_name = ""
brace_depth = 0
site_has_header_block = False

for line in content.split("\n"):
    stripped = line.strip()

    # Detect start of a site block (top-level, not nested)
    if brace_depth == 0 and stripped.endswith("{") and not stripped.startswith("#"):
        site_name = stripped[:-1].strip()
        in_site = True
        brace_depth = 1
        site_has_header_block = False
        new_lines.append(line)

        # Add header stripping for selfsteal :9443 blocks (not lv.conntest.xyz)
        if ":9443" in site_name and "lv.conntest.xyz" not in site_name:
            new_lines.append("    header {")
            new_lines.append("        -Via")
            new_lines.append("        -Alt-Svc")
            new_lines.append("        -Server")
            new_lines.append("    }")

        # Add header stripping for subscription/panel blocks
        elif ":2053" in site_name or ":2054" in site_name:
            new_lines.append("    header {")
            new_lines.append("        -Via")
            new_lines.append("        -Alt-Svc")
            new_lines.append("    }")

        continue

    if in_site:
        for ch in stripped:
            if ch == '{':
                brace_depth += 1
            elif ch == '}':
                brace_depth -= 1

        if brace_depth == 0:
            in_site = False

    new_lines.append(line)

result = "\n".join(new_lines)

with open(output_path, "w") as f:
    f.write(result)

# Stats
via_count = result.count("-Via")
alt_count = result.count("-Alt-Svc")
srv_count = result.count("-Server")
print(f"Sites with -Via: {via_count}")
print(f"Sites with -Alt-Svc: {alt_count}")
print(f"Sites with -Server: {srv_count}")
print(f"admin off: {'yes' if 'admin off' in result else 'no'}")
print(f"protocols h1 h2: {'yes' if 'protocols h1 h2' in result else 'no'}")
