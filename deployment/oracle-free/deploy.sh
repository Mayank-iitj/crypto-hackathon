#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[qshield] Oracle Free deployment bootstrap starting..."

if ! command -v docker >/dev/null 2>&1; then
  echo "[qshield] Docker not found. Installing Docker and Compose plugin..."
  sudo apt-get update -y
  sudo apt-get install -y ca-certificates curl gnupg lsb-release
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker "$USER" || true
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "[qshield] Docker Compose plugin unavailable. Installing plugin..."
  sudo apt-get update -y
  sudo apt-get install -y docker-compose-plugin
fi

sudo apt-get update -y
sudo apt-get install -y openssl git

if [ ! -f .env ]; then
  echo "[qshield] Creating .env from Oracle template"
  cp deployment/oracle-free/.env.oracle-free.example .env
fi

replace_if_placeholder() {
  local key="$1"
  local placeholder="$2"
  local generated="$3"
  if grep -q "^${key}=${placeholder}$" .env; then
    sed -i "s|^${key}=${placeholder}$|${key}=${generated}|" .env
  fi
}

generated_secret="$(openssl rand -base64 48 | tr -d '\n')"
generated_db="$(openssl rand -hex 24)"
generated_redis="$(openssl rand -hex 24)"
generated_grafana="$(openssl rand -hex 16)"

replace_if_placeholder "SECRET_KEY" "REPLACE_WITH_STRONG_SECRET" "$generated_secret"
replace_if_placeholder "DB_PASSWORD" "REPLACE_WITH_STRONG_DB_PASSWORD" "$generated_db"
replace_if_placeholder "REDIS_PASSWORD" "REPLACE_WITH_STRONG_REDIS_PASSWORD" "$generated_redis"
replace_if_placeholder "GRAFANA_PASSWORD" "REPLACE_WITH_STRONG_GRAFANA_PASSWORD" "$generated_grafana"

mkdir -p keys logs
if [ ! -f keys/jwt_private.pem ] || [ ! -f keys/platform_signing.pem ]; then
  echo "[qshield] Generating signing keys..."
  bash scripts/generate_keys.sh
fi

echo "[qshield] Building and starting stack..."
docker compose \
  -f docker-compose.yml \
  -f deployment/oracle-free/docker-compose.oracle-free.yml \
  up -d --build

echo "[qshield] Stack status:"
docker compose ps

echo "[qshield] Deployment complete."
echo "[qshield] Frontend: http://<VM_PUBLIC_IP>:3000"
echo "[qshield] API Docs: http://<VM_PUBLIC_IP>:8000/docs"
echo "[qshield] Grafana: http://<VM_PUBLIC_IP>:3001"
echo "[qshield] Kibana: http://<VM_PUBLIC_IP>:5601"
