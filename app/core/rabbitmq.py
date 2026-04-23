import pika
import json
from typing import Any, Dict


class RabbitMQClient:
    """
    Singleton RabbitMQ client for Topic Exchange publishing
    """

    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange_name = "app_topic_exchange"

    def connect(self):
        credentials = pika.PlainCredentials("hello", "hello")

        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host="localhost",
                port=5672,
                credentials=credentials
            )
        )

        self.channel = self.connection.channel()

        # Topic exchange (CORE of system)
        self.channel.exchange_declare(
            exchange=self.exchange_name,
            exchange_type="topic",
            durable=True
        )

    def publish_to_topic(
        self,
        routing_key: str,
        message: Dict[str, Any]
    ):
        """
        Generic topic publisher
        """

        if not self.channel:
            self.connect()

        self.channel.basic_publish(
            exchange=self.exchange_name,
            routing_key=routing_key,
            body=json.dumps(message),
        )

    def close(self):
        if self.connection:
            self.connection.close()


# Global instance
rabbitmq_client = RabbitMQClient()