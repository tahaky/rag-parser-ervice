import pytest
from app.parsers.factory import ParserFactory
from app.parsers.docx_parser import DocxParser
from app.parsers.pdf_parser import PdfParser
from app.parsers.pptx_parser import PptxParser
from app.parsers.xlsx_parser import XlsxParser


class TestParserFactory:
    """Test cases for ParserFactory."""

    def test_get_docx_parser(self):
        """Test getting DOCX parser."""
        parser = ParserFactory.get_parser("docx")
        assert isinstance(parser, DocxParser)

    def test_get_pdf_parser(self):
        """Test getting PDF parser."""
        parser = ParserFactory.get_parser("pdf")
        assert isinstance(parser, PdfParser)

    def test_get_pptx_parser(self):
        """Test getting PPTX parser."""
        parser = ParserFactory.get_parser("pptx")
        assert isinstance(parser, PptxParser)

    def test_get_xlsx_parser(self):
        """Test getting XLSX parser."""
        parser = ParserFactory.get_parser("xlsx")
        assert isinstance(parser, XlsxParser)

    def test_case_insensitive(self):
        """Test format string is case-insensitive."""
        parser = ParserFactory.get_parser("DOCX")
        assert isinstance(parser, DocxParser)

    def test_unsupported_format(self):
        """Test unsupported format raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported document format"):
            ParserFactory.get_parser("txt")

    def test_get_supported_formats(self):
        """Test getting supported formats."""
        formats = ParserFactory.get_supported_formats()
        assert "docx" in formats
        assert "pdf" in formats
        assert "pptx" in formats
        assert "xlsx" in formats
        assert len(formats) == 4

    def test_get_parser_version(self):
        """Test getting parser version."""
        version = ParserFactory.get_parser_version()
        assert isinstance(version, str)
        assert len(version) > 0
