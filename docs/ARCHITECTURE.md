# Q-Shield Architecture Guide

Technical architecture documentation for Q-Shield cryptographic intelligence platform, including system design, component interactions, data flow, and scalability considerations.

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Component Architecture](#component-architecture)
3. [Data Flow](#data-flow)
4. [Technology Stack](#technology-stack)
5. [Database Schema](#database-schema)
6. [API Design](#api-design)
7. [Scalability](#scalability)
8. [Deployment Topology](#deployment-topology)

---

## Architecture Overview

### High-Level System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      Client Applications                         │
│  (Dashboard, CLI, Third-Party Integrations)                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │   API Gateway   │
                    │   (Ingress)     │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
    ┌───▼────┐          ┌───▼────┐          ┌───▼────┐
    │ Auth   │          │ Assets │          │ Scans  │
    │Service │          │Service │          │Service │
    └────┬───┘          └────┬───┘          └────┬───┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
    ┌───▼──────────┐  ┌─────▼──────┐  ┌──────────▼───┐
    │    TLS       │  │     PQC    │  │    Risk      │
    │  Fingerprint │  │  Validator │  │   Scorer     │
    └───┬──────────┘  └──────┬─────┘  └──────┬───────┘
        │                    │                │
        └────────────────────┼────────────────┘
                             │
        ┌────────────────────┼────────────────┐
        │                    │                │
    ┌───▼────────┐   ┌──────▼──────┐   ┌────▼─────────┐
    │    CBOM    │   │Certificate  │   │  Compliance  │
    │ Generator  │   │   Engine    │   │  Mapper      │
    └───┬────────┘   └──────┬──────┘   └────┬─────────┘
        │                   │               │
        └───────────────────┼───────────────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
        ┌───▼────┐      ┌───▼────┐     ┌──▼────┐
        │         │      │        │     │       │
     PostgreSQL  Redis  Prometheus Grafana Kibana
       (Data)    (Cache) (Metrics) (Dash) (Logs)
```

### Architectural Principles

1. **Microservices**: Independent scanning engines with single responsibilities
2. **Async-First**: All I/O operations non-blocking using asyncio
3. **Separation of Concerns**: Schemas → Models → Services → API layers
4. **Configuration-Driven**: Zero hardcoded values, environment-based
5. **Real Scanning**: Actual TLS handshakes, no mock data
6. **Stateless API**: Easily scalable horizontally
7. **Event-Driven**: Background jobs for long-running scans
8. **Audit Trail**: Comprehensive logging of all security events

---

## Component Architecture

### 1. Authentication Service

**Responsibility**: User authentication, authorization, token management

**Components**:
- `User` model: User accounts, roles, MFA
- `Organization` model: Multi-tenancy support
- JWT token generation and validation
- Password hashing (bcrypt)
- API key management

**Endpoints**:
```
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
POST   /api/v1/auth/logout
PUT    /api/v1/auth/change-password
POST   /api/v1/auth/mfa/enable
```

**Key Files**:
- `app/schemas/schemas.py`: Authentication models
- `app/core/security.py`: Token and password logic

### 2. Asset Management Service

**Responsibility**: Inventory and management of cryptographic assets

**Data Model**:
- `Asset`: A network endpoint with TLS/crypto configuration
- `ScanResult`: Result of scanning an asset
- `Organization`: Assets belong to organizations

**Endpoints**:
```
GET    /api/v1/assets
POST   /api/v1/assets
GET    /api/v1/assets/{asset_id}
PUT    /api/v1/assets/{asset_id}
DELETE /api/v1/assets/{asset_id}
GET    /api/v1/assets/{asset_id}/scan-history
```

**Key Attributes**:
- Hostname, IP, port
- Last scan timestamp
- Current PQC readiness level
- Risk score
- Asset classification

### 3. TLS Fingerprinting Engine

**Responsibility**: Real TLS handshake scanning and configuration extraction

**File**: `app/services/discovery/tls_fingerprint.py` (767 lines)

**Methods**:
```python
scan(hostname, port) -> TLSConfiguration
  - Initiates TLS handshake
  - Extracts supported versions
  - Enumerates cipher suites
  - Parses certificate
  - Checks security headers (HSTS, OCSP)

batch_fingerprint(targets) -> List[TLSConfiguration]
  - Parallelizes scanning
  - Handles timeouts
  - Aggregates results
```

**Output**:
```json
{
  "hostname": "api.example.com",
  "tls_version": "1.3",
  "supported_versions": ["TLS 1.3", "TLS 1.2"],
  "cipher_suites": [
    "TLS_AES_256_GCM_SHA384",
    "TLS_CHACHA20_POLY1305_SHA256"
  ],
  "certificate": {
    "subject": "CN=api.example.com",
    "issuer": "CN=Let's Encrypt Authority X3",
    "key_size": 2048,
    "signature_algorithm": "sha256WithRSAEncryption",
    "validity": {
      "not_before": "2024-01-01T00:00:00Z",
      "not_after": "2024-04-01T00:00:00Z"
    }
  },
  "pfs_enabled": true,
  "ocsp_stapling": true,
  "hsts_header": "max-age=31536000; includeSubDomains"
}
```

### 4. PQC Validator Engine

**Responsibility**: NIST-compliant post-quantum cryptography assessment

**File**: `app/services/pqc/pqc_validator.py` (800+ lines)

**Methods**:
```python
assess_tls_configuration(tls_config) -> QuantumRiskAssessment
  - Detects PQC algorithms in cipher suites
  - Analyzes key exchange mechanisms
  - Identifies quantum threats
  - Calculates readiness level
  - Generates remediation steps

detect_pqc_algorithms() -> List[PQCAlgorithm]
  - Identifies ML-KEM, ML-DSA, SLH-DSA
  - Detects legacy PQC (Kyber, Dilithium, FALCON)
  - Confirms hybrid TLS support
```

**Supported Algorithms**:
```python
ML-KEM-512/768/1024  # NIST-standardized KEM
ML-DSA-44/65/87      # NIST-standardized signature
SLH-DSA-128s/f       # Stateless hash-based signature
Kyber-512/768/1024   # Legacy KEM (being standardized)
Dilithium-2/3/5      # Legacy signature
FALCON-512/1024      # Lattice signature
SPHINCS+-128/192/256 # Hash-based signature
```

**Readiness Levels**:
1. **FULLY_QUANTUM_SAFE**: Uses NIST-standardized PQC algorithms
2. **PQC_READY**: Hybrid TLS with PQC support
3. **TRANSITIONAL**: Strong classical crypto, no PQC yet
4. **VULNERABLE**: Weak algorithms or missing security features

### 5. Risk Scoring Engine

**Responsibility**: Quantify cryptographic risk on 0-100 scale

**File**: `app/services/risk/risk_scoring.py` (700+ lines)

**Scoring Methodology**:
```
Total Score = Base (0) + Component Scores

Components (max 100):
├── TLS Version Score (max 40)
│   ├── SSL/TLS 1.0: -50 (penalizes)
│   ├── TLS 1.1: -30
│   ├── TLS 1.2: -15
│   └── TLS 1.3: 0 (no penalty)
├── Key Exchange Score (max 25)
│   ├── RSA-KE: -50
│   ├── Static ECDH/DH: -35
│   └── ECDHE/DHE: 0
├── Cipher Strength Score (max 20)
│   ├── RC4, DES: -60
│   ├── 3DES: -40
│   ├── AES-128: -10
│   └── AES-256: 0
├── Certificate Score (max 10)
│   ├── Expired: -60
│   ├── <30 days left: -30
│   ├── RSA <2048: -45
│   └── RSA ≥3072: 0
└── Quantum Readiness Score (max 5)
    ├── No PQC: -50
    ├── Legacy PQC: -20
    └── NIST PQC: 0
```

**Severity Mapping**:
```python
CRITICAL: 80-100   # Immediate action required
HIGH:     60-79    # Address within 30 days
MEDIUM:   40-59    # Address within 90 days
LOW:      20-39    # Monitor and plan
INFO:     0-19     # Informational
```

### 6. CBOM Generator

**Responsibility**: Generate machine-readable and signed cryptographic reports

**File**: `app/services/cbom/cbom_generator.py` (700+ lines)

**Export Formats**:

1. **JSON**: Structured, human and machine-readable
   ```json
   {
     "metadata": {
       "organization": "ACME Corp",
       "generated_at": "2024-01-10T10:50:00Z",
       "version": "1.0"
     },
     "executive_summary": "...",
     "statistics": {
       "total_assets": 100,
       "quantum_safe": 45,
       "quantum_ready": 30,
       "vulnerable": 25
     },
     "assets": [...]
   }
   ```

2. **JWS**: JSON Web Signature (RSA-PSS-SHA384)
   ```
   eyJhbGciOiJQUzM4NCJ9.{payload}.{signature}
   ```

3. **PDF**: Executive report with charts
   - Statistics graphs
   - Asset-by-asset table
   - Remediation recommendations
   - QR code for verification

4. **CSV**: Spreadsheet format for analysis
   ```csv
   hostname,port,pqc_readiness,risk_score,tls_version
   api.example.com,443,PQC_READY,35,1.3
   ```

### 7. Quantum-Safe Certificate Engine

**Responsibility**: Issue verifiable PQC readiness certificates

**File**: `app/services/certificate/certificate_engine.py` (600+ lines)

**Certificate Data**:
```python
{
  "certificate_id": "cert-001",
  "hostname": "api.example.com",
  "port": 443,
  "level": "PQC_READY",
  "issued_at": "2024-01-10T11:00:00Z",
  "expires_at": "2025-01-10T11:00:00Z",
  "signature": "base64-encoded-rsa-pss-sha384-signature",
  "qr_code": "base64-encoded-png"
}
```

**Features**:
- Digital signature (RSA-PSS-SHA384)
- QR code for mobile verification
- Embeddable HTML badge
- SVG badge for web embeds
- HTML report with verification URL

### 8. Compliance Mapper

**Responsibility**: Map findings to regulatory frameworks

**File**: `app/services/compliance/compliance_engine.py` (700+ lines)

**Supported Frameworks**:

1. **NIST SP 800-208**: PQC migration guidance
   - Controls: PQC-1 through PQC-4
   - Assessment: Algorithm selection, hybrid support

2. **NIST SP 800-52 Rev 1**: TLS guidelines
   - Controls: TLS-1 through TLS-5
   - Assessment: Version, ciphers, certificates

3. **ISO/IEC 27001:2022**: Information security
   - Controls: A.5 through A.15
   - Assessment: Policy, implementation, audit

4. **RBI Cyber Security Framework**: Indian banking
   - Controls: CS-1 through CS-7
   - Assessment: Encryption, key management, incident response

**Output**:
```python
{
  "framework": "NIST_SP_800_208",
  "status": "partial",  # compliant, partial, non-compliant
  "compliance_percentage": 75,
  "controls": [
    {
      "control_id": "PQC-1",
      "name": "Post-Quantum Algorithm Selection",
      "status": "compliant",
      "findings": []
    },
    {
      "control_id": "PQC-3",
      "name": "Legacy Algorithm Deprecation",
      "status": "non-compliant",
      "gaps": ["RSA-2048 keys still in use"],
      "remediation": "Migrate to RSA-4096 or EC"
    }
  ]
}
```

---

## Data Flow

### Asset Scanning Flow

```
1. User initiates scan
   POST /api/v1/scans
   {
     "name": "Weekly Security Scan",
     "targets": ["api.example.com:443"]
   }

2. Scan job created
   ├─ Create Scan record in DB
   ├─ Enqueue scan targets
   └─ Return scan_id to user

3. Background worker picks up scan
   ├─ Perform TLS fingerprint (TLSScanner)
   ├─ Extract certificate details
   └─ Collect TLS configuration

4. Results processed by engines
   ├─ PQC validation (Readiness level, threats)
   ├─ Risk scoring (0-100 score, severity)
   └─ Compliance assessment (Framework status)

5. Results stored in database
   ├─ Create ScanResult record
   ├─ Update Asset with new findings
   └─ Audit log entry created

6. User retrieves results
   GET /api/v1/scans/{scan_id}
   Returns: Status, progress, results
```

### CBOM Generation Flow

```
1. User requests CBOM
   POST /api/v1/cbom/generate
   {
     "asset_ids": ["asset-1", "asset-2"],
     "format": "pdf"
   }

2. Asset data retrieved
   ├─ Query Asset table
   ├─ Get latest ScanResult for each
   └─ Retrieve compliance findings

3. CBOM document generated
   ├─ Build metadata (org, timestamp)
   ├─ Calculate statistics
   ├─ Create executive summary
   └─ Compile per-asset details

4. Format-specific export
   ├─ If JSON: serialize to JSON
   ├─ If JWS: sign with RSA-PSS
   ├─ If PDF: render with ReportLab
   └─ If CSV: write to CSV

5. Return to user
   Response: CBOM document (bytes or JSON)
```

---

## Technology Stack

### Backend
- **Framework**: FastAPI 0.104.1 (async Python web framework)
- **Web Server**: Uvicorn 0.24.0 (ASGI server)
- **Database ORM**: SQLAlchemy 2.0 (async)
- **Database Driver**: asyncpg 0.29.0 (PostgreSQL)
- **Async HTTP**: aiohttp 3.9.1 (HTTP client)
- **Cryptography**: cryptography 41.0.7, pyOpenSSL 23.3.0
- **Authentication**: python-jose 3.3.0 (JWT)
- **Validation**: pydantic 2.5.0 (data validation)
- **Cache**: redis 5.0.1 (in-memory cache)
- **Task Queue**: APScheduler 3.10.4 (background jobs)
- **PDF Export**: reportlab 4.0.9
- **QR Codes**: qrcode 7.4.2, Pillow 10.1.0
- **Logging**: python-json-logger 2.0.7
- **Testing**: pytest 7.4.3, pytest-asyncio 0.21.1

### Frontend (To be implemented)
- **Framework**: React 18.2.0 (UI library)
- **Language**: TypeScript 5.3.3 (static typing)
- **Styling**: Tailwind CSS 3.4.1 (utility CSS)
- **State Management**: Redux Toolkit 1.9.7 (state)
- **HTTP Client**: Axios 1.6.2 (API communication)
- **Charts**: Chart.js 4.4.0 (data visualization)
- **Tables**: TanStack Table 8.10.3 (data tables)
- **Forms**: React Hook Form 7.48.0 (form handling)

### Infrastructure
- **Database**: PostgreSQL 16 (relational database)
- **Cache**: Redis 7 (in-memory data store)
- **Container**: Docker 24 (containerization)
- **Orchestration**: Docker Compose, Kubernetes
- **Monitoring**: Prometheus (metrics), Grafana (dashboards)
- **Logging**: Elasticsearch 8, Kibana 8 (log aggregation)
- **Security**: TLS 1.2+ (encryption in transit)

### Development Tools
- **Version Control:** Git
- **CI/CD**: GitHub Actions, GitLab CI, or Jenkins
- **Code Quality**: Black, Flake8, Pylint, MyPy
- **Testing**: pytest, pytest-cov
- **Documentation**: MkDocs, Sphinx

---

## Database Schema

### Core Tables

**users**
```sql
CREATE TABLE users (
  id UUID PRIMARY KEY,
  email VARCHAR UNIQUE NOT NULL,
  password_hash VARCHAR NOT NULL,
  full_name VARCHAR,
  organization_id UUID FOREIGN KEY,
  role VARCHAR (admin, analyst, viewer),
  mfa_enabled BOOLEAN,
  is_active BOOLEAN,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

**assets**
```sql
CREATE TABLE assets (
  id UUID PRIMARY KEY,
  organization_id UUID FOREIGN KEY,
  hostname VARCHAR NOT NULL,
  port INTEGER,
  ip_address INET,
  pqc_readiness VARCHAR (FULLY_QUANTUM_SAFE, PQC_READY, TRANSITIONAL, VULNERABLE),
  risk_score INTEGER,
  last_scanned TIMESTAMP,
  next_scan TIMESTAMP,
  created_at TIMESTAMP
);
```

**scan_results**
```sql
CREATE TABLE scan_results (
  id UUID PRIMARY KEY,
  asset_id UUID FOREIGN KEY,
  scan_id UUID FOREIGN KEY,
  tls_version VARCHAR,
  ciphers JSONB,
  certificate JSONB,
  pqc_assessment JSONB,
  risk_score_breakdown JSONB,
  compliance_findings JSONB,
  created_at TIMESTAMP
);
```

**quantum_safe_certificates**
```sql
CREATE TABLE quantum_safe_certificates (
  id UUID PRIMARY KEY,
  asset_id UUID FOREIGN KEY,
  hostname VARCHAR,
  port INTEGER,
  level VARCHAR (FULLY_QUANTUM_SAFE, PQC_READY),
  issued_at TIMESTAMP,
  expires_at TIMESTAMP,
  signature VARCHAR,
  created_at TIMESTAMP
);
```

**audit_logs**
```sql
CREATE TABLE audit_logs (
  id UUID PRIMARY KEY,
  user_id UUID FOREIGN KEY,
  action VARCHAR,
  resource_type VARCHAR,
  resource_id VARCHAR,
  changes JSONB,
  ip_address INET,
  user_agent VARCHAR,
  timestamp TIMESTAMP,
  integrity_hash VARCHAR
);
```

**Indexes**:
- `idx_assets_org_pqc`: assets(organization_id, pqc_readiness)
- `idx_scans_status`: scans(status, created_at)
- `idx_audit_user_date`: audit_logs(user_id, timestamp)
- `idx_certs_expiry`: quantum_safe_certificates(expires_at)

---

## API Design

### RESTful Conventions

```
GET    /api/v1/resources          # List (paginated)
POST   /api/v1/resources          # Create
GET    /api/v1/resources/{id}     # Retrieve
PUT    /api/v1/resources/{id}     # Update
DELETE /api/v1/resources/{id}     # Delete
```

### Request/Response Format

**Successful Response** (200, 201):
```json
{
  "status": "success",
  "data": { /* response data */ },
  "meta": {
    "timestamp": "2024-01-10T10:00:00Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

**Error Response** (400, 401, 500):
```json
{
  "status": "error",
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Invalid port number",
    "details": { /* field-specific errors */ }
  },
  "meta": {
    "timestamp": "2024-01-10T10:00:00Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### Pagination

```
GET /api/v1/assets?skip=0&limit=50

Response:
{
  "data": [...],
  "pagination": {
    "skip": 0,
    "limit": 50,
    "total": 1250,
    "has_next": true
  }
}
```

---

## Scalability

### Horizontal Scaling

**Stateless API**:
- No session state on API servers
- JWT tokens contain all authentication info
- Can scale API replicas independently

**Load Balancing**:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: qshield-api
spec:
  selector:
    app: qshield-api
  type: LoadBalancer
  ports:
  - port: 8000
    targetPort: 8000
```

**Auto-Scaling**:
```yaml
kind: HorizontalPodAutoscaler
metadata:
  name: qshield-api-hpa
spec:
  scaleTargetRef:
    kind: Deployment
    name: qshield-api
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
```

### Database Scaling

**Connection Pooling**:
```python
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    poolclass=AsyncNullPool,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
)
```

**Read Replicas**:
- PostgreSQL streaming replication
- Route read-only queries to replicas
- Offload analytics to separate database

**Data Partitioning**:
- Partition `scan_results` by date
- Partition `audit_logs` by organization
- Archive old data to cold storage

### Caching Strategy

**Cache Layers**:
```
Client Requests
    ↓
API Server (in-memory cache)
    ↓
Redis (distributed cache)
    ↓
PostgreSQL (persistent storage)
```

**Cache Keys**:
```python
{
  "asset:{asset_id}": 3600,           # 1 hour
  "scan_result:{scan_id}": 7200,      # 2 hours
  "compliance:{framework}": 86400,    # 24 hours
  "user_permission:{user_id}": 1800   # 30 min
}
```

### Performance Targets

- API Response Time: <200ms (p95)
- TLS Fingerprint Duration: <5s per target
- CBOM Generation: <10s for 1000 assets
- Database Queries: <50ms (p95)
- Cache Hit Rate: >80%

---

## Deployment Topology

### Development

```
Local Machine
├── PostgreSQL (local)
├── Redis (local)
├── Q-Shield API (localhost:8000)
└── Hot reload via uvicorn --reload
```

### Production (Docker Compose)

```
Docker Host
├── qshield-api (port 8000)
├── postgres (port 5432)
├── redis (port 6379)
├── prometheus (port 9090)
├── grafana (port 3000)
├── elasticsearch (port 9200)
└── kibana (port 5601)
```

### Cloud (Kubernetes)

```
K8s Cluster
├── qshield-api (3-10 replicas)
├── postgres (1 master, 2 replicas)
├── redis (cluster mode)
├── prometheus (stateful)
├── grafana (stateless)
├── elasticsearch (cluster)
└── Ingress Controller
```

---

For deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md).
For security hardening, see [SECURITY.md](SECURITY.md).
For API reference, see [API.md](API.md).
