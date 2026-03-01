# Q-Shield - Deployment Ready Build

## Environment Variables to Set

### Backend Environment
```bash
export ENVIRONMENT=production
export SECRET_KEY=your-production-secret-key-min-32-chars
export DATABASE_URL=postgresql+asyncpg://user:password@db-host:5432/qshield
export DATABASE_POOL_SIZE=30
export DATABASE_MAX_OVERFLOW=20

# Redis
export REDIS_URL=redis://redis-host:6379/0
export REDIS_PASSWORD=your-redis-password

# OAuth Credentials
export GOOGLE_CLIENT_ID=your-google-client-id
export GOOGLE_CLIENT_SECRET=your-google-client-secret
export GITHUB_CLIENT_ID=your-github-client-id
export GITHUB_CLIENT_SECRET=your-github-client-secret
export MICROSOFT_CLIENT_ID=your-microsoft-client-id
export MICROSOFT_CLIENT_SECRET=your-microsoft-client-secret

# Logging
export LOG_LEVEL=INFO
export LOG_FILE_PATH=/var/log/qshield/app.log
export AUDIT_LOG_PATH=/var/log/qshield/audit.log

# CORS
export CORS_ORIGINS=["https://yourdomain.com"]

# Deployment
export WORKERS=4
export WORKER_TIMEOUT=120
```

## Pre-Deployment Checklist

- [ ] Database PostgreSQL 16+ running
- [ ] Redis 7+ running  
- [ ] All environment variables configured
- [ ] SSL/TLS certificates ready
- [ ] OAuth provider credentials obtained and configured
- [ ] Log directories created and permissions set
- [ ] Database migrations run
- [ ] HTTPS enforced in production

## Docker Deployment

```bash
# Build image
docker build -t qshield:latest -f backend/Dockerfile .

# Run container
docker run -d \
  --name qshield-api \
  -p 8000:8000 \
  --env-file .env.production \
  -v /var/log/qshield:/var/log/qshield \
  qshield:latest
```

## Kubernetes Deployment

```bash
# Create namespace
kubectl create namespace qshield

# Create secrets
kubectl create secret generic qshield-secrets \
  --from-literal=secret-key=$SECRET_KEY \
  --from-literal=db-url=$DATABASE_URL \
  -n qshield

# Deploy
kubectl apply -f deployment/kubernetes/qshield-deployment.yaml \
  -n qshield

# Check status
kubectl get pods -n qshield
kubectl logs -f -n qshield -l app=qshield
```

## API Server Startup

```bash
cd backend

# Using uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Using gunicorn (recommended for production)
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120
```

## Health Checks

```bash
# API Health
curl https://yourdomain.com/api/v1/health

# OAuth Providers
curl https://yourdomain.com/api/v1/auth/providers

# Database Connection
curl https://yourdomain.com/api/v1/health
```

## Monitoring

- Application logs: `/var/log/qshield/app.log`
- Audit logs: `/var/log/qshield/audit.log`
- Metrics: `/metrics` (Prometheus format)
- Health: `/health` endpoint

## Security Best Practices

1. **HTTPS Only**: All traffic must use HTTPS
2. **API Keys**: Use strong, randomly generated keys
3. **Database**: Connect only over VPN or private network
4. **Secrets Management**: Use environment variables or secrets manager
5. **Backups**: Regular automated backups of PostgreSQL
6. **Monitoring**: Enable audit logging and access logs
7. **Rate Limiting**: Implemented on all public endpoints
8. **CORS**: Configure to specific origin domains only

## Performance Tuning

- Database connection pool: 20-30 connections
- Worker processes: 2-4 per CPU core
- Worker timeout: 120 seconds
- Request timeout: 30 seconds
- Cache TTL: 5-10 minutes (Redis)

See `docs/DEPLOYMENT.md` for complete deployment guide.
