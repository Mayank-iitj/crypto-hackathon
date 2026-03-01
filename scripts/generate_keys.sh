#!/bin/bash
# Generate cryptographic keys for Q-Shield

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Create keys directory
mkdir -p keys
cd keys

echo "Generating Q-Shield cryptographic keys..."

# 1. Generate JWT signing key pair (RSA 4096)
echo "Generating JWT key pair..."
openssl genrsa -out jwt_private.pem 4096
openssl rsa -in jwt_private.pem -pubout -out jwt_public.pem && \
echo -e "${GREEN}✓${NC} JWT keys generated"

# 2. Generate platform signing key pair (RSA 4096 for Quantum-Safe Certificates)
echo "Generating platform signing key pair..."
openssl genrsa -out platform_signing.pem 4096
openssl rsa -in platform_signing.pem -pubout -out platform_public.pem && \
echo -e "${GREEN}✓${NC} Platform keys generated"

# 3. Generate TLS certificate for internal communications (self-signed)
echo "Generating TLS certificate for internal communications..."
openssl req -x509 -newkey rsa:2048 -keyout internal_key.pem -out internal_cert.pem -days 365 -nodes \
    -subj "/C=US/ST=State/L=City/O=Q-Shield/OU=Internal/CN=localhost" && \
echo -e "${GREEN}✓${NC} Internal TLS certificate generated"

# Fix permissions
chmod 600 jwt_private.pem
chmod 644 jwt_public.pem
chmod 600 platform_signing.pem
chmod 644 platform_public.pem
chmod 600 internal_key.pem
chmod 644 internal_cert.pem

echo ""
echo -e "${GREEN}All cryptographic keys generated successfully!${NC}"
echo ""
echo "Key files:"
echo "  - jwt_private.pem (JWT signing private key)"
echo "  - jwt_public.pem (JWT signing public key)"
echo "  - platform_signing.pem (Certificate signing private key)"
echo "  - platform_public.pem (Certificate signing public key)"
echo "  - internal_key.pem (Internal TLS private key)"
echo "  - internal_cert.pem (Internal TLS certificate)"
echo ""
echo "⚠️  IMPORTANT: Keep private keys secure!"
echo "    - Never commit to version control"
echo "    - Restrict file permissions"
echo "    - Backup securely"
echo "    - Rotate periodically"
