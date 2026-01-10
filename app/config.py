from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Service Configuration
    service_name: str = Field(default="rag-parser-service", alias="SERVICE_NAME")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    temp_dir: str = Field(default="/tmp/parser", alias="TEMP_DIR")

    # Kafka Configuration
    kafka_bootstrap_servers: str = Field(default="localhost:9092", alias="KAFKA_BOOTSTRAP_SERVERS")
    kafka_consumer_group: str = Field(default="parser-service", alias="KAFKA_CONSUMER_GROUP")
    kafka_topic_uploaded: str = Field(default="document.uploaded", alias="KAFKA_TOPIC_UPLOADED")
    kafka_topic_parsed: str = Field(default="document.parsed", alias="KAFKA_TOPIC_PARSED")
    kafka_topic_errors: str = Field(default="errors.processing", alias="KAFKA_TOPIC_ERRORS")
    kafka_max_poll_interval_ms: int = Field(default=300000, alias="KAFKA_MAX_POLL_INTERVAL_MS")
    kafka_session_timeout_ms: int = Field(default=30000, alias="KAFKA_SESSION_TIMEOUT_MS")

    # Database Configuration
    database_url: str = Field(default="postgresql://parser:parser@localhost:5432/parser_db", alias="DATABASE_URL")

    # MinIO/S3 Configuration
    minio_endpoint: str = Field(default="localhost:9000", alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="minioadmin", alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="minioadmin", alias="MINIO_SECRET_KEY")
    minio_bucket: str = Field(default="documents", alias="MINIO_BUCKET")
    minio_secure: bool = Field(default=False, alias="MINIO_SECURE")
    max_file_size_mb: int = Field(default=500, alias="MAX_FILE_SIZE_MB")

    # Worker Configuration
    worker_count: int = Field(default=4, alias="WORKER_COUNT")
    graceful_shutdown_timeout: int = Field(default=30, alias="GRACEFUL_SHUTDOWN_TIMEOUT")

    # Retry Configuration
    max_retries: int = Field(default=3, alias="MAX_RETRIES")
    retry_backoff_seconds: str = Field(default="5,15,45", alias="RETRY_BACKOFF_SECONDS")

    # Parser Configuration
    enable_ocr: bool = Field(default=False, alias="ENABLE_OCR")
    parser_version: str = Field(default="1.0.0", alias="PARSER_VERSION")

    # Health Check Configuration
    health_check_host: str = Field(default="0.0.0.0", alias="HEALTH_CHECK_HOST")
    health_check_port: int = Field(default=8080, alias="HEALTH_CHECK_PORT")

    @property
    def retry_backoff_list(self) -> List[int]:
        """Parse retry backoff string into list of integers."""
        return [int(x.strip()) for x in self.retry_backoff_seconds.split(",")]

    @property
    def max_file_size_bytes(self) -> int:
        """Convert max file size from MB to bytes."""
        return self.max_file_size_mb * 1024 * 1024


# Global settings instance
settings = Settings()
