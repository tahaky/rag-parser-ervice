from typing import Dict, Any
from app.parsers.base import BaseParser
from app.parsers.docx_parser import DocxParser
from app.parsers.pdf_parser import PdfParser
from app.parsers.pptx_parser import PptxParser
from app.parsers.xlsx_parser import XlsxParser
from app.config import settings


class ParserFactory:
    """Factory for creating parser instances."""

    _parsers: Dict[str, type] = {
        "docx": DocxParser,
        "pdf": PdfParser,
        "pptx": PptxParser,
        "xlsx": XlsxParser,
    }

    @classmethod
    def get_parser(cls, format: str) -> BaseParser:
        """
        Get parser instance for the given format.

        Args:
            format: Document format (docx, pdf, pptx, xlsx)

        Returns:
            Parser instance

        Raises:
            ValueError: If format is not supported
        """
        format_lower = format.lower()
        parser_class = cls._parsers.get(format_lower)

        if not parser_class:
            raise ValueError(f"Unsupported document format: {format}")

        return parser_class(enable_ocr=settings.enable_ocr)

    @classmethod
    def get_supported_formats(cls) -> list:
        """Get list of supported formats."""
        return list(cls._parsers.keys())

    @classmethod
    def get_parser_version(cls) -> str:
        """Get parser version."""
        return settings.parser_version
