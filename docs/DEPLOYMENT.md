# Q-Shield Deployment Guide

Comprehensive guide for deploying Q-Shield to production environments including Docker, Kubernetes, and cloud platforms.

## Table of Contents
1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Docker Deployment](#docker-deployment)
3. [Kubernetes Deployment](#kubernetes-deployment)
4. [Cloud Platform Deployment](#cloud-platform-deployment)
5. [Configuration Management](#configuration-management)
6. [Security Hardening](#security-hardening)
7. [Monitoring & Observability](#monitoring--observability)
8. [Backup & Recovery](#backup--recovery)
9. [Scaling](#scaling)
10. [Troubleshooting](#troubleshooting)

---

## Pre-Deployment Checklist

### Code Quality
- [ ] All tests passing (`pytest --cov`)
- [ ] Code coverage >85%
- [ ] No type errors (`mypy`)
- [ ] Code style compliance (`black`, `flake8`)
- [ ] Security audit completed
- [ ] Dependencies up-to-date (`pip list --outdated`)

### Configuration
- [ ] Environment variables documented
- [ ] Secrets management configured
- [ ] Database migrations tested
- [ ] Cryptographic keys generated securely
- [ ] TLS certificates obtained

### Infrastructure
- [ ] Database capacity planned (CPU, RAM, storage)
- [ ] Redis capacity sufficient for cache/queue
- [ ] Network policies defined
- [ ] Backup strategy implemented
- [ ] Monitoring configured
- [ ] Log aggregation setup

### Security
- [ ] No hardcoded credentials
- [ ] API authentication enforced
- [ ] Rate limiting enabled
- [ ] CORS configured correctly
- [ ] Security headers configured
- [ ] Input validation implemented
- [ ] Audit logging enabled

---

## Docker Deployment

### Building the Image

```bash
# Build with tag
docker build -t qshield:1.0.0 -f backend/Dockerfile backend/

# Build with registry
docker build -t registry.example.com/qshield:1.0.0 backend/

# Build with build args
docker build \
  --build-arg PYTHON_VERSION=3.11 \
  --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
  -t qshield:1.0.0 backend/
```

### Production Docker Compose

**File**: `docker-compose.prod.yml`

```yaml
version: '3.9'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: qshield
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: qshield
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U qshield"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    image: qshield:latest
    environment:
      DATABASE_URL: postgresql+asyncpg://qshield:${DB_PASSWORD}@postgres:5432/qshield
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379
      SECRET_KEY: ${SECRET_KEY}
      ENVIRONMENT: production
      LOG_LEVEL: INFO
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./keys:/app/keys:ro
      - ./logs:/var/log/qshield
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    restart: unless-stopped
    networks:
      - qshield_network

  postgres:
    image: postgres:16-alpine
    # ... (same as above)

  redis:
    image: redis:7-alpine
    # ... (same as above)

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local

networks:
  qshield_network:
    driver: bridge
```

### Deployment Commands

```bash
# Pull latest code
git pull origin main

# Build image
docker build -t qshield:$(git rev-parse --short HEAD) backend/

# Push to registry
docker push registry.example.com/qshield:latest

# Start with docker-compose
docker-compose -f docker-compose.prod.yml up -d

# Verify services
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f api

# Stop services
docker-compose -f docker-compose.prod.yml down
```

---

## Kubernetes Deployment

### Prerequisites

```bash
# Install kubectl
kubectl version --client

# Configure cluster access
kubectl config use-context prod-cluster

# Verify cluster access
kubectl cluster-info
```

### Create Namespace

```bash
kubectl create namespace qshield
kubectl config set-context --current --namespace=qshield
```

### Create Secrets

```bash
# Database password
kubectl create secret generic db-secrets \
  --from-literal=password=$(openssl rand -base64 32) \
  -n qshield

# Redis password
kubectl create secret generic redis-secrets \
  --from-literal=password=$(openssl rand -base64 32) \
  -n qshield

# JWT keys
kubectl create secret generic jwt-secrets \
  --from-file=private_key=keys/jwt_private.pem \
  --from-file=public_key=keys/jwt_public.pem \
  -n qshield

# API secrets
kubectl create secret generic api-secrets \
  --from-literal=secret_key=$(openssl rand -base64 32) \
  --from-literal=api_key=$(openssl rand -base64 32) \
  -n qshield
```

### Create ConfigMap

```bash
kubectl create configmap qshield-config \
  --from-literal=ENVIRONMENT=production \
  --from-literal=LOG_LEVEL=INFO \
  --from-literal=API_HOST=0.0.0.0 \
  --from-literal=API_PORT=8000 \
  -n qshield
```

### Deploy Services

```bash
# PostgreSQL StatefulSet
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: qshield
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:16-alpine
        ports:
        - containerPort: 5432
        env:
        - name: POSTGRES_DB
          value: qshield
        - name: POSTGRES_USER
          value: qshield
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: db-secrets
              key: password
        volumeMounts:
        - name: data
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 10Gi
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: qshield
spec:
  clusterIP: None
  selector:
    app: postgres
  ports:
  - protocol: TCP
    port: 5432
    targetPort: 5432
EOF
```

### Deploy Q-Shield API

```bash
kubectl apply -f deployment/kubernetes/qshield-api.yaml
```

### Verify Deployment

```bash
# Check deployment status
kubectl get deployments -n qshield

# Check pods
kubectl get pods -n qshield

# Check services
kubectl get svc -n qshield

# Check events
kubectl get events -n qshield

# View logs
kubectl logs -f deployment/qshield-api -n qshield

# Port forward for testing
kubectl port-forward svc/qshield-api 8000:8000 -n qshield
# Access: http://localhost:8000
```

### Update Deployment

```bash
# Build and push new image
docker build -t registry.example.com/qshield:1.1.0 backend/
docker push registry.example.com/qshield:1.1.0

# Update deployment
kubectl set image deployment/qshield-api \
  qshield-api=registry.example.com/qshield:1.1.0 \
  -n qshield

# Monitor rollout
kubectl rollout status deployment/qshield-api -n qshield

# View rollout history
kubectl rollout history deployment/qshield-api -n qshield

# Rollback if needed
kubectl rollout undo deployment/qshield-api -n qshield
```

---

## Cloud Platform Deployment

### AWS ECS

```bash
# Create ECR repository
aws ecr create-repository --repository-name qshield

# Build and push image
docker build -t qshield:latest backend/
docker tag qshield:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/qshield:latest
aws ecr get-login-password | docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/qshield:latest

# Deploy with CloudFormation or Terraform
terraform apply -var="image_uri=123456789.dkr.ecr.us-east-1.amazonaws.com/qshield:latest"
```

### Google Cloud Run

```bash
# Build with Cloud Build
gcloud builds submit --tag gcr.io/PROJECT_ID/qshield

# Deploy to Cloud Run
gcloud run deploy qshield \
  --image gcr.io/PROJECT_ID/qshield:latest \
  --platform managed \
  --region us-central1 \
  --memory 1Gi \
  --cpu 2 \
  --set-env-vars DATABASE_URL=... \
  --set-env-vars REDIS_URL=...
```

### Azure Container Instances

```bash
# Create container registry
az acr create --resource-group qshield --name qshieldregistry --sku Basic

# Build and push
az acr build --registry qshieldregistry --image qshield:latest backend/

# Deploy container
az container create \
  --resource-group qshield \
  --name qshield-api \
  --image qshieldregistry.azurecr.io/qshield:latest \
  --environment-variables DATABASE_URL=... REDIS_URL=... \
  --ports 8000
```

---

## Configuration Management

### Environment Variables

**Production `.env` Template**:

```env
# Application
ENVIRONMENT=production
API_TITLE=Q-Shield Production
API_HOST=0.0.0.0
API_PORT=8000
API_VERSION=1.0.0

# Database
DATABASE_URL=postgresql+asyncpg://qshield:PASSWORD@db.prod.example.com/qshield
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40
SQLALCHEMY_ECHO=False

# Redis
REDIS_URL=redis://redis.prod.example.com:6379
REDIS_PASSWORD=PASSWORD

# Security
SECRET_KEY=GENERATED_KEY
JWT_ALGORITHM=RS256
JWT_EXPIRATION_MINUTES=30
HASH_ALGORITHM=bcrypt

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
SENTRY_DSN=https://...@o0000000.ingest.sentry.io/0000000

# CORS
CORS_ORIGINS=["https://dashboard.q-shield.example.com"]
CORS_ALLOW_CREDENTIALS=true

# TLS/SSL
SSL_CERT_FILE=/etc/ssl/certs/server.crt
SSL_KEY_FILE=/etc/ssl/private/server.key
VERIFY_SSL=true

# External APIs (optional)
SHODAN_API_KEY=XXXXX
CENSYS_API_ID=XXXXX
CENSYS_API_SECRET=XXXXX

# Feature Flags
ENABLE_NMAP_SCANNING=true
ENABLE_ZGRAB_SCANNING=true
ENABLE_COMPLIANCE_REPORTS=true

# Monitoring
PROMETHEUS_ENABLED=true
PROMETHEUS_METRICS_PORT=9090
DATADOG_API_KEY=XXXXX

# Email/Notifications
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=noreply@q-shield.example.com
SMTP_PASSWORD=PASSWORD
NOTIFICATION_EMAIL=alerts@example.com
```

### Kubernetes Secrets Management

```bash
# Create secret from file
kubectl create secret generic app-secrets \
  --from-literal=DATABASE_URL=postgresql://... \
  --from-literal=REDIS_URL=redis://... \
  --from-literal=SECRET_KEY=... \
  -n qshield

# Create secret from env file
kubectl create secret generic app-secrets \
  --from-env-file=.env.prod \
  -n qshield

# Use external secret manager (Sealed Secrets)
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.18.0/controller.yaml
kubeseal -f secret.yaml -w sealed-secret.yaml
kubectl apply -f sealed-secret.yaml
```

---

## Security Hardening

### Network Security

```yaml
# NetworkPolicy: Restrict traffic
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: qshield-deny-all
  namespace: qshield
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: qshield-allow
  namespace: qshield
spec:
  podSelector:
    matchLabels:
      app: qshield-api
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
  - to:
    - namespaceSelector: {}
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
```

### Container Security

```dockerfile
# Dockerfile hardening
FROM python:3.11-slim

# Run as non-root
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy files
COPY --chown=appuser:appuser . /app
WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Security settings
RUN chmod -R 755 /app
RUN mkdir -p /var/log/qshield && chmod 755 /var/log/qshield

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### API Security

```python
# Rate limiting
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.backends.redis import RedisBackend

limiter = FastAPILimiter(
    backend=RedisBackend(redis),
    key_func=get_remote_address,
    default_limits=["100/minute"]
)

# CORS hardening
CORSMiddleware(
    app,
    allow_origins=["https://dashboard.example.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

# Security headers
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["api.example.com"]
)
```

---

## Monitoring & Observability

### Prometheus Metrics

```yaml
# Kubernetes ServiceMonitor
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: qshield-api
  namespace: qshield
spec:
  selector:
    matchLabels:
      app: qshield-api
  endpoints:
  - port: metrics
    interval: 30s
```

### Grafana Dashboards

```bash
# Import dashboard
curl -X POST http://localhost:3000/api/dashboards/db \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d @dashboards/qshield-overview.json
```

### ELK Stack Integration

```yaml
# Filebeat configuration
filebeat.prospectors:
- type: log
  enabled: true
  paths:
    - /var/log/qshield/*.log
  json.message_key: message
  json.keys_under_root: true

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "qshield-%{+yyyy.MM.dd}"
```

### Alerting

```yaml
# Prometheus alerting rules
groups:
- name: qshield
  interval: 30s
  rules:
  - alert: APIDown
    expr: up{job="qshield-api"} == 0
    for: 5m
    annotations:
      summary: "Q-Shield API is down"
  
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
    for: 5m
    annotations:
      summary: "High error rate detected"
  
  - alert: DatabaseConnectionPoolExhausted
    expr: db_connection_pool_exhausted > 0
    for: 5m
    annotations:
      summary: "Database connection pool exhausted"
```

---

## Backup & Recovery

### Database Backup

```bash
# Automated daily backup
0 2 * * * pg_dump -U qshield qshield | gzip > /backups/qshield-$(date +\%Y\%m\%d).sql.gz

# S3 backup
aws s3 cp /backups/qshield-*.sql.gz s3://qshield-backups/

# Restore from backup
gunzip < /backups/qshield-20240110.sql.gz | psql -U qshield qshield
```

### Redis Backup

```bash
# Manual backup
redis-cli --rdb /backups/dump.rdb

# Restore from backup
docker cp /backups/dump.rdb redis:/data/
```

### Kubernetes PVC Backup

```bash
# Create snapshot
kubectl exec -it postgres-0 -n qshield -- \
  pg_basebackup -D - | gzip > postgres-backup-$(date +%Y%m%d).tar.gz

# Store in object storage
gsutil cp postgres-backup-*.tar.gz gs://qshield-backups/
```

---

## Scaling

### Horizontal Scaling

```bash
# Scale API replicas
kubectl scale deployment qshield-api --replicas=5 -n qshield

# Auto-scaling based on metrics
kubectl autoscale deployment qshield-api \
  --min=3 --max=10 \
  --cpu-percent=80 \
  -n qshield
```

### Database Scaling

```bash
# PostgreSQL read replicas
# Use Terraform or CloudFormation to create replicas

# Connection pooling
# PgBouncer or similar in front of database

# Vertical scaling
kubectl set resources deployment qshield-api \
  -c=qshield-api \
  --requests=cpu=1000m,memory=1Gi \
  --limits=cpu=2000m,memory=2Gi \
  -n qshield
```

### Redis Scaling

```bash
# Redis cluster
# Use AWS ElastiCache with cluster mode enabled

# Or self-hosted Redis Cluster
redis-cli --cluster create \
  127.0.0.1:6379 127.0.0.1:6380 127.0.0.1:6381 \
  127.0.0.1:6382 127.0.0.1:6383 127.0.0.1:6384
```

---

## Troubleshooting

### Pod not starting

```bash
# Check pod events
kubectl describe pod qshield-api-0 -n qshield

# Check logs
kubectl logs -f pod/qshield-api-0 -n qshield

# Check resource constraints
kubectl top pod -n qshield

# Check node resources
kubectl top nodes
```

### Database connection issues

```bash
# Test connection
kubectl exec -it qshield-api-0 -n qshield -- \
  psql postgresql://user@host/dbname

# Check network policies
kubectl get networkpolicies -n qshield
kubectl describe networkpolicy qshield-allow -n qshield
```

### Memory leaks

```bash
# Monitor memory usage
kubectl top pod qshield-api-0 -n qshield --containers

# Profile Python process
python -m memory_profiler app/main.py

# Use Py-Spy
pip install py-spy
py-spy record -o profile.svg -- python app/main.py
```

### Performance issues

```bash
# Check slow queries
kubectl exec -it postgres-0 -n qshield -- \
  psql -c "SELECT * FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"

# Check Redis usage
redis-cli info stats

# Profile API endpoints
# Use py-spy or cProfile
```

---

## Summary Checklist

- [ ] Pre-deployment checks passed
- [ ] Secrets securely configured
- [ ] Backups automated and tested
- [ ] Monitoring configured and alerting enabled
- [ ] Auto-scaling configured
- [ ] Security hardening applied
- [ ] Network policies in place
- [ ] Health checks functioning
- [ ] Rollback procedure documented
- [ ] On-call runbooks created

For more information, see [SECURITY.md](SECURITY.md) and [README.md](../README.md).
