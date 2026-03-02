# Q-Shield Quick Start Guide

## 🚀 Super Quick Start (2 Minutes)

### Prerequisites
- Docker Desktop (Windows/Mac) or Docker + Docker Compose (Linux)
- Git

### Get Running
```bash
# 1. Navigate to project
cd c:\projects\q-shield

# 2. Start everything
docker compose up -d

# 3. Wait 30 seconds for services to boot
sleep 30

# 4. Verify all healthy
docker compose ps

# 5. Access services
```

### Access Points
| Service | URL | Purpose |
|---------|-----|---------|
| **Frontend** | http://localhost:3000 | Web application |
| **API Docs** | http://localhost:8000/docs | API documentation |
| **Grafana** | http://localhost:3001 | Metrics dashboards |
| **Kibana** | http://localhost:5601 | Log visualization |

## 📊 Development Workflow

### Common Tasks

**View Logs**
```bash
docker compose logs api -f          # Follow API logs
docker compose logs postgres -f     # Follow database logs
docker compose logs redis -f        # Follow cache logs
```

**Access Database**
```bash
docker compose exec postgres psql -U qshield -d qshield
```

**Access Redis**
```bash
docker compose exec redis redis-cli
```

**Restart Services**
```bash
docker compose restart api          # Restart API
docker compose down && docker compose up -d  # Restart all
```

**Stop Everything**
```bash
docker compose down
```

## 🔧 Configuration

### Environment Files

- `.env.development` - Development environment settings (loaded by default)
- `.env.production` - Production template (requires manual config)
- `frontend/.env.development` - Frontend dev config
- `frontend/.env.production` - Frontend prod config

### Change Environment
```bash
# Use production config locally
cp .env.production .env
docker compose down && docker compose up -d
```

## 🔐 Security Secrets

### Default Development Credentials

| Service | Username | Password | Use |
|---------|----------|----------|-----|
| PostgreSQL | qshield | qshield123 | Development only |
| Redis | N/A | (none) | Development only |
| Grafana | admin | admin123 | Development only |
| Elasticsearch | elastic | (disabled) | Development only |

**⚠️ NEVER use these in production!**

## 📈 Monitoring Dashboard

### Grafana Access
1. Open http://localhost:3001
2. Login: admin / admin123
3. View dashboards:
   - System Metrics
   - Application Performance
   - Database Health
   - Cache Performance

### Kibana Logs
1. Open http://localhost:5601
2. Search logs by service, timestamp, level

### Prometheus Metrics
1. Open http://localhost:9090
2. Query metrics: `http_requests_total`, `http_request_duration_seconds`, etc.

## ✅ Health Checks

### Verify Everything is Working
```bash
# API health
curl http://localhost:8000/health

# Database health
curl http://localhost:8000/health  # Returns DB connectivity status

# Redis health
docker compose exec redis redis-cli ping

# API docs
curl http://localhost:8000/openapi.json

# Frontend
curl http://localhost:3000
```

All should return HTTP 200 or similar success status.

## 🐛 Troubleshooting

### Service Won't Start
```bash
# Check logs
docker compose logs <service-name>

# Check if ports are in use
netstat -tulpn | grep LISTEN

# Force restart with recreation
docker compose up -d --force-recreate
```

### Database Connection Error
```bash
# Verify database is running
docker compose ps postgres

# Check database logs
docker compose logs postgres

# Reset database
docker compose down -v    # Remove all volumes
docker compose up -d      # Recreate fresh
```

### Frontend Can't Connect to API
```bash
# Check CORS configuration
docker compose logs api | grep CORS

# Verify API is responding
curl -v http://localhost:8000/health

# Check frontend environment
cat frontend/.env.development
# Should have: REACT_APP_API_URL=http://localhost:8000
```

### High Memory Usage
```bash
# Check service resource usage
docker compose stats

# Reduce memory limits in docker-compose.yml
# Restart services
docker compose down && docker compose up -d
```

### Port Already in Use
```bash
# Find what's using the port (example: port 3000)
netstat -tulpn | grep 3000

# Kill the process or change docker-compose port mapping
```

## 📚 Documentation

### For Complete Information

1. **Architecture & Design**
   - Read: `docs/ARCHITECTURE.md`

2. **API Reference**
   - Read: `docs/API.md`
   - Or: http://localhost:8000/docs

3. **Deployment Guide**
   - Read: `DEPLOYMENT_GUIDE.md` (production deployment)
   - Read: `deployment/terraform/README.md` (AWS cloud)

4. **Operations & Monitoring**
   - Read: `OPERATIONS_REFERENCE.md` (alerts, dashboards, runbooks)

5. **Pre-Launch Checklist**
   - Read: `PRODUCTION_READINESS_CHECKLIST.md` (before going live)

6. **Security**
   - Read: `docs/SECURITY.md`

## 🚀 Next Steps

### For Local Testing
1. ✅ Services are running - start developing!
2. Make code changes
3. Changes hot-reload automatically
4. Check API at http://localhost:8000/docs
5. Check Frontend at http://localhost:3000

### For Deployment
1. Read: `DEPLOYMENT_GUIDE.md` (single server)
2. Read: `deployment/terraform/README.md` (AWS)
3. Use: `PRODUCTION_READINESS_CHECKLIST.md` (pre-launch)
4. Reference: `OPERATIONS_REFERENCE.md` (running in production)

### For Team Setup
1. Share this quick start guide with team
2. Have them run `docker compose up -d`
3. Verify at http://localhost:3000
4. Share `OPERATIONS_REFERENCE.md` for monitoring
5. Share `docs/API.md` for API reference

## 🎯 Common Commands Reference

```bash
# Status checks
docker compose ps                          # View service status
docker compose stats                       # View resource usage
docker compose logs                        # View all logs

# Service management
docker compose up -d                       # Start all services
docker compose down                        # Stop all services
docker compose restart <service>           # Restart specific service
docker compose pull                        # Update images

# Database operations
docker compose exec postgres psql -U qshield -d qshield -c "SELECT 1"
docker compose exec postgres pg_dump -U qshield qshield > backup.sql

# Cache operations
docker compose exec redis redis-cli info
docker compose exec redis redis-cli flushall  # Clear all keys (dev only!)

# Cleanup
docker compose down -v                     # Stop and remove volumes (DELETES DATA)
docker system prune                        # Remove unused containers/images
```

## 📞 Support

**Issues not covered here?**

1. Check `OPERATIONS_REFERENCE.md` for common problems
2. Review service logs: `docker compose logs <service>`
3. Check Docker/Kubernetes documentation
4. Review code comments in `backend/app/` and `frontend/src/`

---

**That's it!** Your Q-Shield platform is ready to develop, test, and deploy. 🎉
