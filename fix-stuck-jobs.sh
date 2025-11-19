#!/bin/bash
# Emergency script to stop stuck jobs from crashing the server

echo "=== Artemis Insight - Emergency Job Cleanup ==="
echo ""

# Stop the celery worker to prevent task restarts
echo "[1/5] Stopping Celery worker..."
docker stop artemis-insight-celery-worker

# Purge all pending Celery tasks
echo "[2/5] Purging Celery queue..."
docker exec artemis-insight-redis redis-cli FLUSHDB

# Get MongoDB connection details from env
MONGO_USER="${MONGO_ROOT_USERNAME:-admin}"
MONGO_PASS="${MONGO_ROOT_PASSWORD}"

# Fail all processing/pending jobs in MongoDB
echo "[3/5] Failing stuck jobs in database..."
docker exec artemis-insight-mongodb mongosh -u "$MONGO_USER" -p "$MONGO_PASS" \
  --authenticationDatabase admin artemis_insight --quiet --eval '
    var result = db.jobs.updateMany(
      { status: { $in: ["processing", "pending"] } },
      {
        $set: {
          status: "failed",
          error: "Job terminated - server recovery. Please retry.",
          updated_at: new Date()
        }
      }
    );
    print("Updated " + result.modifiedCount + " jobs");
  '

# Clear Redis task metadata
echo "[4/5] Clearing Redis task metadata..."
docker exec artemis-insight-redis redis-cli --scan --pattern "celery-task-meta-*" | \
  xargs -L 1 docker exec -i artemis-insight-redis redis-cli DEL

# Restart celery worker
echo "[5/5] Restarting Celery worker..."
docker start artemis-insight-celery-worker

echo ""
echo "=== Cleanup Complete ==="
echo "All stuck jobs have been failed and the queue has been cleared."
echo "Users can now retry their jobs with the improved PDF processing."
