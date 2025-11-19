#!/usr/bin/env python3
"""Check for stuck jobs in production"""

from pymongo import MongoClient
from app.config import settings
from datetime import datetime, timedelta

client = MongoClient(settings.mongo_uri)
db = client.get_default_database()

# Find stuck jobs
stuck_jobs = list(db.jobs.find({
    'status': {'$in': ['pending', 'running']}
}).sort('created_at', -1).limit(10))

print(f"\n=== Found {len(stuck_jobs)} stuck jobs ===\n")

for job in stuck_jobs:
    updated_ago = datetime.utcnow() - job.get('updated_at', job['created_at'])
    print(f"Job ID: {job['_id']}")
    print(f"  Status: {job['status']}")
    print(f"  Progress: {job.get('progress', 0)}%")
    print(f"  Document: {job.get('document_id')}")
    print(f"  Template: {job.get('template_id')}")
    print(f"  Last updated: {updated_ago.total_seconds() / 60:.1f} minutes ago")
    print(f"  Created: {job['created_at']}")
    print()

client.close()
