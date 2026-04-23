from app.core.rabbitmq import rabbitmq_client

rabbitmq_client.publish_to_topic(
    routing_key="chat.test.event",
    message={"msg": "RabbitMQ is working!"}
)

print("Message sent 🚀")