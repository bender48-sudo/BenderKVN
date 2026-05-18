"""In-process payment webhook queue with SQLite idempotency and DLQ (P6-RED-PAY-01)."""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import queue
import threading
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from shop_bot.data_manager.database import (
    claim_webhook_delivery,
    mark_webhook_done,
    mark_webhook_failed,
    mark_webhook_processing,
)
from shop_bot.webhook_server.payload_redact import redact_webhook_payload
from shop_bot.webhook_server.payment_amount_verify import (
    verify_crypto_amount,
    verify_yookassa_amount,
)

logger = logging.getLogger(__name__)

PaymentProcessor = Callable[..., Awaitable[None]]


@dataclass(frozen=True)
class WebhookJob:
    idempotency_key: str
    source: str
    payload: dict[str, Any]


def idempotency_key_yookassa(event_json: dict[str, Any]) -> str | None:
    obj = event_json.get("object") or {}
    pay_id = obj.get("id")
    if pay_id:
        return f"yk:{pay_id}"
    return None


def idempotency_key_crypto(data: dict[str, Any]) -> str:
    for field in ("order_id", "invoice_id", "payment_id", "id", "uuid"):
        val = data.get(field)
        if val:
            return f"crypto:{field}:{val}"
    digest = hashlib.sha256(
        json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:32]
    return f"crypto:hash:{digest}"


def idempotency_key_cryptobot(data: dict[str, Any]) -> str:
    for field in ("invoice_id", "order_id", "id"):
        val = data.get(field)
        if val:
            return f"cryptobot:{val}"
    digest = hashlib.sha256(
        json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:32]
    return f"cryptobot:hash:{digest}"


class PaymentWebhookQueue:
    def __init__(self, bot: Any, payment_processor: PaymentProcessor, event_loop: asyncio.AbstractEventLoop):
        self._bot = bot
        self._payment_processor = payment_processor
        self._loop = event_loop
        self._q: queue.Queue[WebhookJob | None] = queue.Queue()
        self._worker = threading.Thread(target=self._run, name="payment-webhook-worker", daemon=True)
        self._worker.start()

    def submit(self, idempotency_key: str, source: str, payload: dict[str, Any]) -> str:
        stored = redact_webhook_payload(source, payload)
        payload_json = json.dumps(stored, ensure_ascii=False)
        status = claim_webhook_delivery(idempotency_key, source, payload_json)
        if status == "duplicate":
            logger.info("Webhook duplicate (done): %s", idempotency_key)
            return "duplicate"
        if status == "in_progress":
            logger.info("Webhook already queued/processing: %s", idempotency_key)
            return "in_progress"
        self._q.put(WebhookJob(idempotency_key, source, payload))
        return status

    def _run(self) -> None:
        while True:
            job = self._q.get()
            if job is None:
                break
            self._process_job(job)
            self._q.task_done()

    def _process_job(self, job: WebhookJob) -> None:
        mark_webhook_processing(job.idempotency_key)
        try:
            fut = asyncio.run_coroutine_threadsafe(
                self._dispatch(job), self._loop
            )
            fut.result(timeout=180)
            mark_webhook_done(job.idempotency_key)
        except Exception as exc:
            logger.error(
                "Webhook job failed %s (%s): %s",
                job.idempotency_key,
                job.source,
                exc,
                exc_info=True,
            )
            mark_webhook_failed(job.idempotency_key, str(exc))

    async def _dispatch(self, job: WebhookJob) -> None:
        if job.source == "yookassa":
            await self._handle_yookassa(job)
        elif job.source in ("crypto", "cryptobot"):
            await self._handle_crypto(job)
        else:
            raise ValueError(f"unknown webhook source: {job.source}")

    async def _handle_yookassa(self, job: WebhookJob) -> None:
        event_json = job.payload
        if event_json.get("event") != "payment.succeeded":
            return
        if not verify_yookassa_amount(event_json):
            raise ValueError("yookassa amount verification failed")
        metadata = (event_json.get("object") or {}).get("metadata") or {}
        obj = event_json.get("object") or {}
        if metadata.get("t") == "topup":
            from shop_bot.bot.handlers import process_topup_payment

            user_id = int(metadata.get("user_id") or metadata.get("u") or 0)
            amount_rub = float(metadata.get("amount") or metadata.get("a") or 0)
            await process_topup_payment(
                self._bot,
                user_id,
                amount_rub,
                idempotency_key=job.idempotency_key,
                notify=True,
            )
        elif metadata:
            metadata = dict(metadata)
            metadata["webhook_idempotency_key"] = job.idempotency_key
            await self._payment_processor(self._bot, metadata)

    async def _handle_crypto(self, job: WebhookJob) -> None:
        data = job.payload
        if data.get("status") != "paid":
            return
        if not verify_crypto_amount(data):
            raise ValueError("crypto amount verification failed")
        metadata = data.get("metadata") or data
        if not metadata:
            return
        meta = dict(metadata)
        meta["webhook_idempotency_key"] = job.idempotency_key
        await self._payment_processor(self._bot, meta)
