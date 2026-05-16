#!/usr/bin/env python3
"""Generate sanitized Caddyfile for Latvia — OPSEC Stage 2"""

with open("/etc/caddy/Caddyfile", "r") as f:
    content = f.read()

# 1. Add global options block at the very beginning
global_block = """{
    admin off
    servers {
        protocols h1 h2
    }
}

"""
if not content.startswith("{"):
    content = global_block + content

# 2. For each :9443 reverse_proxy block, add header_down directives
# Strategy: find each "header_up -X-Forwarded-Host" and insert header_down after it
lines = content.split("\n")
new_lines = []
in_9443_block = False
i = 0
while i < len(lines):
    line = lines[i]

    # Track if we're in a :9443 site block
    if ":9443 {" in line and "lv.conntest.xyz" not in line:
        in_9443_block = True

    # Insert header_down after the last header_up in selfsteal reverse_proxy
    if in_9443_block and "header_up -X-Forwarded-Host" in line:
        new_lines.append(line)
        # Add header_down directives
        new_lines.append("        header_down -Via")
        new_lines.append("        header_down -Alt-Svc")
        new_lines.append("        header_down -Server")
        i += 1
        continue

    # End of site block
    if in_9443_block and line.strip() == "}" and not any(
        lines[max(0, i-1)].strip().startswith(k)
        for k in ["transport", "reverse_proxy", "tls_server_name", "dial_timeout", "versions"]
    ):
        # Check if previous non-empty line closes a nested block
        prev_stripped = ""
        for j in range(i - 1, max(0, i - 5), -1):
            if lines[j].strip():
                prev_stripped = lines[j].strip()
                break
        if prev_stripped == "}":
            in_9443_block = False

    new_lines.append(line)
    i += 1

content = "\n".join(new_lines)

# 3. Fix subscription proxy — add header_down after header_up lines
content = content.replace(
    '        header_up X-Forwarded-For {remote_host}\n'
    '    }\n'
    '}\n'
    '\n'
    ':2054 {',
    '        header_up X-Forwarded-For {remote_host}\n'
    '        header_down -Via\n'
    '        header_down -Alt-Svc\n'
    '    }\n'
    '}\n'
    '\n'
    ':2054 {'
)

# 4. Fix :2054 panel proxy
content = content.replace(
    ':2054 {\n'
    '    reverse_proxy http://127.0.0.1:3000 {\n'
    '        header_up X-Forwarded-Proto "https"\n'
    '        header_up X-Forwarded-For {remote_host}\n'
    '    }\n'
    '}',
    ':2054 {\n'
    '    reverse_proxy http://127.0.0.1:3000 {\n'
    '        header_up X-Forwarded-Proto "https"\n'
    '        header_up X-Forwarded-For {remote_host}\n'
    '        header_down -Via\n'
    '        header_down -Alt-Svc\n'
    '    }\n'
    '}'
)

# 5. Fix k9x2m1 panel proxy
content = content.replace(
    'k9x2m1.conntest.xyz:2053 {\n'
    '    reverse_proxy http://127.0.0.1:3000 {\n'
    '        header_up X-Forwarded-Proto "https"\n'
    '        header_up X-Forwarded-For {remote_host}\n'
    '    }\n'
    '}',
    'k9x2m1.conntest.xyz:2053 {\n'
    '    reverse_proxy http://127.0.0.1:3000 {\n'
    '        header_up X-Forwarded-Proto "https"\n'
    '        header_up X-Forwarded-For {remote_host}\n'
    '        header_down -Via\n'
    '        header_down -Alt-Svc\n'
    '    }\n'
    '}'
)

with open("/tmp/Caddyfile.new", "w") as f:
    f.write(content)

# Stats
via_count = content.count("header_down -Via")
alt_count = content.count("header_down -Alt-Svc")
srv_count = content.count("header_down -Server")
print(f"header_down -Via: {via_count} blocks")
print(f"header_down -Alt-Svc: {alt_count} blocks")
print(f"header_down -Server: {srv_count} blocks")
print(f"admin off: {'yes' if 'admin off' in content else 'no'}")
print(f"protocols h1 h2: {'yes' if 'protocols h1 h2' in content else 'no'}")
