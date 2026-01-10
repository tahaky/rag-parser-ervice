import json
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, ValidationError
from datetime import datetime


class DocumentUploadedEvent(BaseModel):
    """Schema for document.uploaded event."""

    document_id: str = Field(..., description="Document UUID")
    original_name: str = Field(..., description="Original filename")
    storage_path: str = Field(..., description="Object key in MinIO")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="MIME type of the document")
    md5_checksum: str = Field(..., description="MD5 checksum")
    user_id: str = Field(..., description="User ID who uploaded the document")
    organization_id: str = Field(..., description="Organization ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    timestamp: str = Field(..., description="Upload timestamp")
    
    def get_format(self) -> str:
        """
        Derive document format from MIME type for backward compatibility.
        
        Returns:
            Format string (docx, pdf, pptx, xlsx)
        """
        mime_to_format = {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
            "application/msword": "doc",
            "application/pdf": "pdf",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
            "application/vnd.ms-powerpoint": "ppt",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
            "application/vnd.ms-excel": "xls",
        }
        
        # Try exact match first
        if self.mime_type in mime_to_format:
            return mime_to_format[self.mime_type]
        
        # Try to extract from filename extension as fallback
        if "." in self.original_name:
            ext = self.original_name.rsplit(".", 1)[-1].lower()
            if ext in ["docx", "doc", "pdf", "pptx", "ppt", "xlsx", "xls"]:
                return ext
        
        # Default to pdf if cannot determine
        return "pdf"


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
