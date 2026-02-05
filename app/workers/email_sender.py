"""Example background worker that consumes notification events and sends emails.

Run with:
    uv run python -m app.workers.email_sender
"""
from __future__ import annotations

import asyncio
import json
import logging

from app.queue import consume, init_rabbit

logger = logging.getLogger("app.email_sender")


async def handle_email(payload: dict[str, str]) -> None:  # pragma: no cover
    logger.info("Send email notification: %s", json.dumps(payload))
    # Here you would integrate an actual email service.


async def main() -> None:  # pragma: no cover
    await init_rabbit()
    await consume("notification.events", handle_email)
    # Keep running
    await asyncio.Future()


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level="INFO")
    asyncio.run(main())
