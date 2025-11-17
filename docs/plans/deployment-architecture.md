# Artemis-Insight Production Deployment Architecture

## Deployment Strategy

**Pattern**: Follow Serelo's proven deployment model with Artemis-Insight adaptations.

**Key Principles:**
1. Infrastructure services deployed first (MongoDB, Redis, MinIO)
2. Separate Jenkins pipelines for API and Frontend
3. Manual approval gates before production deployment
4. Memory-adaptive build settings
5. Aggressive cleanup without touching infrastructure
6. Network isolation via dedicated Docker network

## Network Architecture

```
artemis-insight-net (172.22.0.0/16)
├── artemis-insight-mongodb:27017
├── artemis-insight-redis:6379
├── artemis-insight-minio:9000,9001
├── artemis-insight-backend:8000
├── artemis-insight-celery-worker
└── artemis-insight-frontend:80

Host Network Bindings:
├── 127.0.0.1:27018 → mongodb:27017
├── 127.0.0.1:6381 → redis:6379
├── 127.0.0.1:9002 → minio:9000
├── 127.0.0.1:9003 → minio:9001
├── 127.0.0.1:8002 → backend:8000
└── 127.0.0.1:3003 → frontend:80

Nginx Reverse Proxy:
├── https://api.insights.artemisinnovations.co.za → 127.0.0.1:8002
└── https://app.insights.artemisinnovations.co.za → 127.0.0.1:3003
```

## Container Configuration

### Infrastructure Services

**MongoDB:**
```yaml
container_name: artemis-insight-mongodb
image: mongo:7.0
ports: ['127.0.0.1:27018:27017']
network: artemis-insight-net
volumes: [artemis-insight-mongodb-data:/data/db]
restart: unless-stopped
```

**Redis:**
```yaml
container_name: artemis-insight-redis
image: redis:7-alpine
ports: ['127.0.0.1:6381:6379']
network: artemis-insight-net
volumes: [artemis-insight-redis-data:/data]
command: redis-server --appendonly yes
restart: unless-stopped
```

**MinIO:**
```yaml
container_name: artemis-insight-minio
image: minio/minio:latest
ports: ['127.0.0.1:9002:9000', '127.0.0.1:9003:9001']
network: artemis-insight-net
volumes: [artemis-insight-minio-data:/data]
command: server /data --console-address ":9001"
restart: unless-stopped
```

### Application Services

**Backend API:**
```yaml
container_name: artemis-insight-backend
image: ghcr.io/poolchaos/artemis-insight-backend:<commit-sha>
ports: ['127.0.0.1:8002:8000']
network: artemis-insight-net
restart: unless-stopped
environment: [All credentials from Jenkins]
depends_on: [mongodb, redis, minio]
```

**Celery Worker:**
```yaml
container_name: artemis-insight-celery-worker
image: ghcr.io/poolchaos/artemis-insight-backend:<commit-sha>
network: artemis-insight-net
restart: unless-stopped
command: celery -A app.celery_app worker --loglevel=info --concurrency=2
environment: [All credentials from Jenkins]
depends_on: [mongodb, redis, minio]
```

**Frontend:**
```yaml
container_name: artemis-insight-frontend
image: ghcr.io/poolchaos/artemis-insight-frontend:<commit-sha>
ports: ['127.0.0.1:3003:80']
network: artemis-insight-net
restart: unless-stopped
depends_on: [backend]
```

## Jenkins Pipeline Structure

### Pipeline: Artemis Insight API

**Stages:**
1. **Initial Memory Check** - Verify available memory, basic cleanup
2. **Workspace Setup** - Shallow clone, verify structure
3. **Docker Build** - Memory-adaptive build with cache
4. **Push to Registry** - GHCR with latest tag
5. **Approve Deploy** - Manual approval gate
6. **Deploy Infrastructure** - MongoDB, Redis, MinIO (if not exists)
7. **Deploy to Production** - Backend API container
8. **Deploy Celery Worker** - Background task processor
9. **Post-Deploy Verification** - Health checks, logs

**Credentials Required:**
- `github-repo-access` - Repository access
- `GHCR_USERNAME` - GitHub Container Registry username
- `GHCR_TOKEN` - GitHub Container Registry token
- `ARTEMIS_INSIGHT_MONGO_USERNAME`
- `ARTEMIS_INSIGHT_MONGO_PASSWORD`
- `ARTEMIS_INSIGHT_MONGO_DATABASE`
- `ARTEMIS_INSIGHT_MINIO_USER`
- `ARTEMIS_INSIGHT_MINIO_PASSWORD`
- `ARTEMIS_INSIGHT_MINIO_BUCKET`
- `ARTEMIS_INSIGHT_JWT_SECRET`
- `ARTEMIS_INSIGHT_OPENAI_KEY`

### Pipeline: Artemis Insight Frontend

**Stages:**
1. **Safe Memory Management** - Memory check and cleanup
2. **Workspace Setup** - Clone repository
3. **Docker Build** - Build with API URL build arg
4. **Push to Registry** - GHCR with latest tag
5. **Approve Deploy** - Manual approval gate
6. **Deploy to Production** - Frontend container
7. **Post-Deploy Verification** - Health checks

**Credentials Required:**
- `github-repo-access`
- `GHCR_USERNAME`
- `GHCR_TOKEN`
- `ARTEMIS_INSIGHT_API_URL` (https://api.insights.artemisinnovations.co.za)

## Deployment Sequence

### Initial Infrastructure Setup (One-time)

```bash
# 1. Create Docker network
docker network create artemis-insight-net --subnet 172.22.0.0/16

# 2. Create volumes
docker volume create artemis-insight-mongodb-data
docker volume create artemis-insight-redis-data
docker volume create artemis-insight-minio-data

# 3. Deploy MongoDB
docker run -d --name artemis-insight-mongodb \
  --restart unless-stopped \
  --network artemis-insight-net \
  -p 127.0.0.1:27018:27017 \
  -e MONGO_INITDB_ROOT_USERNAME=<username> \
  -e MONGO_INITDB_ROOT_PASSWORD=<password> \
  -e MONGO_INITDB_DATABASE=<database> \
  -v artemis-insight-mongodb-data:/data/db \
  mongo:7.0

# 4. Deploy Redis
docker run -d --name artemis-insight-redis \
  --restart unless-stopped \
  --network artemis-insight-net \
  -p 127.0.0.1:6381:6379 \
  -v artemis-insight-redis-data:/data \
  redis:7-alpine redis-server --appendonly yes

# 5. Deploy MinIO
docker run -d --name artemis-insight-minio \
  --restart unless-stopped \
  --network artemis-insight-net \
  -p 127.0.0.1:9002:9000 \
  -p 127.0.0.1:9003:9001 \
  -e MINIO_ROOT_USER=<user> \
  -e MINIO_ROOT_PASSWORD=<password> \
  -v artemis-insight-minio-data:/data \
  minio/minio:latest server /data --console-address ":9001"
```

### Application Deployment (Via Jenkins)

1. **Backend deployment** triggered by push to `main` branch
   - Builds Docker image
   - Pushes to GHCR
   - Waits for manual approval
   - Deploys infrastructure (if needed)
   - Deploys backend + celery worker

2. **Frontend deployment** triggered separately or manually
   - Builds Docker image with API URL
   - Pushes to GHCR
   - Waits for manual approval
   - Deploys frontend

3. **Nginx configuration** (manual step, one-time)
   - Add routes to `/etc/nginx/sites-available/artemisinnovations`
   - Generate SSL certificates with certbot
   - Reload Nginx

## Safety Mechanisms

### Container Isolation
- Dedicated network prevents cross-contamination
- No shared volumes with other applications
- Explicit container names prevent pattern matching errors

### Memory Management
```bash
# Memory-adaptive limits
if [ "$AVAILABLE_MB" -gt "1200" ]; then
    MEMORY_LIMIT="1024m"
    SWAP_LIMIT="1536m"
elif [ "$AVAILABLE_MB" -gt "800" ]; then
    MEMORY_LIMIT="800m"
    SWAP_LIMIT="1200m"
else
    MEMORY_LIMIT="600m"
    SWAP_LIMIT="800m"
fi
```

### Infrastructure Protection
```bash
# ONLY stop/remove Artemis Insight containers
docker stop artemis-insight-backend 2>/dev/null || true
docker rm artemis-insight-backend 2>/dev/null || true

# NEVER do this in application deployments:
# docker stop artemis-insight-mongodb  ❌
# docker stop artemis-insight-redis    ❌
# docker stop artemis-insight-minio    ❌
```

### Cleanup Strategy
```bash
# Safe cleanup - only removes dangling resources
docker container prune -f  # Removes stopped containers
docker image prune -f      # Removes dangling images

# NEVER use in production deployments:
# docker system prune -a -f  ❌ (removes all unused images)
# docker volume prune -f     ❌ (removes unused volumes)
```

## Rollback Procedure

### If Deployment Fails

1. **Backend failure:**
```bash
# Re-tag previous working image as latest
docker tag ghcr.io/poolchaos/artemis-insight-backend:<previous-sha> \
  ghcr.io/poolchaos/artemis-insight-backend:latest

# Redeploy
docker stop artemis-insight-backend
docker rm artemis-insight-backend
docker run -d --name artemis-insight-backend [same args as deployment]
```

2. **Frontend failure:**
```bash
# Same process but for frontend container
docker tag ghcr.io/poolchaos/artemis-insight-frontend:<previous-sha> \
  ghcr.io/poolchaos/artemis-insight-frontend:latest
# Redeploy frontend container
```

3. **Infrastructure failure:**
   - MongoDB/Redis/MinIO should NEVER be touched during app deployments
   - If infrastructure fails, requires separate investigation
   - Data persistence via named volumes ensures no data loss

## Monitoring & Health Checks

### Container Health
```bash
# Check all Artemis Insight containers
docker ps --filter name=artemis-insight

# Check logs
docker logs --tail 50 artemis-insight-backend
docker logs --tail 50 artemis-insight-frontend
docker logs --tail 50 artemis-insight-celery-worker
```

### Application Health
```bash
# Backend health check
curl -f http://localhost:8002/health

# Frontend health check
curl -f http://localhost:3003/

# Redis health check
docker exec artemis-insight-redis redis-cli ping

# MongoDB health check
docker exec artemis-insight-mongodb mongosh --eval "db.adminCommand('ping')"
```

### Nginx Status
```bash
# Check Nginx configuration
sudo nginx -t

# Reload Nginx (safe, no downtime)
sudo systemctl reload nginx

# View access logs
sudo tail -f /var/log/nginx/access.log | grep insights
```

## Credential Management

### Jenkins Credential IDs

**GitHub & Registry:**
- `github-repo-access` (existing)
- `GHCR_USERNAME` (existing)
- `GHCR_TOKEN` (existing)

**Artemis Insight Specific (to be created):**
- `ARTEMIS_INSIGHT_MONGO_USERNAME` - MongoDB admin username
- `ARTEMIS_INSIGHT_MONGO_PASSWORD` - MongoDB admin password
- `ARTEMIS_INSIGHT_MONGO_DATABASE` - Database name (e.g., artemis_insight)
- `ARTEMIS_INSIGHT_MINIO_USER` - MinIO access key
- `ARTEMIS_INSIGHT_MINIO_PASSWORD` - MinIO secret key
- `ARTEMIS_INSIGHT_MINIO_BUCKET` - Bucket name (e.g., artemis-insight)
- `ARTEMIS_INSIGHT_JWT_SECRET` - JWT signing secret
- `ARTEMIS_INSIGHT_OPENAI_KEY` - OpenAI API key
- `ARTEMIS_INSIGHT_OPENAI_MODEL` - Model name (e.g., gpt-4)
- `ARTEMIS_INSIGHT_API_URL` - API URL for frontend builds

### Environment Variable Mapping

**Backend/Worker:**
```bash
MONGO_URI=mongodb://${MONGO_USERNAME}:${MONGO_PASSWORD}@artemis-insight-mongodb:27017/${MONGO_DATABASE}?authSource=admin
MINIO_ENDPOINT=artemis-insight-minio:9000
MINIO_ACCESS_KEY=${MINIO_USER}
MINIO_SECRET_KEY=${MINIO_PASSWORD}
MINIO_BUCKET=${MINIO_BUCKET}
REDIS_URL=redis://artemis-insight-redis:6379/0
CELERY_BROKER_URL=redis://artemis-insight-redis:6379/0
JWT_SECRET_KEY=${JWT_SECRET}
OPENAI_API_KEY=${OPENAI_KEY}
OPENAI_MODEL=${OPENAI_MODEL}
```

**Frontend:**
```dockerfile
ARG VITE_API_URL=https://api.insights.artemisinnovations.co.za
```

## Post-Deployment Verification Checklist

- [ ] All containers running: `docker ps --filter name=artemis-insight`
- [ ] No container restarts: Check Status column for continuous uptime
- [ ] Backend health: `curl http://localhost:8002/health` returns 200
- [ ] Frontend accessible: `curl http://localhost:3003` returns 200
- [ ] SSL certificates valid: `curl https://api.insights.artemisinnovations.co.za/health`
- [ ] Frontend loads: `curl https://app.insights.artemisinnovations.co.za`
- [ ] Celery worker connected: Check logs for "ready" message
- [ ] MongoDB accessible: Health check passes
- [ ] Redis accessible: Health check passes
- [ ] MinIO accessible: Check logs
- [ ] No impact on Serelo: Check Serelo containers still running
- [ ] No impact on TM-Sanity: Check TM-Sanity containers still running
- [ ] Nginx reload successful: `sudo nginx -t && sudo systemctl reload nginx`
- [ ] Disk space sufficient: `df -h | grep mapper`
- [ ] Memory usage acceptable: `free -h`
