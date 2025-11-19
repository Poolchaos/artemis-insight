"""
Integration tests for summary retry endpoint.
"""

import pytest
from datetime import datetime, timedelta
from bson import ObjectId
from unittest.mock import patch, MagicMock

from app.models.job import JobStatus
from app.models.summary import SummaryStatus
from app.models.document import DocumentStatus


@pytest.fixture
async def setup_retry_test_data(test_db, test_user):
    """Setup test data for retry endpoint tests."""
    # Create a completed document
    document_id = ObjectId()
    await test_db.documents.insert_one({
        "_id": document_id,
        "user_id": test_user.id,
        "filename": "test.pdf",
        "file_path": "documents/test.pdf",
        "file_size": 1024,
        "mime_type": "application/pdf",
        "status": DocumentStatus.COMPLETED,
        "page_count": 10,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })

    # Create a template
    template_id = ObjectId()
    await test_db.templates.insert_one({
        "_id": template_id,
        "name": "Test Template",
        "description": "Test",
        "is_active": True,
        "sections": [
            {
                "title": "Introduction",
                "guidance_prompt": "Test",
                "order": 1,
                "required": True
            }
        ],
        "processing_strategy": {
            "approach": "multi-pass",
            "chunk_size": 500,
            "overlap": 50,
            "embedding_model": "text-embedding-3-small",
            "summarization_model": "gpt-4o-mini",
            "max_tokens_per_section": 1500,
            "temperature": 0.3
        },
        "system_prompt": "Test",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })

    # Create a failed job
    job_id = ObjectId()
    await test_db.jobs.insert_one({
        "_id": job_id,
        "user_id": test_user.id,
        "document_id": document_id,
        "template_id": template_id,
        "job_type": "summarize",
        "status": JobStatus.FAILED,
        "progress": 50,
        "error_message": "OpenAI API timeout",
        "started_at": datetime.utcnow(),
        "completed_at": datetime.utcnow(),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })

    # Create a failed summary
    summary_id = ObjectId()
    await test_db.summaries.insert_one({
        "_id": summary_id,
        "user_id": test_user.id,
        "document_id": document_id,
        "job_id": job_id,
        "template_id": str(template_id),
        "template_name": "Test Template",
        "status": SummaryStatus.FAILED,
        "error_message": "OpenAI API timeout",
        "sections": [],
        "started_at": datetime.utcnow(),
        "completed_at": datetime.utcnow(),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })

    return {
        "document_id": document_id,
        "template_id": template_id,
        "job_id": job_id,
        "summary_id": summary_id
    }


class TestSummaryRetryEndpoint:
    """Test POST /api/summaries/{id}/retry endpoint."""

    @pytest.mark.asyncio
    async def test_retry_failed_summary_success(
        self, client, access_token, setup_retry_test_data, test_db
    ):
        """Test successful retry of a failed summary."""
        summary_id = setup_retry_test_data["summary_id"]

        # Mock Celery task
        with patch('app.routes.summaries.generate_summary_task') as mock_task:
            mock_task.apply_async.return_value = MagicMock(id="celery-task-123")

            # Make retry request
            response = await client.post(
                f"/api/summaries/{summary_id}/retry",
                headers={"Authorization": f"Bearer {access_token}"}
            )

        # Verify response
        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"
        assert "Poll GET /api/jobs/" in data["message"]

        # Verify old summary was deleted
        old_summary = await test_db.summaries.find_one({"_id": summary_id})
        assert old_summary is None

        # Verify new job was created
        new_job_id = ObjectId(data["job_id"])
        new_job = await test_db.jobs.find_one({"_id": new_job_id})
        assert new_job is not None
        assert new_job["status"] == JobStatus.PENDING
        assert new_job["job_type"] == "summarize"
        assert new_job["document_id"] == setup_retry_test_data["document_id"]
        assert new_job["template_id"] == setup_retry_test_data["template_id"]

        # Verify Celery task was started
        mock_task.apply_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_nonexistent_summary(self, client, access_token):
        """Test retry with invalid summary ID."""
        fake_id = str(ObjectId())

        response = await client.post(
            f"/api/summaries/{fake_id}/retry",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_retry_completed_summary_fails(
        self, client, access_token, test_db, test_user, setup_retry_test_data
    ):
        """Test that retrying a completed summary fails."""
        # Create a completed summary
        completed_summary_id = ObjectId()
        await test_db.summaries.insert_one({
            "_id": completed_summary_id,
            "user_id": test_user.id,
            "document_id": setup_retry_test_data["document_id"],
            "job_id": ObjectId(),
            "template_id": str(setup_retry_test_data["template_id"]),
            "template_name": "Test Template",
            "status": SummaryStatus.COMPLETED,
            "sections": [
                {
                    "title": "Introduction",
                    "order": 1,
                    "content": "Test content",
                    "source_chunks": 5,
                    "pages_referenced": [1, 2],
                    "word_count": 100,
                    "generated_at": datetime.utcnow().isoformat()
                }
            ],
            "metadata": {
                "total_pages": 10,
                "total_words": 1000,
                "total_chunks": 20,
                "embedding_count": 20,
                "processing_duration_seconds": 30
            },
            "started_at": datetime.utcnow(),
            "completed_at": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })

        response = await client.post(
            f"/api/summaries/{completed_summary_id}/retry",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 400
        assert "Can only retry failed summaries" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_retry_processing_summary_fails(
        self, client, access_token, test_db, test_user, setup_retry_test_data
    ):
        """Test that retrying a processing summary fails."""
        # Create a processing summary
        processing_summary_id = ObjectId()
        await test_db.summaries.insert_one({
            "_id": processing_summary_id,
            "user_id": test_user.id,
            "document_id": setup_retry_test_data["document_id"],
            "job_id": ObjectId(),
            "template_id": str(setup_retry_test_data["template_id"]),
            "template_name": "Test Template",
            "status": SummaryStatus.PROCESSING,
            "sections": [],
            "started_at": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })

        response = await client.post(
            f"/api/summaries/{processing_summary_id}/retry",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 400
        assert "Can only retry failed summaries" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_retry_with_deleted_document_fails(
        self, client, access_token, test_db, test_user, setup_retry_test_data
    ):
        """Test retry fails when original document is deleted."""
        summary_id = setup_retry_test_data["summary_id"]

        # Delete the document
        await test_db.documents.delete_one({"_id": setup_retry_test_data["document_id"]})

        response = await client.post(
            f"/api/summaries/{summary_id}/retry",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 404
        assert "document not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_retry_with_processing_document_fails(
        self, client, access_token, test_db, setup_retry_test_data
    ):
        """Test retry fails when document is still processing."""
        summary_id = setup_retry_test_data["summary_id"]

        # Update document status to processing
        await test_db.documents.update_one(
            {"_id": setup_retry_test_data["document_id"]},
            {"$set": {"status": DocumentStatus.PROCESSING}}
        )

        response = await client.post(
            f"/api/summaries/{summary_id}/retry",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 400
        assert "must be 'completed'" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_retry_with_deleted_template_fails(
        self, client, access_token, test_db, setup_retry_test_data
    ):
        """Test retry fails when original template is deleted."""
        summary_id = setup_retry_test_data["summary_id"]

        # Delete the template
        await test_db.templates.delete_one({"_id": setup_retry_test_data["template_id"]})

        response = await client.post(
            f"/api/summaries/{summary_id}/retry",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 404
        assert "template not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_retry_without_auth_fails(self, client, setup_retry_test_data):
        """Test retry without authentication fails."""
        summary_id = setup_retry_test_data["summary_id"]

        response = await client.post(f"/api/summaries/{summary_id}/retry")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_retry_other_users_summary_fails(
        self, client, test_db, setup_retry_test_data
    ):
        """Test that users cannot retry other users' summaries."""
        # Create another user
        from app.services.user_service import UserService
        from app.models.user import UserCreate
        from app.utils.auth import create_access_token

        user_service = UserService(test_db)
        other_user = await user_service.create_user(UserCreate(
            email="other@example.com",
            name="Other User",
            password="password123"
        ))
        other_token = create_access_token(str(other_user.id))

        summary_id = setup_retry_test_data["summary_id"]

        response = await client.post(
            f"/api/summaries/{summary_id}/retry",
            headers={"Authorization": f"Bearer {other_token}"}
        )

        assert response.status_code == 404  # Not found (filtered by user_id)

    @pytest.mark.asyncio
    async def test_retry_invalid_summary_id_format(self, client, access_token):
        """Test retry with invalid ObjectId format."""
        response = await client.post(
            "/api/summaries/invalid-id/retry",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 400
        assert "Invalid summary_id format" in response.json()["detail"]


class TestCleanupStuckJobsEndpoint:
    """Test POST /api/jobs/cleanup-stuck endpoint."""

    @pytest.mark.asyncio
    async def test_cleanup_stuck_jobs_success(
        self, client, access_token, test_db, test_user
    ):
        """Test successful cleanup of stuck jobs."""
        # Create a stuck job (2 hours old)
        stuck_job_id = ObjectId()
        await test_db.jobs.insert_one({
            "_id": stuck_job_id,
            "user_id": test_user.id,
            "document_id": ObjectId(),
            "template_id": ObjectId(),
            "job_type": "summarize",
            "status": JobStatus.RUNNING,
            "progress": 10,
            "created_at": datetime.utcnow() - timedelta(hours=2),
            "updated_at": datetime.utcnow() - timedelta(hours=2),
            "started_at": datetime.utcnow() - timedelta(hours=2)
        })

        response = await client.post(
            "/api/jobs/cleanup-stuck",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "failed_count" in data
        assert "message" in data

    @pytest.mark.asyncio
    async def test_cleanup_without_auth_fails(self, client):
        """Test cleanup without authentication fails."""
        response = await client.post("/api/jobs/cleanup-stuck")

        assert response.status_code == 401
