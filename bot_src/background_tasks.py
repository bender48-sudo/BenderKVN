"""Track fire-and-forget asyncio tasks (P2-RED-BOT-INTEGRITY-01)."""
from __future__ import annotations

import asyncio

_tasks: set[asyncio.Task] = set()


def create_background_task(coro) -> asyncio.Task:
    task = asyncio.create_task(coro)
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return task
