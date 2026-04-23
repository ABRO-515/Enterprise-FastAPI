from app.services.event_publisher import event_publisher

def handle_user_message(user_id: str, message: str):

    # 1. publish event
    event_publisher.publish_chat_message_created(user_id, message)

    # 2. process logic (AI / DB / etc)

    response = f"AI response for: {message}"

    # 3. publish AI event
    event_publisher.publish_ai_response_generated(user_id, response)

    return response