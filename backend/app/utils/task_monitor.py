"""
Task monitoring utilities to detect and handle stuck/zombie tasks.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Any
from app.models.job import JobStatus

logger = logging.getLogger(__name__)


async def detect_stuck_jobs(
    db: Any,
    timeout_minutes: int = 60
) -> List[str]:
    """
    Detect jobs that have been "running" for too long without progress updates.

    Args:
        db: MongoDB database instance
        timeout_minutes: Consider jobs stuck if no update for this many minutes

    Returns:
        List of stuck job IDs
    """
    cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)

    stuck_jobs = await db.jobs.find({
        "status": {"$in": [JobStatus.PENDING, JobStatus.RUNNING]},
        "updated_at": {"$lt": cutoff_time}
    }).to_list(length=100)

    stuck_job_ids = [str(job["_id"]) for job in stuck_jobs]

    if stuck_job_ids:
        logger.warning(
            f"Found {len(stuck_job_ids)} stuck jobs (no update for >{timeout_minutes} minutes): "
            f"{', '.join(stuck_job_ids[:5])}{'...' if len(stuck_job_ids) > 5 else ''}"
        )

    return stuck_job_ids


async def auto_fail_stuck_jobs(
    db: Any,
    timeout_minutes: int = 60
) -> int:
    """
    Automatically mark stuck jobs as FAILED.

    Args:
        db: MongoDB database instance
        timeout_minutes: Consider jobs stuck if no update for this many minutes

    Returns:
        Number of jobs marked as failed
    """
    stuck_job_ids = await detect_stuck_jobs(db, timeout_minutes)

    if not stuck_job_ids:
        return 0

    from bson import ObjectId

    result = await db.jobs.update_many(
        {"_id": {"$in": [ObjectId(job_id) for job_id in stuck_job_ids]}},
        {
            "$set": {
                "status": JobStatus.FAILED,
                "error_message": f"Job timed out (no progress for >{timeout_minutes} minutes). Please try again.",
                "completed_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        }
    )

    # Also mark associated summaries as failed
    await db.summaries.update_many(
        {"job_id": {"$in": [ObjectId(job_id) for job_id in stuck_job_ids]}},
        {
            "$set": {
                "status": "failed",
                "error_message": "Processing timeout - task did not complete within expected timeframe",
                "completed_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        }
    )

    logger.info(f"Marked {result.modified_count} stuck jobs as FAILED")

    return result.modified_count
