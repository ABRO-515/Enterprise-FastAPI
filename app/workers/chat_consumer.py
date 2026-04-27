import asyncio
import logging
import logging
logging.basicConfig(level=logging.INFO)
from app.message_broker import consume

logger = logging.getLogger(__name__)


async def handle_message(data):
    logger.info(f"🔥 consumer received: {data}")


async def consume_events():
    await consume(
        queue_name="chat_queue",
        routing_patterns=["chat.*"],
        handler=handle_message
    )

    logger.info("🚀 consumer is now listening for chat events")

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(consume_events())