# Q-Shield API Usage Guide

Complete reference for Q-Shield REST API endpoints with examples, request/response formats, and error handling.

## Table of Contents
1. [Authentication](#authentication)
2. [Assets Management](#assets-management)
3. [Scanning](#scanning)
4. [Assessment](#assessment)
5. [CBOM Generation](#cbom-generation)
6. [Certificates](#certificates)
7. [Compliance Checking](#compliance-checking)
8. [Error Handling](#error-handling)
9. [Rate Limiting](#rate-limiting)

---

## Authentication

All API endpoints (except `/health`) require JWT authentication.

### 1. Register User
Create a new user account.

**Endpoint**: `POST /api/v1/auth/register`

**Request**:
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "full_name": "John Doe"
}
```

**Response** (201):
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "full_name": "John Doe",
  "organization_id": "org-123",
  "created_at": "2024-01-10T10:00:00Z"
}
```

**cURL**:
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePassword123!",
    "full_name": "John Doe"
  }'
```

### 2. Login
Obtain JWT access token.

**Endpoint**: `POST /api/v1/auth/login`

**Request**:
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Response** (200):
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**cURL**:
```bash
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePassword123!"
  }' | jq -r '.access_token')

echo $TOKEN
```

### 3. Refresh Token
Extend session without re-logging in.

**Endpoint**: `POST /api/v1/auth/refresh`

**Headers**:
```
Authorization: Bearer <access_token>
```

**Response** (200):
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 1800
}
```

**cURL**:
```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Authorization: Bearer $TOKEN"
```

---

## Assets Management

### 1. List Assets
Retrieve all assets in your organization with optional filtering.

**Endpoint**: `GET /api/v1/assets`

**Query Parameters**:
- `skip` (int, default: 0) - Pagination offset
- `limit` (int, default: 50) - Results per page
- `pqc_readiness` (string) - Filter by: VULNERABLE, TRANSITIONAL, PQC_READY, FULLY_QUANTUM_SAFE
- `risk_level` (string) - Filter by: CRITICAL, HIGH, MEDIUM, LOW, INFO
- `search` (string) - Search by hostname or IP

**Response** (200):
```json
{
  "assets": [
    {
      "asset_id": "asset-123",
      "hostname": "api.example.com",
      "port": 443,
      "ip_address": "203.0.113.1",
      "pqc_readiness": "PQC_READY",
      "risk_score": 35,
      "last_scanned": "2024-01-10T09:30:00Z",
      "next_scan": "2024-01-17T09:30:00Z",
      "organization_id": "org-123"
    },
    {
      "asset_id": "asset-124",
      "hostname": "db.example.com",
      "port": 443,
      "ip_address": "203.0.113.2",
      "pqc_readiness": "VULNERABLE",
      "risk_score": 78,
      "last_scanned": "2024-01-09T14:20:00Z",
      "next_scan": "2024-01-16T14:20:00Z",
      "organization_id": "org-123"
    }
  ],
  "total": 2,
  "skip": 0,
  "limit": 50
}
```

**cURL**:
```bash
# List all assets
curl http://localhost:8000/api/v1/assets \
  -H "Authorization: Bearer $TOKEN"

# Filter by PQC readiness
curl "http://localhost:8000/api/v1/assets?pqc_readiness=VULNERABLE" \
  -H "Authorization: Bearer $TOKEN"

# Search and paginate
curl "http://localhost:8000/api/v1/assets?search=example.com&limit=10&skip=0" \
  -H "Authorization: Bearer $TOKEN"
```

### 2. Create Asset
Register a new asset for scanning.

**Endpoint**: `POST /api/v1/assets`

**Request**:
```json
{
  "hostname": "new-api.example.com",
  "port": 443,
  "ip_address": "203.0.113.3",
  "description": "Production API server",
  "asset_type": "web_service",
  "owner_email": "owner@example.com"
}
```

**Response** (201):
```json
{
  "asset_id": "asset-125",
  "hostname": "new-api.example.com",
  "port": 443,
  "ip_address": "203.0.113.3",
  "pqc_readiness": "UNKNOWN",
  "risk_score": null,
  "last_scanned": null,
  "next_scan": null,
  "organization_id": "org-123"
}
```

**cURL**:
```bash
curl -X POST http://localhost:8000/api/v1/assets \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "new-api.example.com",
    "port": 443,
    "ip_address": "203.0.113.3",
    "description": "Production API server",
    "asset_type": "web_service",
    "owner_email": "owner@example.com"
  }'
```

### 3. Get Asset Details
Retrieve detailed information about a specific asset.

**Endpoint**: `GET /api/v1/assets/{asset_id}`

**Response** (200):
```json
{
  "asset_id": "asset-123",
  "hostname": "api.example.com",
  "port": 443,
  "ip_address": "203.0.113.1",
  "pqc_readiness": "PQC_READY",
  "risk_score": 35,
  "risk_severity": "MEDIUM",
  "last_scanned": "2024-01-10T09:30:00Z",
  "next_scan": "2024-01-17T09:30:00Z",
  "scan_count": 5,
  "latest_scan_result": {
    "scan_id": "scan-456",
    "tls_version": "1.3",
    "cipher_suites": [
      "TLS_AES_256_GCM_SHA384",
      "TLS_CHACHA20_POLY1305_SHA256"
    ],
    "certificate_info": {
      "subject": "CN=api.example.com",
      "issuer": "CN=Let's Encrypt Authority X3",
      "validity_start": "2024-01-01T00:00:00Z",
      "validity_end": "2024-04-01T00:00:00Z",
      "key_size": 2048,
      "signature_algorithm": "sha256WithRSAEncryption"
    },
    "pqc_assessment": {
      "readiness_level": "PQC_READY",
      "quantum_threats": [
        {
          "threat_id": "harvest-now-decrypt-later",
          "severity": "HIGH",
          "description": "RSA 2048-bit keys vulnerable to quantum decryption",
          "timeline_years": 15
        }
      ],
      "remediation_steps": [
        {
          "priority": "HIGH",
          "action": "Migrate to RSA-4096 or elliptic curve keys",
          "timeline": "Within 6 months"
        }
      ]
    },
    "risk_score_breakdown": {
      "total_score": 35,
      "severity": "MEDIUM",
      "tls_score": 10,
      "cipher_score": 5,
      "certificate_score": 15,
      "quantum_score": 30
    }
  }
}
```

**cURL**:
```bash
curl http://localhost:8000/api/v1/assets/asset-123 \
  -H "Authorization: Bearer $TOKEN"
```

### 4. Update Asset
Modify asset information.

**Endpoint**: `PUT /api/v1/assets/{asset_id}`

**Request**:
```json
{
  "description": "Updated production API server",
  "owner_email": "new-owner@example.com"
}
```

**Response** (200):
```json
{
  "asset_id": "asset-123",
  "hostname": "api.example.com",
  "port": 443,
  "description": "Updated production API server",
  "owner_email": "new-owner@example.com"
}
```

### 5. Delete Asset
Remove an asset from monitoring.

**Endpoint**: `DELETE /api/v1/assets/{asset_id}`

**Response** (204): No content

---

## Scanning

### 1. Initiate Scan
Start a new cryptographic scan on assets.

**Endpoint**: `POST /api/v1/scans`

**Request**:
```json
{
  "name": "Weekly Security Scan",
  "description": "Regular PQC readiness assessment",
  "scan_type": "full",
  "targets": [
    "api.example.com:443",
    "db.example.com:5432"
  ],
  "options": {
    "check_certificate": true,
    "check_pqc": true,
    "check_compliance": true,
    "timeout_seconds": 30
  }
}
```

**Scan Types**:
- `full` - Complete cryptographic assessment
- `tls_fingerprint` - TLS configuration only
- `pqc_assessment` - PQC readiness only
- `compliance_check` - Regulatory compliance only

**Response** (202):
```json
{
  "scan_id": "scan-789",
  "name": "Weekly Security Scan",
  "scan_type": "full",
  "status": "pending",
  "targets": [
    "api.example.com:443",
    "db.example.com:5432"
  ],
  "progress": {
    "total": 2,
    "completed": 0,
    "in_progress": 0,
    "failed": 0
  },
  "started_at": "2024-01-10T10:30:00Z",
  "estimated_completion": "2024-01-10T10:45:00Z",
  "organization_id": "org-123"
}
```

**cURL**:
```bash
SCAN_ID=$(curl -X POST http://localhost:8000/api/v1/scans \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Quick Scan",
    "scan_type": "full",
    "targets": ["api.example.com:443"]
  }' | jq -r '.scan_id')

echo $SCAN_ID
```

### 2. Get Scan Status
Monitor scan progress and results.

**Endpoint**: `GET /api/v1/scans/{scan_id}`

**Response** (200):
```json
{
  "scan_id": "scan-789",
  "status": "in_progress",
  "progress": {
    "total": 2,
    "completed": 1,
    "in_progress": 1,
    "failed": 0
  },
  "started_at": "2024-01-10T10:30:00Z",
  "estimated_completion": "2024-01-10T10:40:00Z",
  "results": [
    {
      "target": "api.example.com:443",
      "status": "completed",
      "pqc_readiness": "PQC_READY",
      "risk_score": 35,
      "tls_version": "1.3",
      "completed_at": "2024-01-10T10:32:00Z"
    },
    {
      "target": "db.example.com:5432",
      "status": "in_progress",
      "pqc_readiness": null,
      "risk_score": null,
      "started_at": "2024-01-10T10:33:00Z"
    }
  ]
}
```

**cURL**:
```bash
# Check scan status
curl http://localhost:8000/api/v1/scans/$SCAN_ID \
  -H "Authorization: Bearer $TOKEN"

# Poll until completion
while true; do
  STATUS=$(curl -s http://localhost:8000/api/v1/scans/$SCAN_ID \
    -H "Authorization: Bearer $TOKEN" | jq -r '.status')
  
  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
    break
  fi
  
  echo "Status: $STATUS - waiting..."
  sleep 5
done
```

### 3. List Scans
View all scans in your organization.

**Endpoint**: `GET /api/v1/scans`

**Query Parameters**:
- `skip` (int, default: 0)
- `limit` (int, default: 50)
- `status` (string) - Filter by: pending, in_progress, completed, failed
- `scan_type` (string) - Filter by type

**Response** (200):
```json
{
  "scans": [
    {
      "scan_id": "scan-789",
      "name": "Weekly Security Scan",
      "status": "completed",
      "scan_type": "full",
      "target_count": 2,
      "completed_at": "2024-01-10T10:45:00Z"
    }
  ],
  "total": 1
}
```

---

## Assessment

### Single Endpoint Assessment
Perform cryptographic assessment on a single endpoint without creating a formal scan.

**Endpoint**: `POST /api/v1/assess/crypto`

**Request**:
```json
{
  "hostname": "example.com",
  "port": 443,
  "protocol": "tls"
}
```

**Response** (200):
```json
{
  "hostname": "example.com",
  "port": 443,
  "assessment": {
    "tls_config": {
      "tls_version": "1.3",
      "supported_versions": [
        "TLS 1.3",
        "TLS 1.2"
      ],
      "cipher_suites": [
        "TLS_AES_256_GCM_SHA384",
        "TLS_CHACHA20_POLY1305_SHA256",
        "TLS_AES_128_GCM_SHA256"
      ],
      "pfs_enabled": true,
      "ocsp_stapling": true,
      "hsts_header": "max-age=31536000; includeSubDomains"
    },
    "pqc_assessment": {
      "readiness_level": "PQC_READY",
      "quantum_threats": [
        {
          "threat_id": "rsa-2048-key",
          "severity": "HIGH",
          "timeline_years": 15
        }
      ]
    },
    "risk_score": 35,
    "risk_severity": "MEDIUM",
    "compliance_status": {
      "nist_800_208": "partial",
      "nist_800_52": "compliant",
      "iso_27001": "compliant",
      "rbi_csf": "partial"
    }
  }
}
```

**cURL**:
```bash
curl -X POST http://localhost:8000/api/v1/assess/crypto \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "example.com",
    "port": 443
  }'
```

---

## CBOM Generation

### Generate Cryptographic Bill of Materials
Create a structured report of all cryptographic assets.

**Endpoint**: `POST /api/v1/cbom/generate`

**Request**:
```json
{
  "format": "json",
  "asset_ids": ["asset-123", "asset-124"],
  "organization": "ACME Corp",
  "scan_period_days": 30,
  "include_remediation": true
}
```

**Formats**:
- `json` - Human and machine readable JSON
- `jws` - Digitally signed JSON (RSA-PSS-SHA384)
- `pdf` - Executive report with graphics
- `csv` - Spreadsheet format

**Response** (200):
```json
{
  "cbom_id": "cbom-001",
  "format": "json",
  "generated_at": "2024-01-10T10:50:00Z",
  "total_assets": 2,
  "assets_quantum_safe": 1,
  "critical_issues": 1,
  "cbom": {
    "metadata": {
      "organization": "ACME Corp",
      "generated_at": "2024-01-10T10:50:00Z",
      "scan_period": 30
    },
    "executive_summary": "1 of 2 assets (50%) are quantum-safe. 1 critical issue requires immediate attention.",
    "statistics": {
      "total_assets": 2,
      "quantum_safe": 1,
      "quantum_ready": 0,
      "vulnerable": 1,
      "avg_risk_score": 56.5,
      "compliance_rate": 66.7
    },
    "assets": [
      {
        "hostname": "api.example.com",
        "port": 443,
        "pqc_readiness": "PQC_READY",
        "risk_score": 35,
        "tls_version": "1.3",
        "certificate_expiry": "2024-04-01T00:00:00Z"
      }
    ]
  }
}
```

**cURL**:
```bash
# Generate JSON CBOM
curl -X POST http://localhost:8000/api/v1/cbom/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "format": "json",
    "asset_ids": ["asset-123", "asset-124"],
    "organization": "ACME Corp"
  }' > cbom.json

# Generate PDF CBOM (save as binary)
curl -X POST http://localhost:8000/api/v1/cbom/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "format": "pdf",
    "asset_ids": ["asset-123", "asset-124"]
  }' --output cbom.pdf

# Generate signed JWS
curl -X POST http://localhost:8000/api/v1/cbom/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "format": "jws",
    "asset_ids": ["asset-123", "asset-124"]
  }' > cbom.jws
```

---

## Certificates

### Issue Quantum-Safe Certificate
Create a verifiable certificate for a PQC-ready asset.

**Endpoint**: `POST /api/v1/certificates/issue`

**Request**:
```json
{
  "asset_id": "asset-123",
  "certification_level": "PQC_READY",
  "validity_days": 365,
  "include_badge": true
}
```

**Response** (201):
```json
{
  "certificate_id": "cert-001",
  "hostname": "api.example.com",
  "port": 443,
  "level": "PQC_READY",
  "issued_at": "2024-01-10T11:00:00Z",
  "expires_at": "2025-01-10T11:00:00Z",
  "verification_url": "https://q-shield.example.com/verify/cert-001",
  "badge_html": "<img src='https://q-shield.example.com/badge/cert-001.svg' alt='PQC Ready'/>",
  "badge_svg_url": "https://q-shield.example.com/badge/cert-001.svg"
}
```

**cURL**:
```bash
curl -X POST http://localhost:8000/api/v1/certificates/issue \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "asset_id": "asset-123",
    "certification_level": "PQC_READY",
    "validity_days": 365
  }'
```

### Get Certificate Details
Retrieve certificate details and HTML report.

**Endpoint**: `GET /api/v1/certificates/{certificate_id}`

**Response** (200):
```json
{
  "certificate_id": "cert-001",
  "hostname": "api.example.com",
  "port": 443,
  "level": "PQC_READY",
  "issued_at": "2024-01-10T11:00:00Z",
  "expires_at": "2025-01-10T11:00:00Z",
  "issuer": "Q-Shield Certificate Authority",
  "verification_status": "valid",
  "html_report_url": "https://q-shield.example.com/certificates/cert-001/report.html"
}
```

### Verify Certificate
Verify a certificate without authentication (public endpoint).

**Endpoint**: `GET /api/v1/certificates/{certificate_id}/verify`

**Response** (200):
```json
{
  "valid": true,
  "certificate_id": "cert-001",
  "hostname": "api.example.com",
  "level": "PQC_READY",
  "issued_at": "2024-01-10T11:00:00Z",
  "expires_at": "2025-01-10T11:00:00Z",
  "expired": false
}
```

**cURL**:
```bash
# Public verification (no auth required)
curl https://q-shield.example.com/api/v1/certificates/cert-001/verify
```

---

## Compliance Checking

### Assess Compliance
Evaluate assets against regulatory frameworks.

**Endpoint**: `POST /api/v1/compliance/check`

**Request**:
```json
{
  "asset_ids": ["asset-123", "asset-124"],
  "frameworks": [
    "NIST_SP_800_208",
    "NIST_SP_800_52",
    "ISO_27001",
    "RBI_CSF"
  ]
}
```

**Response** (200):
```json
{
  "assessment_id": "compliance-001",
  "generated_at": "2024-01-10T11:10:00Z",
  "frameworks": {
    "NIST_SP_800_208": {
      "status": "partial",
      "compliance_percentage": 75,
      "controls": [
        {
          "control_id": "PQC-1",
          "name": "Post-Quantum Algorithm Selection",
          "status": "compliant",
          "description": "Asset supports PQC-enabled TLS"
        },
        {
          "control_id": "PQC-3",
          "name": "Legacy Algorithm Deprecation",
          "status": "non-compliant",
          "gap": "RSA-2048 keys still in use",
          "remediation": "Migrate to RSA-4096 or elliptic curve"
        }
      ]
    },
    "NIST_SP_800_52": {
      "status": "compliant",
      "compliance_percentage": 100,
      "controls": [
        {
          "control_id": "TLS-1",
          "name": "TLS Version",
          "status": "compliant"
        }
      ]
    },
    "ISO_27001": {
      "status": "compliant",
      "compliance_percentage": 95
    },
    "RBI_CSF": {
      "status": "partial",
      "compliance_percentage": 80
    }
  },
  "summary": {
    "compliant_frameworks": 2,
    "partial_frameworks": 2,
    "non_compliant_frameworks": 0,
    "critical_gaps": 1,
    "overall_compliance": 87.5
  }
}
```

**cURL**:
```bash
curl -X POST http://localhost:8000/api/v1/compliance/check \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "asset_ids": ["asset-123", "asset-124"],
    "frameworks": [
      "NIST_SP_800_208",
      "NIST_SP_800_52",
      "ISO_27001",
      "RBI_CSF"
    ]
  }'
```

---

## Error Handling

### Common Error Responses

**400 Bad Request** - Invalid request parameters:
```json
{
  "detail": {
    "error_code": "INVALID_REQUEST",
    "message": "Invalid port number: port must be 1-65535",
    "field": "port"
  }
}
```

**401 Unauthorized** - Missing or invalid authentication:
```json
{
  "detail": {
    "error_code": "INVALID_TOKEN",
    "message": "Token is invalid or expired"
  }
}
```

**403 Forbidden** - Insufficient permissions:
```json
{
  "detail": {
    "error_code": "INSUFFICIENT_PERMISSIONS",
    "message": "You do not have permission to access this asset",
    "required_role": "asset_owner"
  }
}
```

**404 Not Found** - Resource doesn't exist:
```json
{
  "detail": {
    "error_code": "NOT_FOUND",
    "message": "Asset with ID 'asset-123' not found"
  }
}
```

**429 Too Many Requests** - Rate limit exceeded:
```json
{
  "detail": {
    "error_code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests",
    "retry_after": 60
  }
}
```

**500 Internal Server Error** - Server error:
```json
{
  "detail": {
    "error_code": "INTERNAL_ERROR",
    "message": "An unexpected error occurred",
    "trace_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### Error Handling in cURL

```bash
# Check HTTP status code
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/assets \
  -H "Authorization: Bearer $TOKEN")

if [ $HTTP_CODE -eq 401 ]; then
  echo "Authentication failed - invalid token"
elif [ $HTTP_CODE -eq 429 ]; then
  echo "Rate limited - waiting..."
  sleep 60
elif [ $HTTP_CODE -ge 500 ]; then
  echo "Server error - retry later"
fi

# Get detailed error response
ERROR=$(curl -s http://localhost:8000/api/v1/assets/invalid-id \
  -H "Authorization: Bearer $TOKEN" | jq '.detail.error_code')

echo "Error: $ERROR"
```

---

## Rate Limiting

Rate limits apply to all endpoints to prevent abuse:

- **Default**: 100 requests per minute per user
- **Burst**: 10 requests per second
- **Rate limit headers**:
  ```
  X-RateLimit-Limit: 100
  X-RateLimit-Remaining: 95
  X-RateLimit-Reset: 1704870660
  ```

---

## Complete Example: Full Workflow

```bash
#!/bin/bash

# 1. Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password"
  }' | jq -r '.access_token')

echo "✓ Logged in"

# 2. Create asset
ASSET=$(curl -s -X POST http://localhost:8000/api/v1/assets \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "example.com",
    "port": 443,
    "description": "Example API Server"
  }' | jq -r '.asset_id')

echo "✓ Created asset: $ASSET"

# 3. Initiate scan
SCAN=$(curl -s -X POST http://localhost:8000/api/v1/scans \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Initial Scan\",
    \"scan_type\": \"full\",
    \"targets\": [\"example.com:443\"]
  }" | jq -r '.scan_id')

echo "✓ Started scan: $SCAN"

# 4. Wait for completion
while true; do
  STATUS=$(curl -s http://localhost:8000/api/v1/scans/$SCAN \
    -H "Authorization: Bearer $TOKEN" | jq -r '.status')
  
  if [ "$STATUS" = "completed" ]; then
    echo "✓ Scan completed"
    break
  elif [ "$STATUS" = "failed" ]; then
    echo "✗ Scan failed"
    exit 1
  fi
  
  echo "  Scanning... ($STATUS)"
  sleep 2
done

# 5. Generate CBOM
CBOM=$(curl -s -X POST http://localhost:8000/api/v1/cbom/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"format\": \"json\",
    \"asset_ids\": [\"$ASSET\"]
  }" | jq -r '.cbom')

echo "✓ Generated CBOM"
echo "$CBOM" | jq '.assets'

# 6. Check compliance
curl -s -X POST http://localhost:8000/api/v1/compliance/check \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"asset_ids\": [\"$ASSET\"],
    \"frameworks\": [\"NIST_SP_800_208\"]
  }" | jq '.frameworks.NIST_SP_800_208'

echo "✓ Complete workflow finished"
```

---

## API Documentation

- **Interactive Docs**: http://localhost:8000/docs (Swagger UI)
- **Alternative Docs**: http://localhost:8000/redoc (ReDoc)
- **OpenAPI Spec**: http://localhost:8000/openapi.json (Machine readable)

---

For more information, see the [main README](../README.md) or [Development Guide](DEVELOPMENT.md).
