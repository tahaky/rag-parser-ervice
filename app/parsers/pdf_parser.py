from typing import Dict, Any, List
import pdfplumber
import fitz  # PyMuPDF

from app.parsers.base import BaseParser


class PdfParser(BaseParser):
    """Parser for PDF documents using pdfplumber and PyMuPDF."""

    def parse(self, file_path: str) -> Dict[str, Any]:
        """Parse PDF document into structured JSON."""
        # Use pdfplumber for text and tables
        pages = []
        total_text_length = 0
        total_tables = 0
        
        try:
            with pdfplumber.open(file_path) as pdf:
                # Extract metadata
                metadata = self.build_metadata(
                    title=pdf.metadata.get("Title", ""),
                    author=pdf.metadata.get("Author", ""),
                    subject=pdf.metadata.get("Subject", ""),
                    creator=pdf.metadata.get("Creator", ""),
                    producer=pdf.metadata.get("Producer", ""),
                    creation_date=pdf.metadata.get("CreationDate", ""),
                )

                # Parse each page
                for page_num, page in enumerate(pdf.pages, 1):
                    page_data = {
                        "page_number": page_num,
                        "text": "",
                        "tables": [],
                    }

                    # Extract text
                    text = page.extract_text()
                    if text:
                        page_data["text"] = text.strip()
                        page_data["text_hash"] = self.calculate_hash(text)
                        total_text_length += len(text)

                    # Extract tables
                    try:
                        tables = page.extract_tables()
                        if tables:
                            for table in tables:
                                if table:
                                    table_data = self._process_table(table)
                                    page_data["tables"].append(table_data)
                                    total_tables += 1
                    except Exception as e:
                        # Graceful degradation - continue without tables
                        pass

                    pages.append(page_data)

        except Exception as e:
            # If pdfplumber fails, try PyMuPDF as fallback
            pages, total_text_length = self._parse_with_pymupdf(file_path)
            metadata = self.build_metadata()

        # Count images using PyMuPDF
        total_images = self._count_images(file_path)

        # Build structure
        structure = {
            "format": "pdf",
            "pages": pages,
        }

        # Build stats
        stats = self.build_stats(
            total_pages=len(pages),
            total_text_length=total_text_length,
            total_tables=total_tables,
            total_images=total_images,
        )

        return {
            "format": "pdf",
            "metadata": metadata,
            "structure": structure,
            "stats": stats,
        }

    def _process_table(self, table: List[List[str]]) -> Dict[str, Any]:
        """Process extracted table data."""
        # Clean up table cells
        cleaned_rows = []
        for row in table:
            cleaned_row = [cell.strip() if cell else "" for cell in row]
            cleaned_rows.append(cleaned_row)

        table_text = " ".join(" ".join(row) for row in cleaned_rows)
        return {
            "rows": cleaned_rows,
            "row_count": len(cleaned_rows),
            "col_count": len(cleaned_rows[0]) if cleaned_rows else 0,
            "hash": self.calculate_hash(table_text),
        }

    def _parse_with_pymupdf(self, file_path: str) -> tuple[List[Dict[str, Any]], int]:
        """Fallback parser using PyMuPDF."""
        pages = []
        total_text_length = 0

        try:
            doc = fitz.open(file_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                
                page_data = {
                    "page_number": page_num + 1,
                    "text": text.strip(),
                    "tables": [],
                }
                
                if text:
                    page_data["text_hash"] = self.calculate_hash(text)
                    total_text_length += len(text)
                
                pages.append(page_data)
            
            doc.close()
        except Exception:
            # Return empty if both fail
            pass

        return pages, total_text_length

    def _count_images(self, file_path: str) -> int:
        """Count images in PDF using PyMuPDF."""
        try:
            doc = fitz.open(file_path)
            image_count = 0
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images()
                image_count += len(image_list)
            doc.close()
            return image_count
        except Exception:
            return 0
