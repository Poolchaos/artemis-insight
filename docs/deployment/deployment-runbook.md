# Artemis Insight Production Deployment Runbook

## Pre-Deployment Checklist

- [ ] DNS records created for `app.insights.artemisinnovations.co.za` and `api.insights.artemisinnovations.co.za`
- [ ] GitHub repository `artemis-insight` pushed to `main` branch
- [ ] Jenkins credentials created (see `jenkins-setup.md`)
- [ ] Server has sufficient resources (check `free -h` and `df -h`)
- [ ] All other applications (Serelo, TM-Sanity) are running and healthy

## Deployment Sequence

### Phase 1: DNS Configuration (5-10 minutes)

1. **Add DNS A Records** to your DNS provider:
   ```
   Type: A, Host: app.insights, Value: 165.73.87.59, TTL: 3600
   Type: A, Host: api.insights, Value: 165.73.87.59, TTL: 3600
   ```

2. **Verify DNS propagation**:
   ```bash
   dig app.insights.artemisinnovations.co.za
   dig api.insights.artemisinnovations.co.za
   ```

   Both should resolve to `165.73.87.59`. Wait if not propagated yet.

### Phase 2: Jenkins Setup (10-15 minutes)

Follow instructions in `docs/deployment/jenkins-setup.md`:

1. **Create all Jenkins credentials** (MongoDB, MinIO, JWT, OpenAI)
2. **Create Jenkins job**: "Artemis Insight API"
3. **Create Jenkins job**: "Artemis Insight Frontend"
4. **Test credential access**: Run a dry-run build to verify credentials load

### Phase 3: Initial Infrastructure Deployment (15-20 minutes)

**Note**: First API deployment will automatically deploy infrastructure.

1. **Trigger API Pipeline**:
   - Go to Jenkins → "Artemis Insight API"
   - Click "Build Now"
   - Monitor console output

2. **Monitor Build Stages**:
   - ✅ Initial Memory Check
   - ✅ Workspace Setup
   - ✅ Docker Build (this will take 5-10 minutes)
   - ✅ Push to Registry
   - ⏸️ Approve Deploy (WAIT HERE)

3. **Verify Build Before Approval**:
   ```bash
   ssh tmsanity_admin@165.73.87.59 "docker images | grep artemis-insight-backend"
   ```
   Should show newly built image with commit SHA tag.

4. **Approve Deployment**:
   - Click "Deploy Now" in Jenkins
   - Monitor infrastructure deployment logs

5. **Verify Infrastructure Running**:
   ```bash
   ssh tmsanity_admin@165.73.87.59 "docker ps --filter name=artemis-insight"
   ```

   Expected containers:
   - `artemis-insight-mongodb`
   - `artemis-insight-redis`
   - `artemis-insight-minio`
   - `artemis-insight-backend`
   - `artemis-insight-celery-worker`

6. **Check Container Health**:
   ```bash
   # MongoDB
   ssh tmsanity_admin@165.73.87.59 "docker exec artemis-insight-mongodb mongosh --eval \"db.adminCommand('ping')\""

   # Redis
   ssh tmsanity_admin@165.73.87.59 "docker exec artemis-insight-redis redis-cli ping"

   # Backend API
   ssh tmsanity_admin@165.73.87.59 "curl -f http://localhost:8002/health"
   ```

   All should respond successfully.

### Phase 4: Frontend Deployment (10-15 minutes)

1. **Trigger Frontend Pipeline**:
   - Go to Jenkins → "Artemis Insight Frontend"
   - Click "Build Now"
   - Monitor console output

2. **Monitor Build Stages**:
   - ✅ Safe Memory Management
   - ✅ Workspace Setup
   - ✅ Docker Build (5-10 minutes for React build)
   - ✅ Push to Registry
   - ⏸️ Approve Deploy (WAIT HERE)

3. **Verify Build**:
   ```bash
   ssh tmsanity_admin@165.73.87.59 "docker images | grep artemis-insight-frontend"
   ```

4. **Approve Deployment**:
   - Click "Deploy Now" in Jenkins
   - Monitor deployment logs

5. **Verify Frontend Running**:
   ```bash
   ssh tmsanity_admin@165.73.87.59 "docker ps --filter name=artemis-insight-frontend"
   ssh tmsanity_admin@165.73.87.59 "curl -f http://localhost:3003/"
   ```

### Phase 5: Nginx Configuration & SSL (15-20 minutes)

1. **SSH into Server**:
   ```bash
   ssh tmsanity_admin@165.73.87.59
   ```

2. **Backup Current Nginx Config**:
   ```bash
   sudo cp /etc/nginx/sites-available/artemisinnovations /etc/nginx/sites-available/artemisinnovations.backup.$(date +%Y%m%d)
   ```

3. **Edit Nginx Config**:
   ```bash
   sudo nano /etc/nginx/sites-available/artemisinnovations
   ```

   Add the server blocks from `docs/deployment/nginx-ssl-setup.md`.

   **Important**: Add at the end of the file, before the closing brace.

4. **Test Nginx Configuration**:
   ```bash
   sudo nginx -t
   ```

   Expected: `nginx: configuration file /etc/nginx/nginx.conf test is successful`

   **If errors**: Review syntax, check for typos, verify brackets match.

5. **Reload Nginx** (safe, no downtime):
   ```bash
   sudo systemctl reload nginx
   ```

6. **Generate SSL Certificates**:
   ```bash
   sudo certbot --nginx -d app.insights.artemisinnovations.co.za -d api.insights.artemisinnovations.co.za
   ```

   Follow prompts:
   - Enter email for urgent renewal notices
   - Agree to terms of service
   - Select "No" for EFF mailing list (optional)
   - Certbot will automatically configure HTTPS

7. **Verify SSL Certificates**:
   ```bash
   sudo certbot certificates
   ```

   Should show certificate for `app.insights.artemisinnovations.co.za` with both domains.

8. **Test Nginx Again**:
   ```bash
   sudo nginx -t && sudo systemctl reload nginx
   ```

### Phase 6: Verification & Testing (10 minutes)

1. **Verify HTTP to HTTPS Redirect**:
   ```bash
   curl -I http://app.insights.artemisinnovations.co.za
   ```
   Expected: `301 Moved Permanently` with `Location: https://...`

2. **Verify HTTPS Works**:
   ```bash
   curl -I https://app.insights.artemisinnovations.co.za
   ```
   Expected: `200 OK`

3. **Verify API Health Endpoint**:
   ```bash
   curl https://api.insights.artemisinnovations.co.za/health
   ```
   Expected: `{"status":"healthy"}` or similar

4. **Test Frontend in Browser**:
   - Navigate to: `https://app.insights.artemisinnovations.co.za`
   - Should load React application
   - Check browser console for errors
   - Verify SSL certificate is valid (green padlock)

5. **Test API Connection from Frontend**:
   - Try to login or access API-dependent features
   - Verify no CORS errors in browser console

6. **Verify No Impact on Other Applications**:
   ```bash
   # Check all containers still running
   ssh tmsanity_admin@165.73.87.59 "docker ps"

   # Test Serelo
   curl -I https://app.serelo.artemisinnovations.co.za
   curl https://api.serelo.artemisinnovations.co.za/health

   # Test TM-Sanity
   curl -I https://app.tm-sanity.artemisinnovations.co.za
   curl https://api.tm-sanity.artemisinnovations.co.za/health
   ```

   All should respond successfully.

7. **Check Resource Usage**:
   ```bash
   ssh tmsanity_admin@165.73.87.59 "free -h && df -h | grep mapper"
   ```

   Verify:
   - Memory usage acceptable (<90%)
   - Disk space sufficient (>10% free)

### Phase 7: Post-Deployment Tasks (5 minutes)

1. **Create Initial Admin User** (if applicable):
   ```bash
   ssh tmsanity_admin@165.73.87.59 "docker exec artemis-insight-backend python -m app.scripts.create_admin"
   ```
   Or use registration endpoint if that's the flow.

2. **Seed Initial Templates** (if needed):
   ```bash
   ssh tmsanity_admin@165.73.87.59 "docker exec artemis-insight-backend python seed_templates.py"
   ```

3. **Document Deployment**:
   - Record deployment timestamp
   - Record commit SHA deployed
   - Record any issues encountered
   - Update internal documentation

## Rollback Procedure (If Issues)

### Backend Rollback

1. **Identify Previous Working Image**:
   ```bash
   ssh tmsanity_admin@165.73.87.59 "docker images | grep artemis-insight-backend"
   ```

2. **Redeploy Previous Image**:
   ```bash
   ssh tmsanity_admin@165.73.87.59 "
   docker stop artemis-insight-backend artemis-insight-celery-worker
   docker rm artemis-insight-backend artemis-insight-celery-worker
   docker run -d --name artemis-insight-backend [same args as Jenkinsfile] ghcr.io/poolchaos/artemis-insight-backend:<previous-sha>
   docker run -d --name artemis-insight-celery-worker [same args as Jenkinsfile] ghcr.io/poolchaos/artemis-insight-backend:<previous-sha> celery -A app.celery_app worker --loglevel=info --concurrency=2
   "
   ```

### Frontend Rollback

```bash
ssh tmsanity_admin@165.73.87.59 "
docker stop artemis-insight-frontend
docker rm artemis-insight-frontend
docker run -d --name artemis-insight-frontend -p 127.0.0.1:3003:80 --restart unless-stopped --network artemis-insight-net ghcr.io/poolchaos/artemis-insight-frontend:<previous-sha>
"
```

### Infrastructure Rollback (Only if Necessary)

**Warning**: Only do this if infrastructure is corrupted. This will destroy data!

```bash
ssh tmsanity_admin@165.73.87.59 "
docker stop artemis-insight-mongodb artemis-insight-redis artemis-insight-minio
docker rm artemis-insight-mongodb artemis-insight-redis artemis-insight-minio
docker volume rm artemis-insight-mongodb-data artemis-insight-redis-data artemis-insight-minio-data
"
```

Then redeploy infrastructure via Jenkins API pipeline.

## Common Issues & Solutions

### Issue: Certificate Generation Fails

**Symptom**: Certbot fails with "Challenge failed" or "Connection refused"

**Solution**:
1. Verify DNS is propagated: `dig app.insights.artemisinnovations.co.za`
2. Ensure port 80 is accessible: `sudo netstat -tlnp | grep ':80'`
3. Temporarily remove HTTPS blocks from Nginx, keep only HTTP blocks
4. Reload Nginx: `sudo systemctl reload nginx`
5. Retry certbot
6. After success, add HTTPS blocks back

### Issue: API Returns 502 Bad Gateway

**Symptom**: Nginx returns 502 when accessing API

**Solution**:
1. Check backend container is running: `docker ps --filter name=artemis-insight-backend`
2. Check backend logs: `docker logs artemis-insight-backend --tail 50`
3. Verify backend listening on port 8000: `docker exec artemis-insight-backend netstat -tlnp`
4. Check MongoDB/Redis connections in logs

### Issue: Frontend Shows Connection Error

**Symptom**: Frontend loads but can't connect to API

**Solution**:
1. Check browser console for CORS errors
2. Verify API URL in frontend build: `VITE_API_URL` should be `https://api.insights.artemisinnovations.co.za`
3. Rebuild frontend with correct API URL
4. Check FastAPI CORS configuration in backend

### Issue: Out of Memory During Build

**Symptom**: Docker build fails with "killed" or "context canceled"

**Solution**:
1. Check memory: `free -h`
2. If <400MB available, wait or manually clean up:
   ```bash
   docker container prune -f
   docker image prune -f
   ```
3. Retry build
4. Consider stopping non-critical containers temporarily

### Issue: Container Keeps Restarting

**Symptom**: `docker ps` shows container restarting repeatedly

**Solution**:
1. Check logs: `docker logs artemis-insight-backend --tail 100`
2. Common causes:
   - Database connection failed (check MongoDB credentials)
   - Redis connection failed (check Redis is running)
   - MinIO connection failed (check MinIO is running)
   - Invalid environment variable
3. Fix issue and redeploy

## Monitoring Commands

```bash
# Check all Artemis Insight containers
docker ps --filter name=artemis-insight

# Check container resource usage
docker stats --no-stream $(docker ps --filter name=artemis-insight --format '{{.Names}}')

# Check application logs
docker logs -f artemis-insight-backend
docker logs -f artemis-insight-frontend
docker logs -f artemis-insight-celery-worker

# Check Nginx access logs
sudo tail -f /var/log/nginx/access.log | grep insights

# Check Nginx error logs
sudo tail -f /var/log/nginx/error.log | grep insights

# Check system resources
free -h
df -h
```

## Success Criteria

Deployment is successful when:

- [✓] All containers running without restarts
- [✓] Backend health endpoint returns 200
- [✓] Frontend loads in browser with valid SSL
- [✓] API accessible via HTTPS
- [✓] No CORS errors in browser console
- [✓] Celery worker connected to Redis
- [✓] MongoDB/Redis/MinIO healthy
- [✓] No impact on Serelo or TM-Sanity applications
- [✓] SSL certificate valid and auto-renewing
- [✓] Memory and disk usage acceptable

## Deployment Complete

Artemis Insight is now live at:
- **Frontend**: https://app.insights.artemisinnovations.co.za
- **API**: https://api.insights.artemisinnovations.co.za

Monitor for 24 hours to ensure stability.
