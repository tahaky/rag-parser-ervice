import json
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, ValidationError
from datetime import datetime


class DocumentUploadedEvent(BaseModel):
    """Schema for document.uploaded event."""

    event_id: str = Field(..., description="Unique event ID")
    document_id: str = Field(..., description="Document UUID")
    filename: str = Field(..., description="Original filename")
    format: str = Field(..., description="Document format (docx, pdf, pptx, xlsx)")
    storage_path: str = Field(..., description="Object key in MinIO")
    uploaded_at: str = Field(..., description="Upload timestamp")
    checksum: Optional[str] = Field(None, description="MD5 checksum if available")


class DocumentParsedEvent(BaseModel):
    """Schema for document.parsed event."""

    event_id: str = Field(..., description="Unique event ID")
    document_id: str = Field(..., description="Document UUID")
    structure_id: str = Field(..., description="DocumentStructure UUID")
    format: str = Field(..., description="Document format")
    parsed_at: str = Field(..., description="Parse timestamp")
    parse_duration_ms: int = Field(..., description="Parse duration in milliseconds")
    parser_version: str = Field(..., description="Parser version used")


class ErrorEvent(BaseModel):
    """Schema for errors.processing event."""

    event_id: str = Field(..., description="Unique event ID")
    document_id: str = Field(..., description="Document UUID")
    error_type: str = Field(..., description="Error type classification")
    error_message: str = Field(..., description="Error description")
    service: str = Field(..., description="Service name")
    timestamp: str = Field(..., description="Error timestamp")
    retryable: bool = Field(..., description="Whether error is retryable")


def validate_event(event_data: Dict[str, Any], event_class) -> Optional[BaseModel]:
    """
    Validate event data against schema.

    Args:
        event_data: Raw event dictionary
        event_class: Pydantic model class

    Returns:
        Validated event instance or None if invalid
    """
    try:
        return event_class(**event_data)
    except ValidationError as e:
        return None
