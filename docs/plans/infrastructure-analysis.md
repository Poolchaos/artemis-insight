# Server Infrastructure Analysis

## Current Server State

**Server**: `tmsanity_admin@165.73.87.59`

### Resource Availability

- **Memory**: 3.8GB total, 2.1GB used, 1.4GB available
- **Swap**: 2GB total, 1.1GB used
- **Disk**: 90GB total, 50GB used, 37GB available (58% used)
- **Warning**: Limited available memory - must use memory-efficient deployment strategies

### Docker Networks

| Network Name | Network ID | Subnet | Purpose |
|--------------|------------|--------|---------|
| `serelo-net` | `9c77624d31fc` | `172.20.0.0/16` | Serelo application isolation |
| `tm-sanity-prod-network` | `9a6f060c7b88` | Unknown | TM-Sanity application |
| `app_tm-prod-network` | `4dbf2897de87` | Unknown | Legacy app network |

**Decision**: Create new `artemis-insight-net` network with subnet `172.22.0.0/16` to avoid conflicts (172.21.0.0/16 is used by tm-sanity-prod-network).

### Running Containers

#### Serelo Stack (Reference Pattern)
- `serelo-api` - API server (port 127.0.0.1:8000)
- `serelo-web-prod` - Frontend (port 127.0.0.1:3001, unhealthy status noted)
- `serelo-celery-worker` - Background task processor
- `serelo-celery-beat` - Scheduled task executor
- `serelo-mongo` - MongoDB 7.0 (shared with TM-Sanity)
- `serelo-redis` - Redis 7-alpine
- `serelo-minio` - MinIO object storage (ports 127.0.0.1:9000-9001)

#### TM-Sanity Stack
- `tm-sanity-api` - API server (port 127.0.0.1:3000)
- `web-prod` - Frontend (port 0.0.0.0:8080)
- `support-prod` - Support app (port 127.0.0.1:3002)
- `mongodb-prod` - MongoDB 7.0 (shared with Serelo)

#### Infrastructure
- `jenkins-controller` - CI/CD (ports 0.0.0.0:8081, 0.0.0.0:50000)

### Volume Management

**Named Volumes:**
- `serelo-mongo-data` - Serelo MongoDB data
- `serelo-redis-data` - Serelo Redis persistence
- `serelo-minio-data` - Serelo object storage
- `app_mongo_prod_data` - Shared MongoDB data
- `jenkins_home` - Jenkins configuration and jobs
- `redis-data` - Shared Redis data (if applicable)

**Critical**: Infrastructure volumes must NEVER be removed during application deployments.

### Nginx Configuration

**Location**: `/etc/nginx/sites-available/artemisinnovations` (symlinked from sites-enabled)

**Existing Routes:**
- `support.artemisinnovations.co.za` → 127.0.0.1:3002 (HTTPS, Let's Encrypt)
- `app.tm-sanity.artemisinnovations.co.za` → 127.0.0.1:8080 (HTTPS, basic auth)
- `api.tm-sanity.artemisinnovations.co.za` → 127.0.0.1:3000 (HTTPS)
- `app.serelo.artemisinnovations.co.za` → 127.0.0.1:3001 (HTTPS, basic auth)
- `api.serelo.artemisinnovations.co.za` → 127.0.0.1:8000 (HTTPS)
- `jenkins.artemisinnovations.co.za` → 127.0.0.1:8081 (HTTPS)

**SSL Certificates** (Let's Encrypt):
- `support.artemisinnovations.co.za`
- `app.tm-sanity.artemisinnovations.co.za` (wildcard cert used for API too)
- `jenkins.artemisinnovations.co.za`

**Port Allocation Plan:**
- Frontend: 127.0.0.1:3003 (next available)
- Backend: 127.0.0.1:8002 (next available)
- MongoDB: 127.0.0.1:27018 (avoid 27017 conflict)
- Redis: 127.0.0.1:6381 (avoid 6379 conflict)
- MinIO API: 127.0.0.1:9002
- MinIO Console: 127.0.0.1:9003

### Jenkins Configuration

**Container**: `jenkins-controller` (image: `tmsanity_admin-jenkins`)
**Access**: https://jenkins.artemisinnovations.co.za

**Existing Jobs:**
- Artemis Website
- Serelo API (uses `Jenkinsfile.api.prod` from main branch)
- Serelo Webapp (uses `Jenkinsfile.web.prod` from main branch)
- Support App
- TM-Sanity API
- TM-Sanity App

**Credentials in Jenkins** (referenced in Serelo pipelines):
- `github-repo-access` - GitHub repository access
- `GHCR_USERNAME` - GitHub Container Registry username
- `GHCR_TOKEN` - GitHub Container Registry PAT
- `SERELO_*` - Various Serelo environment credentials

### Serelo Deployment Pattern Analysis

**Build Strategy:**
1. Memory-aware resource limits (adaptive based on available memory)
2. Docker BuildKit with layer caching from `:latest` tag
3. Shallow git clone to minimize workspace size
4. Aggressive cleanup between stages

**Deployment Strategy:**
1. Infrastructure-first deployment (MongoDB, Redis, MinIO)
2. Separate pipelines for API and Web
3. Manual approval before production deployment
4. Stop and remove old container, start new with same name
5. Credential injection via environment variables
6. Health checks after deployment
7. Celery worker/beat deployed after API verification

**Critical Safety Measures:**
- Never removes infrastructure containers (MongoDB, Redis, MinIO)
- Uses targeted container operations (`docker stop <name>`)
- Memory checks before builds
- Build locks to prevent concurrent builds
- Cleanup only application containers, not infrastructure

## Artemis-Insight Requirements

### New Resources Needed

**Docker Network:**
- Name: `artemis-insight-net`
- Subnet: `172.22.0.0/16`
- Driver: bridge

**Containers:**
- `artemis-insight-backend` (FastAPI)
- `artemis-insight-frontend` (React/Nginx)
- `artemis-insight-celery-worker`
- `artemis-insight-mongodb`
- `artemis-insight-redis`
- `artemis-insight-minio`

**Nginx Routes:**
- `app.insights.artemisinnovations.co.za` → 127.0.0.1:3003
- `api.insights.artemisinnovations.co.za` → 127.0.0.1:8002

**SSL Certificates:**
- New Let's Encrypt certificates for both domains

**Jenkins Jobs:**
- Artemis Insight API
- Artemis Insight Web
- (Optional) Artemis Insight Celery Worker (or deployed with API)

### Environment Credentials Required

From `.env.example` analysis:
- `MONGO_ROOT_USERNAME`
- `MONGO_ROOT_PASSWORD`
- `MONGO_DATABASE`
- `MINIO_ROOT_USER`
- `MINIO_ROOT_PASSWORD`
- `MINIO_BUCKET`
- `JWT_SECRET_KEY`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENAI_EMBEDDING_MODEL`
- `MONTHLY_BUDGET_ZAR`

## Deployment Risk Assessment

### High Risk Areas
1. **Memory constraints** - Only 1.4GB available, builds can consume 800MB-1GB
2. **Port conflicts** - Must carefully allocate unused ports
3. **Network isolation** - Must ensure no cross-contamination with Serelo/TM-Sanity
4. **MongoDB conflicts** - Port 27017 already in use

### Mitigation Strategies
1. Use memory-adaptive build settings (follow Serelo pattern)
2. Explicit port mapping with 127.0.0.1 binding
3. Dedicated Docker network for complete isolation
4. Separate MongoDB instance on different port
5. Aggressive cleanup between build stages
6. Sequential (not parallel) Jenkins builds

### Zero-Risk Guarantees
1. No infrastructure container operations (MongoDB, Redis preservation)
2. Targeted container operations only (by name, not pattern matching)
3. Network isolation prevents cross-app communication issues
4. Port binding to localhost prevents external exposure
5. Separate volumes prevent data collision

## Next Steps

1. Design Artemis-Insight deployment architecture
2. Create production docker-compose.yml
3. Create Jenkinsfiles (API, Web, Worker)
4. Configure Nginx routes
5. Set up Jenkins jobs with credentials
6. Test deployment in isolation
7. Verify no impact on existing applications
