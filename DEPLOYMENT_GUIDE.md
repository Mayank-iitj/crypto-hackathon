# Q-Shield Production Deployment Guide

## Overview

This guide covers deploying the complete Q-Shield platform to production with all monitoring, logging, and security components enabled.

## Architecture

**8-Service Production Stack:**
1. **PostgreSQL 16** - Primary database (port 5432)
2. **Redis 7** - Cache/queue layer (port 6379)
3. **FastAPI API** - Core service (port 8000)
4. **Prometheus** - Metrics collection (port 9090)
5. **Grafana** - Dashboard visualization (port 3001)
6. **Elasticsearch** - Log aggregation (port 9200)
7. **Kibana** - Log visualization (port 5601)
8. **Frontend** - React application (port 3000)

## Prerequisites

- **Docker** 20.10+
- **Docker Compose** 2.0+
- **Ubuntu 20.04 LTS** (recommended) or equivalent
- **4GB+ RAM**, **20GB+ disk space**
- **Domain name** with DNS access
- **OAuth Credentials** (Google, GitHub, Microsoft)

## Local Development Setup

For local development with monitoring services:

```bash
# Copy environment files
cp .env.development .env
cp frontend/.env.development frontend/.env.local

# Start services with development overrides
docker compose up -d

# Verify services
docker compose ps

# View logs
docker compose logs -f api
```

**Development Access Points:**
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Frontend: http://localhost:3000
- Grafana: http://localhost:3000 (same as frontend)
- Prometheus: http://localhost:9090
- Kibana: http://localhost:5601

## Production Deployment

## Best Free Platform (Recommended)

Use Oracle Cloud Always Free VM for the full stack.

Quick path:

```bash
cd /opt/qshield
chmod +x deployment/oracle-free/deploy.sh
./deployment/oracle-free/deploy.sh
```

Reference: [deployment/oracle-free/README.md](deployment/oracle-free/README.md)

### Step 1: Server Preparation

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add current user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
docker compose version
```

### Step 2: Environment Configuration

```bash
# Create production directory
mkdir -p /opt/qshield
cd /opt/qshield

# Clone repository
git clone <your-repo-url> .

# Copy production environment template
cp .env.production .env

# Edit with production values
nano .env
```

**Critical .env Production Variables:**

```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql+asyncpg://qshield:${DB_PASSWORD}@postgres:5432/qshield
DB_PASSWORD=<generate-strong-password>

# Redis
REDIS_PASSWORD=<generate-strong-password>
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0

# Security
SECRET_KEY=<generate-with-openssl-rand-hex-32>
ALLOWED_HOSTS=["api.yourdomain.com","yourdomain.com"]
CORS_ORIGINS=["https://yourdomain.com"]

# OAuth Providers
GOOGLE_CLIENT_ID=<from-google-cloud-console>
GOOGLE_CLIENT_SECRET=<from-google-cloud-console>
GOOGLE_REDIRECT_URI=https://api.yourdomain.com/auth/oauth/google/callback

GITHUB_CLIENT_ID=<from-github-settings>
GITHUB_CLIENT_SECRET=<from-github-settings>
GITHUB_REDIRECT_URI=https://api.yourdomain.com/auth/oauth/github/callback

MICROSOFT_CLIENT_ID=<from-azure-portal>
MICROSOFT_CLIENT_SECRET=<from-azure-portal>
MICROSOFT_REDIRECT_URI=https://api.yourdomain.com/auth/oauth/microsoft/callback

# Elasticsearch
ELASTICSEARCH_PASSWORD=<generate-strong-password>

# Grafana
GRAFANA_PASSWORD=<generate-strong-password>

# SMTP Email
SMTP_SERVER=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=<sendgrid-api-key>
SMTP_FROM=noreply@yourdomain.com

# TLS/SSL
TLS_CERT_PATH=/app/certs/cert.pem
TLS_KEY_PATH=/app/certs/key.pem
```

### Step 3: Generate Security Keys

```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Generate self-signed certificate (replace with real cert)
openssl req -x509 -newkey rsa:4096 -nodes -out certs/cert.pem -keyout certs/key.pem -days 365

# Create keys directory with proper permissions
mkdir -p keys
chmod 700 keys
```

### Step 4: TLS/SSL Certificate

**Using Let's Encrypt (Recommended):**

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-dns-route53

# Obtain certificate
certbot certonly --dns-route53 -d yourdomain.com -d api.yourdomain.com

# Certificates location: /etc/letsencrypt/live/yourdomain.com/
# Mount in docker-compose.yml:
#   - /etc/letsencrypt/live/yourdomain.com:/app/certs:ro
```

**Manual certificate deployment:**
1. Place fullchain.pem as certs/cert.pem
2. Place privkey.pem as certs/key.pem
3. Set permissions: `chmod 600 certs/*`

### Step 5: Configure Reverse Proxy (Nginx)

```bash
# Install Nginx
sudo apt-get install nginx

# Create config at /etc/nginx/sites-available/qshield
```

**Nginx Configuration:**

```nginx
upstream api {
  server localhost:8000;
}

upstream frontend {
  server localhost:3000;
}

server {
  listen 80;
  server_name api.yourdomain.com yourdomain.com;
  
  # Redirect HTTP to HTTPS
  return 301 https://$server_name$request_uri;
}

server {
  listen 443 ssl http2;
  server_name api.yourdomain.com;
  
  ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
  
  # SSL Security
  ssl_protocols TLSv1.2 TLSv1.3;
  ssl_ciphers HIGH:!aNULL:!MD5;
  ssl_prefer_server_ciphers on;
  ssl_session_cache shared:SSL:10m;
  ssl_session_timeout 10m;
  
  # Security Headers
  add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
  add_header X-Content-Type-Options "nosniff" always;
  add_header X-Frame-Options "SAMEORIGIN" always;
  add_header X-XSS-Protection "1; mode=block" always;
  
  # API Proxy
  location / {
    proxy_pass http://api;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 300s;
    proxy_connect_timeout 75s;
  }
}

server {
  listen 443 ssl http2;
  server_name yourdomain.com;
  
  ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
  
  # Same SSL config as above...
  
  # Frontend Proxy
  location / {
    proxy_pass http://frontend;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
  
  # WebSocket Support
  location /ws {
    proxy_pass http://frontend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
  }
}
```

**Enable Nginx config:**
```bash
sudo ln -s /etc/nginx/sites-available/qshield /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Step 6: Database Initialization

```bash
# Start PostgreSQL service
docker compose up -d postgres

# Wait for postgres to be healthy (30 seconds)
sleep 30

# Run migrations
docker compose exec api alembic upgrade head

# Seed initial data (if available)
docker compose exec api python -c "from app.db.database import seed_db; seed_db()"
```

### Step 7: Start Production Services

```bash
# Pull latest images
docker compose pull

# Start all services
docker compose up -d

# Verify all services are healthy
docker compose ps

# Expected output shows all services with "healthy" status under 30 seconds
```

### Step 8: Verify Deployment

**Check Service Health:**
```bash
# API Health
curl -s https://api.yourdomain.com/health | jq .

# Prometheus
curl -s https://yourdomain.com:9090/api/prom/query?query=up | jq .

# Elasticsearch
curl -s -u elastic:${ELASTICSEARCH_PASSWORD} https://localhost:9200/_cluster/health | jq .

# Kibana
curl -s https://localhost:5601/api/status | jq .
```

**Check Logs:**
```bash
# API logs
docker compose logs api --tail=50

# Multiple services
docker compose logs postgres redis api prometheus grafana elasticsearch kibana --tail=20
```

**Test API Endpoints:**
```bash
# Health check
curl -s https://api.yourdomain.com/health

# API documentation
curl -s https://api.yourdomain.com/openapi.json | jq .

# Auth endpoints
curl -s https://api.yourdomain.com/auth/oauth/google/authorize?state=test
```

## Monitoring & Logging

### Prometheus Metrics

Access at `http://yourdomain.com:9090`

**Key Metrics:**
- `http_request_duration_seconds` - Request latency
- `http_requests_total` - Total requests
- `postgres_up` - Database connectivity
- `redis_connected_clients` - Redis connections

**Common Queries:**
```promql
# Request rate
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m])

# Response time p95
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

### Grafana Dashboards

Access at `http://yourdomain.com:3001` (login: admin / your-password)

**Provisioned Dashboards:**
1. **System Metrics** - CPU, Memory, Disk I/O
2. **Application Metrics** - Request latency, throughput, errors
3. **Database Metrics** - Query performance, connection pool
4. **Cache Metrics** - Redis commands, memory usage

### Elasticsearch/Kibana Logging

Access Kibana at `http://yourdomain.com:5601`

**Log Indices Created:**
- `qshield-logs-*` - Application logs
- `qshield-access-*` - HTTP access logs
- `qshield-errors-*` - Error logs

**Common Searches:**
```
# Recent errors
level: "ERROR" AND NOT pod_name: "prometheus"

# API latency analysis
service: "qshield-api" AND response_time_ms: [1000 TO *]

# Failed authentication attempts
endpoint: "/auth/*" AND status_code: [400 TO 401]
```

## Maintenance & Operations

### Database Backups

**Automated Backups (configured in docker-compose.yml):**
```bash
# Manual backup
docker compose exec postgres pg_dump -U qshield qshield > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore from backup
docker compose exec -T postgres psql -U qshield qshield < backup_20240101_120000.sql
```

### Certificate Renewal

```bash
# Certbot auto-renewal (runs via cron daily)
certbot renew --quiet

# Manual renewal
certbot renew --force-renewal
```

### Updates & Patching

```bash
# Pull latest images
docker compose pull

# Rebuild API image with latest dependencies
docker compose build --no-cache api

# Graceful restart (blue-green deployment pattern)
docker compose up -d --no-deps api
```

### Scaling

For high-traffic production, scale API services:

```bash
# Scale API to 3 replicas
docker compose up -d --scale api=3

# Note: Update docker-compose.yml ports section for load balancer routing
```

## Troubleshooting

### Services Won't Start

Check logs:
```bash
docker compose logs <service_name> --tail=100
```

Common issues:
- **Port conflicts**: `netstat -tulpn | grep LISTEN`
- **Disk space**: `df -h`
- **Memory**: `free -h`
- **Docker daemon**: `systemctl restart docker`

### Database Connection Fails

```bash
# Check postgres is running
docker compose ps postgres

# Test connection
docker compose exec api psql -h postgres -U qshield -d qshield -c "SELECT 1"

# Check logs
docker compose logs postgres
```

### High Memory Usage

```bash
# Check container resource usage
docker compose stats

# Adjust limits in docker-compose.yml:
# deploy:
#   resources:
#     limits:
#       memory: 2G
```

### Missing Prometheus Metrics

```bash
# Verify Prometheus scrape targets
curl -s http://localhost:9090/api/v1/targets | jq .

# Check API metrics endpoint
curl -s http://localhost:8000/metrics
```

## Security Checklist

- [ ] SECRET_KEY is 32+ character random string (not default)
- [ ] All passwords changed from defaults
- [ ] HTTPS/TLS enabled with valid certificate
- [ ] CORS_ORIGINS restricted to specific domains
- [ ] OAuth credentials obtained from providers
- [ ] Database backups configured and tested
- [ ] Log retention policies configured
- [ ] Firewall rules limit access to ports 80, 443 only
- [ ] Regular security updates applied (`docker compose pull && docker compose up -d`)
- [ ] Monitoring alerts configured in Grafana
- [ ] Rate limiting enabled on API endpoints
- [ ] API key rotation schedule established

## Disaster Recovery

### Full System Recovery

```bash
# 1. Restore database from backup
docker compose exec -T postgres psql -U qshield qshield < latest_backup.sql

# 2. Restart services
docker compose down
docker compose up -d

# 3. Verify
docker compose ps
docker compose logs api | head -20
```

### Data Recovery

```bash
# PostgreSQL point-in-time recovery (requires WAL archiving enabled)
# Contact operations team for automated recovery procedures
```

## Support

For issues not covered here:
1. Check logs: `docker compose logs -f <service>`
2. Review [DEVELOPMENT.md](docs/DEVELOPMENT.md) for local debugging
3. Check [API.md](docs/API.md) for endpoint documentation
4. Review [ARCHITECTURE.md](docs/ARCHITECTURE.md) for system design
5. Contact: devops@yourdomain.com

## Useful Commands Reference

```bash
# Service management
docker compose ps                                    # Status
docker compose up -d                                # Start all
docker compose down                                 # Stop all
docker compose restart <service>                    # Restart service
docker compose logs <service> -f --tail=50          # Follow logs

# Database operations
docker compose exec api alembic upgrade head        # Run migrations
docker compose exec postgres pg_dump -U qshield... # Backup
docker compose exec api pytest tests/               # Run tests

# Monitoring
docker compose exec prometheus promtool check rules  # Validate Prometheus
docker compose exec elasticsearch curl -X GET...    # ES cluster health
docker stats                                        # Resource usage

# Cleanup
docker compose down -v                              # Remove volumes
docker system prune -a                              # Remove unused images
```
