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
            "document_id": "550e8400-e29b-41d4-a716-446655440000",
            "original_name": "test.pdf",
            "storage_path": "documents/test.pdf",
            "file_size": 1024000,
            "mime_type": "application/pdf",
            "md5_checksum": "abc123def456",
            "user_id": "user-123",
            "organization_id": "org-456",
            "metadata": {"key": "value"},
            "timestamp": "2024-01-10T10:00:00Z",
        }

        from app.kafka.schemas import DocumentUploadedEvent, validate_event
        
        result = validate_event(event_data, DocumentUploadedEvent)
        assert result is not None
        assert result.document_id == "550e8400-e29b-41d4-a716-446655440000"
        assert result.original_name == "test.pdf"
        assert result.mime_type == "application/pdf"
        assert result.get_format() == "pdf"

    def test_invalid_event(self):
        """Test validation fails for invalid event."""
        from app.kafka.schemas import DocumentUploadedEvent, validate_event
        
        invalid_event = {"document_id": "123"}  # Missing required fields
        result = validate_event(invalid_event, DocumentUploadedEvent)
        
        assert result is None
    
    def test_get_format_from_mime_type_docx(self):
        """Test format extraction from DOCX MIME type."""
        event_data = {
            "document_id": "550e8400-e29b-41d4-a716-446655440000",
            "original_name": "test.docx",
            "storage_path": "documents/test.docx",
            "file_size": 1024000,
            "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "md5_checksum": "abc123def456",
            "user_id": "user-123",
            "organization_id": "org-456",
            "metadata": {},
            "timestamp": "2024-01-10T10:00:00Z",
        }
        
        event = DocumentUploadedEvent(**event_data)
        assert event.get_format() == "docx"
    
    def test_get_format_from_mime_type_xlsx(self):
        """Test format extraction from XLSX MIME type."""
        event_data = {
            "document_id": "550e8400-e29b-41d4-a716-446655440000",
            "original_name": "test.xlsx",
            "storage_path": "documents/test.xlsx",
            "file_size": 1024000,
            "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "md5_checksum": "abc123def456",
            "user_id": "user-123",
            "organization_id": "org-456",
            "metadata": {},
            "timestamp": "2024-01-10T10:00:00Z",
        }
        
        event = DocumentUploadedEvent(**event_data)
        assert event.get_format() == "xlsx"
    
    def test_get_format_from_filename_fallback(self):
        """Test format extraction from filename when MIME type is unknown."""
        event_data = {
            "document_id": "550e8400-e29b-41d4-a716-446655440000",
            "original_name": "test.pptx",
            "storage_path": "documents/test.pptx",
            "file_size": 1024000,
            "mime_type": "application/octet-stream",
            "md5_checksum": "abc123def456",
            "user_id": "user-123",
            "organization_id": "org-456",
            "metadata": {},
            "timestamp": "2024-01-10T10:00:00Z",
        }
        
        event = DocumentUploadedEvent(**event_data)
        assert event.get_format() == "pptx"
