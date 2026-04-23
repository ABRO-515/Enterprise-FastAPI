from app.core.rabbitmq import rabbitmq_client


class EventPublisher:

    # -------------------------
    # CHAT EVENTS
    # -------------------------

    def publish_chat_message_created(self, user_id: str, message: str):
        rabbitmq_client.publish_to_topic(
            routing_key="chat.message.created",
            message={
                "user_id": user_id,
                "message": message
            }
        )

    def publish_chat_message_processed(self, message_id: str):
        rabbitmq_client.publish_to_topic(
            routing_key="chat.message.processed",
            message={
                "message_id": message_id
            }
        )

    # -------------------------
    # AI EVENTS
    # -------------------------

    def publish_ai_response_generated(self, user_id: str, response: str):
        rabbitmq_client.publish_to_topic(
            routing_key="chat.ai.response.generated",
            message={
                "user_id": user_id,
                "response": response
            }
        )

    # -------------------------
    # ERROR EVENTS
    # -------------------------

    def publish_error(self, service: str, error: str):
        rabbitmq_client.publish_to_topic(
            routing_key="chat.error.occurred",
            message={
                "service": service,
                "error": error
            }
        )


event_publisher = EventPublisher()