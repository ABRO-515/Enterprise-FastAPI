import asyncio
from app.message_broker import consume


async def notification_handler(message: dict):
    print("🔔 NOTIFICATION:", message)


async def main():
    await consume(
        queue_name="notification-service",
        routing_patterns=[
            "*.deleted",
        ],
        handler=notification_handler,
    )


if __name__ == "__main__":
    asyncio.run(main())