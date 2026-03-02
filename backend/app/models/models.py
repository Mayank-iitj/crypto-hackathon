"""
Q-Shield Database Models
SQLAlchemy ORM models for all entities.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List
import uuid as uuid_module

from sqlalchemy import (
    String, Text, Boolean, Integer, Float, DateTime, JSON, 
    ForeignKey, Enum as SQLEnum, Index, UniqueConstraint,
    LargeBinary
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

from app.db.database import Base


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


# Models
class Organization(Base):
    """Organization/tenant for multi-tenancy support."""
    
    __tablename__ = "organizations"
    
    uuid: Mapped[uuid_module.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid_module.uuid4, unique=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=True)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relationships
    users: Mapped[List["User"]] = relationship("User", back_populates="organization")
    assets: Mapped[List["Asset"]] = relationship("Asset", back_populates="organization")
    scans: Mapped[List["Scan"]] = relationship("Scan", back_populates="organization")


class User(Base):
    """User account for authentication and authorization."""
    
    __tablename__ = "users"
    
    uuid: Mapped[uuid_module.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid_module.uuid4, unique=True, index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.VIEWER)
    permissions: Mapped[list] = mapped_column(ARRAY(String), default=list)
    
    # OAuth fields
    oauth_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    oauth_provider_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    oauth_access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    oauth_refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    oauth_token_expiry: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    organization: Mapped[Optional["Organization"]] = relationship("Organization", back_populates="users")
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    api_key_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    api_key_last_used: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    __table_args__ = (
        Index("idx_users_org_role", "organization_id", "role"),
    )


class Asset(Base):
    """Discovered internet-facing asset."""
    
    __tablename__ = "assets"
    
    uuid: Mapped[uuid_module.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid_module.uuid4, unique=True, index=True
    )
    
    # Basic identification
    hostname: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True, index=True)
    port: Mapped[int] = mapped_column(Integer, default=443)
    protocol: Mapped[str] = mapped_column(String(50), default="HTTPS")
    
    # Classification
    asset_type: Mapped[AssetType] = mapped_column(SQLEnum(AssetType), default=AssetType.WEB_SERVER)
    exposure_type: Mapped[ExposureType] = mapped_column(SQLEnum(ExposureType), default=ExposureType.PUBLIC)
    
    # Organization
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    organization: Mapped[Optional["Organization"]] = relationship("Organization", back_populates="assets")
    
    # Discovery metadata
    discovery_source: Mapped[str] = mapped_column(String(100), nullable=True)
    asn: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    asn_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    country_code: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    cloud_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_scanned: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Current state (latest scan results)
    risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pqc_readiness: Mapped[PQCReadiness] = mapped_column(
        SQLEnum(PQCReadiness), default=PQCReadiness.UNKNOWN
    )
    
    # Tags and metadata
    tags: Mapped[list] = mapped_column(ARRAY(String), default=list)
    asset_metadata: Mapped[dict] = mapped_column(JSONB, name="metadata", default=dict)
    
    # Relationships
    scan_results: Mapped[List["ScanResult"]] = relationship("ScanResult", back_populates="asset")
    certificates: Mapped[List["QuantumSafeCertificate"]] = relationship("QuantumSafeCertificate", back_populates="asset")
    
    __table_args__ = (
        UniqueConstraint("hostname", "port", "organization_id", name="uq_asset_endpoint"),
        Index("idx_assets_pqc_readiness", "pqc_readiness"),
        Index("idx_assets_risk_score", "risk_score"),
        Index("idx_assets_org_type", "organization_id", "asset_type"),
    )


class Scan(Base):
    """Scan job tracking."""
    
    __tablename__ = "scans"
    
    uuid: Mapped[uuid_module.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid_module.uuid4, unique=True, index=True
    )
    
    name: Mapped[str] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Scan configuration
    scan_type: Mapped[str] = mapped_column(String(50), default="full")
    targets: Mapped[list] = mapped_column(JSONB, default=list)  # List of target specifications
    options: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    # Status
    status: Mapped[ScanStatus] = mapped_column(SQLEnum(ScanStatus), default=ScanStatus.PENDING)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Results summary
    total_targets: Mapped[int] = mapped_column(Integer, default=0)
    completed_targets: Mapped[int] = mapped_column(Integer, default=0)
    failed_targets: Mapped[int] = mapped_column(Integer, default=0)
    
    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Organization
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    organization: Mapped[Optional["Organization"]] = relationship("Organization", back_populates="scans")
    
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    
    # Relationships
    results: Mapped[List["ScanResult"]] = relationship("ScanResult", back_populates="scan")
    
    __table_args__ = (
        Index("idx_scans_status", "status"),
        Index("idx_scans_org_date", "organization_id", "created_at"),
    )


class ScanResult(Base):
    """Individual scan result for an asset."""
    
    __tablename__ = "scan_results"
    
    uuid: Mapped[uuid_module.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid_module.uuid4, unique=True, index=True
    )
    
    # References
    scan_id: Mapped[int] = mapped_column(ForeignKey("scans.id"), nullable=False)
    scan: Mapped["Scan"] = relationship("Scan", back_populates="results")
    
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False)
    asset: Mapped["Asset"] = relationship("Asset", back_populates="scan_results")
    
    # TLS Configuration
    tls_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    cipher_suites: Mapped[list] = mapped_column(JSONB, default=list)
    preferred_cipher: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    key_exchange: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    perfect_forward_secrecy: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    session_resumption: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    ocsp_stapling: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    hsts_enabled: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    hsts_max_age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    alpn_protocols: Mapped[list] = mapped_column(JSONB, default=list)
    
    # Certificate information
    cert_public_key_algorithm: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    cert_key_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cert_signature_algorithm: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    cert_issuer: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    cert_subject: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    cert_not_before: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cert_not_after: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cert_san: Mapped[list] = mapped_column(JSONB, default=list)
    cert_chain_valid: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    cert_revocation_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    cert_fingerprint_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    # PQC Detection
    pqc_key_encapsulation: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    pqc_signature: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    hybrid_tls_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    hybrid_tls_details: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    # Risk Assessment
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    pqc_readiness: Mapped[PQCReadiness] = mapped_column(
        SQLEnum(PQCReadiness), default=PQCReadiness.UNKNOWN
    )
    vulnerabilities: Mapped[list] = mapped_column(JSONB, default=list)
    
    # Compliance
    compliance_findings: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    # Full raw data
    raw_handshake_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    raw_certificate_chain: Mapped[list] = mapped_column(JSONB, default=list)
    
    # Scan metadata
    scan_duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    scan_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    __table_args__ = (
        Index("idx_scanresults_asset", "asset_id"),
        Index("idx_scanresults_scan", "scan_id"),
        Index("idx_scanresults_pqc", "pqc_readiness"),
    )


class QuantumSafeCertificate(Base):
    """Quantum-Safe Certificate issued by Q-Shield."""
    
    __tablename__ = "quantum_safe_certificates"
    
    uuid: Mapped[uuid_module.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid_module.uuid4, unique=True, index=True
    )
    
    certificate_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    
    # Asset reference
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False)
    asset: Mapped["Asset"] = relationship("Asset", back_populates="certificates")
    
    # Certificate details
    level: Mapped[CertificateLevel] = mapped_column(SQLEnum(CertificateLevel))
    
    # Cryptographic details at time of issuance
    tls_version: Mapped[str] = mapped_column(String(20), nullable=False)
    key_exchange: Mapped[str] = mapped_column(String(100), nullable=False)
    cipher_suite: Mapped[str] = mapped_column(String(255), nullable=False)
    pqc_algorithms: Mapped[list] = mapped_column(JSONB, default=list)
    
    # Validity
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Digital signature
    signature: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    signature_algorithm: Mapped[str] = mapped_column(String(50), default="RSA-PSS-SHA384")
    
    # Verification
    verification_url: Mapped[str] = mapped_column(String(512), nullable=False)
    qr_code_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Status
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revocation_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Metadata
    cert_metadata: Mapped[dict] = mapped_column(JSONB, name="metadata", default=dict)
    
    __table_args__ = (
        Index("idx_certs_asset", "asset_id"),
        Index("idx_certs_valid", "is_valid", "expires_at"),
    )


class ComplianceMapping(Base):
    """Compliance framework mappings."""
    
    __tablename__ = "compliance_mappings"
    
    framework: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    control_id: Mapped[str] = mapped_column(String(50), nullable=False)
    control_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Mapping to crypto requirements
    crypto_requirements: Mapped[dict] = mapped_column(JSONB, default=dict)
    remediation_guidance: Mapped[str] = mapped_column(Text, nullable=True)
    
    severity: Mapped[str] = mapped_column(String(20), default="medium")
    
    __table_args__ = (
        UniqueConstraint("framework", "control_id", name="uq_compliance_control"),
    )


class AuditLog(Base):
    """Persistent audit log entries."""
    
    __tablename__ = "audit_logs"
    
    uuid: Mapped[uuid_module.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid_module.uuid4, unique=True, index=True
    )
    
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    resource: Mapped[str] = mapped_column(String(512), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
    integrity_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    
    __table_args__ = (
        Index("idx_audit_actor_date", "actor", "created_at"),
        Index("idx_audit_event_date", "event_type", "created_at"),
    )


class CBOMExport(Base):
    """CBOM export records."""
    
    __tablename__ = "cbom_exports"
    
    uuid: Mapped[uuid_module.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid_module.uuid4, unique=True, index=True
    )
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    format: Mapped[str] = mapped_column(String(20), nullable=False)  # json, jws, pdf, csv
    
    # Scope
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    asset_ids: Mapped[list] = mapped_column(JSONB, default=list)
    scan_id: Mapped[Optional[int]] = mapped_column(ForeignKey("scans.id"), nullable=True)
    
    # Export metadata
    total_assets: Mapped[int] = mapped_column(Integer, default=0)
    generated_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    
    # File storage
    file_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    file_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    # For signed exports
    signature: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    
    __table_args__ = (
        Index("idx_cbom_org", "organization_id"),
    )
