# Artemis Insight Deployment - Ready to Deploy

## Investigation Complete

Comprehensive infrastructure analysis completed. Server environment documented:
- **Memory**: 1.4GB available (constrained - requires memory-adaptive builds)
- **Disk**: 37GB available
- **Networks**: Serelo on `172.20.0.0/16`, TM-Sanity on separate networks
- **Port Allocations**: Documented and conflict-free

## Deployment Artifacts Created

### 1. Production Configuration
- ✅ `docker-compose.prod.yml` - Production container orchestration
- ✅ Port allocations: Frontend (3003), Backend (8002), MongoDB (27018), Redis (6381), MinIO (9002-9003)
- ✅ Dedicated network: `artemis-insight-net` (172.21.0.0/16)
- ✅ Resource limits defined to prevent memory exhaustion

### 2. Jenkins Pipelines
- ✅ `Jenkinsfile.api.prod` - Backend API deployment pipeline
  - Memory-adaptive build settings (600MB-1024MB based on available memory)
  - Infrastructure-first deployment (MongoDB, Redis, MinIO)
  - Credential injection from Jenkins
  - Celery worker deployment
  - Health checks and verification

- ✅ `Jenkinsfile.web.prod` - Frontend deployment pipeline
  - React build with API URL baked in
  - Nginx serving on port 3003
  - Memory-efficient build strategy
  - Health checks and verification

### 3. Nginx & SSL Configuration
- ✅ `docs/deployment/nginx-ssl-setup.md` - Complete Nginx configuration
  - Server blocks for `app.insights` and `api.insights`
  - SSL certificate generation with certbot
  - HTTP to HTTPS redirects
  - Reverse proxy configuration

### 4. Jenkins Setup Guide
- ✅ `docs/deployment/jenkins-setup.md` - Complete credential and job setup
  - 11 credentials required (MongoDB, MinIO, JWT, OpenAI, etc.)
  - Password generation commands
  - Job creation instructions
  - Troubleshooting guide

### 5. Deployment Runbook
- ✅ `docs/deployment/deployment-runbook.md` - Step-by-step deployment guide
  - 7 deployment phases
  - Verification commands at each step
  - Rollback procedures
  - Common issues and solutions
  - Monitoring commands

### 6. Architecture Documentation
- ✅ `docs/plans/infrastructure-analysis.md` - Current state analysis
- ✅ `docs/plans/deployment-architecture.md` - Deployment design

## Safety Mechanisms Implemented

### Infrastructure Protection
- **NEVER** removes MongoDB, Redis, or MinIO containers during app deployments
- Targeted container operations by name (not pattern matching)
- Separate Docker network prevents cross-contamination
- Port binding to localhost only (127.0.0.1)

### Memory Management
- Pre-build memory checks
- Adaptive resource limits based on available memory
- Aggressive cleanup between stages (containers, images, builder cache)
- Build locks to prevent concurrent builds

### Deployment Safety
- Manual approval gates before production deployment
- Health checks after each stage
- Rollback procedures documented
- No-downtime Nginx reload

## Deployment Sequence

Follow this order:

1. **DNS Configuration** (5-10 minutes)
   - Add A records for `app.insights` and `api.insights`
   - Wait for propagation

2. **Jenkins Setup** (10-15 minutes)
   - Create 11 Jenkins credentials
   - Create 2 Jenkins jobs (API, Frontend)

3. **Backend Deployment** (15-20 minutes)
   - Trigger Jenkins API pipeline
   - Automatically deploys infrastructure
   - Approve deployment
   - Verify containers running

4. **Frontend Deployment** (10-15 minutes)
   - Trigger Jenkins Frontend pipeline
   - Approve deployment
   - Verify container running

5. **Nginx & SSL** (15-20 minutes)
   - Add server blocks to Nginx config
   - Generate Let's Encrypt certificates
   - Verify HTTPS working

6. **Verification** (10 minutes)
   - Test all endpoints
   - Verify no impact on Serelo/TM-Sanity
   - Check resource usage

**Total Estimated Time**: 65-90 minutes

## Pre-Deployment Requirements

### DNS Records Needed
```
Type: A, Host: app.insights, Value: 165.73.87.59
Type: A, Host: api.insights, Value: 165.73.87.59
```

### Credentials to Generate
Use `openssl rand` commands in `docs/deployment/jenkins-setup.md`:
- MongoDB username/password
- MinIO access/secret keys
- JWT secret (64 chars)
- OpenAI API key (from OpenAI account)

### Jenkins Access
- URL: https://jenkins.artemisinnovations.co.za
- Need admin access to create credentials and jobs

### Server Access
- SSH: `ssh tmsanity_admin@165.73.87.59`
- Sudo access for Nginx configuration

## Quick Start Command Reference

```bash
# Check server resources
ssh tmsanity_admin@165.73.87.59 "free -h && df -h"

# Verify DNS
dig app.insights.artemisinnovations.co.za
dig api.insights.artemisinnovations.co.za

# Generate credentials
openssl rand -base64 24  # MongoDB password
openssl rand -hex 10     # MinIO access key
openssl rand -base64 40  # MinIO secret key
openssl rand -base64 64 | tr -d '\n'  # JWT secret

# Deploy via Jenkins
# → Jenkins → "Artemis Insight API" → Build Now → Approve
# → Jenkins → "Artemis Insight Frontend" → Build Now → Approve

# Configure Nginx & SSL
ssh tmsanity_admin@165.73.87.59
sudo nano /etc/nginx/sites-available/artemisinnovations  # Add server blocks
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d app.insights.artemisinnovations.co.za -d api.insights.artemisinnovations.co.za

# Verify deployment
curl https://api.insights.artemisinnovations.co.za/health
curl https://app.insights.artemisinnovations.co.za
```

## Success Criteria

Deployment complete when:
- ✅ All containers running (MongoDB, Redis, MinIO, Backend, Worker, Frontend)
- ✅ HTTPS accessible for both frontend and API
- ✅ Health checks passing
- ✅ No CORS errors
- ✅ No impact on Serelo or TM-Sanity
- ✅ Resource usage acceptable

## Next Steps

1. **Create DNS records** in your DNS provider
2. **Review** `docs/deployment/deployment-runbook.md` for detailed steps
3. **Generate credentials** using provided commands
4. **Set up Jenkins** credentials and jobs
5. **Execute deployment** following the runbook

All deployment artifacts are ready. The system is designed to deploy safely without affecting existing applications.

## Documentation Index

- **Infrastructure Analysis**: `docs/plans/infrastructure-analysis.md`
- **Deployment Architecture**: `docs/plans/deployment-architecture.md`
- **Deployment Runbook**: `docs/deployment/deployment-runbook.md`
- **Jenkins Setup**: `docs/deployment/jenkins-setup.md`
- **Nginx & SSL Setup**: `docs/deployment/nginx-ssl-setup.md`
- **Production Compose**: `docker-compose.prod.yml`
- **API Pipeline**: `Jenkinsfile.api.prod`
- **Frontend Pipeline**: `Jenkinsfile.web.prod`

---

**Status**: 🟢 READY FOR DEPLOYMENT

All investigation complete. All deployment artifacts created. All safety mechanisms in place. Ready to proceed when you are.
