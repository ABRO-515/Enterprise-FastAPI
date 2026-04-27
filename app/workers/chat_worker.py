import asyncio
import logging
from app.message_broker import consume

logger = logging.getLogger(__name__)


async def handle_chat_event(data):
    logger.info(f"🔥 Worker received: {data}")


async def main():
    await consume(
        queue_name="chat_queue",
        routing_patterns=["chat.*"],
        handler=handle_chat_event
    )

    logger.info("🚀 Worker is now listening for chat events")

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())

        