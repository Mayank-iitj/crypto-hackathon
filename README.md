# Q-Shield: Cryptographic Intelligence Platform for Post-Quantum Readiness

A production-grade, enterprise-ready platform that automatically discovers internet-facing banking assets, scans cryptographic configurations, evaluates Post-Quantum Cryptography (PQC) readiness, and issues digitally verifiable Quantum-Safe Certificates.

## 🚀 Quick Start

**Get running in 2 minutes:**

```bash
cd c:\projects\q-shield
docker compose up -d
```

Then access:
- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Grafana Dashboards**: http://localhost:3001
- **Kibana Logs**: http://localhost:5601

📖 **Full documentation**: See [QUICK_START.md](QUICK_START.md)

## 🎯 Mission

Q-Shield enables banks and financial institutions to:
- **Detect quantum vulnerabilities today** before CRQCs (Cryptographically Relevant Quantum Computers) emerge
- **Transition to Post-Quantum Cryptography** systematically and securely
- **Maintain regulatory compliance** with NIST, ISO 27001, and RBI Cyber Security Framework

## 📚 Documentation

| Document | Purpose | Audience |
|----------|---------|----------|
| [QUICK_START.md](QUICK_START.md) | 2-minute setup guide | Everyone |
| [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) | Complete doc index | Oriented reference |
| [PRODUCTION_DEPLOYMENT_SUMMARY.md](PRODUCTION_DEPLOYMENT_SUMMARY.md) | What's included | Leads/Architects |
| [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) | Single-server deployment | DevOps/SRE |
| [deployment/terraform/README.md](deployment/terraform/README.md) | AWS cloud deployment | Cloud Engineers |
| [deployment/helm/HELM_GUIDE.md](deployment/helm/HELM_GUIDE.md) | Kubernetes deployment | K8s Operators |
| [PRODUCTION_READINESS_CHECKLIST.md](PRODUCTION_READINESS_CHECKLIST.md) | Pre-launch validation | Engineering Leads |
| [OPERATIONS_REFERENCE.md](OPERATIONS_REFERENCE.md) | Monitoring & runbooks | On-call Engineers |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design | Architects/Mentors |
| [docs/API.md](docs/API.md) | API reference | API Users |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Code standards | Developers |
| [docs/SECURITY.md](docs/SECURITY.md) | Security model | Security Teams |
| [docs/OAUTH_SETUP.md](docs/OAUTH_SETUP.md) | OAuth integration | Integrators |

**→ Start here:** [QUICK_START.md](QUICK_START.md) or [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)

## ✨ Key Features

### 🔍 Asset Discovery Engine
- Automatic discovery of internet-facing banking assets
- Domain enumeration, subdomain discovery, IP range scanning
- ASN-based lookup for infrastructure mapping
- Public cloud exposure detection
- Only identifies truly public-facing assets

### 🔐 Cryptographic Inventory Scanner
- Real TLS handshakes (no mocked data)
- Extract TLS versions, cipher suites, key exchange mechanisms
- Certificate chain analysis with revocation checking
- Perfect Forward Secrecy (PFS) detection
- OCSP stapling and HSTS analysis
- API layer crypto assessment (mTLS, JWT, OAuth)
- VPN protocol enumeration (IKE, DH groups)

### 🧬 Post-Quantum Validation Engine
- Latest NIST standards (FIPS 203, FIPS 204)
- Detect ML-KEM, ML-DSA, SPHINCS+ support
- Hybrid TLS detection (ECDHE + ML-KEM)
- Quantum-risk classification logic
- Harvest-now-decrypt-later vulnerability assessment
- Automatic downgrade attack detection

### 📜 CBOM Generator
- Machine-readable Cryptographic Bill of Materials
- Formats: JSON, JWS (signed), PDF, CSV
- Compliance mapping to NIST/ISO standards
- Automatic remediation recommendations
- QR code verification

### 🏷️ Quantum-Safe Certificate Engine
- Issue unique, digitally signed certificates
- Two certification levels:
  - **Fully Quantum Safe**: Using NIST PQC algorithms
  - **PQC Ready**: Modern classical crypto, upgrade path clear
- QR-verifiable badge for website embedding
- Third-party verification endpoints
- Tamper-proof digital signatures

### 📊 Enterprise Dashboard
- Real-time asset inventory view
- Cryptographic heatmap visualization
- PQC readiness breakdown
- Risk score trends
- Compliance gap analysis
- Expiring certificate tracking
- Role-based access control
- Dark mode support

### 🛡️ Compliance Mapping
- NIST SP 800-208 (PQC Migration)
- NIST SP 800-52 Rev 1 (TLS Guidelines)
- ISO/IEC 27001:2022
- RBI Cyber Security Framework
- Automated remediation guidance
- Control-to-control mapping

### 🔒 Security Features
- JWT authentication with RS256
- Role-Based Access Control (RBAC)
- Full audit logging with integrity hashing
- Encrypted database at rest
- TLS for all internal services
- Input validation and rate limiting
- Tamper-proof audit trails

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Q-Shield Platform                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           REST API (FastAPI)                         │   │
│  │  /assets  /scans  /cbom  /certificates  /compliance  │   │
│  └──────────────────────────────────────────────────────┘   │
│                          ▲                                    │
│                          │ HTTP/HTTPS                        │
│  ┌──────────────────────┴───────────────────────────────┐   │
│  │                                                        │   │
│  │   ┌──────────────┐    ┌──────────────┐              │   │
│  │   │ Asset        │    │ Crypto TLS   │              │   │
│  │   │ Discovery    │    │ Fingerprint  │              │   │
│  │   │ Engine       │    │ Engine       │              │   │
│  │   └──────────────┘    └──────────────┘              │   │
│  │                                                        │   │
│  │   ┌──────────────┐    ┌──────────────┐              │   │
│  │   │ PQC          │    │ Risk         │              │   │
│  │   │ Validator    │    │ Scoring      │              │   │
│  │   │ Engine       │    │ Engine       │              │   │
│  │   └──────────────┘    └──────────────┘              │   │
│  │                                                        │   │
│  │   ┌──────────────┐    ┌──────────────┐              │   │
│  │   │ CBOM         │    │ Quantum-Safe │              │   │
│  │   │ Generator    │    │ Certificate  │              │   │
│  │   │              │    │ Engine       │              │   │
│  │   └──────────────┘    └──────────────┘              │   │
│  │                                                        │   │
│  │   ┌──────────────┐    ┌──────────────┐              │   │
│  │   │ Compliance   │    │ Audit &      │              │   │
│  │   │ Mapping      │    │ Logging      │              │   │
│  │   │ Engine       │    │ System       │              │   │
│  │   └──────────────┘    └──────────────┘              │   │
│  │                                                        │   │
│  └────────────────────┬─────────────────────────────────┘   │
│                       │                                      │
│  ┌────────────────────▼────────────────────┐               │
│  │  PostgreSQL Database (Assets, Scans)    │               │
│  │  Redis Cache (Sessions, Queue)          │               │
│  └─────────────────────────────────────────┘               │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- PostgreSQL 14+
- Python 3.11+
- OpenSSL & Nmap

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/q-shield.git
cd q-shield
```

2. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your settings
```

3. **Generate cryptographic keys**
```bash
./scripts/generate_keys.sh
```

4. **Start with Docker Compose**
```bash
docker-compose up -d
```

5. **Initialize database**
```bash
curl -X POST http://localhost:8000/api/v1/init
```

6. **Access the application**
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Dashboard**: http://localhost:3000
- **Grafana**: http://localhost:3000

### Local Development

```bash
# Install dependencies
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://user:password@localhost:5432/qshield"
export REDIS_URL="redis://localhost:6379/0"

# Run API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# In another terminal, start React dashboard
cd ../frontend
npm install
npm start
```

## 📖 Usage

### 1. Discover Assets
```bash
curl -X POST http://localhost:8000/api/v1/assets \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "bank.example.com",
    "port": 443,
    "asset_type": "web_server"
  }'
```

### 2. Initiate Scan
```bash
curl -X POST http://localhost:8000/api/v1/scans \
  -H "Content-Type: application/json" \
  -d '{
    "scan_type": "full",
    "targets": ["bank.example.com:443", "api.bank.example.com:443"]
  }'
```

### 3. Get PQC Assessment
```bash
curl http://localhost:8000/api/v1/assess/crypto?hostname=bank.example.com&port=443
```

### 4. Generate CBOM
```bash
curl -X POST http://localhost:8000/api/v1/cbom/generate \
  -H "Content-Type: application/json" \
  -d '{
    "format": "json",
    "asset_ids": [1, 2, 3],
    "organization": "Example Bank"
  }'
```

### 5. Issue Certificate
```bash
curl -X POST http://localhost:8000/api/v1/certificates/issue \
  -H "Content-Type: application/json" \
  -d '{"asset_id": 1}'
```

### 6. Check Compliance
```bash
curl -X POST http://localhost:8000/api/v1/compliance/check \
  -H "Content-Type: application/json" \
  -d '{
    "asset_id": 1,
    "frameworks": ["nist_sp_800_208", "nist_sp_800_52"]
  }'
```

## 📊 API Endpoints

### Assets
- `GET /api/v1/assets` - List assets
- `POST /api/v1/assets` - Create asset
- `GET /api/v1/assets/{id}` - Get asset details

### Scanning
- `POST /api/v1/scans` - Initiate scan
- `GET /api/v1/scans/{id}` - Get scan status
- `GET /api/v1/scans/{id}/results` - Get scan results

### Assessment
- `POST /api/v1/assess/crypto` - Assess crypto configuration
- `POST /api/v1/assess/pqc` - PQC readiness assessment
- `POST /api/v1/assess/compliance` - Compliance assessment

### CBOM
- `POST /api/v1/cbom/generate` - Generate CBOM
- `GET /api/v1/cbom/{id}` - Get CBOM
- `GET /api/v1/cbom/{id}/download` - Download CBOM

### Certificates
- `POST /api/v1/certificates/issue` - Issue certificate
- `GET /api/v1/certificates/{id}` - Get certificate
- `GET /api/v1/certificates/{id}/verify` - Verify certificate

### Compliance
- `POST /api/v1/compliance/check` - Check compliance
- `GET /api/v1/compliance/reports` - List reports
- `GET /api/v1/compliance/frameworks` - List frameworks

## 🧪 Testing

```bash
# Run unit tests
pytest tests/unit -v

# Run integration tests
pytest tests/integration -v

# Coverage report
pytest --cov=app tests/

# Run with Docker
docker-compose exec api pytest tests/
```

## 📚 Documentation

- [API Documentation](docs/API.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Security Hardening](docs/SECURITY.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Developer Guide](docs/DEVELOPER.md)

## 🔐 Security

- **No hardcoded credentials**: All secrets in environment variables
- **No mock data**: Real TLS handshakes, actual scanning
- **Tamper-proof logging**: Integrity hashing for audit trail
- **Encrypted at rest**: Database encryption, key management
- **Zero-trust**: All internal APIs require authentication

## 📋 Regulatory Standards

- **NIST SP 800-208**: Post-Quantum Cryptography Migration
- **NIST SP 800-52 Rev 1**: TLS Recommendations
- **ISO/IEC 27001:2022**: Information Security
- **RBI Cyber Security Framework**: Indian Banking Regulations

## 🤝 Contributing

Contributions welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md)

## 📜 License

Proprietary - Copyright 2024 Q-Shield Inc.

## 🙌 Support

- **Security Issues**: security@qshield.io
- **Support**: support@qshield.io
- **Documentation**: https://docs.qshield.io

## 🚨 Important Notes

1. **Production Deployment**: 
   - Change all default credentials
   - Generate strong SECRET_KEY (32+ chars)
   - Use HTTPS for all traffic
   - Enable database encryption
   - Configure regular backups

2. **Scanning Scope**:
   - Only scan assets you own or have permission to test
   - Respect rate limits and network policies
   - Use in compliance with all applicable laws

3. **Data Handling**:
   - Sensitive cryptographic data is processed
   - Implement appropriate access controls
   - Follow your organization's data retention policies

---

Made with ❤️ for Post-Quantum Cryptography Readiness

**Q-Shield: Cryptographic Intelligence for a Quantum-Safe Future**
