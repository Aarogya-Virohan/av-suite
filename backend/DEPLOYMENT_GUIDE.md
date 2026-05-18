"""
AV SUITE BACKEND - DEPLOYMENT GUIDE
====================================

Purpose: Production deployment instructions aur best practices
Yeh guide backend ko production environment mein safely deploy karne ke liye.

Target Audience: DevOps, System Administrators, Deployment Engineers
Last Updated: 2026-05-18
"""

# ============================================================================
# DEPLOYMENT PREREQUISITES
# ============================================================================

/*
Server Requirements:
- OS: Linux (Ubuntu 22.04 LTS recommended)
- Python: 3.11 or higher
- RAM: Minimum 2GB (4GB+ recommended)
- Disk: 10GB+ free space
- Database: PostgreSQL 14+ (Supabase hosted)
- Network: IPv4 connectivity to Supabase pooler

Services:
- Redis: For caching (optional, local or managed)
- Nginx: Reverse proxy (recommended)
- Docker: Container runtime (optional but recommended)
- GitHub Actions: CI/CD (already configured)
*/


# ============================================================================
# ENVIRONMENT SETUP
# ============================================================================

## Production .env Configuration

/*
Production environment variables setup:

1. Copy template file:
   cp .env.example .env.production

2. Update critical variables:
   ENVIRONMENT=production
   DEBUG=false
   
3. Database Configuration:
   DATABASE_URL=postgresql+asyncpg://user.projectid:password@region.pooler.supabase.com:5432/postgres
   
   - Replace region with Supabase region (e.g., aws-0-ap-northeast-1)
   - Use Session Pooler URL (pooler subdomain for IPv4)
   - Ensure strong database password
   
4. Security Variables:
   JWT_SECRET_KEY=<generate with openssl rand -hex 32>
   
5. CORS Configuration:
   CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
   
   - Do NOT include localhost in production
   - Only include trusted frontend domains
   - Comma-separated list no spaces
   
6. Redis Configuration (Optional):
   REDIS_URL=redis://redis-server-host:6379
   
   - Use managed Redis service if possible
   - SSL/TLS recommended for external connections

Security Checklist:
✓ DEBUG=false (no debug information exposure)
✓ Strong JWT_SECRET_KEY (32+ hex characters)
✓ CORS_ORIGINS restricted (only trusted domains)
✓ DATABASE_URL from Supabase (Session Pooler)
✓ .env file not committed to git
✓ File permissions: 600 (owner read/write only)
*/


# ============================================================================
# DEPLOYMENT OPTIONS
# ============================================================================

## Option 1: Docker Container Deployment (Recommended)

### Build Docker Image

/*
Dockerfile already provided in repository.

Build command:
docker build -t av-suite-backend:latest .

Build with version tag:
docker build -t av-suite-backend:0.1.0 .

Verify build:
docker images | grep av-suite-backend
*/

### Run Docker Container

/*
docker run -d \\
  --name av-suite-backend \\
  -p 8000:8000 \\
  --env-file .env.production \\
  av-suite-backend:latest

Options Explained:
-d: Detach (run in background)
--name: Container name (av-suite-backend)
-p: Port mapping (host:container)
--env-file: Load environment variables from file
av-suite-backend:latest: Image name and tag

Verify running:
docker ps | grep av-suite-backend

View logs:
docker logs -f av-suite-backend

Stop container:
docker stop av-suite-backend

Remove container:
docker rm av-suite-backend
*/

### Docker Compose (Multiple Services)

/*
docker-compose.yml for full stack:

version: '3.8'
services:
  backend:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env.production
    environment:
      DATABASE_URL: postgresql+asyncpg://...
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

Start stack:
docker-compose -f docker-compose.yml up -d

View logs:
docker-compose logs -f backend

Stop stack:
docker-compose down
*/


## Option 2: Direct Server Deployment

### 1. Clone Repository

/*
git clone https://github.com/Aarogya-Virohan/av-suite.git
cd av-suite/backend
*/

### 2. Create Virtual Environment

/*
python3 -m venv /opt/av-suite/venv
source /opt/av-suite/venv/bin/activate
*/

### 3. Install Dependencies

/*
pip install -e .
pip install gunicorn python-multipart
*/

### 4. Create Production .env

/*
vi /opt/av-suite/.env.production

(Copy from template and update values)
*/

### 5. Run Database Migrations

/*
export DATABASE_URL="postgresql+asyncpg://..."
source .env.production

alembic upgrade head

Verify migrations:
alembic current
*/

### 6. Run with Gunicorn

/*
gunicorn app.main:app \\
  --bind 0.0.0.0:8000 \\
  --workers 4 \\
  --worker-class uvicorn.workers.UvicornWorker \\
  --timeout 120 \\
  --access-logfile - \\
  --error-logfile -

Production settings:
--workers: 2 * CPU_CORES (e.g., 4 for 2 cores)
--timeout: 120 seconds for long operations
--log files: - means stdout (collect by systemd/docker)
*/

### 7. Run with Systemd (Long-term)

/*
Create /etc/systemd/system/av-suite-backend.service:

[Unit]
Description=AV Suite Backend
After=network.target

[Service]
Type=notify
User=av-suite
WorkingDirectory=/opt/av-suite
Environment="PATH=/opt/av-suite/venv/bin"
EnvironmentFile=/opt/av-suite/.env.production
ExecStart=/opt/av-suite/venv/bin/gunicorn app.main:app \\
    --bind unix:/run/av-suite/sock \\
    --workers 4 \\
    --worker-class uvicorn.workers.UvicornWorker
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
KillSignal=SIGTERM
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target

Enable and start service:
sudo systemctl enable av-suite-backend
sudo systemctl start av-suite-backend

View status:
sudo systemctl status av-suite-backend

View logs:
sudo journalctl -u av-suite-backend -f
*/


## Option 3: Kubernetes Deployment (Advanced)

/*
Kubernetes YAML deployment (k8s/deployment.yaml):

apiVersion: apps/v1
kind: Deployment
metadata:
  name: av-suite-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: av-suite-backend
  template:
    metadata:
      labels:
        app: av-suite-backend
    spec:
      containers:
      - name: backend
        image: av-suite-backend:0.1.0
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: av-suite-secrets
              key: database-url
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: av-suite-secrets
              key: jwt-secret
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

Deploy:
kubectl apply -f k8s/deployment.yaml

Scale replicas:
kubectl scale deployment av-suite-backend --replicas=5

View logs:
kubectl logs deployment/av-suite-backend
*/


# ============================================================================
# NGINX REVERSE PROXY CONFIGURATION
# ============================================================================

/*
Production nginx configuration:

/etc/nginx/sites-available/av-suite-backend:

upstream av_suite_backend {
    # Load balancing across multiple workers
    server 127.0.0.1:8000 max_fails=3 fail_timeout=30s;
    # Add more servers for clustering
    # server 127.0.0.1:8001;
    # server 127.0.0.1:8002;
}

server {
    listen 443 ssl http2;
    server_name api.av-suite.example.com;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/api.av-suite.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.av-suite.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Logging
    access_log /var/log/nginx/av-suite-access.log;
    error_log /var/log/nginx/av-suite-error.log;
    
    location / {
        proxy_pass http://av_suite_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name api.av-suite.example.com;
    return 301 https://$server_name$request_uri;
}

Enable nginx config:
sudo ln -s /etc/nginx/sites-available/av-suite-backend /etc/nginx/sites-enabled/

Test configuration:
sudo nginx -t

Reload nginx:
sudo systemctl reload nginx
*/


# ============================================================================
# DATABASE SETUP
# ============================================================================

/*
Database Migration Steps:

1. Ensure DATABASE_URL configured
   export DATABASE_URL="postgresql+asyncpg://..."

2. Apply migrations
   alembic upgrade head

3. Verify migrations
   alembic current
   
   Should show: rev_number (head), alembic head

4. Create initial data (if needed)
   python scripts/init_data.py

5. Verify database connection
   python test_supabase_connection.py
   
   Should output: ✅ All checks passed!

Rollback (if needed):
   alembic downgrade -1    # Rollback one migration
   alembic downgrade base  # Rollback all migrations

View migration history:
   alembic history
*/


# ============================================================================
# MONITORING & MAINTENANCE
# ============================================================================

### Application Monitoring

/*
Health check:
curl https://api.av-suite.example.com/health

Expected response:
{"status": "healthy"}

Database connection test:
python test_supabase_connection.py

View logs (Docker):
docker logs av-suite-backend

View logs (Systemd):
journalctl -u av-suite-backend -f

Monitor resources:
top, htop, or container monitoring tools
*/

### Backup Strategy

/*
Database backups (Supabase):
1. Supabase automatically backs up daily
2. Enable point-in-time recovery
3. Configure automated backups to external storage

Application code:
1. Use git for version control
2. Tag releases: git tag v0.1.0
3. Push to remote: git push origin v0.1.0

.env and secrets:
1. Store in HashiCorp Vault (recommended)
2. Or environment variable service
3. Never commit to git
*/

### Performance Optimization

/*
Database connection pooling:
- Use Supabase Session Pooler (already configured)
- Min connections: 5
- Max connections: 50-100 (based on load)

Caching:
- Implement Redis for session/query caching (future)
- Cache exercise listings (static data)
- Cache user profiles

API rate limiting:
- Implement rate limiting (future enhancement)
- Recommend: 100 requests/minute per user

Load testing:
- Use Apache JMeter or k6
- Test endpoints under load
- Monitor response times and memory
*/


# ============================================================================
# TROUBLESHOOTING
# ============================================================================

### Application Won't Start

/*
Check logs:
docker logs av-suite-backend
journalctl -u av-suite-backend -n 50

Common issues:
1. Database connection string invalid
   → Verify DATABASE_URL format
   → Check credentials
   → Ensure network connectivity

2. Port already in use
   → Change port: -p 8001:8000
   → Kill process: lsof -i :8000

3. Missing dependencies
   → Reinstall: pip install -e .
   → Check Python version: python3 --version

4. Permission errors
   → Check file permissions: ls -la .env
   → Fix: chmod 600 .env
*/

### Database Connection Issues

/*
Session pooler not responding:
1. Check internet connectivity
2. Verify Supabase status page
3. Test connection: python test_supabase_connection.py
4. Check credentials in .env

Connection timeout:
1. Increase timeout in database config
2. Check if pooler limits reached (increase in Supabase)
3. Monitor active connections

Connection refused:
1. Verify host and port in DATABASE_URL
2. Check firewall rules
3. Ensure Supabase project is active
*/

### High Memory Usage

/*
Monitor memory:
free -h
docker stats av-suite-backend

Solutions:
1. Reduce worker count in gunicorn
2. Enable Redis caching
3. Optimize database queries
4. Implement connection pooling
5. Scale horizontally (multiple instances)
*/


# ============================================================================
# SCALING CONSIDERATIONS
# ============================================================================

### Horizontal Scaling

/*
Multiple instances behind load balancer:
1. Backend 1: :8001 → nginx
2. Backend 2: :8002 → nginx
3. Backend 3: :8003 → nginx

Load balancer distributes requests.

Session management:
- Use shared Redis (not local)
- Stateless design (already implemented)
- No local file storage for user data
*/

### Vertical Scaling

/*
Single large instance:
- Increase server RAM
- Upgrade CPU
- Use SSD storage
- Optimize database queries

Database scaling:
- Supabase auto-scales
- Monitor connection usage
- Upgrade plan if needed
*/


# ============================================================================
# SECURITY DEPLOYMENT CHECKLIST
# ============================================================================

✓ SSL/TLS enabled (HTTPS only)
✓ Firewall configured (only needed ports open)
✓ .env file secured (600 permissions, not tracked)
✓ DEBUG mode disabled (DEBUG=false)
✓ Strong JWT secret (32+ characters, random)
✓ CORS properly configured (trusted domains only)
✓ Database credentials protected
✓ Regular backups enabled
✓ Monitoring and alerts configured
✓ Log files rotate (avoid filling disk)
✓ Regular security updates applied
✓ API rate limiting considered
✓ Input validation enabled
✓ Error messages don't expose sensitive data


# ============================================================================
# ROLLBACK PROCEDURE
# ============================================================================

/*
If deployment fails:

1. Identify the issue
   docker logs av-suite-backend
   systemctl status av-suite-backend

2. Revert code to previous version
   git checkout v0.1.0  # Or previous tag
   docker pull av-suite-backend:v0.0.9
   docker run ... av-suite-backend:v0.0.9

3. Rollback database (if migrations changed)
   alembic downgrade -1

4. Restart service
   docker restart av-suite-backend
   systemctl restart av-suite-backend

5. Verify health
   curl https://api.av-suite.example.com/health
*/


# ============================================================================
# SUPPORT & DOCUMENTATION
# ============================================================================

For more information:
- Supabase Documentation: https://supabase.com/docs
- FastAPI Documentation: https://fastapi.tiangolo.com
- Docker Documentation: https://docs.docker.com
- Kubernetes Documentation: https://kubernetes.io/docs
- Nginx Documentation: https://nginx.org/en/docs
