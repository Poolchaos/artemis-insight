"""
Integration tests for summary and job routes.
"""

import pytest
from unittest.mock import patch, Mock, AsyncMock
from bson import ObjectId
from datetime import datetime

from app.models.summary import SummaryStatus
from app.models.job import JobStatus, JobType
from app.models.document import DocumentStatus


@pytest.fixture
def auth_headers(access_token):
    """Create authorization headers."""
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
async def test_document(test_db, test_user):
    """Create a test document."""
    document_id = ObjectId()
    await test_db.documents.insert_one({
        "_id": document_id,
        "user_id": test_user.id,
        "filename": "test_feasibility_study.pdf",
        "file_path": "/app/uploads/test.pdf",
        "file_size": 1024000,
        "mime_type": "application/pdf",
        "storage_key": "documents/test.pdf",
        "status": DocumentStatus.COMPLETED,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })
    return str(document_id)


@pytest.fixture
async def test_template(test_db):
    """Create a test template."""
    from app.models.template import TemplateInDB, TemplateSection, ProcessingStrategy

    template_id = ObjectId()
    template = TemplateInDB(
        _id=template_id,
        name="Test Template",
        description="Test template for integration tests",
        target_length="5 pages",
        category="engineering",
        sections=[
            TemplateSection(
                title="Introduction",
                guidance_prompt="Extract introduction",
                order=1,
                required=True
            ),
            TemplateSection(
                title="Conclusion",
                guidance_prompt="Extract conclusion",
                order=2,
                required=True
            )
        ],
        processing_strategy=ProcessingStrategy(),
        is_active=True
    )

    await test_db.templates.insert_one(template.model_dump(by_alias=True))
    return str(template_id)


@pytest.fixture
async def test_summary(test_db, test_user, test_document, test_template):
    """Create a test summary."""
    summary_id = ObjectId()
    await test_db.summaries.insert_one({
        "_id": summary_id,
        "user_id": test_user.id,
        "document_id": ObjectId(test_document),
        "template_id": test_template,
        "template_name": "Test Template",
        "status": SummaryStatus.COMPLETED,
        "sections": [
            {
                "title": "Introduction",
                "order": 1,
                "content": "This is the introduction section...",
                "source_chunks": 10,
                "pages_referenced": [1, 2, 3],
                "word_count": 150,
                "generated_at": datetime.utcnow()
            }
        ],
        "metadata": {
            "total_pages": 50,
            "total_words": 25000,
            "total_chunks": 50,
            "embedding_count": 50
        },
        "started_at": datetime.utcnow(),
        "completed_at": datetime.utcnow(),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })
    return str(summary_id)


class TestCreateSummary:
    """Test POST /api/summaries endpoint."""

    @pytest.mark.asyncio
    async def test_create_summary_success(
        self,
        client,
        test_db,
        auth_headers,
        test_document,
        test_template
    ):
        """Test successful summary creation."""
        # Mock Celery task
        with patch('app.routes.summaries.generate_summary_task') as mock_task:
            mock_result = Mock()
            mock_result.id = "celery-task-123"
            mock_task.apply_async.return_value = mock_result

            # Act
            response = await client.post(
                f"/api/summaries?document_id={test_document}&template_id={test_template}",
                headers=auth_headers
            )

            # Assert
            assert response.status_code == 202
            data = response.json()
            assert "job_id" in data
            assert "celery_task_id" in data
            assert data["status"] == JobStatus.PENDING
            assert "Poll GET /api/jobs/" in data["message"]

            # Verify Celery task was called
            mock_task.apply_async.assert_called_once()
            call_kwargs = mock_task.apply_async.call_args[1]["kwargs"]
            assert call_kwargs["document_id"] == test_document
            assert call_kwargs["template_id"] == test_template

            # Verify job was created in database
            job = await test_db.jobs.find_one({"_id": ObjectId(data["job_id"])})
            assert job is not None
            assert job["job_type"] == JobType.SUMMARIZE
            assert job["status"] == JobStatus.PENDING

    @pytest.mark.asyncio
    async def test_create_summary_invalid_document_id(
        self,
        client,
        auth_headers,
        test_template
    ):
        """Test create summary with invalid document_id."""
        response = await client.post(
            f"/api/summaries?document_id=invalid&template_id={test_template}",
            headers=auth_headers
        )

        assert response.status_code == 400
        assert "Invalid document_id format" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_summary_document_not_found(
        self,
        client,
        auth_headers,
        test_template
    ):
        """Test create summary with non-existent document."""
        fake_doc_id = str(ObjectId())
        response = await client.post(
            f"/api/summaries?document_id={fake_doc_id}&template_id={test_template}",
            headers=auth_headers
        )

        assert response.status_code == 404
        assert "Document not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_summary_template_not_found(
        self,
        client,
        auth_headers,
        test_document
    ):
        """Test create summary with non-existent template."""
        fake_template_id = str(ObjectId())
        response = await client.post(
            f"/api/summaries?document_id={test_document}&template_id={fake_template_id}",
            headers=auth_headers
        )

        assert response.status_code == 404
        assert "Template not found" in response.json()["detail"]


class TestListSummaries:
    """Test GET /api/summaries endpoint."""

    @pytest.mark.asyncio
    async def test_list_summaries_success(
        self,
        client,
        auth_headers,
        test_summary
    ):
        """Test listing summaries."""
        response = await client.get(
            "/api/summaries",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert data[0]["id"] == test_summary
        assert "template_name" in data[0]
        assert "section_count" in data[0]
        assert "total_word_count" in data[0]

    @pytest.mark.asyncio
    async def test_list_summaries_with_filters(
        self,
        client,
        auth_headers,
        test_document,
        test_summary
    ):
        """Test listing summaries with filters."""
        response = await client.get(
            f"/api/summaries?document_id={test_document}&status={SummaryStatus.COMPLETED}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        for summary in data:
            assert summary["status"] == SummaryStatus.COMPLETED


class TestGetSummary:
    """Test GET /api/summaries/{summary_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_summary_success(
        self,
        client,
        auth_headers,
        test_summary
    ):
        """Test getting a specific summary."""
        response = await client.get(
            f"/api/summaries/{test_summary}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_summary
        assert "sections" in data
        assert len(data["sections"]) > 0
        assert "metadata" in data
        assert data["status"] == SummaryStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_get_summary_not_found(
        self,
        client,
        auth_headers
    ):
        """Test getting non-existent summary."""
        fake_id = str(ObjectId())
        response = await client.get(
            f"/api/summaries/{fake_id}",
            headers=auth_headers
        )

        assert response.status_code == 404
        assert "Summary not found" in response.json()["detail"]


class TestDeleteSummary:
    """Test DELETE /api/summaries/{summary_id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_summary_success(
        self,
        client,
        test_db,
        auth_headers,
        test_summary
    ):
        """Test deleting a summary."""
        response = await client.delete(
            f"/api/summaries/{test_summary}",
            headers=auth_headers
        )

        assert response.status_code == 204

        # Verify summary was deleted
        summary = await test_db.summaries.find_one({"_id": ObjectId(test_summary)})
        assert summary is None


class TestRegenerateSection:
    """Test POST /api/summaries/{summary_id}/regenerate-section endpoint."""

    @pytest.mark.asyncio
    async def test_regenerate_section_success(
        self,
        client,
        test_db,
        auth_headers,
        test_summary
    ):
        """Test regenerating a section."""
        with patch('app.routes.summaries.regenerate_section_task') as mock_task:
            mock_result = Mock()
            mock_result.id = "celery-task-456"
            mock_task.apply_async.return_value = mock_result

            response = await client.post(
                f"/api/summaries/{test_summary}/regenerate-section?section_title=Introduction",
                headers=auth_headers
            )

            assert response.status_code == 202
            data = response.json()
            assert "job_id" in data
            assert data["section_title"] == "Introduction"
            assert "Poll GET /api/jobs/" in data["message"]

            # Verify Celery task was called
            mock_task.apply_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_regenerate_section_not_found(
        self,
        client,
        auth_headers,
        test_summary
    ):
        """Test regenerating non-existent section."""
        response = await client.post(
            f"/api/summaries/{test_summary}/regenerate-section?section_title=NonExistent",
            headers=auth_headers
        )

        assert response.status_code == 404
        assert "Section 'NonExistent' not found" in response.json()["detail"]


class TestGetJobStatus:
    """Test GET /api/jobs/{job_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_job_status_success(
        self,
        client,
        test_db,
        auth_headers,
        test_user,
        test_document,
        test_template
    ):
        """Test getting job status."""
        # Create a job
        job_id = ObjectId()
        await test_db.jobs.insert_one({
            "_id": job_id,
            "user_id": test_user.id,
            "document_id": ObjectId(test_document),
            "template_id": ObjectId(test_template),
            "job_type": JobType.SUMMARIZE,
            "status": JobStatus.RUNNING,
            "progress": 50,
            "started_at": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })

        response = await client.get(
            f"/api/jobs/{str(job_id)}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(job_id)
        assert data["status"] == JobStatus.RUNNING
        assert data["progress"] == 50


class TestListJobs:
    """Test GET /api/jobs endpoint."""

    @pytest.mark.asyncio
    async def test_list_jobs_success(
        self,
        client,
        test_db,
        auth_headers,
        test_user,
        test_document,
        test_template
    ):
        """Test listing jobs."""
        # Create test jobs
        for i in range(3):
            await test_db.jobs.insert_one({
                "_id": ObjectId(),
                "user_id": test_user.id,
                "document_id": ObjectId(test_document),
                "template_id": ObjectId(test_template),
                "job_type": JobType.SUMMARIZE,
                "status": JobStatus.COMPLETED if i % 2 == 0 else JobStatus.RUNNING,
                "progress": 100 if i % 2 == 0 else 50,
                "started_at": datetime.utcnow(),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })

        response = await client.get(
            "/api/jobs",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3

    @pytest.mark.asyncio
    async def test_list_jobs_with_filters(
        self,
        client,
        auth_headers
    ):
        """Test listing jobs with filters."""
        response = await client.get(
            f"/api/jobs?job_type={JobType.SUMMARIZE}&status={JobStatus.COMPLETED}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestCancelJob:
    """Test POST /api/jobs/{job_id}/cancel endpoint."""

    @pytest.mark.asyncio
    async def test_cancel_job_success(
        self,
        client,
        test_db,
        auth_headers,
        test_user,
        test_document,
        test_template
    ):
        """Test cancelling a running job."""
        # Create a running job
        job_id = ObjectId()
        await test_db.jobs.insert_one({
            "_id": job_id,
            "user_id": test_user.id,
            "document_id": ObjectId(test_document),
            "template_id": ObjectId(test_template),
            "job_type": JobType.SUMMARIZE,
            "status": JobStatus.RUNNING,
            "progress": 30,
            "celery_task_id": "test-task-123",
            "started_at": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })

        with patch('app.routes.jobs.celery_app') as mock_celery:
            response = await client.post(
                f"/api/jobs/{str(job_id)}/cancel",
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == JobStatus.CANCELLED

            # Verify Celery revoke was called
            mock_celery.control.revoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_completed_job(
        self,
        client,
        test_db,
        auth_headers,
        test_user,
        test_document,
        test_template
    ):
        """Test cancelling a completed job (should fail)."""
        # Create a completed job
        job_id = ObjectId()
        await test_db.jobs.insert_one({
            "_id": job_id,
            "user_id": test_user.id,
            "document_id": ObjectId(test_document),
            "template_id": ObjectId(test_template),
            "job_type": JobType.SUMMARIZE,
            "status": JobStatus.COMPLETED,
            "progress": 100,
            "started_at": datetime.utcnow(),
            "completed_at": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })

        response = await client.post(
            f"/api/jobs/{str(job_id)}/cancel",
            headers=auth_headers
        )

        assert response.status_code == 400
        assert "Cannot cancel job with status" in response.json()["detail"]
