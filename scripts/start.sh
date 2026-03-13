#!/bin/bash
# Q-Shield Quick Start Script
# Automates setup and startup of the Q-Shield platform

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════╗"
echo "║         Q-Shield Platform - Quick Start               ║"
echo "║     Cryptographic Intelligence Platform               ║"
echo "╚════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Detect docker compose command (v2 plugin preferred, v1 fallback)
if docker compose version &> /dev/null; then
    DC="docker compose"
elif command -v docker-compose &> /dev/null; then
    DC="docker-compose"
else
    echo -e "${RED}✗${NC} Neither 'docker compose' nor 'docker-compose' is available"
    exit 1
fi

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

commands=("docker" "openssl")
for cmd in "${commands[@]}"; do
    if ! command -v $cmd &> /dev/null; then
        echo -e "${RED}✗${NC} $cmd is not installed"
        exit 1
    fi
    echo -e "${GREEN}✓${NC} $cmd found"
done
echo -e "${GREEN}✓${NC} $DC found"

# Generate keys
echo ""
echo -e "${YELLOW}Generating cryptographic keys...${NC}"
if [ ! -d "keys" ]; then
    mkdir -p keys
fi

if [ ! -f "keys/jwt_private.pem" ]; then
    bash scripts/generate_keys.sh
else
    echo -e "${GREEN}✓${NC} Keys already exist"
fi

# Create .env if not exists
echo ""
echo -e "${YELLOW}Setting up environment...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env from .env.example${NC}"
    cp .env.example .env
    
    # Generate a random SECRET_KEY for .env (48 bytes = 64 base64 chars, well above 32 char minimum)
    SECRET_KEY=$(openssl rand -base64 48)
    if [ "$(uname)" == "Darwin" ]; then
        # macOS
        sed -i '' "s|^SECRET_KEY=.*|SECRET_KEY=$SECRET_KEY|" .env
    else
        # Linux
        sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$SECRET_KEY|" .env
    fi
    echo -e "${GREEN}✓${NC} .env created with secure SECRET_KEY"
    echo -e "${YELLOW}   Note: Review .env and customize as needed${NC}"
else
    # Verify SECRET_KEY is set (required field)
    if ! grep -qE "^SECRET_KEY=.{32,}" .env 2>/dev/null; then
        echo -e "${RED}✗${NC} SECRET_KEY in .env is missing or too short (minimum 32 characters)"
        echo "   Generate one with: openssl rand -base64 48"
        exit 1
    fi
    echo -e "${GREEN}✓${NC} .env already exists"
fi

# Create logs directory
mkdir -p logs

# Build Docker images
echo ""
echo -e "${YELLOW}Building Docker images...${NC}"
$DC build --quiet
echo -e "${GREEN}✓${NC} Docker images built"

# Start services
echo ""
echo -e "${YELLOW}Starting Q-Shield services...${NC}"
$DC up -d
echo -e "${GREEN}✓${NC} Services started"

# Wait for services to be ready
echo ""
echo -e "${YELLOW}Waiting for API to be ready...${NC}"
max_attempts=60
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if curl -sf http://localhost:8000/health &> /dev/null; then
        echo -e "${GREEN}✓${NC} API is ready"
        break
    fi
    attempt=$((attempt + 1))
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo -e "${RED}✗${NC} API failed to start within timeout. Check logs: $DC logs api"
    exit 1
fi

# Print startup information
echo ""
echo -e "${GREEN}═════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Q-Shield is now running!${NC}"
echo -e "${GREEN}═════════════════════════════════════════════════════════${NC}"
echo ""
echo "URLs:"
echo -e "  ${BLUE}Frontend:${NC}        http://localhost:3000"
echo -e "  ${BLUE}API:${NC}             http://localhost:8000"
echo -e "  ${BLUE}API Docs:${NC}        http://localhost:8000/docs"
echo -e "  ${BLUE}API Redoc:${NC}       http://localhost:8000/redoc"
echo -e "  ${BLUE}Prometheus:${NC}      http://localhost:9090"
echo -e "  ${BLUE}Grafana:${NC}         http://localhost:3001"
echo -e "  ${BLUE}Kibana:${NC}          http://localhost:5601"
echo ""
echo "Database:"
echo -e "  ${BLUE}PostgreSQL:${NC}      localhost:5432 (user: qshield)"
echo -e "  ${BLUE}Redis:${NC}           localhost:6379"
echo ""
echo "Services Status:"
$DC ps | grep -E "postgres|redis|api|frontend|prometheus|grafana" || true
echo ""
echo "Next steps:"
echo "  1. Review configuration in .env"
echo "  2. Access the frontend at http://localhost:3000"
echo "  3. Access API documentation at http://localhost:8000/docs"
echo "  4. Create first assets and initiate scans"
echo "  5. Monitor with Grafana dashboard at http://localhost:3001"
echo ""
echo "Useful commands:"
echo -e "  ${BLUE}$DC logs api${NC}           - View API logs"
echo -e "  ${BLUE}$DC exec api bash${NC}      - Access API container"
echo -e "  ${BLUE}$DC down${NC}               - Stop all services"
echo ""
echo -e "${YELLOW}For detailed documentation, see README.md${NC}"
echo ""
