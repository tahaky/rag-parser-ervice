from typing import Dict, Any
from fastapi import FastAPI, Response, HTTPException
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import uuid

from app.utils.database import check_db_health, get_db_session
from app.utils.metrics import registry
from app.config import settings
from app.models import Document, DocumentStructure

app = FastAPI(title=settings.service_name)


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint with dependency checks.

    Returns:
        Health status of the service and its dependencies
    """
    checks = {
        "database": "unknown",
        "kafka": "unknown",
        "minio": "unknown",
    }

    # Check database
    try:
        checks["database"] = "healthy" if check_db_health() else "unhealthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)}"

    # Overall status
    overall_healthy = all(status == "healthy" for status in checks.values() if status != "unknown")

    return {
        "status": "healthy" if overall_healthy else "degraded",
        "service": settings.service_name,
        "version": settings.parser_version,
        "checks": checks,
    }


@app.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.

    Returns:
        Prometheus metrics in text format
    """
    metrics_output = generate_latest(registry)
    return Response(content=metrics_output, media_type=CONTENT_TYPE_LATEST)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": settings.service_name,
        "version": settings.parser_version,
        "status": "running",
    }


@app.get("/documents/{document_id}")
async def get_document(document_id: str) -> Dict[str, Any]:
    """
    Get document data by document_id.

    Args:
        document_id: Document UUID

    Returns:
        Document metadata and parsed structure

    Raises:
        HTTPException: 400 for invalid UUID, 404 if document not found
    """
    # Validate UUID format
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document_id format. Must be a valid UUID.")

    # Fetch document and structure from database
    with get_db_session() as session:
        # Get document
        document = session.query(Document).filter_by(id=doc_uuid).first()
        if not document:
            raise HTTPException(status_code=404, detail=f"Document with id {document_id} not found")

        # Get document structure
        structure = session.query(DocumentStructure).filter_by(document_id=doc_uuid).first()

        # Prepare response
        response = {
            "document_id": str(document.id),
            "filename": document.filename,
            "format": document.format,
            "status": document.status,
            "error_message": document.error_message,
            "uploaded_at": document.uploaded_at.isoformat() if document.uploaded_at else None,
            "updated_at": document.updated_at.isoformat() if document.updated_at else None,
        }

        # Add structure data if available
        if structure:
            response["structure"] = {
                "structure_id": str(structure.id),
                "structure": structure.structure,
                "metadata": structure.doc_metadata,
                "stats": structure.stats,
                "parsed_at": structure.parsed_at.isoformat() if structure.parsed_at else None,
                "parse_duration_ms": structure.parse_duration_ms,
                "parser_version": structure.parser_version,
                "checksum": structure.checksum,
            }
        else:
            response["structure"] = None

        return response
