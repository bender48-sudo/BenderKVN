import os, re

new_url = "https://apps.apple.com/ru/app/happ-proxy-utility-plus/id6746188973"
files_fixed = []

for root, dirs, files in os.walk("/opt/remna-shop/src"):
    for f in files:
        if not f.endswith(".py"):
            continue
        path = os.path.join(root, f)
        with open(path) as fh:
            content = fh.read()
        if "apps.apple.com" not in content:
            continue
        new_content = re.sub(
            r'https://apps\.apple\.com[^\s"\'\\)]+',
            new_url,
            content
        )
        if new_content != content:
            old_urls = re.findall(r'https://apps\.apple\.com[^\s"\'\\)]+', content)
            for u in old_urls:
                print(f"  {path}: {u} -> {new_url}")
            with open(path, "w") as fh:
                fh.write(new_content)
            files_fixed.append(path)

if not files_fixed:
    print("ERROR: No URLs found")
else:
    print(f"SUCCESS: Fixed {len(files_fixed)} file(s)")
