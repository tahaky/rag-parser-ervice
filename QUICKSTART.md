# Quick Start Guide

This guide will help you get the RAG Parser Service up and running quickly.

## Prerequisites

- Docker and Docker Compose installed
- OR Python 3.11+ with pip

## Option 1: Docker Compose (Recommended)

The fastest way to run the entire stack:

```bash
# Clone the repository
git clone https://github.com/tahaky/rag-parser-ervice.git
cd rag-parser-ervice

# Start all services (PostgreSQL, Kafka, MinIO, Parser Service)
docker-compose up -d

# Check service health
curl http://localhost:8080/health

# View logs
docker-compose logs -f parser-service

# View Prometheus metrics
curl http://localhost:8080/metrics
```

### Access Services

- **Parser Service Health**: http://localhost:8080/health
- **Parser Service Metrics**: http://localhost:8080/metrics
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)
- **PostgreSQL**: localhost:5432 (parser/parser)
- **Kafka**: localhost:9092

### Stop Services

```bash
docker-compose down
```

## Option 2: Local Development

### 1. Install Dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For testing
```

### 2. Setup External Services

You need to have running:
- PostgreSQL (port 5432)
- Kafka (port 9092)
- MinIO (port 9000)

Or use Docker for dependencies only:

```bash
# Start only PostgreSQL, Kafka, and MinIO
docker-compose up -d postgres kafka zookeeper minio minio-setup
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

### 4. Initialize Database

```bash
# Run migrations
alembic upgrade head

# Or let the service create tables on startup
```

### 5. Run the Service

```bash
python cmd/worker/main.py
```

The service will start and:
- Connect to Kafka, PostgreSQL, and MinIO
- Start the health check API on port 8080
- Begin consuming from `document.uploaded` topic

## Testing the Service

### 1. Upload a Test Document to MinIO

Using MinIO client (mc):

```bash
# Configure mc client
mc alias set myminio http://localhost:9000 minioadmin minioadmin

# Create bucket if not exists
mc mb myminio/documents

# Upload a test file
mc cp test.pdf myminio/documents/test.pdf
```

### 2. Publish a Test Event to Kafka

Using kafkacat or similar:

```bash
echo '{
  "event_id": "test-001",
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "test.pdf",
  "format": "pdf",
  "storage_path": "test.pdf",
  "uploaded_at": "2024-01-10T10:00:00Z",
  "checksum": null
}' | kafkacat -b localhost:9092 -t document.uploaded -P
```

### 3. Monitor Processing

Watch the logs:

```bash
# Docker
docker-compose logs -f parser-service

# Local
# Logs go to stdout
```

### 4. Verify Results

Check PostgreSQL:

```bash
docker-compose exec postgres psql -U parser -d parser_db -c "SELECT * FROM document_structures;"
```

Check Kafka for parsed event:

```bash
kafkacat -b localhost:9092 -t document.parsed -C
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_parser_factory.py -v

# Run specific test
pytest tests/unit/test_docx_parser.py::TestDocxParser::test_parse_docx -v
```

## Monitoring

### Health Check

```bash
curl http://localhost:8080/health
```

Response:
```json
{
  "status": "healthy",
  "service": "rag-parser-service",
  "version": "1.0.0",
  "checks": {
    "database": "healthy",
    "kafka": "healthy",
    "minio": "healthy"
  }
}
```

### Prometheus Metrics

```bash
curl http://localhost:8080/metrics
```

Key metrics:
- `documents_parsed_total{format="pdf",status="success"}`
- `parse_duration_seconds_bucket{format="pdf",le="5.0"}`
- `parse_errors_total{format="pdf",error_type="parsing_error"}`
- `active_workers`
- `kafka_consumer_lag{topic="document.uploaded",partition="0"}`

## Troubleshooting

### Service won't start

1. Check if all dependencies are running:
   ```bash
   docker-compose ps
   ```

2. Check logs for errors:
   ```bash
   docker-compose logs parser-service
   ```

3. Verify environment variables:
   ```bash
   docker-compose exec parser-service env | grep -E 'KAFKA|DATABASE|MINIO'
   ```

### Database connection issues

```bash
# Test connection manually
docker-compose exec postgres psql -U parser -d parser_db -c "SELECT 1;"
```

### Kafka connection issues

```bash
# List topics
docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9093
```

### MinIO connection issues

```bash
# Test MinIO health
curl http://localhost:9000/minio/health/live
```

### Parser errors

Check the logs for specific error types:
- **ValueError**: Non-retryable parsing error (corrupted file)
- **S3Error**: MinIO download failure (retryable)
- **SQLAlchemyError**: Database error (retryable)

## Development Workflow

1. Make code changes
2. Run tests: `pytest`
3. Run linting: `black app/ tests/ && flake8 app/ tests/`
4. Test locally: `python cmd/worker/main.py`
5. Build Docker image: `docker-compose build`
6. Test with Docker: `docker-compose up`

## Next Steps

- Review the full [README.md](README.md) for detailed documentation
- Check [IMPLEMENTATION.md](IMPLEMENTATION.md) for implementation details
- Explore the parsers in `app/parsers/`
- Customize configuration in `.env`
- Add your own document format parsers

## Support

For issues and questions:
- GitHub Issues: https://github.com/tahaky/rag-parser-ervice/issues
- Documentation: See README.md and code comments
