"""Fortune wheel — server-authoritative spins + spin economy (GAME-FORTUNE-001, P5).

The SERVER decides the sector by weights (the front only animates to the returned sector — no
win logic on the client). Earned spins accrue at 1 per ``FORTUNE_SPIN_PER_DAYS`` paid active
days and accumulate; a ``extra_spin`` sector refunds the spin. Rub rewards are credited to the
wallet via ``balance_ledger`` (kind='fortune', ref='fortune:<spin_id>' — idempotent per spin).

Gated by ``fortune_live()`` (default OFF, like referral rewards): no spins and no credits happen
until an owner flips it on. Reads (status/history) serve honest zeros while off.

Weights (sum 100): Мимо 55 · Доп.спин 25 · +2₽ 14 · +5₽ 5 · +20₽ 0.9 · Джекпот +50₽ 0.1.
"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone

from shop_bot.config import FORTUNE_SPIN_PER_DAYS, fortune_live
from shop_bot.data_manager.database import credit_ledger, db_connection, get_user

logger = logging.getLogger(__name__)

# Server-authoritative sectors. ``weight`` never leaves the spin decision; the front gets only
# label/kind/amount for drawing the wheel + ``odds_pct`` for honest display.
SECTORS = [
    {"key": "miss", "label": "Мимо", "kind": "nothing", "amount_rub": 0, "weight": 55.0},
    {"key": "extra_spin", "label": "Доп. спин", "kind": "extra_spin", "amount_rub": 0, "weight": 25.0},
    {"key": "rub2", "label": "+2 ₽", "kind": "rub", "amount_rub": 2, "weight": 14.0},
    {"key": "rub5", "label": "+5 ₽", "kind": "rub", "amount_rub": 5, "weight": 5.0},
    {"key": "rub20", "label": "+20 ₽", "kind": "rub", "amount_rub": 20, "weight": 0.9},
    {"key": "jackpot", "label": "Джекпот +50 ₽", "kind": "rub", "amount_rub": 50, "weight": 0.1},
]
_TOTAL_WEIGHT = sum(s["weight"] for s in SECTORS)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _choose_sector() -> dict:
    """Weighted pick using a CSPRNG (unpredictable / non-gameable)."""
    r = secrets.randbelow(10_000_000) / 10_000_000 * _TOTAL_WEIGHT
    upto = 0.0
    for s in SECTORS:
        upto += s["weight"]
        if r < upto:
            return s
    return SECTORS[0]


def _paid_active_days(conn, user_id: int) -> int:
    """Real charged days = user_actions 'daily_balance:%' rows with a numeric (₽) meta."""
    rows = conn.execute(
        "SELECT meta FROM user_actions WHERE user_id = ? AND action LIKE 'daily_balance:%'",
        (int(user_id),),
    ).fetchall()
    n = 0
    for (meta,) in rows:
        try:
            if float(meta) > 0:
                n += 1
        except (TypeError, ValueError):
            pass
    return n


def _spins_done(conn, user_id: int) -> int:
    return int(conn.execute("SELECT COUNT(*) FROM fortune_spins WHERE user_id = ?", (int(user_id),)).fetchone()[0])


def _extra_granted(conn, user_id: int) -> int:
    return int(
        conn.execute(
            "SELECT COUNT(*) FROM fortune_spins WHERE user_id = ? AND sector_key = 'extra_spin'",
            (int(user_id),),
        ).fetchone()[0]
    )


def _available(conn, user_id: int) -> int:
    """earned(by paid days) + extra-spin refunds − spins already taken."""
    earned = _paid_active_days(conn, user_id) // max(1, FORTUNE_SPIN_PER_DAYS)
    return earned + _extra_granted(conn, user_id) - _spins_done(conn, user_id)


def _public_sectors() -> list[dict]:
    return [
        {"key": s["key"], "label": s["label"], "kind": s["kind"], "amount_rub": s["amount_rub"],
         "odds_pct": round(s["weight"] / _TOTAL_WEIGHT * 100, 2)}
        for s in SECTORS
    ]


def status(user_id: int) -> dict:
    """Counters + history + sector layout. Honest zeros while gated off."""
    if not get_user(int(user_id)):
        return {"ok": False, "error": "not_found"}
    with db_connection() as conn:
        paid = _paid_active_days(conn, user_id)
        avail = max(0, _available(conn, user_id))
        done = _spins_done(conn, user_id)
        rows = conn.execute(
            "SELECT sector_key, kind, amount_kopeks, created_at_utc FROM fortune_spins "
            "WHERE user_id = ? ORDER BY id DESC LIMIT 50",
            (int(user_id),),
        ).fetchall()
    remainder = paid % max(1, FORTUNE_SPIN_PER_DAYS)
    history = [
        {"sector_key": r[0], "kind": r[1], "amount_rub": round((r[2] or 0) / 100, 2), "at_iso": r[3]}
        for r in rows
    ]
    return {
        "ok": True,
        "fortune_live": fortune_live(),
        "available_spins": avail,
        "spins_done": done,
        "spin_per_days": FORTUNE_SPIN_PER_DAYS,
        "days_to_next_spin": (FORTUNE_SPIN_PER_DAYS - remainder) if avail == 0 else 0,
        "sectors": _public_sectors(),
        "history": history,
    }


def spin(user_id: int) -> dict:
    """Perform one spin (server-authoritative). Gated; credits rub rewards via ledger."""
    if not fortune_live():
        return {"ok": False, "error": "fortune_disabled"}
    if not get_user(int(user_id)):
        return {"ok": False, "error": "not_found"}

    # Atomically claim a spin slot + record the result.
    try:
        with db_connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            if _available(conn, user_id) <= 0:
                conn.rollback()
                return {"ok": False, "error": "no_spins"}
            sector = _choose_sector()
            amount_kopeks = int(sector["amount_rub"]) * 100
            cur = conn.execute(
                "INSERT INTO fortune_spins (user_id, sector_key, kind, amount_kopeks, created_at_utc) "
                "VALUES (?, ?, ?, ?, ?)",
                (int(user_id), sector["key"], sector["kind"], amount_kopeks, _now_iso()),
            )
            spin_id = cur.lastrowid
            conn.commit()
    except Exception as e:
        logger.error("fortune spin failed user=%s: %s", user_id, e)
        return {"ok": False, "error": "spin_failed"}

    # Credit a rub reward once (idempotent by ref). Spin slot is already consumed regardless.
    if sector["kind"] == "rub" and amount_kopeks > 0:
        ref = f"fortune:{spin_id}"
        if credit_ledger(int(user_id), "fortune", amount_kopeks, ref, meta=f'{{"sector":"{sector["key"]}"}}'):
            with db_connection() as conn:
                conn.execute("UPDATE fortune_spins SET ledger_ref = ? WHERE id = ?", (ref, spin_id))
                conn.commit()

    with db_connection() as conn:
        available_after = max(0, _available(conn, user_id))
    return {
        "ok": True,
        "spin_id": spin_id,
        "sector_key": sector["key"],
        "label": sector["label"],
        "kind": sector["kind"],
        "amount_rub": sector["amount_rub"],
        "available_spins": available_after,
    }
