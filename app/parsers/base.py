import hashlib
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from datetime import datetime


class BaseParser(ABC):
    """Base class for document parsers."""

    def __init__(self, enable_ocr: bool = False):
        self.enable_ocr = enable_ocr

    @abstractmethod
    def parse(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a document and return structured data.

        Args:
            file_path: Path to the document file

        Returns:
            Dictionary with structured document data
        """
        pass

    @staticmethod
    def calculate_hash(content: str) -> str:
        """Calculate MD5 hash of content."""
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    @staticmethod
    def extract_text_hash(text: str) -> str:
        """Extract hash from text content."""
        return BaseParser.calculate_hash(text)

    def build_metadata(self, **kwargs) -> Dict[str, Any]:
        """Build metadata dictionary."""
        metadata = {
            "parsed_at": datetime.utcnow().isoformat(),
            "ocr_enabled": self.enable_ocr,
        }
        metadata.update(kwargs)
        return metadata

    def build_stats(
        self,
        total_pages: int = 0,
        total_text_length: int = 0,
        total_tables: int = 0,
        total_images: int = 0,
        **kwargs,
    ) -> Dict[str, Any]:
        """Build statistics dictionary."""
        stats = {
            "total_pages": total_pages,
            "total_text_length": total_text_length,
            "total_tables": total_tables,
            "total_images": total_images,
        }
        stats.update(kwargs)
        return stats
