"""
Job status and management routes.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db
from app.models.user import UserInDB
from app.models.job import JobResponse, JobStatus, JobType
from app.middleware.auth import get_current_user
from app.utils.task_monitor import auto_fail_stuck_jobs

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobResponse)
@limiter.limit("30/minute")  # Limit job status polling to prevent API overload
async def get_job_status(
    request: Request,
    job_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Get job status and progress.

    Poll this endpoint to track the progress of async summarization jobs.
    Rate limited to 30 requests/minute to prevent server overload.

    Returns:
    - **status**: Job status (pending, running, completed, failed, cancelled)
    - **progress**: Progress percentage (0-100)
    - **error_message**: Error details if job failed
    - **summary_id**: ID of generated summary (when completed)
    """
    if not ObjectId.is_valid(job_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job_id format"
        )

    # Query database
    job = await db.jobs.find_one({
        "_id": ObjectId(job_id),
        "user_id": current_user.id
    })

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Convert to response model
    return JobResponse(
        id=str(job["_id"]),
        user_id=str(job["user_id"]),
        document_id=str(job["document_id"]),
        template_id=str(job["template_id"]) if job.get("template_id") else None,
        summary_id=str(job["summary_id"]) if job.get("summary_id") else None,
        job_type=job["job_type"],
        status=job["status"],
        progress=job["progress"],
        error_message=job.get("error_message"),
        celery_task_id=job.get("celery_task_id"),
        started_at=job["started_at"],
        completed_at=job.get("completed_at"),
        created_at=job["created_at"],
        updated_at=job["updated_at"]
    )


@router.get("", response_model=List[JobResponse])
async def list_jobs(
    job_type: Optional[JobType] = Query(None, description="Filter by job type"),
    status: Optional[JobStatus] = Query(None, description="Filter by status"),
    document_id: Optional[str] = Query(None, description="Filter by document ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records to return"),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    List jobs for the current user.

    Supports filtering by job type, status, and document.
    Returns jobs in reverse chronological order (newest first).
    """
    # Build query
    query = {"user_id": current_user.id}

    if job_type:
        query["job_type"] = job_type

    if status:
        query["status"] = status

    if document_id:
        if not ObjectId.is_valid(document_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid document_id format"
            )
        query["document_id"] = ObjectId(document_id)

    # Query database
    cursor = db.jobs.find(query).sort("created_at", -1).skip(skip).limit(limit)
    jobs = await cursor.to_list(length=limit)

    # Convert to response models
    return [
        JobResponse(
            id=str(job["_id"]),
            user_id=str(job["user_id"]),
            document_id=str(job["document_id"]),
            template_id=str(job["template_id"]) if job.get("template_id") else None,
            summary_id=str(job["summary_id"]) if job.get("summary_id") else None,
            job_type=job["job_type"],
            status=job["status"],
            progress=job["progress"],
            error_message=job.get("error_message"),
            celery_task_id=job.get("celery_task_id"),
            started_at=job["started_at"],
            completed_at=job.get("completed_at"),
            created_at=job["created_at"],
            updated_at=job["updated_at"]
        )
        for job in jobs
    ]


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Delete a job record.

    Note: This only removes the job tracking record, it does not cancel
    a running Celery task or delete the generated summary.
    """
    if not ObjectId.is_valid(job_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job_id format"
        )

    # Delete job
    result = await db.jobs.delete_one({
        "_id": ObjectId(job_id),
        "user_id": current_user.id
    })

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    return None


@router.post("/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(
    job_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Cancel a running job.

    Attempts to revoke the Celery task and updates job status to CANCELLED.
    May not immediately stop the task if it's already processing.
    """
    if not ObjectId.is_valid(job_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job_id format"
        )

    # Query database
    job = await db.jobs.find_one({
        "_id": ObjectId(job_id),
        "user_id": current_user.id
    })

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Check if job can be cancelled
    if job["status"] in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job with status: {job['status']}"
        )

    # Revoke Celery task if exists
    if job.get("celery_task_id"):
        from app.celery_app import celery_app
        celery_app.control.revoke(job["celery_task_id"], terminate=True)

    # Update job status
    await db.jobs.update_one(
        {"_id": ObjectId(job_id)},
        {
            "$set": {
                "status": JobStatus.CANCELLED,
                "completed_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        }
    )

    # Fetch updated job
    updated_job = await db.jobs.find_one({"_id": ObjectId(job_id)})

    return JobResponse(
        id=str(updated_job["_id"]),
        user_id=str(updated_job["user_id"]),
        document_id=str(updated_job["document_id"]),
        template_id=str(updated_job["template_id"]) if updated_job.get("template_id") else None,
        summary_id=str(updated_job["summary_id"]) if updated_job.get("summary_id") else None,
        job_type=updated_job["job_type"],
        status=updated_job["status"],
        progress=updated_job["progress"],
        error_message=updated_job.get("error_message"),
        celery_task_id=updated_job.get("celery_task_id"),
        started_at=updated_job["started_at"],
        completed_at=updated_job.get("completed_at"),
        created_at=updated_job["created_at"],
        updated_at=updated_job["updated_at"]
    )


@router.post("/cleanup-stuck", response_model=dict)
async def cleanup_stuck_jobs(
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Detect and auto-fail stuck jobs (admin utility).

    Jobs stuck in PENDING or RUNNING for more than 60 minutes are marked as FAILED.
    This helps recover from crashed workers or network issues.

    Returns:
        Number of jobs marked as failed
    """
    failed_count = await auto_fail_stuck_jobs(db, timeout_minutes=60)

    return {
        "message": f"Cleaned up {failed_count} stuck job(s)",
        "failed_count": failed_count
    }
