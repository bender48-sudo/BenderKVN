import re
val = open("/tmp/subtok.val").read().strip()
path = "/opt/remnawave/sub/docker-compose.yml"
c = open(path).read()
c2, n = re.subn(r"REMNAWAVE_API_TOKEN=\S+", "REMNAWAVE_API_TOKEN=" + val, c, count=1)
if n != 1:
    raise SystemExit(f"replace count {n}")
open(path, "w").write(c2)
print("ok")
