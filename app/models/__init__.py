import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Text, JSON, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Document(Base):
    """Document metadata table for status tracking."""

    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    format = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="uploaded")  # uploaded, parsed, parse_failed
    error_message = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class DocumentStructure(Base):
    """Parsed document structure table."""

    __tablename__ = "document_structures"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    format = Column(String(50), nullable=False)
    structure = Column(JSONB, nullable=False)
    metadata = Column(JSONB, nullable=False)
    stats = Column(JSONB, nullable=False)
    parsed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    parse_duration_ms = Column(Integer, nullable=False)
    parser_version = Column(String(50), nullable=False)
    checksum = Column(String(64), nullable=True, index=True)  # MD5 hash for idempotency
