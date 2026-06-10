"""Runtime environment classification and QA safety guards (QA-GUARD-001).

Mocks/dry-runs belong at integration boundaries only. Production defaults when
BVPN_ENV is unset so existing deploys keep working without new required env vars.
"""
from __future__ import annotations

import os
from enum import Enum
from pathlib import Path


class QaGuardError(RuntimeError):
    """Blocked sandbox/QA operation that would mutate production integrations."""


class BvpnEnvironment(str, Enum):
    PRODUCTION = "production"
    STAGING = "staging"
    LOCAL = "local"
    TEST = "test"


_VALID_ENVS = frozenset(m.value for m in BvpnEnvironment)
_DEFAULT_ENV = BvpnEnvironment.PRODUCTION


def _env_truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes")


def get_bvpn_env() -> BvpnEnvironment:
    """Classify runtime. Unset BVPN_ENV → production (conservative for guards)."""
    raw = (os.getenv("BVPN_ENV") or "").strip().lower()
    if not raw:
        return _DEFAULT_ENV
    if raw not in _VALID_ENVS:
        raise QaGuardError(
            f"Invalid BVPN_ENV={raw!r}. Use one of: {', '.join(sorted(_VALID_ENVS))}."
        )
    return BvpnEnvironment(raw)


def is_production() -> bool:
    return get_bvpn_env() == BvpnEnvironment.PRODUCTION


def is_non_production() -> bool:
    return get_bvpn_env() != BvpnEnvironment.PRODUCTION


def is_remna_dry_run() -> bool:
    return _env_truthy("BVPN_QA_DRY_RUN_REMNA")


def is_payments_dry_run() -> bool:
    return _env_truthy("BVPN_QA_DRY_RUN_PAYMENTS")


def require_non_production(context: str) -> None:
    """QA seed/fixture/matrix tools must call before any scenario mutation."""
    if is_production():
        raise QaGuardError(
            f"{context}: blocked in production (BVPN_ENV=production or unset). "
            "Set BVPN_ENV=staging, local, or test for sandbox tooling."
        )


def require_qa_tooling_enabled(context: str) -> None:
    """Stricter gate for ops scripts that mutate seeded scenario data."""
    require_non_production(context)
    if not _env_truthy("BVPN_QA_TOOLS_ENABLED"):
        raise QaGuardError(
            f"{context}: set BVPN_QA_TOOLS_ENABLED=1 together with "
            "BVPN_ENV=staging|local|test."
        )


def assert_remna_mutation_allowed(context: str) -> None:
    """Block real Remna create/extend/revoke in non-prod unless dry-run mode."""
    if is_production():
        return
    if is_remna_dry_run():
        return
    env = get_bvpn_env().value
    raise QaGuardError(
        f"{context}: Remna panel mutation blocked in BVPN_ENV={env}. "
        "Set BVPN_QA_DRY_RUN_REMNA=1 to use the dry-run provider, or run in production."
    )


def assert_yookassa_write_allowed(context: str) -> None:
    """Block real YooKassa Payment.create in non-prod unless dry-run mode."""
    if is_production():
        return
    if is_payments_dry_run():
        return
    env = get_bvpn_env().value
    raise QaGuardError(
        f"{context}: YooKassa write blocked in BVPN_ENV={env}. "
        "Set BVPN_QA_DRY_RUN_PAYMENTS=1 to use the dry-run payment provider."
    )


def assert_broadcast_allowed(context: str) -> None:
    """Block mass messaging / broadcast helpers in non-prod by default."""
    if is_production():
        return
    if _env_truthy("BVPN_QA_ALLOW_BROADCAST"):
        return
    env = get_bvpn_env().value
    raise QaGuardError(
        f"{context}: broadcast/mass user messaging blocked in BVPN_ENV={env}. "
        "Set BVPN_QA_ALLOW_BROADCAST=1 only for controlled staging tests."
    )


def resolve_shop_bot_db_path() -> Path:
    """Canonical shop DB path (SHOP_BOT_DB_PATH override or data/shop_bot.db)."""
    override = (os.getenv("SHOP_BOT_DB_PATH") or os.getenv("BVPN_QA_DB_PATH") or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    from shop_bot.data_manager.database import DB_FILE

    return Path(DB_FILE).resolve()


def assert_db_path_allowed_for_qa(db_path: str | os.PathLike[str], context: str) -> None:
    """Reject known production DB paths for sandbox/seed tooling."""
    require_non_production(context)
    resolved = Path(db_path).expanduser().resolve()
    prod_marker = (os.getenv("BVPN_PROD_DB_PATH") or "").strip()
    if prod_marker:
        prod = Path(prod_marker).expanduser().resolve()
        if resolved == prod:
            raise QaGuardError(
                f"{context}: refusing QA on production DB path {resolved}. "
                "Point SHOP_BOT_DB_PATH at an isolated staging/local database."
            )
    known_prod_paths = (
        "/app/data/shop_bot.db",
        "/var/lib/bendervpn/shop_bot.db",
    )
    for marker in known_prod_paths:
        if resolved == Path(marker).resolve():
            raise QaGuardError(
                f"{context}: path {resolved} looks like a production shop DB. "
                "Use SHOP_BOT_DB_PATH for an isolated QA database."
            )
