// One-off: fetch Remnawave default subpage config and print JSON to stdout.
import https from "node:https";

const URL =
  "https://raw.githubusercontent.com/remnawave/backend/master/src/modules/subscription-page-configs/constants/default-subpage-config.ts";

const text = await new Promise((resolve, reject) => {
  https
    .get(URL, (res) => {
      let b = "";
      res.on("data", (c) => (b += c));
      res.on("end", () => resolve(b));
    })
    .on("error", reject);
});

const start = text.indexOf("{");
const end = text.lastIndexOf("};");
if (start < 0 || end < 0) {
  console.error("parse bounds failed");
  process.exit(1);
}
const objCode = text.slice(start, end + 1);
// eslint-disable-next-line no-eval
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const config = eval(`(${objCode})`);
const out =
  process.argv[2] ||
  path.join(path.dirname(fileURLToPath(import.meta.url)), "assets", "remnawave-default-subpage-config.json");
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, JSON.stringify(config, null, 2), "utf8");
console.error("wrote", out, "bytes", fs.statSync(out).size);
