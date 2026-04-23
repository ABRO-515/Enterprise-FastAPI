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

result = channel.queue_declare(queue="", exclusive=True)
queue_name = result.method.queue

channel.queue_bind(
    exchange="app_topic_exchange",
    queue=queue_name,
    routing_key="chat.#"
)

def callback(ch, method, properties, body):
    print("Received:", method.routing_key, json.loads(body))

channel.basic_consume(
    queue=queue_name,
    on_message_callback=callback,
    auto_ack=True
)

print("Waiting for messages...")
channel.start_consuming()