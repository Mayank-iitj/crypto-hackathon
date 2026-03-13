"""
Q-Shield Post-Quantum Cryptography Validation Engine
Evaluates PQC readiness and quantum threat assessment.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any

from app.core.logging import get_logger

logger = get_logger("pqc.validator")


class PQCAlgorithm(str, Enum):
    """NIST-standardized Post-Quantum Cryptography algorithms."""
    # Key Encapsulation Mechanisms (KEM)
    ML_KEM_512 = "ML-KEM-512"
    ML_KEM_768 = "ML-KEM-768"
    ML_KEM_1024 = "ML-KEM-1024"
    
    # Digital Signatures
    ML_DSA_44 = "ML-DSA-44"
    ML_DSA_65 = "ML-DSA-65"
    ML_DSA_87 = "ML-DSA-87"
    SLH_DSA_SHA2_128S = "SLH-DSA-SHA2-128s"
    SLH_DSA_SHA2_128F = "SLH-DSA-SHA2-128f"
    SLH_DSA_SHA2_192S = "SLH-DSA-SHA2-192s"
    SLH_DSA_SHA2_192F = "SLH-DSA-SHA2-192f"
    SLH_DSA_SHA2_256S = "SLH-DSA-SHA2-256s"
    SLH_DSA_SHA2_256F = "SLH-DSA-SHA2-256f"
    
    # Legacy pre-standardization names
    KYBER_512 = "Kyber-512"
    KYBER_768 = "Kyber-768"
    KYBER_1024 = "Kyber-1024"
    DILITHIUM_2 = "Dilithium-2"
    DILITHIUM_3 = "Dilithium-3"
    DILITHIUM_5 = "Dilithium-5"
    FALCON_512 = "FALCON-512"
    FALCON_1024 = "FALCON-1024"
    SPHINCS_SHA2_128S = "SPHINCS-SHA2-128s"
    SPHINCS_SHA2_128F = "SPHINCS-SHA2-128f"
    SPHINCS_SHA2_192S = "SPHINCS-SHA2-192s"
    SPHINCS_SHA2_192F = "SPHINCS-SHA2-192f"
    SPHINCS_SHA2_256S = "SPHINCS-SHA2-256s"
    SPHINCS_SHA2_256F = "SPHINCS-SHA2-256f"


class PQCReadinessLevel(str, Enum):
    """PQC readiness assessment levels."""
    FULLY_QUANTUM_SAFE = "fully_quantum_safe"
    PQC_READY = "pqc_ready"
    TRANSITIONAL = "transitional"
    VULNERABLE = "vulnerable"
    UNKNOWN = "unknown"


@dataclass
class QuantumThreat:
    """Represents a quantum-era threat to cryptography."""
    threat_id: str
    name: str
    description: str
    affected_algorithms: List[str]
    nist_reference: str
    severity: str  # critical, high, medium, low
    harvest_now_decrypt_later_risk: bool = False
    timeline_years: Optional[int] = None


@dataclass
class QuantumRiskAssessment:
    """Assessment of quantum cryptographic risk."""
    asset_id: str
    scan_timestamp: datetime
    
    # PQC Detection
    pqc_kem_detected: Optional[PQCAlgorithm] = None
    pqc_signature_detected: Optional[PQCAlgorithm] = None
    hybrid_kem_detected: bool = False
    hybrid_signature_detected: bool = False
    
    # Post-Quantum Ready (can be easily upgraded)
    uses_tls_1_3: bool = False
    uses_aes_256: bool = False
    uses_sha_384_or_better: bool = False
    uses_ecdhe: bool = False
    
    # Vulnerabilities
    rsa_key_size_bits: Optional[int] = None
    dh_key_size_bits: Optional[int] = None
    uses_sha1: bool = False
    uses_md5: bool = False
    uses_des_3des: bool = False
    uses_rc4: bool = False
    uses_rc2: bool = False
    uses_dsa: bool = False
    uses_tls_10_or_earlier: bool = False
    uses_tls_11: bool = False
    uses_aes_128_only: bool = False
    
    # Derived assessment
    readiness_level: PQCReadinessLevel = PQCReadinessLevel.UNKNOWN
    risk_score: float = 0.0
    threats: List[QuantumThreat] = field(default_factory=list)
    remediation_steps: List[str] = field(default_factory=list)
    days_until_quantum_threat: Optional[int] = None


class PQCValidator:
    """
    Main PQC validation engine.
    Assesses quantum cryptographic readiness based on NIST standards.
    """
    
    # NIST SP 800-208 recommendations
    CLASSICAL_THREAT_TIMELINE = 20  # Years until CRQC (Conservative Resistant Quantum Computer)
    
    # Security categories for PQC algorithms
    SECURITY_CATEGORIES = {
        # ML-KEM
        PQCAlgorithm.ML_KEM_512: 1,
        PQCAlgorithm.ML_KEM_768: 3,
        PQCAlgorithm.ML_KEM_1024: 5,
        # ML-DSA
        PQCAlgorithm.ML_DSA_44: 2,
        PQCAlgorithm.ML_DSA_65: 3,
        PQCAlgorithm.ML_DSA_87: 5,
        # Legacy names
        PQCAlgorithm.KYBER_512: 1,
        PQCAlgorithm.KYBER_768: 3,
        PQCAlgorithm.KYBER_1024: 5,
        PQCAlgorithm.DILITHIUM_2: 2,
        PQCAlgorithm.DILITHIUM_3: 3,
        PQCAlgorithm.DILITHIUM_5: 5,
    }

    # NIST-standardized sets used for strict PQC label eligibility.
    NIST_STANDARD_KEMS = {
        PQCAlgorithm.ML_KEM_512,
        PQCAlgorithm.ML_KEM_768,
        PQCAlgorithm.ML_KEM_1024,
    }
    NIST_STANDARD_SIGNATURES = {
        PQCAlgorithm.ML_DSA_44,
        PQCAlgorithm.ML_DSA_65,
        PQCAlgorithm.ML_DSA_87,
        PQCAlgorithm.SLH_DSA_SHA2_128S,
        PQCAlgorithm.SLH_DSA_SHA2_128F,
        PQCAlgorithm.SLH_DSA_SHA2_192S,
        PQCAlgorithm.SLH_DSA_SHA2_192F,
        PQCAlgorithm.SLH_DSA_SHA2_256S,
        PQCAlgorithm.SLH_DSA_SHA2_256F,
    }
    
    # Quantum threats dictionary
    QUANTUM_THREATS = {
        "rsa_harvest_now": QuantumThreat(
            threat_id="rsa_harvest_now",
            name="RSA Harvest-Now-Decrypt-Later",
            description="Adversaries harvest encrypted traffic today, decrypt with future QC",
            affected_algorithms=["RSA-2048", "RSA-3072"],
            nist_reference="NIST SP 800-208",
            severity="critical",
            harvest_now_decrypt_later_risk=True,
            timeline_years=15
        ),
        "ecdh_harvest_now": QuantumThreat(
            threat_id="ecdh_harvest_now",
            name="ECDH Harvest-Now-Decrypt-Later",
            description="ECDH without PFS susceptible to future QC attacks",
            affected_algorithms=["ECDH-P256", "ECDH-P384"],
            nist_reference="NIST SP 800-208",
            severity="critical",
            harvest_now_decrypt_later_risk=True,
            timeline_years=15
        ),
        "weak_crypto": QuantumThreat(
            threat_id="weak_crypto",
            name="Weak Classical Cryptography",
            description="SHA-1, DES, RC4 are already broken in classical setting",
            affected_algorithms=["SHA-1", "DES", "3DES", "RC4"],
            nist_reference="NIST SP 800-52",
            severity="critical",
            harvest_now_decrypt_later_risk=False,
        ),
        "insufficient_key_size": QuantumThreat(
            threat_id="insufficient_key_size",
            name="Insufficient Classical Key Size",
            description="RSA/DH < 2048 bits, AES-128 insufficient for long-term",
            affected_algorithms=["RSA-1024", "RSA-2048", "DH-1024", "AES-128"],
            nist_reference="NIST SP 800-208",
            severity="high",
            harvest_now_decrypt_later_risk=False,
        ),
        "missing_pfs": QuantumThreat(
            threat_id="missing_pfs",
            name="Missing Perfect Forward Secrecy",
            description="Static key exchange without PFS enables retroactive decryption",
            affected_algorithms=["RSA-KE", "Static-ECDH"],
            nist_reference="RFC 7539",
            severity="high",
            harvest_now_decrypt_later_risk=True,
        ),
    }
    
    def assess_tls_configuration(
        self,
        tls_version: Optional[str],
        cipher_suites: List[str],
        preferred_cipher: Optional[str],
        key_exchange: Optional[str],
        certificate_key_algorithm: Optional[str],
        certificate_key_size: Optional[int],
        signature_algorithm: Optional[str],
        perfect_forward_secrecy: bool = False,
        pqc_kem: Optional[str] = None,
        pqc_signature: Optional[str] = None,
        asset_id: str = "unknown"
    ) -> QuantumRiskAssessment:
        """
        Assess quantum cryptographic readiness of TLS configuration.
        Based on NIST SP 800-208 and NIST SP 800-52 Rev 1.
        """
        assessment = QuantumRiskAssessment(
            asset_id=asset_id,
            scan_timestamp=datetime.now(timezone.utc)
        )
        
        logger.info(f"Starting PQC assessment for asset {asset_id}")
        
        # Parse TLS version
        if tls_version:
            tls_version_upper = tls_version.upper()
            assessment.uses_tls_1_3 = "1.3" in tls_version_upper
            assessment.uses_tls_11 = "1.1" in tls_version_upper
            assessment.uses_tls_10_or_earlier = any(
                v in tls_version_upper for v in ["1.0", "SSL", "3.0"]
            )
        
        # Detect PQC algorithms
        self._detect_pqc(
            cipher_suites,
            preferred_cipher,
            pqc_kem,
            pqc_signature,
            signature_algorithm,
            assessment,
        )
        
        # Analyze classical crypto components
        self._analyze_key_exchange(key_exchange, perfect_forward_secrecy, assessment)
        self._analyze_certificate(
            certificate_key_algorithm, certificate_key_size, signature_algorithm, assessment
        )
        self._analyze_cipher_suites(cipher_suites, preferred_cipher, assessment)
        
        # Identify quantum threats
        self._identify_threats(assessment)
        
        # Calculate readiness level and risk score
        self._calculate_readiness_level(assessment)
        self._calculate_risk_score(assessment)
        
        # Generate remediation steps
        self._generate_remediation(assessment)
        
        logger.info(
            f"PQC assessment complete for {asset_id}: "
            f"Level={assessment.readiness_level}, Score={assessment.risk_score:.1f}"
        )
        
        return assessment
    
    def _detect_pqc(
        self,
        cipher_suites: List[str],
        preferred_cipher: Optional[str],
        pqc_kem: Optional[str],
        pqc_signature: Optional[str],
        certificate_signature_algorithm: Optional[str],
        assessment: QuantumRiskAssessment
    ):
        """Detect PQC algorithm support."""
        all_ciphers = " ".join(cipher_suites or [])
        
        # Check for ML-KEM (post-standardization)
        if any(name in all_ciphers for name in ["ML-KEM", "mlkem", "X25519MLKEM", "P256_MLKEM", "P384_MLKEM"]):
            assessment.hybrid_kem_detected = True
            if "768" in all_ciphers:
                assessment.pqc_kem_detected = PQCAlgorithm.ML_KEM_768
            elif "1024" in all_ciphers:
                assessment.pqc_kem_detected = PQCAlgorithm.ML_KEM_1024
            elif "512" in all_ciphers:
                assessment.pqc_kem_detected = PQCAlgorithm.ML_KEM_512
        
        # Check for legacy Kyber naming
        elif any(name in all_ciphers for name in ["Kyber", "kyber", "X25519Kyber"]):
            assessment.hybrid_kem_detected = True
            if "1024" in all_ciphers:
                assessment.pqc_kem_detected = PQCAlgorithm.KYBER_1024
            elif "768" in all_ciphers:
                assessment.pqc_kem_detected = PQCAlgorithm.KYBER_768
            elif "512" in all_ciphers:
                assessment.pqc_kem_detected = PQCAlgorithm.KYBER_512
        
        # Check for ML-DSA / Dilithium
        if any(name in all_ciphers for name in ["ML-DSA", "mldsa"]):
            assessment.hybrid_signature_detected = True
            if "87" in all_ciphers or "5" in all_ciphers:
                assessment.pqc_signature_detected = PQCAlgorithm.ML_DSA_87
            elif "65" in all_ciphers or "3" in all_ciphers:
                assessment.pqc_signature_detected = PQCAlgorithm.ML_DSA_65
            elif "44" in all_ciphers or "2" in all_ciphers:
                assessment.pqc_signature_detected = PQCAlgorithm.ML_DSA_44
        
        # Check explicit PQC parameters
        if pqc_kem:
            try:
                assessment.pqc_kem_detected = PQCAlgorithm(pqc_kem)
                assessment.hybrid_kem_detected = True
            except ValueError:
                logger.warning(f"Unknown PQC KEM: {pqc_kem}")
        
        if pqc_signature:
            try:
                assessment.pqc_signature_detected = PQCAlgorithm(pqc_signature)
                assessment.hybrid_signature_detected = True
            except ValueError:
                logger.warning(f"Unknown PQC Signature: {pqc_signature}")

        if not assessment.pqc_signature_detected and certificate_signature_algorithm:
            signature_upper = certificate_signature_algorithm.upper()
            if "ML-DSA-87" in signature_upper:
                assessment.pqc_signature_detected = PQCAlgorithm.ML_DSA_87
                assessment.hybrid_signature_detected = True
            elif "ML-DSA-65" in signature_upper:
                assessment.pqc_signature_detected = PQCAlgorithm.ML_DSA_65
                assessment.hybrid_signature_detected = True
            elif "ML-DSA-44" in signature_upper:
                assessment.pqc_signature_detected = PQCAlgorithm.ML_DSA_44
                assessment.hybrid_signature_detected = True
            elif "SLH-DSA" in signature_upper:
                assessment.pqc_signature_detected = PQCAlgorithm.SLH_DSA_SHA2_128S
                assessment.hybrid_signature_detected = True
    
    def _analyze_key_exchange(
        self,
        key_exchange: Optional[str],
        perfect_forward_secrecy: bool,
        assessment: QuantumRiskAssessment
    ):
        """Analyze key exchange mechanism."""
        if not key_exchange:
            return
        
        kex_upper = key_exchange.upper()
        
        # PQC key exchange (best case)
        if any(pqc in kex_upper for pqc in ["MLKEM", "KYBER"]):
            assessment.hybrid_kem_detected = True
        
        # ECDHE with PFS (good)
        elif "ECDHE" in kex_upper or "ECDH" in kex_upper:
            assessment.uses_ecdhe = True
            # ECDHE provides PFS, but still vulnerable to harvest-now attacks
            if not perfect_forward_secrecy:
                assessment.uses_tls_10_or_earlier = True
        
        # DHE with PFS (good but weaker than ECDHE)
        elif "DHE" in kex_upper:
            assessment.uses_ecdhe = True  # Treat DHE similarly
        
        # Static RSA (critical vulnerability)
        elif "RSA" in kex_upper:
            assessment.uses_ecdhe = False
    
    def _analyze_certificate(
        self,
        cert_key_algorithm: Optional[str],
        cert_key_size: Optional[int],
        signature_algorithm: Optional[str],
        assessment: QuantumRiskAssessment
    ):
        """Analyze certificate cryptography."""
        if not cert_key_algorithm:
            return
        
        # Detect RSA
        if "RSA" in cert_key_algorithm.upper():
            assessment.rsa_key_size_bits = cert_key_size
            
            # Check RSA key size
            if cert_key_size and cert_key_size < 2048:
                assessment.rsa_key_size_bits = cert_key_size
            elif cert_key_size and cert_key_size < 3072:
                # RSA-2048 is borderline; marginal against quantum threats
                pass
        
        # Detect DH
        elif "DH" in cert_key_algorithm.upper():
            assessment.dh_key_size_bits = cert_key_size
        
        # Detect signature algorithm weaknesses
        if signature_algorithm:
            sig_upper = signature_algorithm.upper()
            if "SHA1" in sig_upper or "MD5" in sig_upper:
                assessment.uses_sha1 = True
            if "MD5" in sig_upper:
                assessment.uses_md5 = True
    
    def _analyze_cipher_suites(
        self,
        cipher_suites: List[str],
        preferred_cipher: Optional[str],
        assessment: QuantumRiskAssessment
    ):
        """Analyze encryption cipher suites."""
        all_ciphers = " ".join(cipher_suites or [])
        
        # Check for weak ciphers
        weak_ciphers = {
            "DES": (assessment, "uses_des_3des"),
            "3DES": (assessment, "uses_des_3des"),
            "RC4": (assessment, "uses_rc4"),
            "RC2": (assessment, "uses_rc2"),
        }
        
        for weak_name, (obj, attr) in weak_ciphers.items():
            if weak_name.upper() in all_ciphers.upper():
                setattr(obj, attr, True)
        
        # Check for AES size
        if "AES" in all_ciphers:
            if "AES_256" in all_ciphers or "AES-256" in all_ciphers:
                assessment.uses_aes_256 = True
            elif "AES_128" in all_ciphers or "AES-128" in all_ciphers:
                assessment.uses_aes_128_only = True
        
        # Check for SHA-384+
        if "SHA384" in all_ciphers or "SHA256" in all_ciphers:
            assessment.uses_sha_384_or_better = True
    
    def _identify_threats(self, assessment: QuantumRiskAssessment):
        """Identify applicable quantum threats."""
        threats = []
        
        if assessment.uses_tls_10_or_earlier or assessment.uses_tls_11:
            threats.append("rsa_harvest_now")
            threats.append("ecdh_harvest_now")
        
        if assessment.rsa_key_size_bits and assessment.rsa_key_size_bits < 3072:
            threats.append("rsa_harvest_now")
        
        if assessment.dh_key_size_bits and assessment.dh_key_size_bits < 2048:
            threats.append("ecdh_harvest_now")
        
        if assessment.uses_sha1 or assessment.uses_md5 or assessment.uses_des_3des or assessment.uses_rc4:
            threats.append("weak_crypto")
        
        if assessment.uses_aes_128_only and not assessment.uses_tls_1_3:
            threats.append("insufficient_key_size")
        
        if not assessment.uses_ecdhe and not assessment.hybrid_kem_detected:
            threats.append("missing_pfs")
        
        # Populate threat details
        for threat_id in threats:
            if threat_id in self.QUANTUM_THREATS:
                assessment.threats.append(self.QUANTUM_THREATS[threat_id])
    
    def _calculate_readiness_level(self, assessment: QuantumRiskAssessment):
        """Determine PQC readiness level."""
        has_nist_kem = assessment.pqc_kem_detected in self.NIST_STANDARD_KEMS
        has_nist_signature = assessment.pqc_signature_detected in self.NIST_STANDARD_SIGNATURES
        has_any_pqc = bool(assessment.pqc_kem_detected or assessment.pqc_signature_detected)

        # FULLY_QUANTUM_SAFE: NIST-standard PQC for both KEM and signatures with strong baseline.
        if (
            has_nist_kem and
            has_nist_signature and
            assessment.uses_tls_1_3 and
            assessment.uses_ecdhe and
            assessment.uses_aes_256 and
            assessment.uses_sha_384_or_better
        ):
            assessment.readiness_level = PQCReadinessLevel.FULLY_QUANTUM_SAFE
            return
        
        # PQC_READY: At least one NIST-standard PQC primitive in a hybrid-ready baseline.
        if (
            (has_nist_kem or has_nist_signature) and
            assessment.uses_tls_1_3 and
            assessment.uses_ecdhe and
            assessment.uses_aes_256 and
            assessment.uses_sha_384_or_better
        ):
            assessment.readiness_level = PQCReadinessLevel.PQC_READY
            return
        
        # TRANSITIONAL: Strong modern TLS posture or legacy/non-standard PQC signals.
        if (
            (assessment.uses_tls_1_3 and assessment.uses_ecdhe and assessment.uses_aes_256) or
            has_any_pqc
        ):
            assessment.readiness_level = PQCReadinessLevel.TRANSITIONAL
            return
        
        # VULNERABLE: Weak or missing modern crypto
        if (assessment.uses_sha1 or 
            assessment.uses_des_3des or 
            assessment.uses_rc4 or
            assessment.uses_tls_10_or_earlier or
            assessment.uses_tls_11):
            assessment.readiness_level = PQCReadinessLevel.VULNERABLE
            return
        
        assessment.readiness_level = PQCReadinessLevel.UNKNOWN
    
    def _calculate_risk_score(self, assessment: QuantumRiskAssessment):
        """Calculate risk score (0-100)."""
        score = 0.0
        max_score = 100.0
        
        # Existential quantum threats (40 points)
        if assessment.uses_tls_10_or_earlier or assessment.uses_tls_11:
            score += 40
        elif assessment.rsa_key_size_bits and assessment.rsa_key_size_bits < 2048:
            score += 35
        elif assessment.rsa_key_size_bits and assessment.rsa_key_size_bits < 3072:
            score += 25
        elif not assessment.uses_ecdhe and not assessment.pqc_kem_detected:
            score += 20
        
        # Classical crypto weaknesses (30 points)
        if assessment.uses_sha1:
            score += 15
        if assessment.uses_md5:
            score += 20
        if assessment.uses_des_3des:
            score += 25
        if assessment.uses_rc4:
            score += 20
        
        # Missing modern crypto (20 points)
        if not assessment.uses_tls_1_3:
            score += 15
        if assessment.uses_aes_128_only:
            score += 10
        
        # PQC detection (reduce score)
        if assessment.pqc_kem_detected:
            score = max(0, score - 40)
        if assessment.pqc_signature_detected:
            score = max(0, score - 30)
        
        assessment.risk_score = min(100.0, score)
    
    def _generate_remediation(self, assessment: QuantumRiskAssessment):
        """Generate remediation steps."""
        steps = []
        
        # Immediate critical actions
        if assessment.uses_tls_10_or_earlier or assessment.uses_tls_11:
            steps.append("CRITICAL: Update to TLS 1.2 minimum (TLS 1.3 preferred)")
        
        if assessment.uses_sha1 or assessment.uses_md5:
            steps.append("CRITICAL: Update certificate signature algorithm to SHA-256 or stronger")
        
        if assessment.uses_des_3des or assessment.uses_rc4:
            steps.append("CRITICAL: Disable 3DES and RC4 cipher suites")
        
        if assessment.rsa_key_size_bits and assessment.rsa_key_size_bits < 2048:
            steps.append("CRITICAL: Increase RSA key size to 2048 bits or greater")
        
        # High priority actions
        if assessment.rsa_key_size_bits and assessment.rsa_key_size_bits < 3072:
            steps.append("HIGH: Migrate RSA keys from 2048 to 3072 bits (or 4096)")
        
        if not assessment.uses_tls_1_3:
            steps.append("HIGH: Upgrade to TLS 1.3")
        
        if not assessment.uses_ecdhe:
            steps.append("HIGH: Enable ECDHE for Perfect Forward Secrecy")
        
        if assessment.uses_aes_128_only:
            steps.append("HIGH: Upgrade from AES-128 to AES-256")
        
        # Medium priority (PQC migration)
        if not assessment.pqc_kem_detected:
            steps.append("MEDIUM: Evaluate and deploy hybrid ML-KEM key exchange")
        
        if not assessment.pqc_signature_detected:
            steps.append("MEDIUM: Evaluate and deploy ML-DSA digital signatures")
        
        # Network configuration
        steps.append("CONFIG: Configure HSTS with preload list")
        steps.append("CONFIG: Enable OCSP stapling")
        steps.append("CONFIG: Implement certificate pinning for APIs")
        
        assessment.remediation_steps = steps
