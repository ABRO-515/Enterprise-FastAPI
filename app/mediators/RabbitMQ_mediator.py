from app.services.ai_service import ai_service
import logging

logger = logging.getLogger(__name__)


class ChatHandler:
    """
    Mediator between API layer and services
    """

    # -------------------------
    # USER MESSAGE FLOW
    # -------------------------

    async def handle_user_message(self, user_id: str, message: str):
        """
        Entry point from API or WebSocket
        """

        logger.info(f"Received message from user {user_id}")

        # 👉 send event to RabbitMQ via service layer
        result = await ai_service.process_user_message(user_id, message)

        return result

    # -------------------------
    # OPTIONAL: direct AI trigger (if needed later)
    # -------------------------

    async def trigger_ai_response(self, user_id: str, message: str):
        """
        Direct AI pipeline trigger (advanced use-case)
        """

        logger.info("Triggering AI response pipeline")

        return await ai_service.process_user_message(user_id, message)


# Singleton instance (recommended pattern)
chat_handler = ChatHandler()