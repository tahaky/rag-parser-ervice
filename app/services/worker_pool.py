import time
import signal
import threading
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, Future
from queue import Queue

from app.config import settings
from app.kafka.consumer import KafkaConsumerClient
from app.kafka.producer import KafkaProducerClient
from app.kafka.schemas import DocumentUploadedEvent, validate_event
from app.services.document import DocumentService
from app.services.storage import StorageService
from app.utils.logging import get_logger
from app.utils.metrics import active_workers

logger = get_logger(__name__)


class WorkerPool:
    """Thread pool for processing documents with retry logic."""

    def __init__(
        self,
        consumer: KafkaConsumerClient,
        producer: KafkaProducerClient,
        document_service: DocumentService,
    ):
        self.consumer = consumer
        self.producer = producer
        self.document_service = document_service
        self.executor = ThreadPoolExecutor(max_workers=settings.worker_count)
        self.running = False
        self.shutdown_event = threading.Event()
        self.in_flight_jobs: Dict[str, Future] = {}
        self.lock = threading.Lock()

    def start(self):
        """Start the worker pool."""
        self.running = True
        self.consumer.start()
        self.producer.start()

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        logger.info("worker_pool_started", worker_count=settings.worker_count)

        # Main processing loop
        try:
            while self.running:
                self._process_messages()
                
                # Update lag metrics periodically
                if int(time.time()) % 30 == 0:
                    self.consumer.get_lag()

        except KeyboardInterrupt:
            logger.info("keyboard_interrupt_received")
        finally:
            self._shutdown()

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info("shutdown_signal_received", signal=signum)
        self.running = False
        self.shutdown_event.set()

    def _process_messages(self):
        """Process messages from Kafka."""
        msg_data = self.consumer.poll(timeout=1.0)

        if not msg_data:
            return

        try:
            # Validate event schema
            event_data = msg_data["value"]
            event = validate_event(event_data, DocumentUploadedEvent)

            if not event:
                logger.error("invalid_event_schema", event_data=event_data)
                self.producer.publish_error_event(
                    document_id=event_data.get("document_id", "unknown"),
                    error_type="invalid_schema",
                    error_message="Event failed schema validation",
                    retryable=False,
                )
                # Commit to skip invalid message
                self.consumer.commit_message(msg_data["message"])
                return

            # Submit job to thread pool
            logger.info(
                "submitting_job", 
                document_id=event.document_id,
                user_id=event.user_id,
                organization_id=event.organization_id
            )
            
            future = self.executor.submit(
                self._process_document_with_retry,
                event=event,
                message=msg_data["message"],
            )

            with self.lock:
                self.in_flight_jobs[event.document_id] = future
                active_workers.set(len(self.in_flight_jobs))

            # Wait for completion to ensure proper ordering
            future.result()

        except Exception as e:
            logger.error("message_processing_error", error=str(e))
            # Commit to avoid reprocessing
            if msg_data.get("message"):
                self.consumer.commit_message(msg_data["message"])

    def _process_document_with_retry(self, event: DocumentUploadedEvent, message):
        """Process document with retry logic."""
        document_id = event.document_id
        retry_count = 0
        last_error = None

        try:
            while retry_count <= settings.max_retries:
                try:
                    # Get format from mime_type
                    format = event.get_format()
                    
                    # Process document
                    result = self.document_service.process_document(
                        document_id=document_id,
                        filename=event.original_name,
                        format=format,
                        storage_path=event.storage_path,
                        checksum=event.md5_checksum,
                        file_size=event.file_size,
                        mime_type=event.mime_type,
                        user_id=event.user_id,
                        organization_id=event.organization_id,
                        metadata=event.metadata,
                    )

                    # Publish success event
                    self.producer.publish_parsed_event(
                        document_id=document_id,
                        structure_id=result["structure_id"],
                        format=format,
                        parsed_at=datetime.utcnow(),
                        parse_duration_ms=result["parse_duration_ms"],
                    )

                    # Commit offset
                    self.consumer.commit_message(message)

                    logger.info(
                        "document_processed_successfully",
                        document_id=document_id,
                        retry_count=retry_count,
                    )
                    return

                except ValueError as e:
                    # Non-retryable parsing error
                    logger.error(
                        "non_retryable_error",
                        document_id=document_id,
                        error=str(e),
                    )
                    self.producer.publish_error_event(
                        document_id=document_id,
                        error_type="parsing_error",
                        error_message=str(e),
                        retryable=False,
                    )
                    # Commit to skip
                    self.consumer.commit_message(message)
                    return

                except Exception as e:
                    # Potentially retryable error
                    last_error = e
                    retry_count += 1

                    if retry_count <= settings.max_retries:
                        backoff = settings.retry_backoff_list[
                            min(retry_count - 1, len(settings.retry_backoff_list) - 1)
                        ]
                        logger.warning(
                            "retrying_after_error",
                            document_id=document_id,
                            retry_count=retry_count,
                            backoff_seconds=backoff,
                            error=str(e),
                        )
                        time.sleep(backoff)
                    else:
                        logger.error(
                            "max_retries_exceeded",
                            document_id=document_id,
                            error=str(last_error),
                        )
                        self.producer.publish_error_event(
                            document_id=document_id,
                            error_type="max_retries_exceeded",
                            error_message=str(last_error),
                            retryable=False,
                        )
                        # Commit to avoid infinite loop
                        self.consumer.commit_message(message)
                        return

        finally:
            # Remove from in-flight jobs
            with self.lock:
                self.in_flight_jobs.pop(document_id, None)
                active_workers.set(len(self.in_flight_jobs))


    def _shutdown(self):
        """Gracefully shutdown the worker pool."""
        logger.info("shutting_down_worker_pool")

        # Stop accepting new messages
        self.running = False

        # Wait for in-flight jobs with timeout
        logger.info("waiting_for_in_flight_jobs", count=len(self.in_flight_jobs))
        self.executor.shutdown(wait=True)

        # Close clients
        self.consumer.stop()
        self.producer.stop()

        logger.info("worker_pool_shutdown_complete")


from datetime import datetime
