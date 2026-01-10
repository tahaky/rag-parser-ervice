import os
import tempfile
from typing import Optional
from minio import Minio
from minio.error import S3Error

from app.config import settings
from app.utils.logging import get_logger
from app.utils.metrics import storage_download_errors

logger = get_logger(__name__)


class StorageService:
    """MinIO/S3 storage service for downloading documents."""

    def __init__(self):
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self.bucket = settings.minio_bucket
        self.max_size = settings.max_file_size_bytes
        self.temp_dir = settings.temp_dir
        os.makedirs(self.temp_dir, exist_ok=True)

    def download_file(self, object_name: str) -> str:
        """
        Download a file from MinIO to a temporary location.

        Args:
            object_name: The object key in MinIO

        Returns:
            Path to the downloaded temporary file

        Raises:
            ValueError: If file exceeds max size
            S3Error: If download fails
        """
        try:
            # Get object stats first to check size
            stat = self.client.stat_object(self.bucket, object_name)
            file_size = stat.size

            if file_size > self.max_size:
                raise ValueError(
                    f"File size {file_size} exceeds maximum allowed size {self.max_size}"
                )

            # Create temp file
            suffix = os.path.splitext(object_name)[1]
            fd, temp_path = tempfile.mkstemp(suffix=suffix, dir=self.temp_dir)
            os.close(fd)

            logger.info(
                "downloading_file",
                object_name=object_name,
                file_size=file_size,
                temp_path=temp_path,
            )

            # Download file
            self.client.fget_object(self.bucket, object_name, temp_path)

            logger.info("file_downloaded", object_name=object_name, temp_path=temp_path)
            return temp_path

        except S3Error as e:
            storage_download_errors.inc()
            logger.error(
                "storage_download_failed",
                object_name=object_name,
                error=str(e),
                code=e.code,
            )
            raise
        except Exception as e:
            storage_download_errors.inc()
            logger.error("storage_download_failed", object_name=object_name, error=str(e))
            raise

    def cleanup_file(self, file_path: str):
        """Remove temporary file."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug("temp_file_cleaned", file_path=file_path)
        except Exception as e:
            logger.warning("temp_file_cleanup_failed", file_path=file_path, error=str(e))

    def check_health(self) -> bool:
        """Check MinIO connectivity."""
        try:
            self.client.list_buckets()
            return True
        except Exception as e:
            logger.error("minio_health_check_failed", error=str(e))
            return False
