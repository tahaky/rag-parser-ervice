import uuid
import time
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

from app.models import Document, DocumentStructure
from app.parsers.factory import ParserFactory
from app.services.storage import StorageService
from app.utils.database import get_db_session
from app.utils.logging import get_logger
from app.utils.metrics import (
    documents_parsed_total,
    parse_duration_seconds,
    parse_errors_total,
    database_operation_errors,
)
from app.config import settings

logger = get_logger(__name__)


class DocumentService:
    """Service for processing documents."""

    def __init__(self, storage_service: StorageService):
        self.storage = storage_service

    def process_document(
        self,
        document_id: str,
        filename: str,
        format: str,
        storage_path: str,
        checksum: Optional[str] = None,
        file_size: Optional[int] = None,
        mime_type: Optional[str] = None,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process a document: download, parse, and save.

        Args:
            document_id: Document UUID
            filename: Original filename
            format: Document format
            storage_path: Path in MinIO
            checksum: Optional checksum for idempotency
            file_size: Optional file size in bytes
            mime_type: Optional MIME type
            user_id: Optional user ID
            organization_id: Optional organization ID
            metadata: Optional additional metadata

        Returns:
            Dictionary with structure_id and parse_duration_ms

        Raises:
            ValueError: For parsing errors
            Exception: For other errors
        """
        temp_file = None
        start_time = time.time()

        try:
            # Check for existing structure (idempotency)
            if self._check_existing_structure(document_id, checksum):
                logger.info(
                    "document_already_parsed",
                    document_id=document_id,
                    checksum=checksum,
                )
                # Return existing structure
                with get_db_session() as session:
                    structure = (
                        session.query(DocumentStructure)
                        .filter_by(document_id=uuid.UUID(document_id))
                        .first()
                    )
                    return {
                        "structure_id": str(structure.id),
                        "parse_duration_ms": structure.parse_duration_ms,
                        "skipped": True,
                    }

            # Download file
            logger.info(
                "downloading_document", 
                document_id=document_id, 
                storage_path=storage_path,
                file_size=file_size,
                user_id=user_id,
                organization_id=organization_id
            )
            temp_file = self.storage.download_file(storage_path)

            # Parse document
            logger.info("parsing_document", document_id=document_id, format=format)
            parser = ParserFactory.get_parser(format)
            parsed_data = parser.parse(temp_file)

            # Calculate duration
            parse_duration_ms = int((time.time() - start_time) * 1000)
            parse_duration_seconds.labels(format=format).observe(time.time() - start_time)

            # Save to database
            structure_id = self._save_structure(
                document_id=document_id,
                format=format,
                parsed_data=parsed_data,
                parse_duration_ms=parse_duration_ms,
                checksum=checksum,
            )

            # Update document status
            self._update_document_status(document_id, "parsed")

            # Record metrics
            documents_parsed_total.labels(format=format, status="success").inc()

            logger.info(
                "document_parsed_successfully",
                document_id=document_id,
                structure_id=structure_id,
                parse_duration_ms=parse_duration_ms,
            )

            return {
                "structure_id": structure_id,
                "parse_duration_ms": parse_duration_ms,
                "skipped": False,
            }

        except ValueError as e:
            # Non-retryable parsing errors
            parse_errors_total.labels(format=format, error_type="parsing_error").inc()
            documents_parsed_total.labels(format=format, status="failed").inc()
            logger.error("parsing_failed", document_id=document_id, error=str(e))
            self._update_document_status(document_id, "parse_failed", str(e))
            raise

        except Exception as e:
            # Other errors (potentially retryable)
            parse_errors_total.labels(format=format, error_type="system_error").inc()
            logger.error("document_processing_failed", document_id=document_id, error=str(e))
            raise

        finally:
            # Cleanup temp file
            if temp_file:
                self.storage.cleanup_file(temp_file)

    def _check_existing_structure(
        self, document_id: str, checksum: Optional[str]
    ) -> bool:
        """Check if structure already exists for this document."""
        try:
            with get_db_session() as session:
                query = session.query(DocumentStructure).filter_by(
                    document_id=uuid.UUID(document_id)
                )
                if checksum:
                    query = query.filter_by(checksum=checksum)
                return query.first() is not None
        except Exception as e:
            logger.warning("idempotency_check_failed", error=str(e))
            return False

    def _save_structure(
        self,
        document_id: str,
        format: str,
        parsed_data: Dict[str, Any],
        parse_duration_ms: int,
        checksum: Optional[str],
    ) -> str:
        """Save parsed structure to database."""
        try:
            with get_db_session() as session:
                structure = DocumentStructure(
                    id=uuid.uuid4(),
                    document_id=uuid.UUID(document_id),
                    format=format,
                    structure=parsed_data["structure"],
                    doc_metadata=parsed_data["metadata"],
                    stats=parsed_data["stats"],
                    parsed_at=datetime.utcnow(),
                    parse_duration_ms=parse_duration_ms,
                    parser_version=settings.parser_version,
                    checksum=checksum,
                )
                session.add(structure)
                session.commit()
                return str(structure.id)
        except SQLAlchemyError as e:
            database_operation_errors.labels(operation="save_structure").inc()
            logger.error("save_structure_failed", document_id=document_id, error=str(e))
            raise

    def _update_document_status(
        self, document_id: str, status: str, error_message: Optional[str] = None
    ):
        """Update document status in database."""
        try:
            with get_db_session() as session:
                document = session.query(Document).filter_by(id=uuid.UUID(document_id)).first()
                if document:
                    document.status = status
                    document.error_message = error_message
                    document.updated_at = datetime.utcnow()
                    session.commit()
                else:
                    # Create document if it doesn't exist
                    document = Document(
                        id=uuid.UUID(document_id),
                        filename="",
                        format="",
                        status=status,
                        error_message=error_message,
                    )
                    session.add(document)
                    session.commit()
        except SQLAlchemyError as e:
            database_operation_errors.labels(operation="update_status").inc()
            logger.warning("update_document_status_failed", document_id=document_id, error=str(e))
