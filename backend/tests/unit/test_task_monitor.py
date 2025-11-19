"""
Unit tests for stuck job detection and cleanup utilities.
"""

import pytest
from datetime import datetime, timedelta
from bson import ObjectId

from app.utils.task_monitor import detect_stuck_jobs, auto_fail_stuck_jobs
from app.models.job import JobStatus


@pytest.fixture
async def test_db_with_jobs(test_db):
    """Create test database with sample jobs."""
    # Clear existing data
    await test_db.jobs.delete_many({})
    await test_db.summaries.delete_many({})

    # Create current time reference
    now = datetime.utcnow()

    # Job 1: Stuck RUNNING job (2 hours old)
    stuck_running_id = ObjectId()
    await test_db.jobs.insert_one({
        "_id": stuck_running_id,
        "user_id": ObjectId(),
        "document_id": ObjectId(),
        "template_id": ObjectId(),
        "job_type": "summarize",
        "status": JobStatus.RUNNING,
        "progress": 10,
        "created_at": now - timedelta(hours=2),
        "updated_at": now - timedelta(hours=2),
        "started_at": now - timedelta(hours=2)
    })

    # Create associated summary for stuck job
    await test_db.summaries.insert_one({
        "_id": ObjectId(),
        "job_id": stuck_running_id,
        "user_id": ObjectId(),
        "document_id": ObjectId(),
        "template_id": "test_template",
        "template_name": "Test Template",
        "status": "processing",
        "sections": [],
        "created_at": now - timedelta(hours=2),
        "updated_at": now - timedelta(hours=2),
        "started_at": now - timedelta(hours=2)
    })

    # Job 2: Stuck PENDING job (90 minutes old)
    stuck_pending_id = ObjectId()
    await test_db.jobs.insert_one({
        "_id": stuck_pending_id,
        "user_id": ObjectId(),
        "document_id": ObjectId(),
        "template_id": ObjectId(),
        "job_type": "summarize",
        "status": JobStatus.PENDING,
        "progress": 0,
        "created_at": now - timedelta(minutes=90),
        "updated_at": now - timedelta(minutes=90),
        "started_at": now - timedelta(minutes=90)
    })

    # Job 3: Recently updated RUNNING job (5 minutes old)
    recent_running_id = ObjectId()
    await test_db.jobs.insert_one({
        "_id": recent_running_id,
        "user_id": ObjectId(),
        "document_id": ObjectId(),
        "template_id": ObjectId(),
        "job_type": "summarize",
        "status": JobStatus.RUNNING,
        "progress": 50,
        "created_at": now - timedelta(minutes=10),
        "updated_at": now - timedelta(minutes=5),
        "started_at": now - timedelta(minutes=10)
    })

    # Job 4: Completed job (1 hour old)
    completed_id = ObjectId()
    await test_db.jobs.insert_one({
        "_id": completed_id,
        "user_id": ObjectId(),
        "document_id": ObjectId(),
        "template_id": ObjectId(),
        "job_type": "summarize",
        "status": JobStatus.COMPLETED,
        "progress": 100,
        "summary_id": ObjectId(),
        "created_at": now - timedelta(hours=1),
        "updated_at": now - timedelta(hours=1),
        "started_at": now - timedelta(hours=1),
        "completed_at": now - timedelta(hours=1)
    })

    # Job 5: Failed job (30 minutes old)
    failed_id = ObjectId()
    await test_db.jobs.insert_one({
        "_id": failed_id,
        "user_id": ObjectId(),
        "document_id": ObjectId(),
        "template_id": ObjectId(),
        "job_type": "summarize",
        "status": JobStatus.FAILED,
        "progress": 20,
        "error_message": "Test error",
        "created_at": now - timedelta(minutes=30),
        "updated_at": now - timedelta(minutes=30),
        "started_at": now - timedelta(minutes=30),
        "completed_at": now - timedelta(minutes=30)
    })

    yield test_db

    # Cleanup
    await test_db.jobs.delete_many({})
    await test_db.summaries.delete_many({})


class TestDetectStuckJobs:
    """Test stuck job detection."""

    @pytest.mark.asyncio
    async def test_detect_stuck_jobs_default_timeout(self, test_db_with_jobs):
        """Test detecting stuck jobs with default 60-minute timeout."""
        stuck_job_ids = await detect_stuck_jobs(test_db_with_jobs, timeout_minutes=60)

        # Should detect 2 stuck jobs (2 hours and 90 minutes old)
        assert len(stuck_job_ids) == 2

    @pytest.mark.asyncio
    async def test_detect_stuck_jobs_custom_timeout(self, test_db_with_jobs):
        """Test detecting stuck jobs with custom timeout."""
        # Use 30-minute timeout
        stuck_job_ids = await detect_stuck_jobs(test_db_with_jobs, timeout_minutes=30)

        # Should detect 2 stuck jobs (both over 30 minutes)
        assert len(stuck_job_ids) == 2

    @pytest.mark.asyncio
    async def test_detect_stuck_jobs_strict_timeout(self, test_db_with_jobs):
        """Test detecting stuck jobs with very strict timeout."""
        # Use 3-minute timeout
        stuck_job_ids = await detect_stuck_jobs(test_db_with_jobs, timeout_minutes=3)

        # Should detect 3 stuck jobs (all jobs: 2hrs, 90min, and 5min are all > 3min)
        assert len(stuck_job_ids) == 3

    @pytest.mark.asyncio
    async def test_no_stuck_jobs_when_all_recent(self, test_db):
        """Test detection when all jobs are recent."""
        now = datetime.utcnow()

        # Create only recent jobs
        await test_db.jobs.insert_one({
            "_id": ObjectId(),
            "user_id": ObjectId(),
            "document_id": ObjectId(),
            "template_id": ObjectId(),
            "job_type": "summarize",
            "status": JobStatus.RUNNING,
            "progress": 50,
            "created_at": now - timedelta(minutes=5),
            "updated_at": now - timedelta(minutes=1),
            "started_at": now - timedelta(minutes=5)
        })

        stuck_job_ids = await detect_stuck_jobs(test_db, timeout_minutes=60)

        # Should detect no stuck jobs
        assert len(stuck_job_ids) == 0

    @pytest.mark.asyncio
    async def test_completed_jobs_not_detected(self, test_db_with_jobs):
        """Test that completed jobs are not detected as stuck."""
        stuck_job_ids = await detect_stuck_jobs(test_db_with_jobs, timeout_minutes=30)

        # Verify completed and failed jobs are not in results
        all_jobs = await test_db_with_jobs.jobs.find({}).to_list(length=100)
        completed_job_ids = [
            str(job["_id"]) for job in all_jobs
            if job["status"] in [JobStatus.COMPLETED, JobStatus.FAILED]
        ]

        for job_id in completed_job_ids:
            assert job_id not in stuck_job_ids


class TestAutoFailStuckJobs:
    """Test automatic failing of stuck jobs."""

    @pytest.mark.asyncio
    async def test_auto_fail_stuck_jobs(self, test_db_with_jobs):
        """Test automatically marking stuck jobs as failed."""
        # Mark stuck jobs as failed
        failed_count = await auto_fail_stuck_jobs(test_db_with_jobs, timeout_minutes=60)

        # Should have failed 2 jobs
        assert failed_count == 2

        # Verify jobs were updated
        failed_jobs = await test_db_with_jobs.jobs.find({
            "status": JobStatus.FAILED,
            "error_message": {"$regex": "timed out"}
        }).to_list(length=10)

        assert len(failed_jobs) == 2

        # Verify all failed jobs have proper fields
        for job in failed_jobs:
            assert job["status"] == JobStatus.FAILED
            assert "timed out" in job["error_message"]
            assert "completed_at" in job
            assert job["completed_at"] is not None

    @pytest.mark.asyncio
    async def test_auto_fail_updates_summaries(self, test_db_with_jobs):
        """Test that associated summaries are also marked as failed."""
        # Get stuck job with associated summary
        stuck_job = await test_db_with_jobs.jobs.find_one({
            "status": JobStatus.RUNNING,
            "updated_at": {"$lt": datetime.utcnow() - timedelta(hours=1)}
        })

        stuck_job_id = stuck_job["_id"]

        # Mark stuck jobs as failed
        await auto_fail_stuck_jobs(test_db_with_jobs, timeout_minutes=60)

        # Verify associated summary was updated
        summary = await test_db_with_jobs.summaries.find_one({"job_id": stuck_job_id})

        assert summary is not None
        assert summary["status"] == "failed"
        assert "timeout" in summary["error_message"].lower()
        assert "completed_at" in summary
        assert summary["completed_at"] is not None

    @pytest.mark.asyncio
    async def test_auto_fail_no_stuck_jobs(self, test_db):
        """Test auto-fail when there are no stuck jobs."""
        now = datetime.utcnow()

        # Create only recent jobs
        await test_db.jobs.insert_one({
            "_id": ObjectId(),
            "user_id": ObjectId(),
            "document_id": ObjectId(),
            "template_id": ObjectId(),
            "job_type": "summarize",
            "status": JobStatus.RUNNING,
            "progress": 50,
            "created_at": now - timedelta(minutes=5),
            "updated_at": now - timedelta(minutes=1),
            "started_at": now - timedelta(minutes=5)
        })

        # Try to fail stuck jobs
        failed_count = await auto_fail_stuck_jobs(test_db, timeout_minutes=60)

        # Should have failed 0 jobs
        assert failed_count == 0

    @pytest.mark.asyncio
    async def test_auto_fail_custom_timeout(self, test_db_with_jobs):
        """Test auto-fail with custom timeout."""
        # Use 30-minute timeout
        failed_count = await auto_fail_stuck_jobs(test_db_with_jobs, timeout_minutes=30)

        # Should have failed 2 jobs (both over 30 minutes)
        assert failed_count == 2

    @pytest.mark.asyncio
    async def test_error_message_includes_timeout(self, test_db_with_jobs):
        """Test that error messages include timeout information."""
        timeout_minutes = 60
        await auto_fail_stuck_jobs(test_db_with_jobs, timeout_minutes=timeout_minutes)

        # Get failed jobs
        failed_jobs = await test_db_with_jobs.jobs.find({
            "status": JobStatus.FAILED,
            "error_message": {"$regex": "timed out"}
        }).to_list(length=10)

        # Verify error messages contain timeout duration
        for job in failed_jobs:
            assert f">{timeout_minutes} minutes" in job["error_message"]


class TestStuckJobEdgeCases:
    """Test edge cases for stuck job detection."""

    @pytest.mark.asyncio
    async def test_job_at_exact_timeout_boundary(self, test_db):
        """Test job that is exactly at the timeout boundary."""
        now = datetime.utcnow()
        timeout_minutes = 60

        # Create job exactly 60 minutes old
        await test_db.jobs.insert_one({
            "_id": ObjectId(),
            "user_id": ObjectId(),
            "document_id": ObjectId(),
            "template_id": ObjectId(),
            "job_type": "summarize",
            "status": JobStatus.RUNNING,
            "progress": 50,
            "created_at": now - timedelta(minutes=timeout_minutes),
            "updated_at": now - timedelta(minutes=timeout_minutes),
            "started_at": now - timedelta(minutes=timeout_minutes)
        })

        # Should detect as stuck (using less-than, so boundary is included)
        stuck_job_ids = await detect_stuck_jobs(test_db, timeout_minutes=timeout_minutes)
        assert len(stuck_job_ids) == 1

    @pytest.mark.asyncio
    async def test_job_just_under_timeout(self, test_db):
        """Test job that is just under the timeout threshold."""
        now = datetime.utcnow()
        timeout_minutes = 60

        # Create job 59 minutes old
        await test_db.jobs.insert_one({
            "_id": ObjectId(),
            "user_id": ObjectId(),
            "document_id": ObjectId(),
            "template_id": ObjectId(),
            "job_type": "summarize",
            "status": JobStatus.RUNNING,
            "progress": 50,
            "created_at": now - timedelta(minutes=59),
            "updated_at": now - timedelta(minutes=59),
            "started_at": now - timedelta(minutes=59)
        })

        # Should not detect as stuck
        stuck_job_ids = await detect_stuck_jobs(test_db, timeout_minutes=timeout_minutes)
        assert len(stuck_job_ids) == 0

    @pytest.mark.asyncio
    async def test_multiple_stuck_jobs_same_user(self, test_db):
        """Test detecting multiple stuck jobs for the same user."""
        now = datetime.utcnow()
        user_id = ObjectId()

        # Create 3 stuck jobs for same user
        for i in range(3):
            await test_db.jobs.insert_one({
                "_id": ObjectId(),
                "user_id": user_id,
                "document_id": ObjectId(),
                "template_id": ObjectId(),
                "job_type": "summarize",
                "status": JobStatus.RUNNING,
                "progress": 10 * i,
                "created_at": now - timedelta(hours=2),
                "updated_at": now - timedelta(hours=2),
                "started_at": now - timedelta(hours=2)
            })

        # Should detect all 3
        stuck_job_ids = await detect_stuck_jobs(test_db, timeout_minutes=60)
        assert len(stuck_job_ids) == 3

        # Auto-fail should update all 3
        failed_count = await auto_fail_stuck_jobs(test_db, timeout_minutes=60)
        assert failed_count == 3
