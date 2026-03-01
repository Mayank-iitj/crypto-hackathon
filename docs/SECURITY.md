# Q-Shield Security Guide

Comprehensive security documentation for Q-Shield platform covering cryptography, API security, compliance, and operational security best practices.

## Table of Contents
1. [Cryptographic Practices](#cryptographic-practices)
2. [API Security](#api-security)
3. [Database Security](#database-security)
4. [Infrastructure Security](#infrastructure-security)
5. [Compliance Standards](#compliance-standards)
6. [Incident Response](#incident-response)
7. [Security Testing](#security-testing)
8. [Audit & Logging](#audit--logging)

---

## Cryptographic Practices

### JWT Implementation

**Algorithm**: RS256 (RSA Signature with SHA-256)

```python
# JWT Configuration
JWT_ALGORITHM = "RS256"
JWT_EXPIRATION_MINUTES = 30
JWT_REFRESH_EXPIRATION_DAYS = 7
PRIVATE_KEY_PATH = "keys/jwt_private.pem"
PUBLIC_KEY_PATH = "keys/jwt_public.pem"

# Token generation
def create_access_token(user_id: str, expires_delta: Optional[timedelta] = None):
    if expires_delta is None:
        expires_delta = timedelta(minutes=JWT_EXPIRATION_MINUTES)
    
    claims = {
        "sub": user_id,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + expires_delta,
        "type": "access"
    }
    
    encoded_jwt = jwt.encode(
        claims,
        private_key,
        algorithm=JWT_ALGORITHM
    )
    return encoded_jwt

# Token validation
def verify_token(token: str):
    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=[JWT_ALGORITHM]
        )
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### Password Security

```python
# Password hashing configuration
HASH_ALGORITHM = "bcrypt"
BCRYPT_ROUNDS = 12
ARGON2_TIME_COST = 2
ARGON2_MEMORY_COST = 65536
ARGON2_PARALLELISM = 4

# Password hashing
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash password with bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)

# Password requirements
PASSWORD_REQUIREMENTS = {
    "min_length": 12,
    "require_uppercase": True,
    "require_lowercase": True,
    "require_numbers": True,
    "require_special_chars": True
}
```

### Data Encryption at Rest

```python
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

# Generate master key
def generate_master_key():
    """Generate encryption key for at-rest data"""
    password = os.environ["ENCRYPTION_PASSWORD"].encode()
    salt = b'qshield_salt_v1'
    
    kdf = PBKDF2(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000
    )
    key = base64.urlsafe_b64encode(kdf.derive(password))
    return key

# Encrypt sensitive fields
cipher = Fernet(master_key)

def encrypt_field(plaintext: str) -> str:
    """Encrypt sensitive data"""
    return cipher.encrypt(plaintext.encode()).decode()

def decrypt_field(ciphertext: str) -> str:
    """Decrypt sensitive data"""
    return cipher.decrypt(ciphertext.encode()).decode()

# Database column encryption
class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    email = Column(String, unique=True)
    api_key = Column(String)  # Encrypted
    
    @property
    def decrypted_api_key(self):
        return decrypt_field(self.api_key) if self.api_key else None
```

### TLS/SSL Configuration

```python
# TLS configuration for outbound connections
import ssl

ssl_context = ssl.create_default_context()
ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
ssl_context.maximum_version = ssl.TLSVersion.TLSv1_3

# Cipher suites (recommended)
ssl_context.set_ciphers(
    'ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!eNULL:!EXPORT:!DES:!MD5:!PSK:!RC4'
)

# Client certificates
ssl_context.load_cert_chain(
    certfile="keys/client_cert.pem",
    keyfile="keys/client_key.pem"
)

# Verify server certificate
ssl_context.check_hostname = True
ssl_context.verify_mode = ssl.CERT_REQUIRED
ssl_context.load_verify_locations("keys/ca_bundle.pem")
```

### CBOM Signature Generation

```python
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

def sign_cbom(cbom_data: dict) -> str:
    """Generate RSA-PSS-SHA384 signature for CBOM"""
    
    # Load private key
    with open("keys/platform_signing.pem", "rb") as f:
        private_key = serialization.load_pem_private_key(
            f.read(),
            password=None
        )
    
    # Serialize CBOM for signing
    message = json.dumps(cbom_data, sort_keys=True).encode()
    
    # Sign with RSA-PSS
    signature = private_key.sign(
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA384()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA384()
    )
    
    return base64.b64encode(signature).decode()

def verify_cbom_signature(cbom_data: dict, signature: str) -> bool:
    """Verify CBOM signature"""
    
    with open("keys/platform_public.pem", "rb") as f:
        public_key = serialization.load_pem_public_key(f.read())
    
    message = json.dumps(cbom_data, sort_keys=True).encode()
    sig_bytes = base64.b64decode(signature)
    
    try:
        public_key.verify(
            sig_bytes,
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA384()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA384()
        )
        return True
    except Exception:
        return False
```

---

## API Security

### Authentication

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthCredentials = Depends(security)):
    """Verify JWT token in Authorization header"""
    token = credentials.credentials
    
    try:
        payload = jwt.decode(
            token,
            settings.JWT_PUBLIC_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    
    return user_id

async def get_current_user(user_id: str = Depends(verify_token)):
    """Get current authenticated user"""
    user = await User.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# Usage in endpoints
@router.get("/api/v1/assets")
async def list_assets(
    current_user: User = Depends(get_current_user)
):
    return {"assets": [...]}
```

### Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# Global rate limit
@app.get("/api/v1/assets")
@limiter.limit("100/minute")
async def list_assets(request: Request):
    pass

# Strict rate limit for login
@app.post("/api/v1/auth/login")
@limiter.limit("5/minute")
async def login(request: Request, credentials: LoginRequest):
    pass

# Custom rate limits
limiter.limit("1000/hour")(list_assets)  # Generous for background jobs
```

### Input Validation

```python
from pydantic import BaseModel, Field, validator, EmailStr

class CreateAssetRequest(BaseModel):
    hostname: str = Field(..., 
        min_length=1, 
        max_length=255,
        regex=r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
    )
    port: int = Field(..., ge=1, le=65535)
    ip_address: Optional[str] = Field(None, regex=r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    description: str = Field(..., max_length=1000)
    owner_email: EmailStr
    
    @validator('hostname')
    def validate_hostname(cls, v):
        if v.startswith('-') or v.endswith('-'):
            raise ValueError('Hostname components cannot start/end with hyphen')
        return v.lower()

# Request validation
@router.post("/api/v1/assets")
async def create_asset(request: CreateAssetRequest):
    # request is automatically validated by Pydantic
    pass
```

### CORS Configuration

```python
from fastapi.middleware.cors import CORSMiddleware

# Enforce CORS by environment
if settings.ENVIRONMENT == "production":
    allowed_origins = ["https://dashboard.q-shield.example.com"]
else:
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["X-Total-Count"],
    max_age=3600
)
```

### Security Headers

```python
from fastapi.middleware.base import BaseHTTPMiddleware

class SecurityHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response

app.add_middleware(SecurityHeaderMiddleware)
```

---

## Database Security

### Parameterized Queries

```python
# SQLAlchemy prevents SQL injection
from sqlalchemy import select

# Safe - parameterized query
stmt = select(User).where(User.email == email)
result = await session.execute(stmt)

# UNSAFE - never do this
query = f"SELECT * FROM users WHERE email = '{email}'"  # Vulnerable!
```

### Column Encryption

```python
from sqlalchemy import Column, String, TypeDecorator

class EncryptedString(TypeDecorator):
    """Encrypted string column type"""
    impl = String
    cache_ok = True
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return encrypt_field(value)
    
    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return decrypt_field(value)

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    email = Column(String, unique=True)
    phone = Column(EncryptedString)  # Encrypted
    api_key = Column(EncryptedString)  # Encrypted
```

### Row-Level Security

```python
# Ensure users only see their organization's data
async def list_assets(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    stmt = select(Asset).where(
        Asset.organization_id == current_user.organization_id
    )
    result = await session.execute(stmt)
    return result.scalars().all()
```

### Audit Logging

```python
class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"))
    action = Column(String)  # create, update, delete, read
    resource_type = Column(String)  # Asset, Scan, User
    resource_id = Column(String)
    changes = Column(JSON)  # What changed
    ip_address = Column(String)
    user_agent = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Integrity check
    @property
    def integrity_hash(self):
        data = f"{self.user_id}|{self.action}|{self.resource_type}|{self.timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()

async def audit_action(
    session: AsyncSession,
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    changes: dict = None
):
    """Log audit event"""
    log = AuditLog(
        id=str(uuid.uuid4()),
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        changes=changes,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    session.add(log)
    await session.commit()
```

---

## Infrastructure Security

### Network Segmentation

```yaml
# Kubernetes NetworkPolicy - Deny all by default
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: qshield
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress

---
# Allow API -> Database
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-api-to-db
  namespace: qshield
spec:
  podSelector:
    matchLabels:
      app: postgres
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: qshield-api
    ports:
    - protocol: TCP
      port: 5432
```

### Pod Security Policy

```yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: qshield-restricted
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  hostNetwork: false
  hostIPC: false
  hostPID: false
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'MustRunAs'
  supplementalGroups:
    rule: 'MustRunAs'
  fsGroup:
    rule: 'MustRunAs'
  readOnlyRootFilesystem: true
```

### Secret Management

```bash
# Never commit secrets to git
echo "keys/" >> .gitignore
echo ".env" >> .gitignore

# Use environment variables
export JWT_PRIVATE_KEY=$(cat keys/jwt_private.pem)
export DATABASE_PASSWORD=$(openssl rand -base64 32)

# Or use secret management systems
# HashiCorp Vault
# AWS Secrets Manager
# Google Cloud Secret Manager
# Azure Key Vault

# Kubernetes Secrets
kubectl create secret generic app-secrets \
  --from-literal=database-password=XXXX \
  --from-literal=jwt-secret=XXXX \
  -n qshield
```

---

## Compliance Standards

### NIST SP 800-208: Post-Quantum Cryptography

Q-Shield implements NIST SP 800-208 guidance for PQC migration:

```python
# Recommended algorithms per NIST SP 800-208
NIST_PQC_ALGORITHMS = {
    "key_encapsulation": [
        "ML-KEM-512",
        "ML-KEM-768",
        "ML-KEM-1024",
    ],
    "digital_signature": [
        "ML-DSA-44",
        "ML-DSA-65",
        "ML-DSA-87",
        "SLH-DSA-128s",
        "SLH-DSA-128f",
        "SLH-DSA-192s",
        "SLH-DSA-192f",
        "SLH-DSA-256s",
        "SLH-DSA-256f",
    ],
    "legacy_during_transition": [
        "Kyber",
        "Dilithium",
        "FALCON",
        "SPHINCS+"
    ]
}

# Migrate timeline per NIST
MIGRATION_TIMELINE = {
    "immediate": "6 months - Inventory and plan",
    "near_term": "1-2 years - Pilot hybrid solutions",
    "medium_term": "3-5 years - Deploy hybrid solutions",
    "long_term": "5-10 years - Plan post-quantum era"
}
```

### NIST SP 800-52 Rev 1: TLS Guidelines

```python
# Minimum TLS requirements
TLS_REQUIREMENTS = {
    "minimum_version": "1.2",
    "preferred_version": "1.3",
    "key_exchange": "ECDHE",
    "cipher_suites": [
        "TLS_AES_256_GCM_SHA384",
        "TLS_CHACHA20_POLY1305_SHA256",
        "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384",
        "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
    ],
    "certificate_key_size": {
        "RSA": 2048,  # Minimum, 3072+ recommended
        "ECDSA": 256,
        "EdDSA": 256
    },
    "signature_algorithms": [
        "ecdsa_secp256r1_sha256",
        "ecdsa_secp384r1_sha384",
        "rsa_pss_rsae_sha256",
        "rsa_pss_rsae_sha384",
    ]
}
```

### ISO/IEC 27001:2022

```python
# Security controls mapping
ISO_27001_CONTROLS = {
    "A.5.1": "Information security policies",
    "A.5.2": "Information security at the leadership level",
    "A.6.1": "Roles and responsibilities",
    "A.7.1": "Human resource security",
    "A.8.1": "Assets management",
    "A.9.1": "Access control",
    "A.10.1": "Cryptography",  # Key control
    "A.12.1": "Awareness and training",
    "A.13.1": "Communications security",  # TLS, encryption
    "A.14.1": "System acquisition, development",
    "A.15.1": "Supplier relationships",
}

# ISO 27001 A.10.1 - Cryptography control
CRYPTOGRAPHY_REQUIREMENTS = {
    "policy": "Encryption policy for sensitive data",
    "implementation": "TLS 1.2+ for all communications",
    "key_management": "Secure key generation, storage, rotation",
    "algorithm_selection": "NIST-approved algorithms",
    "audit": "Regular cryptographic asset inventory"
}
```

### RBI Cyber Security Framework

```python
# Indian banking sector requirements per RBI
RBI_SECURITY_REQUIREMENTS = {
    "CS-5.1": "Encrypted channels (TLS 1.2+)",
    "CS-5.2": "Key management infrastructure",
    "CS-5.3": "Post-quantum cryptography readiness",
    "CS-6.1": "Data backup and recovery",
    "CS-6.2": "Business continuity planning",
    "CS-7.1": "Logging and monitoring",
    "CS-7.2": "Incident response procedures",
}

# Mandatory for banks by deadline
RBI_PQC_TIMELINE = {
    "assess": "2024-12-31",  # Assess PQC readiness
    "plan": "2025-06-30",    # Submit migration plan
    "implement": "2027-12-31" # Implement PQC solutions
}
```

---

## Incident Response

### Security Incident Classification

```python
class SecurityIncident(Base):
    __tablename__ = "security_incidents"
    
    id = Column(String, primary_key=True)
    severity = Column(Enum(IncidentSeverity))  # CRITICAL, HIGH, MEDIUM, LOW
    type = Column(String)  # breach, ddos, malware, unauthorized_access
    description = Column(String)
    discovery_time = Column(DateTime)
    response_time = Column(DateTime)
    resolution_time = Column(DateTime)
    investigation_notes = Column(String)
    forensic_evidence = Column(String)  # S3 path to evidence
    remediation_actions = Column(JSON)
    post_incident_review = Column(String)

class IncidentSeverity(str, Enum):
    CRITICAL = "critical"  # Immediate threat, active exploitation
    HIGH = "high"          # Significant risk, needs urgent response
    MEDIUM = "medium"      # Moderate risk, respond within hours
    LOW = "low"            # Minor issue, document and monitor
```

### Incident Response Procedures

```python
async def handle_security_incident(
    incident_type: str,
    severity: IncidentSeverity,
    description: str,
    evidence: dict
):
    """Handle security incident"""
    
    incident = SecurityIncident(
        id=str(uuid.uuid4()),
        severity=severity,
        type=incident_type,
        description=description,
        discovery_time=datetime.utcnow()
    )
    
    # 1. Immediate containment
    if severity == IncidentSeverity.CRITICAL:
        await isolate_affected_system()
        await revoke_compromised_credentials()
        await notify_security_team()
    
    # 2. Investigation
    forensic_path = await collect_forensic_evidence(evidence)
    incident.forensic_evidence = forensic_path
    
    # 3. Notification
    if severity in [IncidentSeverity.CRITICAL, IncidentSeverity.HIGH]:
        await notify_ciso()
        await notify_affected_users()
        await notify_regulatory_bodies()  # If required
    
    # 4. Remediation
    remediation_actions = await create_remediation_plan(incident_type)
    incident.remediation_actions = remediation_actions
    
    session.add(incident)
    await session.commit()
```

### Breach Notification

```python
async def notify_data_breach(incident_id: str, affected_users: List[str]):
    """Notify users of confirmed breach"""
    
    incident = await SecurityIncident.get(incident_id)
    
    notification = {
        "subject": "Security Incident Notification",
        "body": f"""
Dear User,

We are writing to inform you that Q-Shield detected a security incident 
that may have affected your account.

Incident Type: {incident.type}
Discovery Date: {incident.discovery_time.isoformat()}
Severity: {incident.severity}

Actions Taken:
- Compromised sessions have been invalidated
- Password reset recommended
- Two-factor authentication enabled for security

What You Should Do:
1. Change your password immediately
2. Enable two-factor authentication
3. Monitor your account for suspicious activity
4. Contact support if you notice any unauthorized access

For more information, visit: https://q-shield.example.com/incident/{incident_id}

Security Team
Q-Shield
""",
        "affected_users": affected_users
    }
    
    # Send notifications via email and in-app messages
    for user_email in affected_users:
        await send_email(user_email, notification["subject"], notification["body"])
```

---

## Security Testing

### OWASP Top 10 Testing

```bash
# 1. Injection (SQL, Command)
# Already mitigated by SQLAlchemy and parameterized queries
pytest tests/security/test_sql_injection.py

# 2. Authentication bypass
pytest tests/security/test_authentication.py

# 3. Sensitive data exposure
pytest tests/security/test_encryption.py

# 4. XXE (XML External Entity)
# Using JSON only - not vulnerable

# 5. Broken access control
pytest tests/security/test_authorization.py

# 6. Security misconfiguration
pytest tests/security/test_config.py

# 7. XSS
pytest tests/security/test_xss.py

# 8. Insecure deserialization
pytest tests/security/test_deserialization.py

# 9. Using vulnerable components
# Check with pip-audit
pip install pip-audit
pip-audit

# 10. Insufficient logging/monitoring
pytest tests/security/test_logging.py
```

### Penetration Testing

```bash
# Run security scanner on API
docker run -it --rm --name zaproxy \
  -v $(pwd):/zap/wrk:rw \
  owasp/zap2docker-stable zap-baseline.py \
  -t http://localhost:8000 \
  -r security_report.html

# API security testing
pip install Safety
safety check

# Dependency vulnerability scanning
pip install bandit
bandit -r app/ -f json -o bandit_report.json

# Code quality and security
pip install pylint
pylint app/ --disable=C0111
```

---

## Audit & Logging

### Logging Strategy

```python
import logging
import json
from pythonjsonlogger import jsonlogger

# JSON logging for structured logs
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)

logger = logging.getLogger()
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# Log sensitive events
logger.info("User login", extra={
    "user_id": user.id,
    "ip_address": request.client.host,
    "timestamp": datetime.utcnow().isoformat(),
    "event": "user_login"
})

logger.warning("Failed login attempt", extra={
    "email": email,
    "ip_address": request.client.host,
    "attempts": failed_attempts,
    "event": "failed_login"
})

logger.error("Security incident detected", extra={
    "incident_type": "potential_breach",
    "resource": resource_id,
    "event": "security_incident"
})
```

### Audit Log Retention

```python
# Retain audit logs for compliance
AUDIT_LOG_RETENTION = {
    "standard": 7,         # days
    "extended": 90,        # for high-risk transactions
    "permanent": 2555,     # 7 years for compliance
}

async def cleanup_old_logs(days: int = 365):
    """Delete audit logs older than retention period"""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    stmt = delete(AuditLog).where(AuditLog.timestamp < cutoff_date)
    await session.execute(stmt)
    await session.commit()

# Schedule cleanup
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()
scheduler.add_job(cleanup_old_logs, "cron", hour=2)
scheduler.start()
```

---

## Security Checklist

Pre-Production:
- [ ] All secrets removed from codebase
- [ ] HTTPS/TLS enabled for all endpoints
- [ ] JWT tokens with short expiration
- [ ] Password hashing with bcrypt (12+ rounds)
- [ ] Rate limiting enforced
- [ ] Input validation on all endpoints
- [ ] CORS configured restrictively
- [ ] Security headers added
- [ ] Audit logging enabled
- [ ] Database encryption enabled
- [ ] Backups encrypted and tested
- [ ] Incident response plan documented
- [ ] Security tests passing
- [ ] Dependencies audited for vulnerabilities

---

For questions or to report security vulnerabilities, please contact: security@q-shield.example.com

See also: [DEPLOYMENT.md](DEPLOYMENT.md) for infrastructure security hardening.
