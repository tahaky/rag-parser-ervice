from typing import Dict, Any
from fastapi import FastAPI, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.utils.database import check_db_health
from app.utils.metrics import registry
from app.config import settings

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
