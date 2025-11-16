"""
Unit tests for job model.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError
from bson import ObjectId

from app.models.job import (
    JobType,
    JobStatus,
    JobBase,
    JobCreate,
    JobUpdate,
    JobInDB,
    JobResponse
)


def test_job_type_enum():
    """Test job type enum values."""
    assert JobType.UPLOAD == "upload"
    assert JobType.EXTRACT == "extract"
    assert JobType.SUMMARIZE == "summarize"
    assert JobType.EMBED == "embed"


def test_job_status_enum():
    """Test job status enum values."""
    assert JobStatus.PENDING == "pending"
    assert JobStatus.RUNNING == "running"
    assert JobStatus.COMPLETED == "completed"
    assert JobStatus.FAILED == "failed"
    assert JobStatus.CANCELLED == "cancelled"


def test_job_base_valid():
    """Test valid job base creation."""
    job = JobBase(
        job_type=JobType.EXTRACT,
        status=JobStatus.PENDING,
        progress=0
    )
    assert job.job_type == JobType.EXTRACT
    assert job.status == JobStatus.PENDING
    assert job.progress == 0


def test_job_base_invalid_progress():
    """Test job base with invalid progress value."""
    with pytest.raises(ValidationError) as exc_info:
        JobBase(
            job_type=JobType.EXTRACT,
            progress=150
        )
    assert "less than or equal to 100" in str(exc_info.value)


def test_job_base_negative_progress():
    """Test job base with negative progress."""
    with pytest.raises(ValidationError) as exc_info:
        JobBase(
            job_type=JobType.EXTRACT,
            progress=-10
        )
    assert "greater than or equal to 0" in str(exc_info.value)


def test_job_create_valid():
    """Test valid job creation."""
    user_id = str(ObjectId())
    document_id = str(ObjectId())
    job = JobCreate(
        user_id=user_id,
        document_id=document_id,
        job_type=JobType.SUMMARIZE,
        celery_task_id="task-123"
    )
    assert job.user_id == user_id
    assert job.document_id == document_id
    assert job.celery_task_id == "task-123"


def test_job_create_invalid_user_id():
    """Test job create with invalid user ID."""
    with pytest.raises(ValidationError) as exc_info:
        JobCreate(
            user_id="invalid-id",
            document_id=str(ObjectId()),
            job_type=JobType.EXTRACT
        )
    assert "Invalid ObjectId" in str(exc_info.value)


def test_job_create_invalid_document_id():
    """Test job create with invalid document ID."""
    with pytest.raises(ValidationError) as exc_info:
        JobCreate(
            user_id=str(ObjectId()),
            document_id="not-an-object-id",
            job_type=JobType.EXTRACT
        )
    assert "Invalid ObjectId" in str(exc_info.value)


def test_job_update():
    """Test job update schema."""
    update = JobUpdate(
        status=JobStatus.COMPLETED,
        progress=100,
        completed_at=datetime.utcnow()
    )
    assert update.status == JobStatus.COMPLETED
    assert update.progress == 100
    assert isinstance(update.completed_at, datetime)


def test_job_update_with_error():
    """Test job update with error message."""
    update = JobUpdate(
        status=JobStatus.FAILED,
        error_message="Processing failed"
    )
    assert update.status == JobStatus.FAILED
    assert update.error_message == "Processing failed"


def test_job_update_partial():
    """Test partial job update."""
    update = JobUpdate(progress=50)
    assert update.progress == 50
    assert update.status is None


def test_job_in_db():
    """Test job in database schema."""
    user_id = ObjectId()
    document_id = ObjectId()
    job = JobInDB(
        user_id=user_id,
        document_id=document_id,
        job_type=JobType.EMBED,
        progress=25
    )
    assert job.user_id == user_id
    assert job.document_id == document_id
    assert job.id is not None
    assert isinstance(job.started_at, datetime)
    assert isinstance(job.created_at, datetime)
    assert job.completed_at is None


def test_job_response():
    """Test job API response schema."""
    response = JobResponse(
        id=str(ObjectId()),
        user_id=str(ObjectId()),
        document_id=str(ObjectId()),
        job_type=JobType.SUMMARIZE,
        status=JobStatus.RUNNING,
        progress=75,
        started_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    assert response.job_type == JobType.SUMMARIZE
    assert response.status == JobStatus.RUNNING
    assert response.progress == 75
