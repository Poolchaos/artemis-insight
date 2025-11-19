#!/usr/bin/env python3
"""Fix the stuck job in production"""

from pymongo import MongoClient
from app.config import settings
from datetime import datetime
from bson import ObjectId

client = MongoClient(settings.mongo_uri)
db = client.get_default_database()

stuck_job_id = ObjectId("691b60799659247ee5c71b78")

# Update job to FAILED
result = db.jobs.update_one(
    {"_id": stuck_job_id},
    {
        "$set": {
            "status": "failed",
            "error_message": "Job timed out after 38+ hours. System has been updated with better timeout handling. Please retry.",
            "completed_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    }
)

print(f"Updated job: {result.modified_count} document(s)")

# Update associated summary if exists
summary_result = db.summaries.update_one(
    {"job_id": stuck_job_id},
    {
        "$set": {
            "status": "failed",
            "error_message": "Processing timeout - system has been updated with better error handling",
            "completed_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    }
)

print(f"Updated summary: {summary_result.modified_count} document(s)")

client.close()
print("\nStuck job has been marked as failed. User can now retry.")
