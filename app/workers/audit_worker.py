import asyncio
from app.message_broker import consume


async def audit_handler(message: dict):
    print("🧾 AUDIT LOG:", message)


async def main():
    await consume(
        queue_name="audit-service",
        routing_patterns=[
            "user.*",   # wildcard → ALL user events
        ],
        handler=audit_handler,
    )


if __name__ == "__main__":
    asyncio.run(main())