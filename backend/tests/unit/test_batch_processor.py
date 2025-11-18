"""
Unit tests for batch processor service
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from fastapi import UploadFile
from io import BytesIO

from app.services.batch_processor import BatchProcessor
from app.models.batch_job import (
    BatchJob,
    BatchJobType,
    BatchJobStatus,
    DocumentCollection
)


@pytest.fixture
def mock_db():
    """Mock MongoDB database"""
    db = Mock()
    db.batch_jobs = AsyncMock()
    db.document_collections = AsyncMock()
    return db


@pytest.fixture
def mock_document_service():
    """Mock document service"""
    service = Mock()
    service.upload_document = AsyncMock()
    return service


@pytest.fixture
def mock_minio_service():
    """Mock MinIO service"""
    return Mock()


@pytest.fixture
def batch_processor(mock_db, mock_document_service, mock_minio_service):
    """Create batch processor instance"""
    return BatchProcessor(
        db=mock_db,
        document_service=mock_document_service,
        minio_service=mock_minio_service
    )


@pytest.fixture
def mock_upload_files():
    """Create mock upload files"""
    files = []
    for i in range(3):
        file = Mock(spec=UploadFile)
        file.filename = f"document_{i+1}.pdf"
        file.file = BytesIO(b"fake pdf content")
        files.append(file)
    return files


@pytest.mark.asyncio
async def test_batch_upload_creates_job(batch_processor, mock_upload_files, mock_db):
    """Test that batch upload creates a job record"""
    user_id = "user123"

    result = await batch_processor.batch_upload(
        files=mock_upload_files,
        user_id=user_id,
        collection_name="Test Collection",
        tags=["test"],
        project_name="Test Project"
    )

    # Verify batch job was created
    assert isinstance(result, BatchJob)
    assert result.user_id == user_id
    assert result.job_type == BatchJobType.UPLOAD
    assert result.total_items == 3
    assert result.status == BatchJobStatus.PENDING

    # Verify job was saved to database
    mock_db.batch_jobs.insert_one.assert_called_once()


@pytest.mark.asyncio
async def test_batch_upload_without_collection(batch_processor, mock_upload_files, mock_db):
    """Test batch upload without creating a collection"""
    user_id = "user123"

    result = await batch_processor.batch_upload(
        files=mock_upload_files,
        user_id=user_id
    )

    assert result.config.get('collection_name') is None
    assert result.total_items == 3


@pytest.mark.asyncio
async def test_update_batch_item_success(batch_processor, mock_db):
    """Test updating batch item with success status"""
    batch_job_id = "job123"
    document_id = "doc456"
    filename = "test.pdf"

    await batch_processor._update_batch_item(
        batch_job_id=batch_job_id,
        document_id=document_id,
        filename=filename,
        status='success'
    )

    # Verify update was called with correct parameters
    call_args = mock_db.batch_jobs.update_one.call_args
    assert call_args[0][0] == {'id': batch_job_id}

    update_dict = call_args[0][1]
    assert '$push' in update_dict
    assert '$inc' in update_dict
    assert update_dict['$inc'] == {'completed_items': 1}


@pytest.mark.asyncio
async def test_update_batch_item_failure(batch_processor, mock_db):
    """Test updating batch item with failure status"""
    batch_job_id = "job123"
    filename = "test.pdf"
    error_message = "Upload failed"

    await batch_processor._update_batch_item(
        batch_job_id=batch_job_id,
        document_id=None,
        filename=filename,
        status='failed',
        error_message=error_message
    )

    # Verify failure counter was incremented
    call_args = mock_db.batch_jobs.update_one.call_args
    update_dict = call_args[0][1]
    assert update_dict['$inc'] == {'failed_items': 1}


@pytest.mark.asyncio
async def test_get_batch_job(batch_processor, mock_db):
    """Test retrieving a batch job"""
    job_id = "job123"
    user_id = "user123"

    mock_job_data = {
        'id': job_id,
        'user_id': user_id,
        'job_type': BatchJobType.UPLOAD,
        'status': BatchJobStatus.COMPLETED,
        'total_items': 3,
        'completed_items': 3,
        'failed_items': 0,
        'item_statuses': [],
        'config': {},
        'created_at': datetime.utcnow(),
        'started_at': datetime.utcnow(),
        'completed_at': datetime.utcnow()
    }

    mock_db.batch_jobs.find_one.return_value = mock_job_data

    result = await batch_processor.get_batch_job(job_id, user_id)

    assert result is not None
    assert result.id == job_id
    assert result.user_id == user_id
    assert result.status == BatchJobStatus.COMPLETED

    mock_db.batch_jobs.find_one.assert_called_once_with({
        'id': job_id,
        'user_id': user_id
    })


@pytest.mark.asyncio
async def test_get_batch_job_not_found(batch_processor, mock_db):
    """Test retrieving non-existent batch job"""
    mock_db.batch_jobs.find_one.return_value = None

    result = await batch_processor.get_batch_job("nonexistent", "user123")

    assert result is None


@pytest.mark.asyncio
async def test_list_batch_jobs(batch_processor, mock_db):
    """Test listing batch jobs"""
    user_id = "user123"

    mock_jobs = [
        {
            'id': 'job1',
            'user_id': user_id,
            'job_type': BatchJobType.UPLOAD,
            'status': BatchJobStatus.COMPLETED,
            'total_items': 3,
            'completed_items': 3,
            'failed_items': 0,
            'item_statuses': [],
            'config': {},
            'created_at': datetime.utcnow(),
            'started_at': datetime.utcnow(),
            'completed_at': datetime.utcnow()
        }
    ]

    mock_cursor = AsyncMock()
    mock_cursor.sort.return_value = mock_cursor
    mock_cursor.limit.return_value = mock_cursor
    mock_cursor.to_list.return_value = mock_jobs

    mock_db.batch_jobs.find.return_value = mock_cursor

    result = await batch_processor.list_batch_jobs(user_id=user_id, limit=50)

    assert len(result) == 1
    assert result[0].id == 'job1'
    assert result[0].status == BatchJobStatus.COMPLETED


@pytest.mark.asyncio
async def test_list_batch_jobs_with_filters(batch_processor, mock_db):
    """Test listing batch jobs with filters"""
    user_id = "user123"

    mock_cursor = AsyncMock()
    mock_cursor.sort.return_value = mock_cursor
    mock_cursor.limit.return_value = mock_cursor
    mock_cursor.to_list.return_value = []

    mock_db.batch_jobs.find.return_value = mock_cursor

    await batch_processor.list_batch_jobs(
        user_id=user_id,
        job_type=BatchJobType.UPLOAD,
        status=BatchJobStatus.COMPLETED,
        limit=20
    )

    # Verify query was called with filters
    call_args = mock_db.batch_jobs.find.call_args
    query = call_args[0][0]
    assert query['user_id'] == user_id
    assert query['job_type'] == BatchJobType.UPLOAD
    assert query['status'] == BatchJobStatus.COMPLETED


@pytest.mark.asyncio
async def test_create_collection(batch_processor, mock_db):
    """Test creating a document collection"""
    user_id = "user123"
    name = "Test Collection"
    document_ids = ["doc1", "doc2", "doc3"]
    tags = ["engineering", "civil"]

    result = await batch_processor.create_collection(
        user_id=user_id,
        name=name,
        document_ids=document_ids,
        tags=tags,
        project_name="Bridge Project"
    )

    assert isinstance(result, DocumentCollection)
    assert result.user_id == user_id
    assert result.name == name
    assert result.document_count == 3
    assert result.tags == tags
    assert result.project_name == "Bridge Project"

    mock_db.document_collections.insert_one.assert_called_once()


@pytest.mark.asyncio
async def test_get_collection(batch_processor, mock_db):
    """Test retrieving a collection"""
    collection_id = "coll123"
    user_id = "user123"

    mock_collection_data = {
        'id': collection_id,
        'user_id': user_id,
        'name': 'Test Collection',
        'description': 'Test description',
        'document_ids': ['doc1', 'doc2'],
        'document_count': 2,
        'tags': ['test'],
        'project_name': 'Test Project',
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }

    mock_db.document_collections.find_one.return_value = mock_collection_data

    result = await batch_processor.get_collection(collection_id, user_id)

    assert result is not None
    assert result.id == collection_id
    assert result.name == 'Test Collection'
    assert result.document_count == 2


@pytest.mark.asyncio
async def test_list_collections(batch_processor, mock_db):
    """Test listing collections"""
    user_id = "user123"

    mock_collections = [
        {
            'id': 'coll1',
            'user_id': user_id,
            'name': 'Collection 1',
            'description': None,
            'document_ids': ['doc1'],
            'document_count': 1,
            'tags': [],
            'project_name': None,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
    ]

    mock_cursor = AsyncMock()
    mock_cursor.sort.return_value = mock_cursor
    mock_cursor.limit.return_value = mock_cursor
    mock_cursor.to_list.return_value = mock_collections

    mock_db.document_collections.find.return_value = mock_cursor

    result = await batch_processor.list_collections(user_id=user_id)

    assert len(result) == 1
    assert result[0].name == 'Collection 1'


@pytest.mark.asyncio
async def test_update_collection_add_documents(batch_processor, mock_db):
    """Test adding documents to a collection"""
    collection_id = "coll123"
    user_id = "user123"

    existing_collection_data = {
        'id': collection_id,
        'user_id': user_id,
        'name': 'Test Collection',
        'description': None,
        'document_ids': ['doc1', 'doc2'],
        'document_count': 2,
        'tags': [],
        'project_name': None,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }

    updated_collection_data = existing_collection_data.copy()
    updated_collection_data['document_ids'] = ['doc1', 'doc2', 'doc3']
    updated_collection_data['document_count'] = 3

    mock_db.document_collections.find_one.side_effect = [
        existing_collection_data,
        updated_collection_data
    ]

    result = await batch_processor.update_collection(
        collection_id=collection_id,
        user_id=user_id,
        add_document_ids=['doc3']
    )

    assert result is not None
    assert result.document_count == 3
    assert 'doc3' in result.document_ids


@pytest.mark.asyncio
async def test_update_collection_remove_documents(batch_processor, mock_db):
    """Test removing documents from a collection"""
    collection_id = "coll123"
    user_id = "user123"

    existing_collection_data = {
        'id': collection_id,
        'user_id': user_id,
        'name': 'Test Collection',
        'description': None,
        'document_ids': ['doc1', 'doc2', 'doc3'],
        'document_count': 3,
        'tags': [],
        'project_name': None,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }

    updated_collection_data = existing_collection_data.copy()
    updated_collection_data['document_ids'] = ['doc1', 'doc2']
    updated_collection_data['document_count'] = 2

    mock_db.document_collections.find_one.side_effect = [
        existing_collection_data,
        updated_collection_data
    ]

    result = await batch_processor.update_collection(
        collection_id=collection_id,
        user_id=user_id,
        remove_document_ids=['doc3']
    )

    assert result is not None
    assert result.document_count == 2
    assert 'doc3' not in result.document_ids


@pytest.mark.asyncio
async def test_delete_collection(batch_processor, mock_db):
    """Test deleting a collection"""
    collection_id = "coll123"
    user_id = "user123"

    mock_result = Mock()
    mock_result.deleted_count = 1
    mock_db.document_collections.delete_one.return_value = mock_result

    result = await batch_processor.delete_collection(collection_id, user_id)

    assert result is True
    mock_db.document_collections.delete_one.assert_called_once_with({
        'id': collection_id,
        'user_id': user_id
    })


@pytest.mark.asyncio
async def test_delete_collection_not_found(batch_processor, mock_db):
    """Test deleting non-existent collection"""
    mock_result = Mock()
    mock_result.deleted_count = 0
    mock_db.document_collections.delete_one.return_value = mock_result

    result = await batch_processor.delete_collection("nonexistent", "user123")

    assert result is False
