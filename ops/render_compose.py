"""Render a sanitized template from compose/ with real secrets from a vault.

Usage as CLI:
    python ops/render_compose.py [--only K1,K2 | --none] <template-path> [<vault-path>]

  --only K1,K2   Replace only these ${K} placeholders (for docker-compose files
                 that must keep ${POSTGRES_*} for Compose interpolation).
  --none         Replace no placeholders (sanity / copy-through after manual edit).

Defaults:
    vault-path = .secrets/vault.env
    substitute = all keys present in vault (same as drift-check "panel .env" mode)

Used both as a CLI helper (render to stdout) and as a library
(`load_vault`, `render_file`) by ops/drift-check.py for sanitized-md5
comparison.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_VAULT = ROOT / ".secrets" / "vault.env"

# Matches ${NAME} placeholders in templates (uppercase + underscore).
PH = re.compile(r'\$\{([A-Z_][A-Z0-9_]*)\}')


def load_vault(path: Path = DEFAULT_VAULT) -> dict[str, str]:
    """Read KEY=VALUE pairs (one per line, # comments OK). Returns {KEY: VALUE}.

    If the file is missing, returns {} (callers track missing keys explicitly).
    Values may be wrapped in single or double quotes; quotes are stripped.
    """
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip()
        if (v.startswith('"') and v.endswith('"')) or \
           (v.startswith("'") and v.endswith("'")):
            v = v[1:-1]
        out[k] = v
    return out


def render_text(text: str, vault: dict[str, str], missing: set[str],
                only_substitute: frozenset[str] | None = None) -> str:
    """Replace every ${PLACEHOLDER} per rules.

    If only_substitute is None, every placeholder found in vault is expanded;
    placeholders not listed in vault are left as '${NAME}' AND name is pushed
    to `missing'.

    If only_substitute is a set (possibly empty): replace **only when**
    NAME ∈ only_substitute **and** NAME ∈ vault. All other ${NAME} text is
    left untouched (needed for docker-compose files that keep ${POSTGRES_*}
    for Compose-time interpolation, and for ``$${VAR}`` escaping where the
    regex would otherwise see a false ${VAR} match after the first ``$``).
    """

    def sub(m: re.Match) -> str:
        name = m.group(1)
        if only_substitute is not None and name not in only_substitute:
            return m.group(0)
        if name in vault:
            return vault[name]
        if only_substitute is None:
            missing.add(name)
        return m.group(0)

    return PH.sub(sub, text)


def render_file(path: Path, vault: dict[str, str], missing: set[str],
                only_substitute: frozenset[str] | None = None) -> bytes:
    """Render a template file and return rendered bytes (utf-8 encoded)."""
    txt = path.read_text(encoding="utf-8")
    out = render_text(txt, vault, missing, only_substitute=only_substitute)
    return out.encode("utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Render compose/*.tmpl with vault env.")
    g = ap.add_mutually_exclusive_group()
    g.add_argument(
        "--only",
        metavar="K1,K2",
        help="comma-separated placeholder names to substitute (others left as ${KEY})",
    )
    g.add_argument(
        "--none",
        action="store_true",
        help="substitute nothing (output template bytes as-is re-encoded)",
    )
    ap.add_argument(
        "template",
        help="path to .tmpl under repo (e.g. compose/ams/remnawave/panel.env.tmpl)",
    )
    ap.add_argument(
        "vault",
        nargs="?",
        default=str(DEFAULT_VAULT),
        help=f"vault file (default: {DEFAULT_VAULT})",
    )
    ns = ap.parse_args()

    tmpl = Path(ns.template)
    if not tmpl.is_absolute():
        tmpl = ROOT / tmpl
    vault_path = Path(ns.vault)
    if not vault_path.is_absolute():
        vault_path = ROOT / vault_path

    if not tmpl.exists():
        sys.exit(f"template not found: {tmpl}")
    vault = load_vault(vault_path)

    if ns.none:
        only_substitute: frozenset[str] | None = frozenset()
    elif ns.only:
        only_substitute = frozenset(k.strip() for k in ns.only.split(",") if k.strip())
    else:
        only_substitute = None

    missing: set[str] = set()
    rendered = render_file(tmpl, vault, missing,
                           only_substitute=only_substitute)
    sys.stdout.buffer.write(rendered)
    if missing:
        print(f"\n# WARN: vault missing keys: {sorted(missing)}",
              file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
