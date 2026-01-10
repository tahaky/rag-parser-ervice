# RAG Parser Service

A production-ready document parsing service for RAG (Retrieval-Augmented Generation) systems. This service consumes document upload events from Kafka, downloads files from MinIO/S3, parses them into structured JSON, saves results to PostgreSQL, and publishes parsed events or error events.

## Features

- **Multi-format Support**: Parses DOCX, PDF, PPTX, and XLSX documents
- **Kafka Integration**: Consumes and produces events with manual offset management
- **MinIO/S3 Storage**: Streams large files efficiently with size limits
- **PostgreSQL Storage**: Stores structured parsing results with idempotency
- **Robust Error Handling**: Automatic retries with exponential backoff
- **Observability**: 
  - Structured JSON logging with structlog
  - Prometheus metrics for monitoring
  - Health check endpoints
- **Production Ready**:
  - Graceful shutdown on SIGTERM/SIGINT
  - Thread pool for concurrent processing
  - Memory efficient (&lt;2GB per worker)
  - Docker support

## Architecture

```
Kafka (document.uploaded) 
    → Worker Pool 
    → MinIO Download 
    → Parser (DOCX/PDF/PPTX/XLSX) 
    → PostgreSQL 
    → Kafka (document.parsed or errors.processing)
```

## Prerequisites

- Python 3.11+
- PostgreSQL 13+
- Kafka 2.8+
- MinIO or S3-compatible storage

## Installation

### Local Development

1. Clone the repository:
```bash
git clone https://github.com/tahaky/rag-parser-ervice.git
cd rag-parser-ervice
```

2. Install dependencies:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development
```

3. Copy environment configuration:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Initialize the database:
```bash
alembic upgrade head
```

5. Run the service:
```bash
python cmd/worker/main.py
```

### Docker Deployment

1. Build and run with Docker Compose:
```bash
docker-compose up -d
```

This starts:
- PostgreSQL database
- MinIO storage
- Kafka + Zookeeper
- Parser service

2. Check service health:
```bash
curl http://localhost:8080/health
```

## Configuration

All configuration is managed through environment variables. See `.env.example` for all available options.

### Key Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka broker addresses | `localhost:9092` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://parser:parser@localhost:5432/parser_db` |
| `MINIO_ENDPOINT` | MinIO endpoint | `localhost:9000` |
| `WORKER_COUNT` | Number of concurrent workers | `4` |
| `MAX_RETRIES` | Maximum retry attempts | `3` |
| `RETRY_BACKOFF_SECONDS` | Retry backoff intervals | `5,15,45` |
| `MAX_FILE_SIZE_MB` | Maximum file size limit | `500` |
| `ENABLE_OCR` | Enable OCR for images | `false` |

## API Endpoints

### Health Check
```bash
GET /health
```

Returns health status of the service and its dependencies.

### Metrics
```bash
GET /metrics
```

Returns Prometheus metrics in text format.

## Kafka Topics

### Consumed Topics

**document.uploaded** - Document upload events
```json
{
  "document_id": "uuid",
  "original_name": "document.pdf",
  "storage_path": "documents/file.pdf",
  "file_size": 1024000,
  "mime_type": "application/pdf",
  "md5_checksum": "md5-hash",
  "user_id": "user-123",
  "organization_id": "org-456",
  "metadata": {
    "key": "value"
  },
  "timestamp": "2024-01-10T10:00:00Z"
}
```

### Produced Topics

**document.parsed** - Successful parsing events
```json
{
  "event_id": "uuid",
  "document_id": "uuid",
  "structure_id": "uuid",
  "format": "pdf",
  "parsed_at": "2024-01-10T10:00:00Z",
  "parse_duration_ms": 1234,
  "parser_version": "1.0.0"
}
```

**errors.processing** - Error events
```json
{
  "event_id": "uuid",
  "document_id": "uuid",
  "error_type": "parsing_error",
  "error_message": "Failed to parse document",
  "service": "rag-parser-service",
  "timestamp": "2024-01-10T10:00:00Z",
  "retryable": false
}
```

## Database Schema

### documents
- `id`: UUID (primary key)
- `filename`: String
- `format`: String (docx, pdf, pptx, xlsx)
- `status`: String (uploaded, parsed, parse_failed)
- `error_message`: Text (nullable)
- `uploaded_at`: DateTime
- `updated_at`: DateTime

### document_structures
- `id`: UUID (primary key)
- `document_id`: UUID (indexed)
- `format`: String
- `structure`: JSONB (parsed structure)
- `doc_metadata`: JSONB (document metadata)
- `stats`: JSONB (statistics)
- `parsed_at`: DateTime
- `parse_duration_ms`: Integer
- `parser_version`: String
- `checksum`: String (indexed, for idempotency)

## Parsed Output Structure

### DOCX
```json
{
  "format": "docx",
  "metadata": {
    "title": "Document Title",
    "author": "Author Name",
    "created": "2024-01-10T10:00:00"
  },
  "structure": {
    "format": "docx",
    "sections": [
      {
        "level": 1,
        "title": "Section Title",
        "paragraphs": [
          {
            "text": "Paragraph text",
            "style": "Normal",
            "hash": "md5-hash"
          }
        ],
        "tables": [
          {
            "rows": [["cell1", "cell2"]],
            "row_count": 1,
            "col_count": 2,
            "hash": "md5-hash"
          }
        ]
      }
    ]
  },
  "stats": {
    "total_pages": 5,
    "total_text_length": 1000,
    "total_tables": 2,
    "total_images": 3
  }
}
```

### PDF
```json
{
  "format": "pdf",
  "structure": {
    "format": "pdf",
    "pages": [
      {
        "page_number": 1,
        "text": "Page text content",
        "text_hash": "md5-hash",
        "tables": [...]
      }
    ]
  }
}
```

### PPTX
```json
{
  "format": "pptx",
  "structure": {
    "format": "pptx",
    "slides": [
      {
        "slide_number": 1,
        "title": "Slide Title",
        "content": [...],
        "tables": [...],
        "notes": "Speaker notes"
      }
    ]
  }
}
```

### XLSX
```json
{
  "format": "xlsx",
  "structure": {
    "format": "xlsx",
    "sheets": [
      {
        "sheet_name": "Sheet1",
        "rows": [["A1", "B1"], ["A2", "B2"]],
        "row_count": 2,
        "col_count": 2,
        "hash": "md5-hash"
      }
    ]
  }
}
```

## Monitoring

### Prometheus Metrics

- `documents_parsed_total{format,status}` - Total documents parsed
- `parse_duration_seconds{format}` - Parse duration histogram
- `parse_errors_total{format,error_type}` - Total parsing errors
- `active_workers` - Currently active worker threads
- `kafka_consumer_lag{topic,partition}` - Consumer lag
- `kafka_messages_consumed_total{topic}` - Messages consumed
- `kafka_messages_produced_total{topic}` - Messages produced

### Logging

Structured JSON logs are written to stdout with the following fields:
- `event`: Log event type
- `timestamp`: ISO 8601 timestamp
- `level`: Log level
- `document_id`: Document UUID (when applicable)
- Additional context fields

## Testing

### Run Unit Tests
```bash
pytest tests/unit/ -v
```

### Run Integration Tests
```bash
pytest tests/integration/ -v
```

### Run All Tests with Coverage
```bash
pytest --cov=app --cov-report=html
```

## Development

### Code Formatting
```bash
black app/ tests/
isort app/ tests/
```

### Linting
```bash
flake8 app/ tests/
mypy app/
```

## Error Handling

### Retryable Errors
- MinIO/S3 download failures
- Database connection issues
- Kafka publish failures

Retries: 3 attempts with backoff (5s, 15s, 45s)

### Non-Retryable Errors
- Invalid event schema
- Corrupt/unsupported files
- Parsing failures

These publish an error event and commit the offset immediately.

## Performance

- **Memory**: &lt;2GB per worker
- **Concurrency**: Configurable thread pool (default: 4 workers)
- **File Size**: Configurable limit (default: 500MB)
- **Throughput**: Depends on document complexity and size

## Graceful Shutdown

On SIGTERM or SIGINT:
1. Stop polling new messages
2. Wait for in-flight jobs to complete (configurable timeout)
3. Close Kafka consumer/producer
4. Shutdown thread pool

## License

MIT License

## Support

For issues and questions, please open a GitHub issue.
