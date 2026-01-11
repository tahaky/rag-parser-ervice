import pytest
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.api import app
from app.models import Document, DocumentStructure


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_document():
    """Create a mock document."""
    doc = MagicMock(spec=Document)
    doc.id = uuid.uuid4()
    doc.filename = "test.pdf"
    doc.format = "pdf"
    doc.status = "parsed"
    doc.error_message = None
    doc.uploaded_at = datetime(2024, 1, 10, 10, 0, 0)
    doc.updated_at = datetime(2024, 1, 10, 10, 5, 0)
    return doc


@pytest.fixture
def mock_structure():
    """Create a mock document structure."""
    structure = MagicMock(spec=DocumentStructure)
    structure.id = uuid.uuid4()
    structure.document_id = None  # Will be set in tests
    structure.format = "pdf"
    structure.structure = {"pages": [{"page_number": 1, "text": "Test content"}]}
    structure.doc_metadata = {"title": "Test Document"}
    structure.stats = {"total_pages": 1, "total_text_length": 100}
    structure.parsed_at = datetime(2024, 1, 10, 10, 5, 0)
    structure.parse_duration_ms = 1234
    structure.parser_version = "1.0.0"
    structure.checksum = "abc123"
    return structure


class TestGetDocumentEndpoint:
    """Test cases for GET /documents/{document_id} endpoint."""

    @patch("app.api.get_db_session")
    def test_get_document_success(self, mock_db_session, client, mock_document, mock_structure):
        """Test successful document retrieval with structure."""
        # Setup
        doc_id = str(mock_document.id)
        mock_structure.document_id = mock_document.id
        
        mock_session = MagicMock()
        mock_session.query().filter_by().first.side_effect = [mock_document, mock_structure]
        mock_db_session.return_value.__enter__.return_value = mock_session

        # Execute
        response = client.get(f"/documents/{doc_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == doc_id
        assert data["filename"] == "test.pdf"
        assert data["format"] == "pdf"
        assert data["status"] == "parsed"
        assert data["structure"] is not None
        assert data["structure"]["structure_id"] == str(mock_structure.id)
        assert data["structure"]["parse_duration_ms"] == 1234

    @patch("app.api.get_db_session")
    def test_get_document_without_structure(self, mock_db_session, client, mock_document):
        """Test document retrieval without parsed structure."""
        # Setup
        doc_id = str(mock_document.id)
        
        mock_session = MagicMock()
        mock_session.query().filter_by().first.side_effect = [mock_document, None]
        mock_db_session.return_value.__enter__.return_value = mock_session

        # Execute
        response = client.get(f"/documents/{doc_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == doc_id
        assert data["filename"] == "test.pdf"
        assert data["structure"] is None

    @patch("app.api.get_db_session")
    def test_get_document_not_found(self, mock_db_session, client):
        """Test document not found returns 404."""
        # Setup
        doc_id = str(uuid.uuid4())
        
        mock_session = MagicMock()
        mock_session.query().filter_by().first.return_value = None
        mock_db_session.return_value.__enter__.return_value = mock_session

        # Execute
        response = client.get(f"/documents/{doc_id}")

        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_get_document_invalid_uuid(self, client):
        """Test invalid UUID format returns 400."""
        # Execute
        response = client.get("/documents/invalid-uuid")

        # Assert
        assert response.status_code == 400
        assert "Invalid document_id format" in response.json()["detail"]

    @patch("app.api.get_db_session")
    def test_get_document_with_error_status(self, mock_db_session, client, mock_document):
        """Test document retrieval with error status."""
        # Setup
        doc_id = str(mock_document.id)
        mock_document.status = "parse_failed"
        mock_document.error_message = "Parsing failed: corrupt file"
        
        mock_session = MagicMock()
        mock_session.query().filter_by().first.side_effect = [mock_document, None]
        mock_db_session.return_value.__enter__.return_value = mock_session

        # Execute
        response = client.get(f"/documents/{doc_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "parse_failed"
        assert data["error_message"] == "Parsing failed: corrupt file"
        assert data["structure"] is None


class TestRootEndpoint:
    """Test cases for root endpoint."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns service info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert "status" in data
