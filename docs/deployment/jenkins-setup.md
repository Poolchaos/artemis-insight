# Jenkins Setup Instructions

## Required Credentials

### 1. GitHub & Container Registry (Already Exist)

- `github-repo-access` - GitHub repository access token
- `GHCR_USERNAME` - GitHub Container Registry username
- `GHCR_TOKEN` - GitHub Container Registry personal access token

### 2. Artemis Insight Credentials (To Be Created)

Navigate to Jenkins → Manage Jenkins → Manage Credentials → (global) → Add Credentials

**MongoDB Credentials:**
- **ID**: `ARTEMIS_INSIGHT_MONGO_USERNAME`
- **Kind**: Secret text
- **Secret**: `admin` (or your chosen username)
- **Description**: Artemis Insight MongoDB Admin Username

- **ID**: `ARTEMIS_INSIGHT_MONGO_PASSWORD`
- **Kind**: Secret text
- **Secret**: [Generate strong password]
- **Description**: Artemis Insight MongoDB Admin Password

- **ID**: `ARTEMIS_INSIGHT_MONGO_DATABASE`
- **Kind**: Secret text
- **Secret**: `artemis_insight`
- **Description**: Artemis Insight MongoDB Database Name

**MinIO Credentials:**
- **ID**: `ARTEMIS_INSIGHT_MINIO_USER`
- **Kind**: Secret text
- **Secret**: [Generate access key, min 3 chars]
- **Description**: Artemis Insight MinIO Access Key

- **ID**: `ARTEMIS_INSIGHT_MINIO_PASSWORD`
- **Kind**: Secret text
- **Secret**: [Generate secret key, min 8 chars]
- **Description**: Artemis Insight MinIO Secret Key

- **ID**: `ARTEMIS_INSIGHT_MINIO_BUCKET`
- **Kind**: Secret text
- **Secret**: `artemis-insight`
- **Description**: Artemis Insight MinIO Bucket Name

**Application Credentials:**
- **ID**: `ARTEMIS_INSIGHT_JWT_SECRET`
- **Kind**: Secret text
- **Secret**: [Generate strong random string, min 32 chars]
- **Description**: Artemis Insight JWT Secret Key

- **ID**: `ARTEMIS_INSIGHT_OPENAI_KEY`
- **Kind**: Secret text
- **Secret**: [Your OpenAI API key]
- **Description**: Artemis Insight OpenAI API Key

- **ID**: `ARTEMIS_INSIGHT_OPENAI_MODEL`
- **Kind**: Secret text
- **Secret**: `gpt-4` (or `gpt-4-turbo`, `gpt-3.5-turbo`)
- **Description**: Artemis Insight OpenAI Model Name

- **ID**: `ARTEMIS_INSIGHT_API_URL`
- **Kind**: Secret text
- **Secret**: `https://api.insights.artemisinnovations.co.za`
- **Description**: Artemis Insight API URL for Frontend

## Generate Strong Passwords

Use these commands to generate secure credentials:

```bash
# MongoDB password (24 chars)
openssl rand -base64 24

# MinIO access key (20 chars)
openssl rand -hex 10

# MinIO secret key (40 chars)
openssl rand -base64 40

# JWT secret (64 chars)
openssl rand -base64 64 | tr -d '\n'
```

## Create Jenkins Jobs

### Job 1: Artemis Insight API

1. Navigate to Jenkins Dashboard
2. Click "New Item"
3. Enter name: `Artemis Insight API`
4. Select "Pipeline"
5. Click "OK"

**Configuration:**

- **Description**: `Artemis Insight Backend API - Production Deployment`
- **General**:
  - ☑ Discard old builds
  - Max # of builds to keep: `10`

- **Build Triggers**:
  - ☑ GitHub hook trigger for GITScm polling (optional)

- **Pipeline**:
  - **Definition**: Pipeline script from SCM
  - **SCM**: Git
    - **Repository URL**: `https://github.com/Poolchaos/artemis-insight.git`
    - **Credentials**: Select `github-repo-access`
    - **Branch**: `*/main`
  - **Script Path**: `Jenkinsfile.api.prod`
  - ☑ Lightweight checkout

4. Click "Save"

### Job 2: Artemis Insight Frontend

1. Navigate to Jenkins Dashboard
2. Click "New Item"
3. Enter name: `Artemis Insight Frontend`
4. Select "Pipeline"
5. Click "OK"

**Configuration:**

- **Description**: `Artemis Insight Frontend Web App - Production Deployment`
- **General**:
  - ☑ Discard old builds
  - Max # of builds to keep: `10`

- **Build Triggers**:
  - ☑ GitHub hook trigger for GITScm polling (optional)

- **Pipeline**:
  - **Definition**: Pipeline script from SCM
  - **SCM**: Git
    - **Repository URL**: `https://github.com/Poolchaos/artemis-insight.git`
    - **Credentials**: Select `github-repo-access`
    - **Branch**: `*/main`
  - **Script Path**: `Jenkinsfile.web.prod`
  - ☑ Lightweight checkout

4. Click "Save"

## Test Jenkins Jobs

### Test API Pipeline

1. Go to "Artemis Insight API" job
2. Click "Build Now"
3. Monitor console output
4. Verify each stage completes successfully
5. Approve deployment when prompted
6. Verify containers running: `docker ps --filter name=artemis-insight`

### Test Frontend Pipeline

1. Go to "Artemis Insight Frontend" job
2. Click "Build Now"
3. Monitor console output
4. Verify each stage completes successfully
5. Approve deployment when prompted
6. Verify container running: `docker ps --filter name=artemis-insight-frontend`

## GitHub Webhook Setup (Optional)

For automatic builds on push to main:

1. Go to GitHub repository settings
2. Navigate to "Webhooks"
3. Click "Add webhook"
4. **Payload URL**: `https://jenkins.artemisinnovations.co.za/github-webhook/`
5. **Content type**: `application/json`
6. **Secret**: [Leave empty or use Jenkins webhook secret]
7. **Events**: Select "Just the push event"
8. ☑ Active
9. Click "Add webhook"

Test webhook:
- Push a commit to main branch
- Jenkins should automatically trigger build
- Check "Recent Deliveries" in GitHub webhook settings

## Credential Security Best Practices

1. **Never commit credentials** to git repository
2. **Rotate credentials regularly** (quarterly recommended)
3. **Use strong passwords** (min 32 chars for secrets)
4. **Limit credential access** in Jenkins to specific jobs
5. **Audit credential usage** regularly in Jenkins logs
6. **Backup credentials** securely (encrypted password manager)

## Troubleshooting

### Credential Not Found Error

```
groovy.lang.MissingPropertyException: No such property: ARTEMIS_INSIGHT_MONGO_USERNAME
```

**Solution**: Ensure credential ID exactly matches in both Jenkins and Jenkinsfile

### Permission Denied on Server

```
Permission denied (publickey)
```

**Solution**:
1. Verify Jenkins can SSH to server: `ssh tmsanity_admin@165.73.87.59 "echo test"`
2. Check Jenkins SSH key is added to server: `~/.ssh/authorized_keys`
3. Add SSH key to Jenkins credentials if needed

### Docker Login Failed

```
Error response from daemon: Get "https://ghcr.io/v2/": unauthorized
```

**Solution**:
1. Verify GHCR_TOKEN has `write:packages` permission
2. Regenerate GitHub personal access token if expired
3. Update GHCR_TOKEN credential in Jenkins

### Build Fails: Out of Memory

```
ERROR: error building image: context canceled
```

**Solution**:
1. Run manual cleanup: `docker system prune -f`
2. Check available memory: `free -h`
3. If <400MB available, wait for memory to free up
4. Restart Jenkins build

### Container Fails to Start

```
Container failed to start
```

**Solution**:
1. Check logs: `docker logs artemis-insight-backend --tail 50`
2. Verify infrastructure running: `docker ps --filter name=artemis-insight`
3. Check environment variables match credential IDs
4. Verify MongoDB/Redis/MinIO healthy
