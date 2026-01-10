import pytest
from unittest.mock import Mock, patch, MagicMock
from app.kafka.schemas import (
    DocumentUploadedEvent,
    DocumentParsedEvent,
    ErrorEvent,
    validate_event,
)


class TestEventSchemas:
    """Test cases for event schemas."""

    def test_valid_document_uploaded_event(self):
        """Test validation of valid document.uploaded event."""
        event_data = {
            "event_id": "123e4567-e89b-12d3-a456-426614174000",
            "document_id": "550e8400-e29b-41d4-a716-446655440000",
            "filename": "test.pdf",
            "format": "pdf",
            "storage_path": "documents/test.pdf",
            "uploaded_at": "2024-01-10T10:00:00Z",
            "checksum": "abc123",
        }

        from app.kafka.schemas import DocumentUploadedEvent, validate_event
        
        result = validate_event(event_data, DocumentUploadedEvent)
        assert result is not None
        assert result.document_id == "123"
        assert result.format == "pdf"

    def test_invalid_event(self):
        """Test validation fails for invalid event."""
        from app.kafka.schemas import DocumentUploadedEvent, validate_event
        
        invalid_event = {"document_id": "123"}  # Missing required fields
        result = validate_event(invalid_event, DocumentUploadedEvent)
        
        assert result is None
