import json
from typing import Optional, Callable, Dict, Any
from confluent_kafka import Consumer, KafkaError, KafkaException, TopicPartition
from confluent_kafka.admin import AdminClient

from app.config import settings
from app.utils.logging import get_logger
from app.utils.metrics import kafka_messages_consumed, kafka_consumer_lag

logger = get_logger(__name__)


class KafkaConsumerClient:
    """Kafka consumer client with manual commit."""

    def __init__(self):
        self.config = {
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "group.id": settings.kafka_consumer_group,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
            "max.poll.interval.ms": settings.kafka_max_poll_interval_ms,
            "session.timeout.ms": settings.kafka_session_timeout_ms,
        }
        self.consumer: Optional[Consumer] = None
        self.running = False

    def start(self):
        """Initialize and start the consumer."""
        self.consumer = Consumer(self.config)
        self.consumer.subscribe([settings.kafka_topic_uploaded])
        self.running = True
        logger.info(
            "kafka_consumer_started",
            topic=settings.kafka_topic_uploaded,
            group=settings.kafka_consumer_group,
        )

    def stop(self):
        """Stop the consumer gracefully."""
        self.running = False
        if self.consumer:
            self.consumer.close()
            logger.info("kafka_consumer_stopped")

    def poll(self, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """
        Poll for a message.

        Args:
            timeout: Poll timeout in seconds

        Returns:
            Message data as dict or None
        """
        if not self.consumer or not self.running:
            return None

        try:
            msg = self.consumer.poll(timeout=timeout)

            if msg is None:
                return None

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    logger.debug("reached_end_of_partition", partition=msg.partition())
                    return None
                else:
                    raise KafkaException(msg.error())

            # Parse message
            value = json.loads(msg.value().decode("utf-8"))
            kafka_messages_consumed.labels(topic=msg.topic()).inc()

            logger.info(
                "message_received",
                topic=msg.topic(),
                partition=msg.partition(),
                offset=msg.offset(),
            )

            return {
                "value": value,
                "topic": msg.topic(),
                "partition": msg.partition(),
                "offset": msg.offset(),
                "message": msg,  # Store raw message for commit
            }

        except json.JSONDecodeError as e:
            logger.error("message_decode_failed", error=str(e))
            # Still need to commit to skip bad message
            if msg:
                self.commit_message(msg)
            return None
        except Exception as e:
            logger.error("poll_error", error=str(e))
            raise

    def commit_message(self, msg):
        """Commit message offset."""
        if self.consumer:
            try:
                self.consumer.commit(message=msg)
                logger.debug("offset_committed", partition=msg.partition(), offset=msg.offset())
            except Exception as e:
                logger.error("commit_failed", error=str(e))

    def get_lag(self) -> Dict[str, int]:
        """Get consumer lag for monitoring (best effort)."""
        if not self.consumer:
            return {}

        try:
            lag_info = {}
            committed = self.consumer.committed(
                self.consumer.assignment(), timeout=5.0
            )

            for tp in committed:
                if tp.offset >= 0:
                    # Get high water mark
                    low, high = self.consumer.get_watermark_offsets(tp, timeout=5.0)
                    lag = high - tp.offset
                    lag_info[f"{tp.topic}-{tp.partition}"] = lag
                    kafka_consumer_lag.labels(
                        topic=tp.topic, partition=str(tp.partition)
                    ).set(lag)

            return lag_info
        except Exception as e:
            logger.warning("lag_calculation_failed", error=str(e))
            return {}

    def check_health(self) -> bool:
        """Check Kafka connectivity."""
        try:
            admin_client = AdminClient({"bootstrap.servers": settings.kafka_bootstrap_servers})
            metadata = admin_client.list_topics(timeout=5)
            return True
        except Exception as e:
            logger.error("kafka_health_check_failed", error=str(e))
            return False
