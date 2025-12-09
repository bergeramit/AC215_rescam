# GCP HTTPS Deployment Guide for Rescam

Complete step-by-step guide to deploy the Rescam application on Google Cloud Platform Compute Engine with HTTPS using Let's Encrypt SSL certificates.

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Architecture](#architecture)
4. [Deployment Steps](#deployment-steps)
5. [Post-Deployment Configuration](#post-deployment-configuration)
6. [Verification](#verification)
7. [Troubleshooting](#troubleshooting)
8. [Maintenance](#maintenance)

---

## Overview

**Deployment URL**: `https://35-224-238-97.nip.io`
**Static IP**: `35.224.238.97`
**DNS Service**: nip.io (free, automatic DNS resolution)
**SSL**: Let's Encrypt (free, auto-renewing certificates)
**Platform**: GCP Compute Engine
**Containers**: Docker Compose (Frontend + API)

### What is nip.io?

nip.io is a free DNS service that automatically resolves IP addresses embedded in domain names:
- Format: `<IP-with-dashes>.nip.io`
- Your domain: `35-224-238-97.nip.io` → resolves to `35.224.238.97`
- **No signup**, no configuration, works instantly
- Perfect for testing and development deployments

---

## Prerequisites

### On Your Local Machine

- [x] GCP account with Compute Engine VM created
- [x] Static external IP: `35.224.238.97`
- [x] SSH access to the VM
- [x] GCP credentials (`secrets/application_default_credentials.json`)
- [x] Git repository with code

### On the VM

The following will be installed during deployment:
- Docker & Docker Compose
- Nginx (reverse proxy)
- Certbot (Let's Encrypt client)

### GCP Firewall Rules

Ensure these ports are open in your GCP firewall:
- **Port 22**: SSH access
- **Port 80**: HTTP (for Let's Encrypt validation and HTTP → HTTPS redirect)
- **Port 443**: HTTPS (production traffic)

To verify:
```bash
# In GCP Console, go to: VPC Network → Firewall rules
# Or use gcloud:
gcloud compute firewall-rules list --filter="name~http"
```

---

## Architecture

```
Internet (HTTPS requests)
          ↓
  35-224-238-97.nip.io:443
          ↓
[GCP Compute Engine VM: 35.224.238.97]
          ↓
  Nginx Reverse Proxy (Host Level)
  - SSL Termination (Let's Encrypt)
  - HTTP → HTTPS Redirect
  - Security Headers
          ↓
    Docker Compose Network
          ↓
    ┌─────────────┬─────────────┐
    ↓             ↓             ↓
Frontend:3000  API:5050
(React SPA)   (Node/FastAPI)
```

**Traffic Flow:**
1. Browser → `https://35-224-238-97.nip.io`
2. Nginx SSL termination → decrypts HTTPS
3. Nginx routes:
   - `/` → Frontend container (port 3000)
   - `/api/*` → API container (port 5050)
   - `/api/emails/stream` → API with SSE handling (no buffering)
4. Frontend (internal) → `/api/*` → Nginx → API container

---

## Deployment Steps

### Step 1: Initial VM Setup

SSH into your Compute Engine VM:

```bash
# From your local machine
gcloud compute ssh <vm-name> --zone=<your-zone>

# Or using standard SSH
ssh <username>@35.224.238.97
```

Once connected, update system and install dependencies:

```bash
# Update system packages
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
sudo apt-get install -y docker.io docker-compose

# Enable and start Docker service
sudo systemctl enable docker
sudo systemctl start docker

# Add your user to docker group (avoid using sudo)
sudo usermod -aG docker $USER
newgrp docker

# Verify Docker installation
docker --version
docker-compose --version

# Install Certbot (Let's Encrypt client)
sudo apt-get install -y certbot python3-certbot-nginx

# Install Nginx (host-level reverse proxy)
sudo apt-get install -y nginx

# Verify Nginx installation
nginx -v
```

### Step 2: Clone Repository to VM

```bash
cd ~

# Clone your repository
git clone https://github.com/yourusername/rescam.git

# Or if using SSH
git clone git@github.com:yourusername/rescam.git

cd rescam
```

### Step 3: Copy GCP Credentials to VM

Transfer your `secrets/` directory from local machine to VM:

**Option 1: Using gcloud SCP (Recommended)**

```bash
# On your local machine, from the rescam directory
gcloud compute scp --recurse ./secrets/ <vm-name>:~/rescam/secrets/ --zone=<your-zone>
```

**Option 2: Using standard SCP**

```bash
# On your local machine, from the rescam directory
scp -r ./secrets/ <username>@35.224.238.97:~/rescam/secrets/
```

**Verify the secrets are copied:**

```bash
# On the VM
ls -la ~/rescam/secrets/
# Should show: application_default_credentials.json
```

### Step 4: Verify DNS Resolution

Test that nip.io is working correctly:

```bash
# Test DNS resolution
nslookup 35-224-238-97.nip.io

# Expected output:
# Server:         127.0.0.53
# Address:        127.0.0.53#53
#
# Non-authoritative answer:
# Name:   35-224-238-97.nip.io
# Address: 35.224.238.97

# Also test with Google DNS
nslookup 35-224-238-97.nip.io 8.8.8.8
```

✅ If you see `35.224.238.97` in the response, DNS is working!
❌ If not, verify your VM's external IP is correct.

### Step 5: Obtain Let's Encrypt SSL Certificates

**IMPORTANT**: Do this BEFORE starting Docker containers, and ensure Nginx is stopped:

```bash
# Stop Nginx if it's running
sudo systemctl stop nginx

# Verify port 80 is free
sudo netstat -tulpn | grep :80
# Should return nothing

# Obtain SSL certificate from Let's Encrypt
sudo certbot certonly --standalone \
  -d 35-224-238-97.nip.io \
  --email amitberger02@gmail.com \
  --agree-tos \
  --non-interactive

# Expected output:
# Successfully received certificate.
# Certificate is saved at: /etc/letsencrypt/live/35-224-238-97.nip.io/fullchain.pem
# Key is saved at:         /etc/letsencrypt/live/35-224-238-97.nip.io/privkey.pem
```

**Verify certificates were created:**

```bash
sudo ls -la /etc/letsencrypt/live/35-224-238-97.nip.io/
# Should show: cert.pem  chain.pem  fullchain.pem  privkey.pem  README
```

**Common Errors:**

- **"Connection refused"**: Port 80 is blocked by firewall. Check GCP firewall rules.
- **"Timeout"**: Nginx is still running on port 80. Run `sudo systemctl stop nginx`.
- **"Challenge failed"**: Wait a few seconds and try again. Sometimes temporary network issues.

### Step 6: Build and Start Docker Compose Services

```bash
cd ~/rescam

# Verify .env.production exists
cat .env.production
# Should show production environment variables

# Build Docker images with production configuration
# --no-cache ensures frontend builds with production VITE_API_URL
docker-compose build --no-cache

# Start services in detached mode
docker-compose up -d

# Verify containers are running
docker-compose ps
# Should show:
# NAME                IMAGE              STATUS
# rescam-frontend     rescam-frontend    Up
# rescam-api          rescam-api         Up
```

**Check container logs:**

```bash
# View all logs
docker-compose logs

# Follow logs in real-time
docker-compose logs -f

# View specific service logs
docker-compose logs frontend
docker-compose logs api

# Check for errors
docker-compose logs | grep -i error
```

### Step 7: Configure Nginx Reverse Proxy

Copy the Nginx configuration to the system:

```bash
# Copy nginx-host.conf to sites-available
sudo cp ~/rescam/nginx-host.conf /etc/nginx/sites-available/rescam

# Create symbolic link to enable the site
sudo ln -s /etc/nginx/sites-available/rescam /etc/nginx/sites-enabled/

# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Test Nginx configuration for syntax errors
sudo nginx -t

# Expected output:
# nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
# nginx: configuration file /etc/nginx/nginx.conf test is successful
```

**Start Nginx:**

```bash
# Start Nginx service
sudo systemctl start nginx

# Enable Nginx to start on boot
sudo systemctl enable nginx

# Check Nginx status
sudo systemctl status nginx
# Should show: active (running)
```

**View Nginx logs:**

```bash
# Access log
sudo tail -f /var/log/nginx/rescam-access.log

# Error log
sudo tail -f /var/log/nginx/rescam-error.log
```

### Step 8: Set Up SSL Certificate Auto-Renewal

Certbot automatically installs a systemd timer for certificate renewal. Verify it's working:

```bash
# Test certificate renewal (dry run - doesn't actually renew)
sudo certbot renew --dry-run

# Expected output:
# Congratulations, all simulated renewals succeeded

# Check auto-renewal timer status
sudo systemctl status certbot.timer

# View renewal schedule
sudo systemctl list-timers | grep certbot
```

**Certificate renewal happens automatically:**
- Certbot checks daily for certificates expiring in 30 days
- Auto-renews before expiration
- No manual intervention needed

**Manual renewal (if needed):**

```bash
# Renew certificates manually
sudo certbot renew

# Reload Nginx to pick up new certificates
sudo systemctl reload nginx
```

---

## Post-Deployment Configuration

### Step 9: Update Google OAuth JavaScript Origins

Your app uses Google Identity Services OAuth 2.0 (popup-based authentication).

1. Go to [Google Cloud Console - Credentials](https://console.cloud.google.com/apis/credentials)
2. Select your project: `articulate-fort-472520-p2`
3. Find OAuth 2.0 Client ID: `1097076476714-9iaegt01febhsqh14niv8m2sjl8q07n7`
4. Click **Edit** (pencil icon)
5. Under **Authorized JavaScript origins**, click **Add URI**
6. Add: `https://35-224-238-97.nip.io`
7. **Do NOT modify** Authorized redirect URIs (not needed for popup OAuth)
8. Click **Save**

**Why this is needed:**
- Your app uses `window.google.accounts.oauth2.initTokenClient()` for authentication
- Google requires the domain to be explicitly whitelisted
- Without this, users will get "origin_mismatch" errors when signing in

### Step 10: Update Pub/Sub Webhook URL

Your app receives Gmail push notifications via Google Pub/Sub. Update the webhook endpoint:

1. Go to [Google Cloud Console - Pub/Sub](https://console.cloud.google.com/cloudpubsub/subscription)
2. Select your project: `articulate-fort-472520-p2`
3. Find the subscription for topic: `gmail-notifications`
4. Click the subscription name, then click **Edit**
5. Under **Delivery type**, update **Endpoint URL**:
   - **Old**: `https://<ngrok-url>/api/pubsub/webhook`
   - **New**: `https://35-224-238-97.nip.io/api/pubsub/webhook`
6. Click **Update**

**Test the webhook:**

```bash
# From your VM, test the endpoint
curl -X POST https://35-224-238-97.nip.io/api/pubsub/webhook \
  -H "Content-Type: application/json" \
  -d '{"message": {"data": "test"}}'

# Check API logs
docker-compose logs api | tail -20
```

---

## Verification

### 1. Test HTTPS Access

```bash
# Test from the VM
curl -I https://35-224-238-97.nip.io

# Expected output:
# HTTP/2 200
# server: nginx/...
# strict-transport-security: max-age=31536000; includeSubDomains

# Test HTTP redirect
curl -I http://35-224-238-97.nip.io

# Expected output:
# HTTP/1.1 301 Moved Permanently
# Location: https://35-224-238-97.nip.io/
```

### 2. Check SSL Certificate

```bash
# View certificate details
sudo certbot certificates

# Expected output:
# Certificate Name: 35-224-238-97.nip.io
#   Domains: 35-224-238-97.nip.io
#   Expiry Date: ... (90 days from issue)
#   Certificate Path: /etc/letsencrypt/live/35-224-238-97.nip.io/fullchain.pem
#   Private Key Path: /etc/letsencrypt/live/35-224-238-97.nip.io/privkey.pem
```

### 3. Test from Your Browser

Open your browser and navigate to:

**🌐 https://35-224-238-97.nip.io**

✅ **What you should see:**
- Valid SSL certificate (green padlock in browser)
- Rescam login page
- No security warnings
- Google Sign-In button works

❌ **If you see issues:**
- **"Not Secure" warning**: SSL certificate not installed correctly
- **"ERR_CONNECTION_REFUSED"**: Nginx not running or firewall blocking port 443
- **"502 Bad Gateway"**: Docker containers not running
- **OAuth errors**: JavaScript origins not updated in Google Console

### 4. Test API Endpoints

```bash
# Test health endpoint
curl https://35-224-238-97.nip.io/api/health

# Expected: {"status":"ok"}

# Test from browser console (F12)
fetch('https://35-224-238-97.nip.io/api/health')
  .then(r => r.json())
  .then(console.log)
```

### 5. Check SSL Security Rating

Test your SSL configuration security:

**Online tool**: https://www.ssllabs.com/ssltest/analyze.html?d=35-224-238-97.nip.io

✅ **Target rating**: A or A+

### 6. Monitor Application Logs

```bash
# Docker containers
docker-compose logs -f

# Nginx access log
sudo tail -f /var/log/nginx/rescam-access.log

# Nginx error log
sudo tail -f /var/log/nginx/rescam-error.log

# System logs
sudo journalctl -u nginx -f
sudo journalctl -u docker -f
```

---

## Troubleshooting

### Issue 1: Can't Access Website (Connection Refused)

**Symptoms:**
- Browser shows "ERR_CONNECTION_REFUSED"
- `curl https://35-224-238-97.nip.io` fails

**Diagnosis:**

```bash
# Check if Nginx is running
sudo systemctl status nginx

# Check if port 443 is listening
sudo netstat -tulpn | grep :443

# Check GCP firewall rules
gcloud compute firewall-rules list --filter="allowed.ports:(443 OR 80)"
```

**Solutions:**

1. **Nginx not running**:
   ```bash
   sudo systemctl start nginx
   sudo systemctl enable nginx
   ```

2. **Port 443 blocked by firewall**:
   ```bash
   # Create firewall rule to allow HTTPS
   gcloud compute firewall-rules create allow-https \
     --allow tcp:443 \
     --source-ranges 0.0.0.0/0 \
     --description "Allow HTTPS traffic"
   ```

3. **Check Nginx configuration**:
   ```bash
   sudo nginx -t
   # If errors, review /etc/nginx/sites-available/rescam
   ```

### Issue 2: SSL Certificate Errors

**Symptoms:**
- Browser shows "Not Secure" or certificate warnings
- SSL certificate is for wrong domain

**Diagnosis:**

```bash
# Check certificate
sudo certbot certificates

# Test SSL
openssl s_client -connect 35-224-238-97.nip.io:443 -servername 35-224-238-97.nip.io
```

**Solutions:**

1. **Certificate not found**:
   ```bash
   # Regenerate certificate
   sudo certbot certonly --standalone -d 35-224-238-97.nip.io
   sudo systemctl reload nginx
   ```

2. **Wrong certificate paths in Nginx**:
   ```bash
   # Edit Nginx config
   sudo nano /etc/nginx/sites-available/rescam
   # Verify paths match:
   # ssl_certificate /etc/letsencrypt/live/35-224-238-97.nip.io/fullchain.pem;
   # ssl_certificate_key /etc/letsencrypt/live/35-224-238-97.nip.io/privkey.pem;

   sudo nginx -t
   sudo systemctl reload nginx
   ```

### Issue 3: Docker Containers Won't Start

**Symptoms:**
- `docker-compose ps` shows containers as "Exited"
- Website shows 502 Bad Gateway

**Diagnosis:**

```bash
# Check container status
docker-compose ps

# View container logs
docker-compose logs

# Check for port conflicts
sudo netstat -tulpn | grep -E '3000|5050'
```

**Solutions:**

1. **Check logs for errors**:
   ```bash
   docker-compose logs api
   docker-compose logs frontend
   ```

2. **Verify .env.production exists**:
   ```bash
   cat .env.production
   ```

3. **Verify secrets directory**:
   ```bash
   ls -la secrets/
   # Should contain: application_default_credentials.json
   ```

4. **Rebuild containers**:
   ```bash
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

5. **Check Docker logs**:
   ```bash
   sudo journalctl -u docker -n 50
   ```

### Issue 4: Google OAuth Sign-In Fails

**Symptoms:**
- "origin_mismatch" error when clicking Sign In
- OAuth popup closes immediately
- "redirect_uri_mismatch" errors

**Solutions:**

1. **Verify JavaScript origins in Google Console**:
   - Go to [Google Cloud Console - Credentials](https://console.cloud.google.com/apis/credentials)
   - OAuth 2.0 Client ID must include: `https://35-224-238-97.nip.io`

2. **Check browser console for errors** (F12):
   ```javascript
   // Should see VITE_GOOGLE_CLIENT_ID and VITE_API_URL in logs
   console.log(import.meta.env.VITE_GOOGLE_CLIENT_ID)
   console.log(import.meta.env.VITE_API_URL)
   ```

3. **Verify frontend was built with correct env vars**:
   ```bash
   # Rebuild frontend with correct production variables
   docker-compose down
   docker-compose build --no-cache frontend
   docker-compose up -d
   ```

### Issue 5: API Calls Return 404

**Symptoms:**
- `/api/*` endpoints return 404
- Browser console shows "Failed to fetch" errors

**Diagnosis:**

```bash
# Test API directly on VM
curl http://localhost:5050/health

# Test through Nginx
curl https://35-224-238-97.nip.io/api/health

# Check Nginx error logs
sudo tail -f /var/log/nginx/rescam-error.log
```

**Solutions:**

1. **API container not running**:
   ```bash
   docker-compose ps api
   docker-compose logs api
   docker-compose restart api
   ```

2. **Nginx not proxying correctly**:
   ```bash
   # Check Nginx config
   sudo nginx -t

   # Review proxy_pass settings
   sudo grep -A 5 "location /api" /etc/nginx/sites-available/rescam
   ```

3. **CORS issues**:
   - Check API logs for CORS errors
   - Verify `X-Forwarded-Proto` header is set in Nginx

### Issue 6: SSE Stream Disconnects

**Symptoms:**
- `/api/emails/stream` endpoint disconnects after 60 seconds
- Real-time email updates stop working

**Solutions:**

1. **Verify SSE-specific Nginx config**:
   ```bash
   sudo grep -A 10 "/api/emails/stream" /etc/nginx/sites-available/rescam

   # Should include:
   # proxy_buffering off;
   # proxy_cache off;
   # proxy_read_timeout 86400s;
   # chunked_transfer_encoding on;
   ```

2. **Test SSE endpoint**:
   ```bash
   # This should keep connection open
   curl -N https://35-224-238-97.nip.io/api/emails/stream
   ```

---

## Maintenance

### Viewing Logs

**Docker Compose Logs:**
```bash
cd ~/rescam

# All services
docker-compose logs -f

# Specific service
docker-compose logs -f frontend
docker-compose logs -f api

# Last 100 lines
docker-compose logs --tail=100

# Since specific time
docker-compose logs --since 2024-01-01T10:00:00
```

**Nginx Logs:**
```bash
# Access log (all requests)
sudo tail -f /var/log/nginx/rescam-access.log

# Error log
sudo tail -f /var/log/nginx/rescam-error.log

# Search for specific IP
sudo grep "35.224.238.97" /var/log/nginx/rescam-access.log
```

**System Logs:**
```bash
# Nginx service
sudo journalctl -u nginx -f

# Docker service
sudo journalctl -u docker -f

# Certbot logs
sudo cat /var/log/letsencrypt/letsencrypt.log
```

### Updating the Application

When you push changes to your repository:

```bash
# SSH to VM
ssh <username>@35.224.238.97

cd ~/rescam

# Pull latest code
git pull origin main

# Rebuild and restart containers
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Verify
docker-compose ps
docker-compose logs -f
```

### Updating Environment Variables

```bash
# Edit production environment
nano ~/rescam/.env.production

# Restart containers to pick up changes
docker-compose down
docker-compose up -d
```

### Restarting Services

```bash
# Restart Docker containers
docker-compose restart

# Restart specific service
docker-compose restart api
docker-compose restart frontend

# Restart Nginx
sudo systemctl restart nginx

# Reload Nginx (graceful restart, no downtime)
sudo systemctl reload nginx
```

### SSL Certificate Management

**Check certificate expiration:**
```bash
sudo certbot certificates
```

**Manual renewal:**
```bash
# Renew all certificates
sudo certbot renew

# Renew specific certificate
sudo certbot renew --cert-name 35-224-238-97.nip.io

# Reload Nginx to use new certificate
sudo systemctl reload nginx
```

**Force renewal (if needed):**
```bash
sudo certbot renew --force-renewal
sudo systemctl reload nginx
```

### Monitoring Resources

**Disk usage:**
```bash
# Check overall disk usage
df -h

# Check Docker disk usage
docker system df

# Clean up unused Docker resources
docker system prune -a
```

**Memory usage:**
```bash
# Overall system
free -h

# Docker containers
docker stats

# Specific container
docker stats rescam-frontend rescam-api
```

**Network connections:**
```bash
# Active connections to Nginx
sudo netstat -an | grep :443 | wc -l

# Connections to API
sudo netstat -an | grep :5050 | wc -l
```

### Backup Recommendations

1. **VM Snapshots**:
   ```bash
   # Create snapshot
   gcloud compute disks snapshot <disk-name> \
     --snapshot-names=rescam-backup-$(date +%Y%m%d) \
     --zone=<your-zone>
   ```

2. **Backup secrets**:
   ```bash
   # Download secrets from VM
   scp -r <username>@35.224.238.97:~/rescam/secrets/ ./secrets-backup/
   ```

3. **Database backups** (if using Firestore):
   ```bash
   # Export Firestore data
   gcloud firestore export gs://rescam-backup-bucket/$(date +%Y%m%d)
   ```

### Security Updates

**Update system packages monthly:**
```bash
sudo apt-get update
sudo apt-get upgrade -y

# Reboot if kernel was updated
sudo reboot
```

**Update Docker images:**
```bash
cd ~/rescam
docker-compose pull
docker-compose up -d
```

---

## Next Steps

### 1. Set Up Monitoring

**GCP Cloud Monitoring:**
- Go to [Cloud Monitoring](https://console.cloud.google.com/monitoring)
- Create dashboard for VM metrics (CPU, memory, disk, network)
- Set up alerts for high resource usage

**Uptime checks:**
```bash
# Create uptime check
gcloud monitoring uptime-checks create https-check \
  --resource-type=uptime-url \
  --host=35-224-238-97.nip.io \
  --path=/api/health
```

### 2. Gmail Watch Renewal

Gmail watch notifications expire after 7 days. Set up automatic renewal:

```bash
# Create cron job
crontab -e

# Add this line (renew every 6 days)
0 0 */6 * * curl -X POST https://35-224-238-97.nip.io/api/gmail/watch
```

See `reports/PUBSUB_WEBHOOK_SETUP.md` for details.

### 3. Move to Custom Domain (Optional)

If you want a custom domain instead of nip.io:

1. Purchase domain (e.g., `rescam.io` from Namecheap, Google Domains)
2. Point domain A record to `35.224.238.97`
3. Update all references from `35-224-238-97.nip.io` to `rescam.io`:
   - `.env.production`
   - `nginx-host.conf`
   - Google OAuth origins
   - Pub/Sub webhook URL
4. Obtain new SSL certificate:
   ```bash
   sudo certbot certonly --standalone -d rescam.io -d www.rescam.io
   ```

### 4. Production Hardening

**Rate limiting (in nginx-host.conf):**
```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

location /api {
    limit_req zone=api_limit burst=20 nodelay;
    # ... rest of config
}
```

**OAuth token persistence:**
- Current: in-memory (lost on restart)
- Production: Store in Firestore or Redis

**Enable fail2ban:**
```bash
sudo apt-get install fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

---

## Summary

Your Rescam application is now deployed at:

🌐 **https://35-224-238-97.nip.io**

**Features:**
- ✅ HTTPS with valid SSL certificate (Let's Encrypt)
- ✅ Automatic HTTP → HTTPS redirect
- ✅ Auto-renewing certificates (90-day lifetime)
- ✅ Security headers (HSTS, X-Frame-Options, etc.)
- ✅ SSE support for real-time email updates
- ✅ Google OAuth integration
- ✅ Gmail push notifications via Pub/Sub

**Maintenance:**
- Certificates renew automatically
- Check logs regularly: `docker-compose logs -f`
- Update code: `git pull && docker-compose build --no-cache && docker-compose up -d`

**Support:**
- Deployment guide: `reports/GCP_HTTPS_DEPLOYMENT.md`
- Pub/Sub setup: `reports/PUBSUB_WEBHOOK_SETUP.md`
- Project README: `README.md`

---

**Deployment Date**: $(date)
**Deployed By**: Claude Code Assistant
**Version**: 1.0.0
