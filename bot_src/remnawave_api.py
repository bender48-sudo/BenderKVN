import asyncio
import os
import logging
import base64
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

import aiohttp
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from shop_bot.config import (
    REMNA_API_CONNECT_TIMEOUT,
    REMNA_API_RETRY_ATTEMPTS,
    REMNA_API_TIMEOUT,
    REMNA_HTTP_CONN_LIMIT,
)

try:
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
    _HAS_CRYPTO = True
except Exception:  # pragma: no cover
    _HAS_CRYPTO = False

logger = logging.getLogger(__name__)

# ENV variables expected:
# REMNA_BASE_URL - e.g. https://panel.domain.com
# REMNA_API_TOKEN - Bearer token with API role (superadmin / API)
# REMNA_COOKIE - session cookie (e.g. olLRagjj=hPCTZLSX)
# REMNA_INBOUND_TAG - tag of inbound (e.g. "VLESS SWE") OR REMNA_INBOUND_UUID
# REMNA_SQUAD_UUID - UUID of internal squad for users
# REMNA_DEFAULT_DAYS - fallback days if not provided (optional)
# REMNA_SERVER_SNI - optional override for SNI (if need to force different host in URI)
# REMNA_FP - fingerprint value for utls (optional)

def _normalize_remna_base_url(url: str) -> str:
    """Panel API must hit :8443; :2053 redirects and aiohttp drops Bearer on port change."""
    u = (url or "").rstrip("/")
    if u.endswith(":2053"):
        return u[:-5] + ":8443"
    return u


BASE_URL = _normalize_remna_base_url(os.getenv("REMNA_BASE_URL", ""))
COOKIE = os.getenv("REMNA_COOKIE")
INBOUND_CACHE_TTL = int(os.getenv("REMNA_INBOUND_CACHE_TTL", "300"))
INBOUND_TAG = os.getenv("REMNA_INBOUND_TAG")
INBOUND_UUID = os.getenv("REMNA_INBOUND_UUID")
SQUAD_UUID = os.getenv("REMNA_SQUAD_UUID")
DEFAULT_DAYS = int(os.getenv("REMNA_DEFAULT_DAYS", "90"))
SERVER_SNI = os.getenv("REMNA_SERVER_SNI", "www.yandex.ru")
UTLS_FP = os.getenv("REMNA_FP") or os.getenv("FP")  # reuse old var if present

def get_api_token() -> str | None:
    """Read token at call time so rotation does not require bot restart (P5-ENG-03)."""
    return (os.getenv("REMNA_API_TOKEN") or "").strip() or None


def remna_client_timeout() -> aiohttp.ClientTimeout:
    """P2-RED-BOT-TIMEOUT-01: avoid hung monitor/scheduler on slow panel."""
    return aiohttp.ClientTimeout(
        connect=REMNA_API_CONNECT_TIMEOUT,
        total=REMNA_API_TIMEOUT,
    )


_TRANSIENT_HTTP = frozenset({502, 503, 504})
_shared_session: aiohttp.ClientSession | None = None
_session_lock = asyncio.Lock()

# P2-RED-BOT-BACKOFF-01: global circuit breaker after consecutive panel failures
_global_backoff_until: float = 0.0
_consecutive_failures: int = 0
_BACKOFF_FAIL_THRESHOLD = 3
_BACKOFF_PAUSE_SEC = 30

_INBOUND_REFRESH_LOCK = asyncio.Lock()
_INBOUND_STALE_GRACE_SEC = int(os.getenv("REMNA_INBOUND_STALE_GRACE_SEC", "60"))


class RemnaTransientHTTPError(Exception):
    """Retryable panel response (502/503/504)."""

    def __init__(self, status: int, method: str, path: str, body: str = ""):
        self.status = status
        self.method = method
        self.path = path
        self.body = body
        super().__init__(f"{method} {path} -> HTTP {status}")


def _retry_if_transient(exc: BaseException) -> bool:
    if isinstance(exc, RemnaTransientHTTPError):
        return True
    if isinstance(
        exc,
        (
            aiohttp.ClientConnectorError,
            aiohttp.ServerDisconnectedError,
            aiohttp.ClientOSError,
            asyncio.TimeoutError,
        ),
    ):
        return True
    if isinstance(exc, aiohttp.ClientResponseError) and exc.status in _TRANSIENT_HTTP:
        return True
    return False


def reset_global_backoff() -> None:
    """Clear circuit breaker (e.g. health_check recovery)."""
    global _global_backoff_until, _consecutive_failures
    _global_backoff_until = 0.0
    _consecutive_failures = 0


def _check_backoff() -> bool:
    """Return True if requests should be skipped (in backoff window)."""
    return time.time() < _global_backoff_until


def _record_api_success() -> None:
    global _consecutive_failures, _global_backoff_until
    _consecutive_failures = 0
    _global_backoff_until = 0.0


def _record_api_failure() -> None:
    global _consecutive_failures, _global_backoff_until
    _consecutive_failures += 1
    if _consecutive_failures >= _BACKOFF_FAIL_THRESHOLD:
        _global_backoff_until = time.time() + _BACKOFF_PAUSE_SEC
        logger.warning(
            "Remna global backoff %.0fs after %s consecutive failures",
            _BACKOFF_PAUSE_SEC,
            _consecutive_failures,
        )


def _log_remna_retry(retry_state) -> None:
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    logger.warning(
        "Remna API retry attempt %s/%s after %s: %s",
        retry_state.attempt_number,
        REMNA_API_RETRY_ATTEMPTS,
        getattr(retry_state, "seconds_since_start", 0),
        exc,
    )


async def get_remna_session() -> aiohttp.ClientSession:
    """P2-RED-BOT-POOL-01: one shared session for monitor/scheduler."""
    global _shared_session
    async with _session_lock:
        if _shared_session is None or _shared_session.closed:
            connector = aiohttp.TCPConnector(limit=REMNA_HTTP_CONN_LIMIT)
            _shared_session = aiohttp.ClientSession(
                timeout=remna_client_timeout(),
                connector=connector,
            )
        return _shared_session


async def close_remna_session() -> None:
    global _shared_session
    async with _session_lock:
        if _shared_session and not _shared_session.closed:
            await _shared_session.close()
        _shared_session = None


@asynccontextmanager
async def remna_client_session(**kwargs):
    """Yield shared session; does not close on exit (use close_remna_session on shutdown)."""
    if kwargs:
        timeout = kwargs.pop("timeout", None) or remna_client_timeout()
        async with aiohttp.ClientSession(timeout=timeout, **kwargs) as session:
            yield session
        return
    yield await get_remna_session()


async def _fetch_json_once(
    session: aiohttp.ClientSession, method: str, path: str, **kwargs
) -> Optional[dict]:
    url = f"{BASE_URL}{path}"
    async with session.request(method, url, headers=_request_headers(), **kwargs) as resp:
        txt = await resp.text()
        if resp.status in _TRANSIENT_HTTP:
            raise RemnaTransientHTTPError(resp.status, method, path, txt[:200])
        if resp.status >= 400:
            logger.error(f"Remna API {method} {path} failed {resp.status}: {txt}")
            return None
        try:
            data = await resp.json(content_type=None)
        except Exception:
            ct = resp.headers.get("Content-Type", "")
            if ct and "json" not in ct.lower():
                logger.warning(f"Non-JSON Content-Type from {path}: {ct}")
            logger.error(f"Failed to parse JSON from {path}: {txt[:200]}")
            return None
        return data


def _request_headers() -> dict[str, str]:
    hdrs: dict[str, str] = {}
    token = get_api_token()
    if token:
        hdrs["Authorization"] = f"Bearer {token}"
    if COOKIE:
        hdrs["Cookie"] = COOKIE
    return hdrs

class RemnaInbound:
    def __init__(self, uuid: str, tag: str, port: int, network: str, security: str, raw: dict):
        self.uuid = uuid
        self.tag = tag
        self.port = port
        self.network = network
        self.security = security
        self.raw = raw or {}

def _iso_expiry(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).replace(microsecond=0).isoformat().replace('+00:00', 'Z')

@retry(
    retry=retry_if_exception(_retry_if_transient),
    stop=stop_after_attempt(REMNA_API_RETRY_ATTEMPTS),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    before_sleep=_log_remna_retry,
    reraise=True,
)
async def _fetch_json_retrying(
    session: aiohttp.ClientSession, method: str, path: str, **kwargs
) -> Optional[dict]:
    return await _fetch_json_once(session, method, path, **kwargs)


async def _fetch_json(
    session: aiohttp.ClientSession, method: str, path: str, **kwargs
) -> Optional[dict]:
    if _check_backoff():
        logger.warning(
            "Remna API skipped (backoff %.1fs left): %s %s",
            _global_backoff_until - time.time(),
            method,
            path,
        )
        return None
    try:
        result = await _fetch_json_retrying(session, method, path, **kwargs)
        if result is not None:
            _record_api_success()
        else:
            _record_api_failure()
        return result
    except RemnaTransientHTTPError as e:
        logger.error("Remna API %s %s exhausted retries: HTTP %s", e.method, e.path, e.status)
        _record_api_failure()
        return None
    except Exception as e:
        if _retry_if_transient(e):
            logger.error("Remna API %s %s exhausted retries: %s", method, path, e)
        else:
            logger.error(f"HTTP error {method} {path}: {e}")
        _record_api_failure()
        return None

_INBOUND_CACHE: Optional[RemnaInbound] = None
_INBOUND_CACHE_AT: float = 0.0

def _parse_inbound_from_response(data: dict) -> Optional[RemnaInbound]:
    if not data or "response" not in data:
        return None
    inbounds = data["response"].get("inbounds", [])
    for inbound in inbounds:
        if INBOUND_UUID and inbound.get("uuid") == INBOUND_UUID:
            raw = inbound.get("rawInbound", {})
            return RemnaInbound(
                inbound["uuid"],
                inbound["tag"],
                inbound["port"],
                inbound["network"],
                inbound["security"],
                raw,
            )
        if INBOUND_TAG and inbound.get("tag") == INBOUND_TAG:
            raw = inbound.get("rawInbound", {})
            return RemnaInbound(
                inbound["uuid"],
                inbound["tag"],
                inbound["port"],
                inbound["network"],
                inbound["security"],
                raw,
            )
    return None


async def get_inbound(session: aiohttp.ClientSession, force_refresh: bool = False) -> Optional[RemnaInbound]:
    global _INBOUND_CACHE, _INBOUND_CACHE_AT
    now = time.time()
    if (
        _INBOUND_CACHE
        and not force_refresh
        and (now - _INBOUND_CACHE_AT) < INBOUND_CACHE_TTL
    ):
        return _INBOUND_CACHE
    if (
        _INBOUND_CACHE
        and not force_refresh
        and _INBOUND_REFRESH_LOCK.locked()
        and (now - _INBOUND_CACHE_AT) < INBOUND_CACHE_TTL + _INBOUND_STALE_GRACE_SEC
    ):
        logger.debug("inbound cache stale-within-grace during refresh")
        return _INBOUND_CACHE
    if not BASE_URL or not get_api_token():
        logger.error("Remna config incomplete: BASE_URL or API_TOKEN missing")
        return None
    async with _INBOUND_REFRESH_LOCK:
        now = time.time()
        if (
            _INBOUND_CACHE
            and not force_refresh
            and (now - _INBOUND_CACHE_AT) < INBOUND_CACHE_TTL
        ):
            return _INBOUND_CACHE
        data = await _fetch_json(session, "GET", "/api/config-profiles/inbounds")
        inbound = _parse_inbound_from_response(data) if data else None
        if inbound:
            _INBOUND_CACHE = inbound
            _INBOUND_CACHE_AT = time.time()
            return _INBOUND_CACHE
    logger.error("Desired inbound not found (tag/uuid)")
    return None

async def get_user_by_telegram_id(session: aiohttp.ClientSession, telegram_id: str) -> Optional[dict]:
    data = await _fetch_json(session, 'GET', f'/api/users/by-telegram-id/{telegram_id}')
    if data and 'response' in data:
        resp = data['response']
        if isinstance(resp, list) and resp:
            return resp[0]
        if isinstance(resp, dict):
            return resp
    return None


async def get_user_by_email(session: aiohttp.ClientSession, email: str) -> Optional[dict]:
    """Lookup panel user by subscription email (web-only customers)."""
    if not email:
        return None
    data = await _fetch_json(session, 'GET', f'/api/users/by-email/{email}')
    if data and 'response' in data:
        resp = data['response']
        if isinstance(resp, list) and resp:
            return resp[0]
        if isinstance(resp, dict):
            return resp
    return None

TRAFFIC_LIMIT_GB = int(os.getenv("REMNA_TRAFFIC_LIMIT_GB", "500"))  # 500 GB default
TRAFFIC_LIMIT_BYTES = TRAFFIC_LIMIT_GB * 1024 * 1024 * 1024
TRAFFIC_STRATEGY = os.getenv("REMNA_TRAFFIC_STRATEGY", "MONTH")  # MONTH resets monthly in panel

async def create_or_extend_user(session: aiohttp.ClientSession, inbound: RemnaInbound, email: str, days_to_add: int, telegram_id: str = None) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Returns (vless_uuid, subscription_url, expire_iso)"""
    existing = None
    if telegram_id:
        existing = await get_user_by_telegram_id(session, telegram_id)
    
    now = datetime.now(timezone.utc)
    if existing:
        # Update existing user
        expire_at_iso = existing.get('expireAt')
        try:
            current_exp = datetime.fromisoformat(expire_at_iso.replace('Z', '+00:00')) if expire_at_iso else now
        except Exception:
            current_exp = now
        base_dt = current_exp if current_exp > now else now
        new_exp = base_dt + timedelta(days=days_to_add)
        new_iso = new_exp.replace(microsecond=0).isoformat().replace('+00:00', 'Z')
        body = {
            "email": email,
            "uuid": existing.get('uuid'),
            "expireAt": new_iso,
            "trafficLimitBytes": TRAFFIC_LIMIT_BYTES,
            "trafficLimitStrategy": TRAFFIC_STRATEGY,
            # НЕ передаем username при обновлении существующего пользователя
        }
        if telegram_id:
            body["telegramId"] = int(telegram_id)
        updated = await _fetch_json(session, 'PATCH', '/api/users', json=body)
        if updated and 'response' in updated:
            u = updated['response']
            return u.get('vlessUuid'), u.get('subscriptionUrl'), u.get('expireAt')
        return None, None, None
    
    # Create new user
    new_iso = _iso_expiry(days_to_add)
    username = (email.split('@')[0])[:32]
    body = {
        "email": email,
        "username": username,
        "expireAt": new_iso,
        "trafficLimitBytes": TRAFFIC_LIMIT_BYTES,
        "trafficLimitStrategy": TRAFFIC_STRATEGY,
    }
    
    # Add telegram ID if provided (convert to int)
    if telegram_id:
        body["telegramId"] = int(telegram_id)
    
    # Add activeInternalSquads if SQUAD_UUID is configured
    if SQUAD_UUID:
        body["activeInternalSquads"] = [SQUAD_UUID]
    
    created = await _fetch_json(session, 'POST', '/api/users', json=body)
    if created and 'response' in created:
        u = created['response']
        return u.get('vlessUuid'), u.get('subscriptionUrl'), u.get('expireAt')
    return None, None, None

def _derive_public_key_from_private(private_b64: str) -> Optional[str]:
    """Derive Reality public key (base64, no padding) from private key if cryptography installed."""
    if not private_b64 or not _HAS_CRYPTO:
        return None
    try:
        priv_bytes = base64.b64decode(private_b64 + '==')  # tolerate missing padding
        priv = X25519PrivateKey.from_private_bytes(priv_bytes)
        pub = priv.public_key().public_bytes()
        b64 = base64.b64encode(pub).decode().rstrip('=').replace('+', '-').replace('/', '_')
        return b64
    except Exception as e:  # pragma: no cover
        logger.debug(f"Failed derive public key: {e}")
        return None

def build_vless_uri(inbound: RemnaInbound, vless_uuid: str, email: str) -> Optional[str]:
    if not inbound or not vless_uuid:
        return None
    reality = inbound.raw.get('streamSettings', {}).get('realitySettings', {})
    server_names = reality.get('serverNames') or []
    short_ids = reality.get('shortIds') or []
    if not server_names or not short_ids:
        logger.error("Reality settings incomplete")
        return None
    sni = SERVER_SNI or server_names[0]
    # NOTE: Remnawave full inbound JSON не возвращает publicKey Reality напрямую (есть только privateKey).
    # Пользователь должен указать REMNA_PUBLIC_KEY в .env (получается при настройке Reality пары ключей в Xray).
    pbk = (os.getenv('REMNA_PUBLIC_KEY') or '').strip()
    if not pbk:
        private_key = reality.get('privateKey')
        pbk = _derive_public_key_from_private(private_key) or ''
    if not pbk:
        logger.error("REMNA_PUBLIC_KEY missing; cannot build VLESS URI (P2-OPS-REMNA-KEY-01)")
        return None
    short_id = short_ids[0]
    fp = UTLS_FP or 'chrome'
    host = sni
    port = inbound.port
    flow = os.getenv('REMNA_FLOW', 'xtls-rprx-vision')  # default flow for VLESS Reality
    return (
        f"vless://{vless_uuid}@{host}:{port}?type={inbound.network}&security=reality&flow={flow}&fp={fp}&pbk={pbk}&sni={sni}&sid={short_id}&spx=%2F"
        f"#{inbound.tag}-{email}"
    )

async def provision_key(email: str, days: int | None = None, telegram_id: str = None) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    days = days or DEFAULT_DAYS
    t0 = time.perf_counter()
    async with remna_client_session() as session:
        inbound = await get_inbound(session)
        if not inbound:
            return None, None, None, None
        vless_uuid, sub_url, expire_iso = await create_or_extend_user(session, inbound, email, days, telegram_id)
        if not vless_uuid:
            return None, None, None, None
        uri = build_vless_uri(inbound, vless_uuid, email)
        elapsed = time.perf_counter() - t0
        if elapsed > 5.0:
            logger.warning(
                "provision_key slow %.2fs email=%s telegram_id=%s",
                elapsed,
                email,
                telegram_id,
            )
        else:
            logger.debug("provision_key %.2fs email=%s", elapsed, email)
        return uri, expire_iso, vless_uuid, sub_url

async def add_extra_traffic(email: str, extra_gb: int, telegram_id: str = None) -> bool:
    """Увеличивает лимит трафика пользователю на extra_gb (ГБ) на сервере.
    Возвращает True при успехе."""
    bytes_add = extra_gb * 1024 * 1024 * 1024
    async with remna_client_session() as session:
        user = None
        if telegram_id:
            user = await get_user_by_telegram_id(session, telegram_id)
        
        if not user:
            return False
        current_limit = user.get('trafficLimitBytes') or 0
        expire_at = user.get('expireAt') or _iso_expiry(DEFAULT_DAYS)
        body = {
            "email": email,
            "uuid": user.get('uuid'),
            "expireAt": expire_at,
            "trafficLimitBytes": current_limit + bytes_add,
            "trafficLimitStrategy": TRAFFIC_STRATEGY,
        }
        if telegram_id:
            body["telegramId"] = int(telegram_id)
        updated = await _fetch_json(session, 'PATCH', '/api/users', json=body)
        return bool(updated and 'response' in updated)

class RemnaWaveAPI:
    def __init__(self, base_url: str, token: str, cookie: str = None):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.cookie = cookie

    async def _fetch_json(self, endpoint: str):
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "accept": "application/json"
        }
        if self.cookie:
            headers["Cookie"] = self.cookie
        async with remna_client_session() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 404:
                    raise Exception(f"Remna API GET {endpoint} failed 404: {await response.text()}")
                response.raise_for_status()
                return await response.json()

    async def get_config_profiles_inbounds(self):
        data = await self._fetch_json("/api/config-profiles/inbounds")
        if "response" in data and "inbounds" in data["response"]:
            return data["response"]["inbounds"]
        else:
            raise Exception("Unexpected response format: missing 'inbounds' key")
