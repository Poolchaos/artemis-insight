"""
Unit tests for document service.
"""

import pytest
from datetime import datetime, timezone
from bson import ObjectId
from unittest.mock import Mock, patch, AsyncMock

from app.services.document_service import DocumentService
from app.models.document import DocumentCreate, DocumentUpdate, DocumentStatus, DocumentInDB


@pytest.fixture
async def document_service(test_db):
    """Create document service with test database."""
    return DocumentService(test_db)


@pytest.fixture
def sample_document_data():
    """Sample document data for testing."""
    return {
        "user_id": str(ObjectId()),
        "filename": "test_document.pdf",
        "file_path": f"documents/{str(ObjectId())}/test_document.pdf",
        "file_size": 102400,
        "mime_type": "application/pdf",
        "status": DocumentStatus.PENDING
    }


@pytest.fixture
def mock_minio_service():
    """Mock MinIO service."""
    with patch('app.services.document_service.minio_service') as mock:
        yield mock


class TestDocumentService:
    """Test document service functionality."""

    @pytest.mark.asyncio
    async def test_create_document(self, document_service, sample_document_data):
        """Test creating a document."""
        # Arrange
        document_data = DocumentCreate(**sample_document_data)

        # Act
        result = await document_service.create_document(
            document_data,
            sample_document_data["file_path"]
        )

        # Assert
        assert result.id is not None
        assert result.filename == sample_document_data["filename"]
        assert result.file_path == sample_document_data["file_path"]
        assert result.file_size == sample_document_data["file_size"]
        assert result.status == DocumentStatus.PENDING
        assert result.created_at is not None
        assert result.updated_at is not None

    @pytest.mark.asyncio
    async def test_get_document_success(self, document_service, sample_document_data):
        """Test retrieving an existing document."""
        # Arrange
        document_data = DocumentCreate(**sample_document_data)
        created = await document_service.create_document(
            document_data,
            sample_document_data["file_path"]
        )

        # Act
        result = await document_service.get_document(str(created.id))

        # Assert
        assert result is not None
        assert result.id == created.id
        assert result.filename == created.filename

    @pytest.mark.asyncio
    async def test_get_document_not_found(self, document_service):
        """Test retrieving non-existent document."""
        # Arrange
        fake_id = str(ObjectId())

        # Act
        result = await document_service.get_document(fake_id)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_document_invalid_id(self, document_service):
        """Test retrieving document with invalid ID."""
        # Act
        result = await document_service.get_document("invalid_id")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_document_by_user_success(self, document_service, sample_document_data):
        """Test retrieving document by specific user."""
        # Arrange
        document_data = DocumentCreate(**sample_document_data)
        created = await document_service.create_document(
            document_data,
            sample_document_data["file_path"]
        )

        # Act
        result = await document_service.get_document_by_user(
            str(created.id),
            sample_document_data["user_id"]
        )

        # Assert
        assert result is not None
        assert result.id == created.id
        assert str(result.user_id) == sample_document_data["user_id"]

    @pytest.mark.asyncio
    async def test_get_document_by_user_wrong_user(self, document_service, sample_document_data):
        """Test retrieving document with wrong user ID."""
        # Arrange
        document_data = DocumentCreate(**sample_document_data)
        created = await document_service.create_document(
            document_data,
            sample_document_data["file_path"]
        )
        wrong_user_id = str(ObjectId())

        # Act
        result = await document_service.get_document_by_user(
            str(created.id),
            wrong_user_id
        )

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_list_user_documents_all(self, document_service, sample_document_data):
        """Test listing all documents for a user."""
        # Arrange
        user_id = sample_document_data["user_id"]

        # Create multiple documents
        for i in range(3):
            doc_data = sample_document_data.copy()
            doc_data["filename"] = f"test_document_{i}.pdf"
            doc_data["file_path"] = f"documents/{user_id}/test_{i}.pdf"
            document_data = DocumentCreate(**doc_data)
            await document_service.create_document(document_data, doc_data["file_path"])

        # Act
        results = await document_service.list_user_documents(user_id)

        # Assert
        assert len(results) == 3
        # Should be sorted by created_at descending
        for i in range(len(results) - 1):
            assert results[i].created_at >= results[i + 1].created_at

    @pytest.mark.asyncio
    async def test_list_user_documents_with_pagination(self, document_service, sample_document_data):
        """Test listing documents with pagination."""
        # Arrange
        user_id = sample_document_data["user_id"]

        # Create 5 documents
        for i in range(5):
            doc_data = sample_document_data.copy()
            doc_data["filename"] = f"test_document_{i}.pdf"
            doc_data["file_path"] = f"documents/{user_id}/test_{i}.pdf"
            document_data = DocumentCreate(**doc_data)
            await document_service.create_document(document_data, doc_data["file_path"])

        # Act - Get first 2
        page1 = await document_service.list_user_documents(user_id, skip=0, limit=2)
        # Get next 2
        page2 = await document_service.list_user_documents(user_id, skip=2, limit=2)

        # Assert
        assert len(page1) == 2
        assert len(page2) == 2
        # No overlap
        page1_ids = {str(doc.id) for doc in page1}
        page2_ids = {str(doc.id) for doc in page2}
        assert len(page1_ids & page2_ids) == 0

    @pytest.mark.asyncio
    async def test_list_user_documents_filter_by_status(self, document_service, sample_document_data):
        """Test filtering documents by status."""
        # Arrange
        user_id = sample_document_data["user_id"]

        # Create documents with different statuses
        for status in [DocumentStatus.PENDING, DocumentStatus.PROCESSING, DocumentStatus.COMPLETED]:
            doc_data = sample_document_data.copy()
            doc_data["status"] = status
            doc_data["filename"] = f"test_{status.value}.pdf"
            doc_data["file_path"] = f"documents/{user_id}/test_{status.value}.pdf"
            document_data = DocumentCreate(**doc_data)
            await document_service.create_document(document_data, doc_data["file_path"])

        # Act
        completed_docs = await document_service.list_user_documents(
            user_id,
            status=DocumentStatus.COMPLETED
        )

        # Assert
        assert len(completed_docs) == 1
        assert completed_docs[0].status == DocumentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_list_user_documents_empty(self, document_service):
        """Test listing documents for user with no documents."""
        # Arrange
        user_id = str(ObjectId())

        # Act
        results = await document_service.list_user_documents(user_id)

        # Assert
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_update_document_success(self, document_service, sample_document_data):
        """Test updating document."""
        # Arrange
        document_data = DocumentCreate(**sample_document_data)
        created = await document_service.create_document(
            document_data,
            sample_document_data["file_path"]
        )

        update_data = DocumentUpdate(
            status=DocumentStatus.COMPLETED,
            processing_metadata={"pages": 10, "word_count": 5000}
        )

        # Act
        result = await document_service.update_document(str(created.id), update_data)

        # Assert
        assert result is not None
        assert result.status == DocumentStatus.COMPLETED
        assert result.processing_metadata == {"pages": 10, "word_count": 5000}
        assert result.updated_at > created.updated_at

    @pytest.mark.asyncio
    async def test_update_document_not_found(self, document_service):
        """Test updating non-existent document."""
        # Arrange
        fake_id = str(ObjectId())
        update_data = DocumentUpdate(status=DocumentStatus.COMPLETED)

        # Act
        result = await document_service.update_document(fake_id, update_data)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_update_document_partial(self, document_service, sample_document_data):
        """Test partial document update."""
        # Arrange
        document_data = DocumentCreate(**sample_document_data)
        created = await document_service.create_document(
            document_data,
            sample_document_data["file_path"]
        )

        # Only update status
        update_data = DocumentUpdate(status=DocumentStatus.PROCESSING)

        # Act
        result = await document_service.update_document(str(created.id), update_data)

        # Assert
        assert result is not None
        assert result.status == DocumentStatus.PROCESSING
        # Other fields unchanged
        assert result.filename == created.filename
        assert result.file_size == created.file_size

    @pytest.mark.asyncio
    async def test_delete_document_success(self, document_service, sample_document_data, mock_minio_service):
        """Test deleting document."""
        # Arrange
        document_data = DocumentCreate(**sample_document_data)
        created = await document_service.create_document(
            document_data,
            sample_document_data["file_path"]
        )

        # Act
        result = await document_service.delete_document(
            str(created.id),
            sample_document_data["user_id"]
        )

        # Assert
        assert result is True
        mock_minio_service.delete_file.assert_called_once_with(sample_document_data["file_path"])

        # Verify document is deleted from DB
        deleted_doc = await document_service.get_document(str(created.id))
        assert deleted_doc is None

    @pytest.mark.asyncio
    async def test_delete_document_not_found(self, document_service, mock_minio_service):
        """Test deleting non-existent document."""
        # Arrange
        fake_id = str(ObjectId())
        user_id = str(ObjectId())

        # Act
        result = await document_service.delete_document(fake_id, user_id)

        # Assert
        assert result is False
        mock_minio_service.delete_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_document_wrong_user(self, document_service, sample_document_data, mock_minio_service):
        """Test deleting document with wrong user ID."""
        # Arrange
        document_data = DocumentCreate(**sample_document_data)
        created = await document_service.create_document(
            document_data,
            sample_document_data["file_path"]
        )
        wrong_user_id = str(ObjectId())

        # Act
        result = await document_service.delete_document(str(created.id), wrong_user_id)

        # Assert
        assert result is False
        mock_minio_service.delete_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_document_minio_failure(self, document_service, sample_document_data, mock_minio_service):
        """Test deleting document when MinIO deletion fails."""
        # Arrange
        document_data = DocumentCreate(**sample_document_data)
        created = await document_service.create_document(
            document_data,
            sample_document_data["file_path"]
        )
        mock_minio_service.delete_file.side_effect = Exception("MinIO error")

        # Act - Should still delete from DB
        result = await document_service.delete_document(
            str(created.id),
            sample_document_data["user_id"]
        )

        # Assert
        assert result is True
        # DB deletion should still succeed
        deleted_doc = await document_service.get_document(str(created.id))
        assert deleted_doc is None

    @pytest.mark.asyncio
    async def test_count_user_documents_all(self, document_service, sample_document_data):
        """Test counting all documents for a user."""
        # Arrange
        user_id = sample_document_data["user_id"]

        # Create 3 documents
        for i in range(3):
            doc_data = sample_document_data.copy()
            doc_data["filename"] = f"test_document_{i}.pdf"
            doc_data["file_path"] = f"documents/{user_id}/test_{i}.pdf"
            document_data = DocumentCreate(**doc_data)
            await document_service.create_document(document_data, doc_data["file_path"])

        # Act
        count = await document_service.count_user_documents(user_id)

        # Assert
        assert count == 3

    @pytest.mark.asyncio
    async def test_count_user_documents_by_status(self, document_service, sample_document_data):
        """Test counting documents by status."""
        # Arrange
        user_id = sample_document_data["user_id"]

        # Create documents with different statuses
        statuses = [
            DocumentStatus.PENDING,
            DocumentStatus.PENDING,
            DocumentStatus.COMPLETED
        ]
        for i, status in enumerate(statuses):
            doc_data = sample_document_data.copy()
            doc_data["status"] = status
            doc_data["filename"] = f"test_{i}.pdf"
            doc_data["file_path"] = f"documents/{user_id}/test_{i}.pdf"
            document_data = DocumentCreate(**doc_data)
            await document_service.create_document(document_data, doc_data["file_path"])

        # Act
        pending_count = await document_service.count_user_documents(
            user_id,
            status=DocumentStatus.PENDING
        )
        completed_count = await document_service.count_user_documents(
            user_id,
            status=DocumentStatus.COMPLETED
        )

        # Assert
        assert pending_count == 2
        assert completed_count == 1

    @pytest.mark.asyncio
    async def test_count_user_documents_zero(self, document_service):
        """Test counting documents for user with no documents."""
        # Arrange
        user_id = str(ObjectId())

        # Act
        count = await document_service.count_user_documents(user_id)

        # Assert
        assert count == 0
