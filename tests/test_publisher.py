import pika
import json

credentials = pika.PlainCredentials("hello", "hello")

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host="localhost", port=5672, credentials=credentials)
)

channel = connection.channel()

channel.exchange_declare(
    exchange="app_topic_exchange",
    exchange_type="topic",
    durable=True
)

message = {
    "user_id": "123",
    "message": "Hello from topic exchange"
}

channel.basic_publish(
    exchange="app_topic_exchange",
    routing_key="chat.message.created",
    body=json.dumps(message)
)

print("Message sent 🚀")
connection.close()