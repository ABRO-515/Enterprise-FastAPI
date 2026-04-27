from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Optional
import aio_pika
from aio_pika import Channel, ExchangeType, Message, RobustConnection

from app.core.config import settings

logger = logging.getLogger("app.message_broker")

_connection: Optional[RobustConnection] = None
_channel: Optional[Channel] = None
_lock = asyncio.Lock()

EXCHANGE_NAME = "events"
DLX_NAME = "dlx"


# -------------------------
# CONNECTION INIT
# -------------------------
async def _get_channel() -> Channel:
    global _connection, _channel

    if _channel and not _channel.is_closed:
        return _channel

    async with _lock:
        if _channel and not _channel.is_closed:
            return _channel

        _connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        _channel = await _connection.channel(publisher_confirms=True)

        # MAIN TOPIC EXCHANGE
        await _channel.declare_exchange(
            EXCHANGE_NAME,
            ExchangeType.TOPIC,
            durable=True
        )

        # DLX (dead letter exchange)
        await _channel.declare_exchange(
            DLX_NAME,
            ExchangeType.TOPIC,
            durable=True
        )

        return _channel


# -------------------------
# PUBLISH (TOPIC)
# -------------------------
async def publish(routing_key: str, message: dict[str, Any]) -> None:
    channel = await _get_channel()

    exchange = await channel.get_exchange(EXCHANGE_NAME)

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **message,
    }

    msg = Message(
        json.dumps(payload).encode(),
        content_type="application/json",
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
    )

    await exchange.publish(msg, routing_key=routing_key)

    logger.info("Published event [%s]: %s", routing_key, message)


# -------------------------
# CONSUMER (SERVICE LEVEL)
# -------------------------
async def consume(
    queue_name: str,
    routing_patterns: list[str],
    handler: Callable[[dict[str, Any]], Awaitable[None]],
) -> None:
    """
    Each service defines its own queue + bindings.
    """

    channel = await _get_channel()

    queue = await channel.declare_queue(
        queue_name,
        durable=True,
        arguments={
            "x-dead-letter-exchange": DLX_NAME,
        },
    )

    exchange = await channel.get_exchange(EXCHANGE_NAME)

    # Bind patterns (THIS is real topic architecture)
    for pattern in routing_patterns:
        await queue.bind(exchange, routing_key=pattern)

    async def callback(message: aio_pika.IncomingMessage):
        async with message.process(requeue=False):
            try:
                body = json.loads(message.body)
                await handler(body)

            except Exception as e:
                logger.exception("Processing failed, sending to DLX: %s", e)

                dlx = await channel.get_exchange(DLX_NAME)

                await dlx.publish(
                    Message(
                        message.body,
                        content_type="application/json",
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    ),
                    routing_key=f"{queue_name}.failed",
                )

    await queue.consume(callback)

    logger.info("Consumer started: %s | patterns=%s", queue_name, routing_patterns)


# -------------------------
# INIT
# -------------------------x
async def init_rabbit() -> None:
    logger.info("RabbitMQ Service started ✅")
    await _get_channel()



# -------------------------
# EXPORTS (IMPORTANT)
# -------------------------

__all__ = [
    "publish",
    "consume",
    "init_rabbit",
]