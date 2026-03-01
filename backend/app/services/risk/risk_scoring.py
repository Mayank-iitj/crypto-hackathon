"""
Q-Shield Risk Scoring Engine
Calculates comprehensive cryptographic risk scores based on NIST standards.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum

from app.core.logging import get_logger

logger = get_logger("risk.scoring")


class RiskSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class RiskFactor:
    """Represents a single risk factor contributing to overall score."""
    factor_id: str
    name: str
    description: str
    severity: RiskSeverity
    weight: float  # 0.0 to 1.0
    points: float  # 0.0 to 100.0
    remediation: str
    nist_control: Optional[str] = None


@dataclass
class RiskScoreBreakdown:
    """Detailed breakdown of risk score calculation."""
    total_score: float  # 0-100
    severity_level: RiskSeverity
    factors: List[RiskFactor] = field(default_factory=list)
    
    # Category scores
    cryptographic_score: float = 0.0  # Crypto implementation (0-100)
    certificate_score: float = 0.0    # Certificate quality (0-100)
    protocol_score: float = 0.0       # Protocol version (0-100)
    quantum_readiness_score: float = 0.0  # PQC readiness (0-100)
    configuration_score: float = 0.0  # Server configuration (0-100)
    
    # Compliance scores
    nist_sp_800_208_score: float = 0.0
    iso_27001_score: float = 0.0
    rbi_csf_score: float = 0.0
    
    # Risk timeline
    critical_action_required: bool = False
    days_to_remediation: Optional[int] = None
    
    # Trend
    trend: Optional[str] = None  # "improving", "stable", "degrading"


class RiskScoringEngine:
    """
    Comprehensive risk scoring system for cryptographic configurations.
    Based on NIST SP 800-208, NIST SP 800-52, and ISO/IEC 27001.
    """
    
    # Risk factor definitions (weights sum to 100%)
    RISK_FACTORS = {
        # CRITICAL FACTORS (50% weight)
        "tls_version": {
            "tls_1_3": {"severity": RiskSeverity.INFO, "weight": 0.0, "points": 0},
            "tls_1_2": {"severity": RiskSeverity.LOW, "weight": 0.08, "points": 15},
            "tls_1_1": {"severity": RiskSeverity.CRITICAL, "weight": 0.15, "points": 40},
            "tls_1_0": {"severity": RiskSeverity.CRITICAL, "weight": 0.15, "points": 50},
            "ssl_3_0": {"severity": RiskSeverity.CRITICAL, "weight": 0.15, "points": 50},
            "unknown": {"severity": RiskSeverity.MEDIUM, "weight": 0.10, "points": 25},
        },
        
        # KEY EXCHANGE (20% weight)
        "key_exchange": {
            "mlkem": {"severity": RiskSeverity.INFO, "weight": 0.0, "points": 0},  # Best
            "ecdhe": {"severity": RiskSeverity.INFO, "weight": 0.02, "points": 5},
            "dhe": {"severity": RiskSeverity.LOW, "weight": 0.05, "points": 15},
            "ecdh_static": {"severity": RiskSeverity.HIGH, "weight": 0.10, "points": 35},
            "dh_static": {"severity": RiskSeverity.HIGH, "weight": 0.10, "points": 35},
            "rsa_ke": {"severity": RiskSeverity.CRITICAL, "weight": 0.15, "points": 50},
        },
        
        # CIPHER STRENGTH (15% weight)
        "bulk_cipher": {
            "aes_256_gcm": {"severity": RiskSeverity.INFO, "weight": 0.0, "points": 0},
            "aes_256_cbc": {"severity": RiskSeverity.LOW, "weight": 0.03, "points": 10},
            "chacha20": {"severity": RiskSeverity.INFO, "weight": 0.0, "points": 5},
            "aes_128_gcm": {"severity": RiskSeverity.LOW, "weight": 0.05, "points": 20},
            "aes_128_cbc": {"severity": RiskSeverity.MEDIUM, "weight": 0.08, "points": 25},
            "3des": {"severity": RiskSeverity.CRITICAL, "weight": 0.15, "points": 50},
            "rc4": {"severity": RiskSeverity.CRITICAL, "weight": 0.15, "points": 50},
            "des": {"severity": RiskSeverity.CRITICAL, "weight": 0.15, "points": 50},
        },
        
        # HASH ALGORITHM (10% weight)
        "hash_algorithm": {
            "sha512": {"severity": RiskSeverity.INFO, "weight": 0.0, "points": 0},
            "sha384": {"severity": RiskSeverity.INFO, "weight": 0.0, "points": 0},
            "sha256": {"severity": RiskSeverity.LOW, "weight": 0.02, "points": 5},
            "sha1": {"severity": RiskSeverity.CRITICAL, "weight": 0.08, "points": 35},
            "md5": {"severity": RiskSeverity.CRITICAL, "weight": 0.10, "points": 50},
        },
        
        # CERTIFICATE ISSUES (25% weight)
        "certificate_quality": {
            "rsa_4096": {"severity": RiskSeverity.INFO, "weight": 0.0, "points": 0},
            "rsa_3072": {"severity": RiskSeverity.LOW, "weight": 0.02, "points": 5},
            "rsa_2048": {"severity": RiskSeverity.MEDIUM, "weight": 0.08, "points": 20},
            "rsa_1024": {"severity": RiskSeverity.CRITICAL, "weight": 0.20, "points": 60},
            "ecc_p384": {"severity": RiskSeverity.INFO, "weight": 0.0, "points": 0},
            "ecc_p256": {"severity": RiskSeverity.LOW, "weight": 0.02, "points": 10},
            "expired": {"severity": RiskSeverity.CRITICAL, "weight": 0.20, "points": 60},
            "expiring_30_days": {"severity": RiskSeverity.HIGH, "weight": 0.10, "points": 30},
            "expiring_90_days": {"severity": RiskSeverity.MEDIUM, "weight": 0.05, "points": 15},
            "self_signed": {"severity": RiskSeverity.HIGH, "weight": 0.10, "points": 40},
            "weak_signature": {"severity": RiskSeverity.CRITICAL, "weight": 0.10, "points": 45},
        },
        
        # SECURITY FEATURES (10% weight)
        "security_features": {
            "perfect_forward_secrecy": {"severity": RiskSeverity.INFO, "weight": 0.0, "points": -10},
            "ocsp_stapling": {"severity": RiskSeverity.LOW, "weight": 0.02, "points": -5},
            "hsts_enabled": {"severity": RiskSeverity.LOW, "weight": 0.02, "points": -5},
            "hsts_preload": {"severity": RiskSeverity.INFO, "weight": 0.0, "points": -10},
            "missing_pfs": {"severity": RiskSeverity.HIGH, "weight": 0.08, "points": 25},
            "weak_session_resumption": {"severity": RiskSeverity.MEDIUM, "weight": 0.05, "points": 15},
        },
    }
    
    def calculate_score(
        self,
        tls_version: Optional[str],
        cipher_suites: List[str],
        preferred_cipher: Optional[str],
        key_exchange: Optional[str],
        certificate_key_algorithm: Optional[str],
        certificate_key_size: Optional[int],
        cert_signature_algorithm: Optional[str],
        cert_not_after: Optional[datetime] = None,
        perfect_forward_secrecy: bool = False,
        ocsp_stapling: bool = False,
        hsts_enabled: bool = False,
        hsts_preload: bool = False,
        self_signed: bool = False,
        pqc_supported: bool = False,
        previous_score: Optional[float] = None,
    ) -> RiskScoreBreakdown:
        """
        Calculate comprehensive risk score based on all cryptographic parameters.
        """
        breakdown = RiskScoreBreakdown()
        
        logger.info(f"Calculating risk score for TLS configuration")
        
        # Analyze each component
        self._score_tls_version(tls_version, breakdown)
        self._score_key_exchange(key_exchange, perfect_forward_secrecy, breakdown)
        self._score_cipher_suites(cipher_suites, preferred_cipher, breakdown)
        self._score_certificate(
            certificate_key_algorithm, certificate_key_size, 
            cert_signature_algorithm, cert_not_after, self_signed, breakdown
        )
        self._score_security_features(
            perfect_forward_secrecy, ocsp_stapling, hsts_enabled, hsts_preload, breakdown
        )
        self._score_pqc_readiness(pqc_supported, breakdown)
        
        # Calculate category scores
        self._calculate_category_scores(breakdown)
        
        # Calculate final score
        self._calculate_final_score(breakdown)
        
        # Determine severity
        self._determine_severity(breakdown)
        
        # Calculate trend
        if previous_score is not None:
            self._calculate_trend(breakdown, previous_score)
        
        logger.info(f"Risk score calculated: {breakdown.total_score:.1f} ({breakdown.severity_level})")
        
        return breakdown
    
    def _score_tls_version(self, tls_version: Optional[str], breakdown: RiskScoreBreakdown):
        """Score TLS version."""
        if not tls_version:
            return
        
        version_upper = tls_version.upper()
        
        if "1.3" in version_upper:
            self._add_factor(breakdown, "tls_1_3", RiskSeverity.INFO, 0.0, 0, 
                           "Protocol version TLS 1.3")
            breakdown.protocol_score = 0
        elif "1.2" in version_upper:
            self._add_factor(breakdown, "tls_1_2", RiskSeverity.LOW, 0.08, 15,
                           "Consider upgrading to TLS 1.3")
            breakdown.protocol_score = 15
        elif "1.1" in version_upper:
            self._add_factor(breakdown, "tls_1_1", RiskSeverity.CRITICAL, 0.15, 40,
                           "URGENT: Upgrade to TLS 1.2 or 1.3")
            breakdown.protocol_score = 40
        elif "1.0" in version_upper:
            self._add_factor(breakdown, "tls_1_0", RiskSeverity.CRITICAL, 0.15, 50,
                           "URGENT: Upgrade from TLS 1.0")
            breakdown.protocol_score = 50
        else:
            self._add_factor(breakdown, "ssl_3_0", RiskSeverity.CRITICAL, 0.15, 50,
                           "URGENT: Upgrade from SSL/legacy protocol")
            breakdown.protocol_score = 50
    
    def _score_key_exchange(
        self, 
        key_exchange: Optional[str],
        perfect_forward_secrecy: bool,
        breakdown: RiskScoreBreakdown
    ):
        """Score key exchange mechanism."""
        if not key_exchange:
            breakdown.cryptographic_score += 15
            return
        
        kex_upper = key_exchange.upper()
        
        if "MLKEM" in kex_upper or "KYBER" in kex_upper:
            self._add_factor(breakdown, "mlkem", RiskSeverity.INFO, 0.0, 0,
                           "Post-Quantum safe key exchange")
            breakdown.cryptographic_score += 0
        elif "ECDHE" in kex_upper:
            if perfect_forward_secrecy:
                self._add_factor(breakdown, "ecdhe", RiskSeverity.INFO, 0.02, 5,
                               "ECDHE with PFS - good choice")
                breakdown.cryptographic_score += 5
            else:
                breakdown.cryptographic_score += 10
        elif "DHE" in kex_upper:
            self._add_factor(breakdown, "dhe", RiskSeverity.LOW, 0.05, 15,
                           "DHE without ECDHE - consider upgrade")
            breakdown.cryptographic_score += 15
        elif "ECDH" in kex_upper and "ECDHE" not in kex_upper:
            self._add_factor(breakdown, "ecdh_static", RiskSeverity.HIGH, 0.10, 35,
                           "Static ECDH without PFS - upgrade to ECDHE")
            breakdown.cryptographic_score += 35
        elif "DH" in kex_upper:
            self._add_factor(breakdown, "dh_static", RiskSeverity.HIGH, 0.10, 35,
                           "Static DH without PFS - upgrade to DHE/ECDHE")
            breakdown.cryptographic_score += 35
        elif "RSA" in kex_upper:
            self._add_factor(breakdown, "rsa_ke", RiskSeverity.CRITICAL, 0.15, 50,
                           "CRITICAL: RSA key exchange - no PFS, vulnerable to quantum")
            breakdown.cryptographic_score += 50
    
    def _score_cipher_suites(
        self,
        cipher_suites: List[str],
        preferred_cipher: Optional[str],
        breakdown: RiskScoreBreakdown
    ):
        """Score encryption cipher suites."""
        if not cipher_suites:
            breakdown.cryptographic_score += 20
            return
        
        all_ciphers = " ".join(cipher_suites).upper()
        
        # Check for weak ciphers
        if "3DES" in all_ciphers:
            self._add_factor(breakdown, "3des", RiskSeverity.CRITICAL, 0.15, 50,
                           "CRITICAL: Remove 3DES cipher suites")
            breakdown.cryptographic_score += 50
        elif "RC4" in all_ciphers:
            self._add_factor(breakdown, "rc4", RiskSeverity.CRITICAL, 0.15, 50,
                           "CRITICAL: Remove RC4 cipher suites")
            breakdown.cryptographic_score += 50
        elif "DES" in all_ciphers:
            self._add_factor(breakdown, "des", RiskSeverity.CRITICAL, 0.15, 50,
                           "CRITICAL: Remove DES cipher suites")
            breakdown.cryptographic_score += 50
        
        # Score preferred cipher
        if preferred_cipher:
            if "AES_256_GCM" in preferred_cipher.upper():
                self._add_factor(breakdown, "aes_256_gcm", RiskSeverity.INFO, 0.0, 0,
                               "Excellent: AES-256-GCM")
                breakdown.cryptographic_score += 0
            elif "AES_256" in preferred_cipher.upper():
                self._add_factor(breakdown, "aes_256_cbc", RiskSeverity.LOW, 0.03, 10,
                               "Good: AES-256 (CBC) - upgrade to GCM")
                breakdown.cryptographic_score += 10
            elif "CHACHA20" in preferred_cipher.upper():
                self._add_factor(breakdown, "chacha20", RiskSeverity.INFO, 0.0, 5,
                               "Good: ChaCha20-Poly1305")
                breakdown.cryptographic_score += 5
            elif "AES_128_GCM" in preferred_cipher.upper():
                self._add_factor(breakdown, "aes_128_gcm", RiskSeverity.LOW, 0.05, 20,
                               "Acceptable: AES-128-GCM - migrate to AES-256")
                breakdown.cryptographic_score += 20
            elif "AES_128" in preferred_cipher.upper():
                self._add_factor(breakdown, "aes_128_cbc", RiskSeverity.MEDIUM, 0.08, 25,
                               "Weak: AES-128-CBC - upgrade to AES-256-GCM")
                breakdown.cryptographic_score += 25
    
    def _score_certificate(
        self,
        certificate_key_algorithm: Optional[str],
        certificate_key_size: Optional[int],
        cert_signature_algorithm: Optional[str],
        cert_not_after: Optional[datetime],
        self_signed: bool,
        breakdown: RiskScoreBreakdown
    ):
        """Score certificate quality."""
        cert_score = 0.0
        now = datetime.now(timezone.utc)
        
        # Check if expired
        if cert_not_after and cert_not_after < now:
            self._add_factor(breakdown, "expired", RiskSeverity.CRITICAL, 0.20, 60,
                           "CRITICAL: Certificate is expired")
            cert_score += 60
        
        # Check expiration timeline
        elif cert_not_after:
            days_until = (cert_not_after - now).days
            if days_until < 30:
                self._add_factor(breakdown, "expiring_30_days", RiskSeverity.HIGH, 0.10, 30,
                               f"Certificate expires in {days_until} days - renew")
                cert_score += 30
            elif days_until < 90:
                self._add_factor(breakdown, "expiring_90_days", RiskSeverity.MEDIUM, 0.05, 15,
                               f"Certificate expires in {days_until} days - plan renewal")
                cert_score += 15
        
        # Check signature algorithm
        if cert_signature_algorithm:
            sig_upper = cert_signature_algorithm.upper()
            if "SHA1" in sig_upper:
                self._add_factor(breakdown, "weak_signature", RiskSeverity.CRITICAL, 0.10, 45,
                               "CRITICAL: SHA-1 signatures - upgrade certificate")
                cert_score += 45
            elif "MD5" in sig_upper:
                self._add_factor(breakdown, "weak_signature", RiskSeverity.CRITICAL, 0.10, 45,
                               "CRITICAL: MD5 signatures - upgrade certificate")
                cert_score += 45
        
        # Check self-signed
        if self_signed:
            self._add_factor(breakdown, "self_signed", RiskSeverity.HIGH, 0.10, 40,
                           "Self-signed certificate - use CA-signed")
            cert_score += 40
        
        # Check key algorithm and size
        if certificate_key_algorithm:
            algo_upper = certificate_key_algorithm.upper()
            
            if "RSA" in algo_upper:
                if certificate_key_size:
                    if certificate_key_size >= 4096:
                        self._add_factor(breakdown, "rsa_4096", RiskSeverity.INFO, 0.0, 0,
                                       "RSA: 4096 bit - excellent")
                    elif certificate_key_size >= 3072:
                        self._add_factor(breakdown, "rsa_3072", RiskSeverity.LOW, 0.02, 5,
                                       "RSA: 3072 bit - good")
                        cert_score += 5
                    elif certificate_key_size >= 2048:
                        self._add_factor(breakdown, "rsa_2048", RiskSeverity.MEDIUM, 0.08, 20,
                                       "RSA: 2048 bit - borderline for quantum era, upgrade to 3072+")
                        cert_score += 20
                    else:
                        self._add_factor(breakdown, "rsa_1024", RiskSeverity.CRITICAL, 0.20, 60,
                                       "CRITICAL: RSA key < 2048 bits - upgrade immediately")
                        cert_score += 60
            
            elif "ECC" in algo_upper or "EC" in algo_upper:
                if "P384" in algo_upper:
                    self._add_factor(breakdown, "ecc_p384", RiskSeverity.INFO, 0.0, 0,
                                   "ECC: P-384 - excellent")
                elif "P256" in algo_upper:
                    self._add_factor(breakdown, "ecc_p256", RiskSeverity.LOW, 0.02, 10,
                                   "ECC: P-256 - good, consider P-384")
                    cert_score += 10
        
        breakdown.certificate_score = min(100, cert_score)
    
    def _score_security_features(
        self,
        perfect_forward_secrecy: bool,
        ocsp_stapling: bool,
        hsts_enabled: bool,
        hsts_preload: bool,
        breakdown: RiskScoreBreakdown
    ):
        """Score security features."""
        feature_score = 0.0
        
        if not perfect_forward_secrecy:
            self._add_factor(breakdown, "missing_pfs", RiskSeverity.HIGH, 0.08, 25,
                           "Missing PFS - enables retroactive decryption")
            feature_score += 25
        else:
            self._add_factor(breakdown, "perfect_forward_secrecy", RiskSeverity.INFO, 0.0, -10,
                           "Perfect Forward Secrecy enabled")
            feature_score -= 10
        
        if ocsp_stapling:
            self._add_factor(breakdown, "ocsp_stapling", RiskSeverity.LOW, 0.02, -5,
                           "OCSP stapling enabled")
            feature_score -= 5
        
        if hsts_enabled:
            self._add_factor(breakdown, "hsts_enabled", RiskSeverity.LOW, 0.02, -5,
                           "HSTS enabled")
            feature_score -= 5
            
            if hsts_preload:
                self._add_factor(breakdown, "hsts_preload", RiskSeverity.INFO, 0.0, -10,
                               "HSTS preload list enabled")
                feature_score -= 10
        
        breakdown.configuration_score = max(0, min(100, feature_score))
    
    def _score_pqc_readiness(self, pqc_supported: bool, breakdown: RiskScoreBreakdown):
        """Score Post-Quantum Cryptography readiness."""
        if pqc_supported:
            breakdown.quantum_readiness_score = 0
        else:
            # No PQC support yet, but score based on crypto quality
            # Good classical crypto = foundation for PQC migration
            # Bad classical crypto = difficult to migrate to PQC
            breakdown.quantum_readiness_score = 50
    
    def _add_factor(
        self,
        breakdown: RiskScoreBreakdown,
        factor_id: str,
        severity: RiskSeverity,
        weight: float,
        points: float,
        description: str,
        nist_control: Optional[str] = None
    ):
        """Add a risk factor to the breakdown."""
        factor = RiskFactor(
            factor_id=factor_id,
            name=factor_id.replace("_", " ").title(),
            description=description,
            severity=severity,
            weight=weight,
            points=points,
            remediation=description,
            nist_control=nist_control
        )
        breakdown.factors.append(factor)
    
    def _calculate_category_scores(self, breakdown: RiskScoreBreakdown):
        """Calculate category-level scores."""
        # Already calculated per component
        pass
    
    def _calculate_final_score(self, breakdown: RiskScoreBreakdown):
        """Calculate final risk score from all factors."""
        total = sum(f.points for f in breakdown.factors)
        breakdown.total_score = min(100.0, max(0.0, total))
    
    def _determine_severity(self, breakdown: RiskScoreBreakdown):
        """Determine overall severity level."""
        if breakdown.total_score >= 80:
            breakdown.severity_level = RiskSeverity.CRITICAL
            breakdown.critical_action_required = True
            breakdown.days_to_remediation = 7
        elif breakdown.total_score >= 60:
            breakdown.severity_level = RiskSeverity.HIGH
            breakdown.critical_action_required = True
            breakdown.days_to_remediation = 30
        elif breakdown.total_score >= 40:
            breakdown.severity_level = RiskSeverity.MEDIUM
            breakdown.critical_action_required = False
            breakdown.days_to_remediation = 60
        elif breakdown.total_score >= 20:
            breakdown.severity_level = RiskSeverity.LOW
            breakdown.critical_action_required = False
            breakdown.days_to_remediation = 90
        else:
            breakdown.severity_level = RiskSeverity.INFO
            breakdown.critical_action_required = False
            breakdown.days_to_remediation = None
    
    def _calculate_trend(self, breakdown: RiskScoreBreakdown, previous_score: float):
        """Calculate score trend."""
        diff = previous_score - breakdown.total_score
        if diff > 5:
            breakdown.trend = "improving"
        elif diff < -5:
            breakdown.trend = "degrading"
        else:
            breakdown.trend = "stable"
