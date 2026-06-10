"""QA dry-run Remna provider (QA-REMNA-DRYRUN-001).

Returns production-shaped tuples without calling the panel API.
Active only when BVPN_ENV is non-production and BVPN_QA_DRY_RUN_REMNA=1.
Never activates in production.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

_SANDBOX_HOST = "sandbox.invalid"
_FORBIDDEN_HOST_FRAGMENTS = (
    "kitsura.fun",
    "bendervpn",
    "yandex.ru",
    ":8443",
    ":2053",
)


def should_use_remna_dry_run() -> bool:
    from shop_bot.runtime_env import is_production, is_remna_dry_run

    if is_production():
        return False
    return is_remna_dry_run()


def _dryrun_vless_uuid(email: str) -> str:
    digest = hashlib.sha256(f"qa-remna:{email}".encode()).hexdigest()
    return str(uuid.UUID(digest[:32]))


def _dryrun_expire_iso(days: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(days=max(0, int(days)))
    return exp.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _dryrun_sub_url(vless_uuid: str) -> str:
    short = vless_uuid.replace("-", "")[:12]
    return f"https://{_SANDBOX_HOST}/sub/qa-{short}"


def _dryrun_vless_uri(vless_uuid: str, email: str) -> str:
    local = (email.split("@")[0] if email else "qa")[:32]
    return (
        f"vless://{vless_uuid}@{_SANDBOX_HOST}:443"
        f"?dryrun=1&security=none#qa-{local}"
    )


def dryrun_provision_key(
    email: str,
    days: int | None = None,
    telegram_id: str | None = None,
) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """Same return shape as remnawave_api.provision_key — no panel HTTP."""
    _ = telegram_id
    d = int(days or 90)
    vless_uuid = _dryrun_vless_uuid(email)
    expire_iso = _dryrun_expire_iso(d)
    sub_url = _dryrun_sub_url(vless_uuid)
    uri = _dryrun_vless_uri(vless_uuid, email)
    return uri, expire_iso, vless_uuid, sub_url


def dryrun_add_extra_traffic(
    email: str,
    extra_gb: int,
    telegram_id: str | None = None,
) -> bool:
    """Pretend traffic pack applied — no panel PATCH."""
    _ = (email, extra_gb, telegram_id)
    return True


def dryrun_set_user_access_days(days: int) -> str | None:
    """Return synthetic expireAt for balance-driven access updates."""
    if int(days) <= 0:
        return _dryrun_expire_iso(0)
    return _dryrun_expire_iso(int(days))


def assert_dummy_response_safe(uri: str | None, sub_url: str | None) -> None:
    """Test helper: dummy URLs must not resemble production endpoints."""
    for value in (uri or "", sub_url or ""):
        lower = value.lower()
        if _SANDBOX_HOST not in lower:
            raise AssertionError(f"dry-run URL must use {_SANDBOX_HOST}: {value!r}")
        for frag in _FORBIDDEN_HOST_FRAGMENTS:
            if frag in lower:
                raise AssertionError(f"dry-run URL must not contain {frag!r}: {value!r}")
