#!/usr/bin/env python3
"""
Main entry point for the RAG Parser Service worker.

This service:
- Consumes document.uploaded events from Kafka
- Downloads files from MinIO
- Parses documents into structured JSON
- Saves results to PostgreSQL
- Publishes document.parsed or error events
"""

import sys
import os
import threading
import uvicorn

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.config import settings
from app.utils.logging import setup_logging, get_logger
from app.utils.database import init_db
from app.kafka.consumer import KafkaConsumerClient
from app.kafka.producer import KafkaProducerClient
from app.services.storage import StorageService
from app.services.document import DocumentService
from app.services.worker_pool import WorkerPool
from app.api import app

# Setup logging
setup_logging()
logger = get_logger(__name__)


def start_api_server():
    """Start FastAPI server for health and metrics endpoints."""
    config = uvicorn.Config(
        app,
        host=settings.health_check_host,
        port=settings.health_check_port,
        log_config=None,  # Use structlog instead
    )
    server = uvicorn.Server(config)
    server.run()


def main():
    """Main entry point."""
    logger.info(
        "starting_parser_service",
        service=settings.service_name,
        version=settings.parser_version,
        worker_count=settings.worker_count,
    )

    try:
        # Initialize database
        logger.info("initializing_database")
        init_db()

        # Create service instances
        storage_service = StorageService()
        document_service = DocumentService(storage_service)
        consumer = KafkaConsumerClient()
        producer = KafkaProducerClient()

        # Start API server in background thread
        logger.info("starting_api_server", port=settings.health_check_port)
        api_thread = threading.Thread(target=start_api_server, daemon=True)
        api_thread.start()

        # Create and start worker pool
        worker_pool = WorkerPool(consumer, producer, document_service)
        worker_pool.start()

    except KeyboardInterrupt:
        logger.info("service_interrupted")
        sys.exit(0)
    except Exception as e:
        logger.error("service_startup_failed", error=str(e), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
