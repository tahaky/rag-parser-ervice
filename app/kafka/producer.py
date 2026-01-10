import json
import uuid
from typing import Dict, Any
from datetime import datetime
from confluent_kafka import Producer

from app.config import settings
from app.utils.logging import get_logger
from app.utils.metrics import kafka_messages_produced

logger = get_logger(__name__)


class KafkaProducerClient:
    """Kafka producer client for publishing events."""

    def __init__(self):
        self.config = {
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "client.id": f"{settings.service_name}-producer",
        }
        self.producer: Producer = None

    def start(self):
        """Initialize the producer."""
        self.producer = Producer(self.config)
        logger.info("kafka_producer_started")

    def stop(self):
        """Stop the producer and flush remaining messages."""
        if self.producer:
            self.producer.flush(timeout=10)
            logger.info("kafka_producer_stopped")

    def _delivery_callback(self, err, msg):
        """Callback for message delivery reports."""
        if err:
            logger.error(
                "message_delivery_failed",
                topic=msg.topic(),
                error=str(err),
            )
        else:
            logger.debug(
                "message_delivered",
                topic=msg.topic(),
                partition=msg.partition(),
                offset=msg.offset(),
            )
            kafka_messages_produced.labels(topic=msg.topic()).inc()

    def publish_parsed_event(
        self,
        document_id: str,
        structure_id: str,
        format: str,
        parsed_at: datetime,
        parse_duration_ms: int,
    ):
        """Publish a document.parsed event."""
        event_data = {
            "event_id": str(uuid.uuid4()),
            "document_id": document_id,
            "structure_id": structure_id,
            "format": format,
            "parsed_at": parsed_at.isoformat(),
            "parse_duration_ms": parse_duration_ms,
            "parser_version": settings.parser_version,
        }

        self._publish(settings.kafka_topic_parsed, event_data)

    def publish_error_event(
        self,
        document_id: str,
        error_type: str,
        error_message: str,
        retryable: bool = False,
    ):
        """Publish an errors.processing event."""
        event_data = {
            "event_id": str(uuid.uuid4()),
            "document_id": document_id,
            "error_type": error_type,
            "error_message": error_message,
            "service": settings.service_name,
            "timestamp": datetime.utcnow().isoformat(),
            "retryable": retryable,
        }

        self._publish(settings.kafka_topic_errors, event_data)

    def _publish(self, topic: str, event_data: Dict[str, Any]):
        """Internal method to publish a message."""
        try:
            message = json.dumps(event_data).encode("utf-8")
            self.producer.produce(
                topic=topic,
                value=message,
                callback=self._delivery_callback,
            )
            # Trigger delivery reports
            self.producer.poll(0)

            logger.info("event_published", topic=topic, event_id=event_data.get("event_id"))

        except Exception as e:
            logger.error("publish_failed", topic=topic, error=str(e))
            raise
