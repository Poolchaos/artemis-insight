# Nginx Configuration and SSL Setup

## Add to /etc/nginx/sites-available/artemisinnovations

Add these server blocks to the existing file:

```nginx
# --- Artemis Insight App (app.insights) ---
server {
    server_name app.insights.artemisinnovations.co.za;

    location / {
        proxy_pass http://127.0.0.1:3003;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/app.insights.artemisinnovations.co.za/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/app.insights.artemisinnovations.co.za/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot
}

# --- Artemis Insight API (api.insights) ---
server {
    server_name api.insights.artemisinnovations.co.za;

    location / {
        proxy_pass http://127.0.0.1:8002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # CORS headers if needed (FastAPI handles this, but can be enforced here)
        # add_header 'Access-Control-Allow-Origin' 'https://app.insights.artemisinnovations.co.za' always;
        # add_header 'Access-Control-Allow-Credentials' 'true' always;
    }

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/app.insights.artemisinnovations.co.za/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/app.insights.artemisinnovations.co.za/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot
}

# HTTP to HTTPS redirects
server {
    if ($host = app.insights.artemisinnovations.co.za) {
        return 301 https://$host$request_uri;
    } # managed by Certbot

    listen 80;
    server_name app.insights.artemisinnovations.co.za;
    return 404; # managed by Certbot
}

server {
    if ($host = api.insights.artemisinnovations.co.za) {
        return 301 https://$host$request_uri;
    } # managed by Certbot

    listen 80;
    server_name api.insights.artemisinnovations.co.za;
    return 404; # managed by Certbot
}
```

## SSL Certificate Generation

### Step 1: Install Certbot (if not already installed)

```bash
sudo apt update
sudo apt install certbot python3-certbot-nginx
```

### Step 2: Generate Certificate for app.insights

```bash
sudo certbot --nginx -d app.insights.artemisinnovations.co.za -d api.insights.artemisinnovations.co.za
```

This will:
- Generate SSL certificates for both domains
- Automatically update the Nginx configuration
- Set up HTTP to HTTPS redirects
- Configure certificate renewal

### Step 3: Verify Certificate

```bash
sudo certbot certificates
```

Expected output should include:
```
Certificate Name: app.insights.artemisinnovations.co.za
  Domains: app.insights.artemisinnovations.co.za api.insights.artemisinnovations.co.za
  Expiry Date: [60-90 days from now]
  Certificate Path: /etc/letsencrypt/live/app.insights.artemisinnovations.co.za/fullchain.pem
  Private Key Path: /etc/letsencrypt/live/app.insights.artemisinnovations.co.za/privkey.pem
```

### Step 4: Test Nginx Configuration

```bash
sudo nginx -t
```

Expected output:
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### Step 5: Reload Nginx

```bash
sudo systemctl reload nginx
```

## Manual Configuration (if Certbot doesn't auto-configure)

### Step 1: Add temporary HTTP-only server blocks

```nginx
server {
    listen 80;
    server_name app.insights.artemisinnovations.co.za;

    location / {
        proxy_pass http://127.0.0.1:3003;
        proxy_set_header Host $host;
    }
}

server {
    listen 80;
    server_name api.insights.artemisinnovations.co.za;

    location / {
        proxy_pass http://127.0.0.1:8002;
        proxy_set_header Host $host;
    }
}
```

### Step 2: Reload Nginx

```bash
sudo nginx -t && sudo systemctl reload nginx
```

### Step 3: Run Certbot in certonly mode

```bash
sudo certbot certonly --nginx -d app.insights.artemisinnovations.co.za -d api.insights.artemisinnovations.co.za
```

### Step 4: Add HTTPS server blocks manually

Use the configuration shown at the top of this document.

### Step 5: Reload Nginx again

```bash
sudo nginx -t && sudo systemctl reload nginx
```

## DNS Configuration Required

Before running certbot, ensure DNS records are set up:

```
Type: A
Host: app.insights
Value: 165.73.87.59
TTL: 3600

Type: A
Host: api.insights
Value: 165.73.87.59
TTL: 3600
```

Verify DNS propagation:
```bash
dig app.insights.artemisinnovations.co.za
dig api.insights.artemisinnovations.co.za
```

Both should return:
```
app.insights.artemisinnovations.co.za. 3600 IN A 165.73.87.59
api.insights.artemisinnovations.co.za. 3600 IN A 165.73.87.59
```

## Verification Checklist

After configuration:

- [ ] DNS records created and propagated
- [ ] Nginx configuration added to `/etc/nginx/sites-available/artemisinnovations`
- [ ] SSL certificates generated with certbot
- [ ] Nginx configuration test passes (`sudo nginx -t`)
- [ ] Nginx reloaded successfully
- [ ] HTTP redirects to HTTPS: `curl -I http://app.insights.artemisinnovations.co.za`
- [ ] HTTPS works: `curl -I https://app.insights.artemisinnovations.co.za`
- [ ] API responds: `curl https://api.insights.artemisinnovations.co.za/health`
- [ ] Frontend loads: `curl https://app.insights.artemisinnovations.co.za`
- [ ] SSL certificate valid: `openssl s_client -connect app.insights.artemisinnovations.co.za:443 -servername app.insights.artemisinnovations.co.za`

## Troubleshooting

### Certificate Generation Fails

```bash
# Check if DNS is resolving correctly
nslookup app.insights.artemisinnovations.co.za

# Check if ports 80 and 443 are open
sudo netstat -tlnp | grep ':80\|:443'

# Check Nginx error logs
sudo tail -f /var/log/nginx/error.log

# Check certbot logs
sudo tail -f /var/log/letsencrypt/letsencrypt.log
```

### Certificate Renewal

Certbot will automatically renew certificates. To test renewal:

```bash
sudo certbot renew --dry-run
```

To force renewal (if needed):

```bash
sudo certbot renew --force-renewal
```

### Remove Old Certificates (if needed)

```bash
sudo certbot delete --cert-name app.insights.artemisinnovations.co.za
```

## Security Considerations

The current configuration:
- Enforces HTTPS with automatic HTTP to HTTPS redirects
- Uses Let's Encrypt TLS 1.2/1.3 with strong cipher suites
- Binds application ports to localhost only (127.0.0.1)
- Prevents direct access to application containers
- Uses Nginx as a reverse proxy for additional security

Optional security enhancements (if needed):
```nginx
# Rate limiting
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req zone=api_limit burst=20 nodelay;

# Security headers
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "no-referrer-when-downgrade" always;
```
