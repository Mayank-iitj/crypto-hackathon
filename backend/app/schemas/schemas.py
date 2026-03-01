"""
Q-Shield API Schemas
Pydantic models for request/response validation.
"""

from datetime import datetime
from typing import Optional, List, Any
from enum import Enum
import uuid

from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator


# Enums
class AssetType(str, Enum):
    WEB_SERVER = "web_server"
    API_ENDPOINT = "api_endpoint"
    VPN_SERVER = "vpn_server"
    MAIL_SERVER = "mail_server"
    DATABASE = "database"
    LOAD_BALANCER = "load_balancer"
    CDN = "cdn"
    OTHER = "other"


class ExposureType(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    HYBRID = "hybrid"


class ScanStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PQCReadiness(str, Enum):
    FULLY_QUANTUM_SAFE = "fully_quantum_safe"
    PQC_READY = "pqc_ready"
    VULNERABLE = "vulnerable"
    UNKNOWN = "unknown"


class CertificateLevel(str, Enum):
    FULLY_QUANTUM_SAFE = "fully_quantum_safe"
    PQC_READY = "pqc_ready"


class UserRole(str, Enum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"
    API_USER = "api_user"


# Base schemas
class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: datetime


# Authentication schemas
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=12)
    full_name: str = Field(..., min_length=2, max_length=255)
    role: UserRole = UserRole.VIEWER
    
    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain a digit")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("Password must contain a special character")
        return v


class UserResponse(BaseSchema, TimestampMixin):
    id: int
    uuid: uuid.UUID
    email: str
    full_name: Optional[str]
    role: UserRole
    is_active: bool
    is_verified: bool
    mfa_enabled: bool
    last_login: Optional[datetime]


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


# Organization schemas
class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    domain: Optional[str] = None


class OrganizationResponse(BaseSchema, TimestampMixin):
    id: int
    uuid: uuid.UUID
    name: str
    domain: Optional[str]
    is_active: bool


# Asset schemas
class AssetCreate(BaseModel):
    hostname: str = Field(..., min_length=1, max_length=512)
    ip_address: Optional[str] = None
    port: int = Field(default=443, ge=1, le=65535)
    protocol: str = "HTTPS"
    asset_type: AssetType = AssetType.WEB_SERVER
    tags: List[str] = []


class AssetResponse(BaseSchema, TimestampMixin):
    id: int
    uuid: uuid.UUID
    hostname: str
    ip_address: Optional[str]
    port: int
    protocol: str
    asset_type: AssetType
    exposure_type: ExposureType
    discovery_source: Optional[str]
    asn: Optional[str]
    asn_name: Optional[str]
    country_code: Optional[str]
    cloud_provider: Optional[str]
    is_active: bool
    last_seen: datetime
    last_scanned: Optional[datetime]
    risk_score: Optional[float]
    pqc_readiness: PQCReadiness
    tags: List[str]


class AssetSummary(BaseSchema):
    id: int
    uuid: uuid.UUID
    hostname: str
    port: int
    risk_score: Optional[float]
    pqc_readiness: PQCReadiness


class AssetDiscoveryRequest(BaseModel):
    """Request to discover assets."""
    domains: List[str] = Field(default=[], description="Domains to enumerate")
    ip_ranges: List[str] = Field(default=[], description="IP ranges in CIDR notation")
    asns: List[str] = Field(default=[], description="ASN numbers to scan")
    include_subdomains: bool = True
    ports: List[int] = Field(default=[443, 8443, 8080, 25, 465, 587, 993, 995])
    scan_options: dict = Field(default={})


class AssetDiscoveryResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    message: str


# Scan schemas
class ScanCreate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    scan_type: str = "full"  # full, tls_only, pqc_only, compliance
    target_asset_ids: List[int] = Field(default=[])
    target_hostnames: List[str] = Field(default=[])
    options: dict = Field(default={})


class ScanRequest(BaseModel):
    """Request to initiate a new scan."""
    name: Optional[str] = None
    description: Optional[str] = None
    scan_type: str = "full"  # full, tls_fingerprint, pqc_assessment, compliance_check
    targets: List[str] = Field(..., description="List of hostnames/IPs to scan")  
    options: Optional[dict] = None


class ScanResponse(BaseSchema, TimestampMixin):
    id: int
    uuid: uuid.UUID
    name: Optional[str]
    description: Optional[str]
    scan_type: str
    status: ScanStatus
    progress: float
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    total_targets: int
    completed_targets: int
    failed_targets: int
    error_message: Optional[str]


class ScanResultResponse(BaseSchema, TimestampMixin):
    id: int
    uuid: uuid.UUID
    asset_id: int
    scan_id: int
    
    # TLS Configuration
    tls_version: Optional[str]
    cipher_suites: List[str]
    preferred_cipher: Optional[str]
    key_exchange: Optional[str]
    perfect_forward_secrecy: Optional[bool]
    session_resumption: Optional[str]
    ocsp_stapling: Optional[bool]
    hsts_enabled: Optional[bool]
    hsts_max_age: Optional[int]
    alpn_protocols: List[str]
    
    # Certificate information
    cert_public_key_algorithm: Optional[str]
    cert_key_size: Optional[int]
    cert_signature_algorithm: Optional[str]
    cert_issuer: Optional[str]
    cert_subject: Optional[str]
    cert_not_before: Optional[datetime]
    cert_not_after: Optional[datetime]
    cert_san: List[str]
    cert_chain_valid: Optional[bool]
    cert_revocation_status: Optional[str]
    
    # PQC Detection
    pqc_key_encapsulation: Optional[str]
    pqc_signature: Optional[str]
    hybrid_tls_detected: bool
    hybrid_tls_details: dict
    
    # Risk Assessment
    risk_score: float
    pqc_readiness: PQCReadiness
    vulnerabilities: List[dict]
    compliance_findings: dict
    
    scan_duration_ms: Optional[int]


# CBOM schemas
class CBOMAsset(BaseModel):
    """Single asset in CBOM."""
    asset_id: str
    hostname: str
    ip_address: Optional[str]
    port: int
    protocol: str
    
    # TLS configuration
    tls_version: Optional[str]
    cipher_suites: List[str]
    preferred_cipher: Optional[str]
    key_exchange: Optional[str]
    perfect_forward_secrecy: Optional[bool]
    
    # Certificate
    certificate: dict
    
    # PQC status
    pqc_readiness: PQCReadiness
    pqc_algorithms: dict
    
    # Risk
    risk_score: float
    vulnerabilities: List[dict]
    
    # Compliance
    compliance_status: dict
    
    # Remediation
    remediation_steps: List[str]
    
    # Metadata
    last_scanned: datetime
    scan_id: str


class CBOMDocument(BaseModel):
    """Cryptographic Bill of Materials."""
    cbom_version: str = "1.0"
    generated_at: datetime
    generator: str = "Q-Shield"
    generator_version: str
    
    # Scope
    organization: Optional[str]
    scan_id: Optional[str]
    
    # Summary
    total_assets: int
    pqc_summary: dict
    risk_summary: dict
    
    # Assets
    assets: List[CBOMAsset]
    
    # Compliance summary
    compliance_summary: dict
    
    # Signature (for signed exports)
    signature: Optional[str] = None
    signature_algorithm: Optional[str] = None


class CBOMRequest(BaseModel):
    """Request to generate CBOM."""
    format: str = Field(default="json", pattern="^(json|jws|pdf|csv)$")
    asset_ids: List[int]
    organization: str
    scan_period: Optional[str] = None


class CBOMResponse(BaseModel):
    """Response with CBOM metadata."""
    cbom_id: str
    format: str
    generated_at: str
    total_assets: int
    assets_quantum_safe: int


class CBOMExportRequest(BaseModel):
    format: str = Field(..., pattern="^(json|jws|pdf|csv)$")
    asset_ids: List[int] = Field(default=[])
    scan_id: Optional[int] = None
    include_raw_data: bool = False


class CBOMExportResponse(BaseModel):
    export_id: uuid.UUID
    format: str
    download_url: str
    expires_at: datetime


# Certificate schemas
class CertificateRequest(BaseModel):
    asset_id: int


class CertificateResponse(BaseSchema, TimestampMixin):
    id: int
    uuid: uuid.UUID
    certificate_id: str
    asset_id: int
    level: CertificateLevel
    tls_version: str
    key_exchange: str
    cipher_suite: str
    pqc_algorithms: List[str]
    issued_at: datetime
    expires_at: datetime
    verification_url: str
    qr_code_data: Optional[str]
    is_valid: bool


class CertificateVerificationResponse(BaseModel):
    certificate_id: str
    is_valid: bool
    level: Optional[CertificateLevel]
    asset_hostname: Optional[str]
    issued_at: Optional[datetime]
    expires_at: Optional[datetime]
    verification_timestamp: datetime
    message: str


# Compliance schemas
class ComplianceControl(BaseModel):
    framework: str
    control_id: str
    control_name: str
    description: Optional[str]
    status: str  # compliant, non_compliant, partial, not_applicable
    findings: List[str]
    remediation: Optional[str]


class ComplianceReport(BaseModel):
    asset_id: int
    hostname: str
    frameworks: List[str]
    overall_status: str
    controls: List[ComplianceControl]
    scan_date: datetime


# Dashboard schemas
class DashboardStats(BaseModel):
    total_assets: int
    pqc_stats: dict
    risk_distribution: dict
    recent_scans: List[dict]
    expiring_certificates: List[dict]
    compliance_overview: dict


class RiskTrendData(BaseModel):
    date: datetime
    average_risk_score: float
    vulnerable_count: int
    pqc_ready_count: int
    fully_safe_count: int


# Pagination
class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    pages: int


# Error responses
class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[dict] = None
    request_id: Optional[str] = None
