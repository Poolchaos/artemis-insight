"""
Unit tests for document model.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError
from bson import ObjectId

from app.models.document import (
    DocumentStatus,
    DocumentBase,
    DocumentCreate,
    DocumentUpdate,
    DocumentInDB,
    DocumentResponse
)


def test_document_status_enum():
    """Test document status enum values."""
    assert DocumentStatus.PENDING == "pending"
    assert DocumentStatus.PROCESSING == "processing"
    assert DocumentStatus.COMPLETED == "completed"
    assert DocumentStatus.FAILED == "failed"


def test_document_base_valid():
    """Test valid document base creation."""
    doc = DocumentBase(
        filename="test.pdf",
        file_path="/documents/test.pdf",
        file_size=1024,
        mime_type="application/pdf",
        status=DocumentStatus.PENDING
    )
    assert doc.filename == "test.pdf"
    assert doc.file_size == 1024
    assert doc.status == DocumentStatus.PENDING


def test_document_base_invalid_mime_type():
    """Test document base with invalid MIME type."""
    with pytest.raises(ValidationError) as exc_info:
        DocumentBase(
            filename="test.doc",
            file_path="/documents/test.doc",
            file_size=1024,
            mime_type="application/msword"
        )
    assert "MIME type must be one of" in str(exc_info.value)


def test_document_base_invalid_file_size():
    """Test document base with invalid file size."""
    with pytest.raises(ValidationError) as exc_info:
        DocumentBase(
            filename="test.pdf",
            file_path="/documents/test.pdf",
            file_size=0
        )
    assert "greater than 0" in str(exc_info.value)


def test_document_base_filename_too_long():
    """Test document base with filename exceeding max length."""
    with pytest.raises(ValidationError) as exc_info:
        DocumentBase(
            filename="a" * 256,
            file_path="/documents/test.pdf",
            file_size=1024
        )
    assert "at most 255 characters" in str(exc_info.value)


def test_document_create_valid():
    """Test valid document creation."""
    user_id = str(ObjectId())
    doc = DocumentCreate(
        user_id=user_id,
        filename="test.pdf",
        file_path="/documents/test.pdf",
        file_size=2048,
        processing_metadata={"pages": 10}
    )
    assert doc.user_id == user_id
    assert doc.processing_metadata["pages"] == 10


def test_document_create_invalid_user_id():
    """Test document create with invalid user ID."""
    with pytest.raises(ValidationError) as exc_info:
        DocumentCreate(
            user_id="invalid-id",
            filename="test.pdf",
            file_path="/documents/test.pdf",
            file_size=1024
        )
    assert "Invalid ObjectId" in str(exc_info.value)


def test_document_update():
    """Test document update schema."""
    update = DocumentUpdate(
        status=DocumentStatus.COMPLETED,
        processing_metadata={"result": "success"}
    )
    assert update.status == DocumentStatus.COMPLETED
    assert update.processing_metadata["result"] == "success"


def test_document_update_partial():
    """Test partial document update."""
    update = DocumentUpdate(status=DocumentStatus.PROCESSING)
    assert update.status == DocumentStatus.PROCESSING
    assert update.processing_metadata is None


def test_document_in_db():
    """Test document in database schema."""
    user_id = ObjectId()
    doc = DocumentInDB(
        user_id=user_id,
        filename="test.pdf",
        file_path="/documents/test.pdf",
        file_size=1024
    )
    assert doc.user_id == user_id
    assert doc.id is not None
    assert isinstance(doc.created_at, datetime)
    assert isinstance(doc.updated_at, datetime)
    assert isinstance(doc.upload_date, datetime)


def test_document_response():
    """Test document API response schema."""
    response = DocumentResponse(
        id=str(ObjectId()),
        user_id=str(ObjectId()),
        filename="test.pdf",
        file_path="/documents/test.pdf",
        file_size=1024,
        mime_type="application/pdf",
        status=DocumentStatus.COMPLETED,
        upload_date=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    assert response.filename == "test.pdf"
    assert response.status == DocumentStatus.COMPLETED
