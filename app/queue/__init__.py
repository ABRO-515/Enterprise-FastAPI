"""RabbitMQ helper using aio-pika.

Provides:
    - init_rabbit(): lazy connection/channel initialiser.
    - publish(exchange, routing_key, message): publish persistent JSON message.
    - consume(queue_name, handler): attach async consumer that processes JSON messages.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Optional

import aio_pika
from aio_pika import Channel, DeliveryMode, Exchange, Message, RobustConnection

from app.core.config import settings

logger = logging.getLogger("app.queue")

_connection: Optional[RobustConnection] = None
_channel: Optional[Channel] = None
_lock = asyncio.Lock()


async def _ensure_channel() -> Channel:  # noqa: C901
    global _connection, _channel
    if _channel and not _channel.is_closed:
        return _channel

    async with _lock:
        if _channel and not _channel.is_closed:
            return _channel

        _connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        _channel = await _connection.channel(publisher_confirms=True)

        # Declare exchanges and DLX once
        dlx = await _channel.declare_exchange("dlx", aio_pika.ExchangeType.TOPIC, durable=True)
        events = await _channel.declare_exchange("events", aio_pika.ExchangeType.TOPIC, durable=True)

        queues = [
            "user.events",
            "order.events",
            "notification.events",
        ]
        for q in queues:
            queue = await _channel.declare_queue(q, durable=True, arguments={"x-dead-letter-exchange": "dlx"})
            await queue.bind(events, routing_key=q)

        # dead-letter queue
        await _channel.declare_queue("dlx.queue", durable=True)
        await _channel.default_exchange.bind(dlx, routing_key="#")

        return _channel


async def publish(exchange_name: str, routing_key: str, message: dict[str, Any]) -> None:
    channel = await _ensure_channel()
    exchange: Exchange = await channel.get_exchange(exchange_name)
    payload = json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(), **message}).encode()
    msg = Message(payload, delivery_mode=DeliveryMode.PERSISTENT, content_type="application/json")
    await exchange.publish(msg, routing_key=routing_key)
    logger.debug("Published %s to %s:%s", message, exchange_name, routing_key)


async def consume(queue_name: str, handler: Callable[[dict[str, Any]], Awaitable[None]]) -> None:
    channel = await _ensure_channel()
    queue = await channel.declare_queue(queue_name, durable=True)

    async def _callback(message: aio_pika.IncomingMessage) -> None:  # noqa: WPS430
        async with message.process(requeue=False):
            try:
                body = json.loads(message.body)
                await handler(body)
            except Exception as exc:  # pylint: disable=broad-except
                logger.exception("Handler failed, sending to DLQ: %s", exc)
                dlx: Exchange = await channel.get_exchange("dlx")
                await dlx.publish(
                    Message(message.body, delivery_mode=DeliveryMode.PERSISTENT),
                    routing_key=f"dlx.{queue_name}",
                )

    await queue.consume(_callback, no_ack=False)
    logger.info("Consuming queue %s", queue_name)


async def init_rabbit() -> None:
    await _ensure_channel()
