# Q-Shield Development Setup Guide

This guide provides step-by-step instructions for setting up Q-Shield for local development and testing.

## Prerequisites

- **Python 3.11+** - Download from [python.org](https://www.python.org)
- **PostgreSQL 14+** - Download from [postgresql.org](https://www.postgresql.org)
- **Redis 7+** - Download from [redis.io](https://redis.io)
- **Docker & Docker Compose** (optional, for containerized setup)
- **Node.js 18+** (for frontend development)
- **Git** - Version control

### macOS
```bash
# Using Homebrew
brew install python3 postgresql redis nodejs git

# Start PostgreSQL (if installed via Homebrew)
brew services start postgresql

# Start Redis
brew services start redis
```

### Ubuntu/Debian
```bash
# Install dependencies
sudo apt-get update
sudo apt-get install python3.11 python3.11-venv python3-pip postgresql postgresql-client redis-server nodejs git

# Start services
sudo systemctl start postgresql
sudo systemctl start redis-server
```

### Windows
- Download and install PostgreSQL from [postgresql.org](https://www.postgresql.org/download/windows/)
- Download and install Redis from [redis.io](https://redis.io/download#redis-installation) or use Windows Subsystem for Linux
- Download and install Python 3.11+ from [python.org](https://www.python.org/downloads/windows/)
- Download and install Node.js from [nodejs.org](https://nodejs.org)

## Backend Setup

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/q-shield.git
cd q-shield
```

### 2. Create Python Virtual Environment
```bash
# Create venv
python3 -m venv venv

# Activate venv
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 4. Set Up Environment Variables
```bash
# Copy example config
cp .env.example .env

# Edit .env with your settings
nano .env
```

Key variables to configure:
```env
# Database
DATABASE_URL=postgresql+asyncpg://qshield:password@localhost/qshield
SQLALCHEMY_ECHO=True  # Debug SQL queries

# Redis
REDIS_URL=redis://localhost:6379

# JWT
SECRET_KEY=<generate-with-openssl-rand-base64-32>
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Logging
LOG_LEVEL=DEBUG
ENVIRONMENT=development

# API
API_HOST=0.0.0.0
API_PORT=8000
API_TITLE=Q-Shield Development
```

### 5. Generate Cryptographic Keys
```bash
cd ..
bash scripts/generate_keys.sh
```

This creates:
- `keys/jwt_private.pem` - JWT signing key
- `keys/jwt_public.pem` - JWT public key
- `keys/platform_signing.pem` - Certificate signing key
- `keys/platform_public.pem` - Public key
- `keys/internal_key.pem` - Internal TLS key
- `keys/internal_cert.pem` - Internal TLS certificate

### 6. Initialize Database
```bash
cd backend

# Create database (PostgreSQL)
createdb qshield

# Run migrations (if using Alembic)
# alembic upgrade head

# Or create schema directly
python -c "from app.db.database import Base, engine; Base.metadata.create_all(engine)"
```

### 7. Start Backend Server
```bash
# From backend directory with venv activated
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **OpenAPI Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Frontend Setup (Optional)

### 1. Navigate to Frontend
```bash
cd frontend
```

### 2. Install Dependencies
```bash
npm install
```

### 3. Set Up Environment
```bash
# Create .env.local
cat > .env.local << EOF
REACT_APP_API_URL=http://localhost:8000
REACT_APP_API_VERSION=v1
EOF
```

### 4. Start Development Server
```bash
npm start
```

The frontend will be available at: http://localhost:3000

## Docker Compose Setup (Recommended for Full Stack)

### Quick Start
```bash
cd q-shield
bash scripts/start.sh
```

This script automatically:
1. Checks prerequisites
2. Generates cryptographic keys
3. Creates `.env` file
4. Builds Docker images
5. Starts all services
6. Initializes database

Services will be available at:
- **API**: http://localhost:8000
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

### Manual Docker Compose
```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

## Testing

### Run Unit Tests
```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test
pytest tests/unit/test_pqc_validator.py
```

### Run Integration Tests
```bash
# Requires running services
pytest tests/integration/

# With verbose output
pytest tests/integration/ -v
```

### Test API Endpoints with curl
```bash
# Health check
curl http://localhost:8000/health

# List assets
curl http://localhost:8000/api/v1/assets \
  -H "Authorization: Bearer YOUR_TOKEN"

# Create scan request
curl -X POST http://localhost:8000/api/v1/scans \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Scan",
    "scan_type": "full",
    "targets": ["example.com:443"]
  }'
```

## Database Management

### Access PostgreSQL
```bash
# Via psql
psql -U qshield -d qshield -h localhost

# Via Docker
docker-compose exec postgres psql -U qshield -d qshield
```

### View Database Schema
```sql
-- List all tables
\dt

-- View table structure
\d <table_name>

-- View indexes
\di

-- View foreign keys
SELECT constraint_name, table_name, column_name 
FROM information_schema.constraint_column_usage
WHERE table_name = '<table_name>';
```

### Reset Database
```bash
# Drop and recreate
dropdb qshield
createdb qshield
python backend/app/db/database.py
```

## Debugging

### View Application Logs
```bash
# Docker Compose
docker-compose logs api

# Follow in real-time
docker-compose logs -f api

# Last 100 lines
docker-compose logs --tail=100 api
```

### Debug with Python
```bash
# Add breakpoints in code
import pdb; pdb.set_trace()

# Or use debugger
breakpoint()  # Python 3.7+
```

### Monitor Redis
```bash
# Connect to Redis CLI
redis-cli

# View all keys
KEYS *

# View key details
GET <key>

# Monitor real-time commands
MONITOR
```

### Database Query Debugging
```env
# In .env
SQLALCHEMY_ECHO=True  # Logs all SQL queries
```

## Performance Testing

### Load Test with Locust
```bash
# Install locust
pip install locust

# Create locustfile.py with test scenarios
# Run load test
locust -f locustfile.py --host=http://localhost:8000
```

### Benchmark Crypto Operations
```bash
cd backend

# Run custom benchmark
python -m scripts.benchmark_crypto

# Profile service
python -m cProfile -s cumulative app/main.py
```

## Code Quality

### Linting
```bash
# Install linters
pip install flake8 black isort pylint

# Run flake8
flake8 app/

# Format with Black
black app/

# Sort imports
isort app/
```

### Type Checking
```bash
# Install mypy
pip install mypy

# Run type checker
mypy app/
```

## Deployment Checklist

Before deploying to production:

- [ ] All tests passing (`pytest`)
- [ ] No type errors (`mypy`)
- [ ] Code style compliant (`black --check`, `flake8`)
- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] Cryptographic keys generated securely
- [ ] Docker images built
- [ ] Docker Compose test successful
- [ ] Kubernetes manifests reviewed
- [ ] Security audit completed
- [ ] Backup strategy defined
- [ ] Monitoring configured (Prometheus/Grafana)

## Troubleshooting

### "database does not exist" error
```bash
# Create database
createdb qshield

# Or via Docker
docker-compose exec postgres createdb -U qshield qshield
```

### "connection refused" error
```bash
# Ensure PostgreSQL is running
sudo systemctl status postgresql

# Or via Docker
docker-compose logs postgres
```

### Redis connection errors
```bash
# Check Redis status
redis-cli ping

# Via Docker
docker-compose exec redis redis-cli ping
```

### Port already in use
```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>

# Or change port in .env and restart
```

### Module import errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check Python path
python -c "import sys; print(sys.path)"
```

## Development Workflow

### 1. Create Feature Branch
```bash
git checkout -b feature/crypto-assessment
```

### 2. Make Changes
```bash
# Edit files
# Run tests
pytest
# Check types
mypy app/
# Format code
black app/
```

### 3. Commit Changes
```bash
git add .
git commit -m "Add PQC assessment endpoint"
git push origin feature/crypto-assessment
```

### 4. Create Pull Request
- Describe changes
- Reference issues
- Request review
- Ensure CI passes

### 5. Merge and Deploy
```bash
# After approval
git checkout main
git pull origin main
git merge feature/crypto-assessment
git push origin main

# Build and deploy to staging
docker build -t qshield:latest .
docker push <registry>/qshield:latest
```

## Additional Resources

- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **ReDoc**: http://localhost:8000/redoc (ReDoc interface)
- **Architecture Guide**: See [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md)
- **Security Guide**: See [docs/SECURITY.md](../docs/SECURITY.md)
- **Contributing Guide**: See [CONTRIBUTING.md](../CONTRIBUTING.md)

## Getting Help

- **Issues**: Report bugs on GitHub Issues
- **Discussions**: Ask questions on GitHub Discussions
- **Email**: dev@q-shield.example.com
- **Docs**: Check README.md for additional information

---

**Happy developing! 🚀**
