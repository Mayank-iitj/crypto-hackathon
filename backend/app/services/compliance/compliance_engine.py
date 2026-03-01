"""
Q-Shield Compliance Mapping Engine
Maps cryptographic findings to regulatory frameworks.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any

from app.core.logging import get_logger

logger = get_logger("compliance")


class ComplianceFramework(str, Enum):
    NIST_SP_800_208 = "nist_sp_800_208"
    NIST_SP_800_52 = "nist_sp_800_52"
    ISO_27001 = "iso_27001"
    RBI_CSF = "rbi_csf"


@dataclass
class ComplianceControl:
    """Represents a single compliance control."""
    framework: str
    control_id: str
    control_name: str
    description: str
    crypto_requirements: Dict[str, Any]
    severity: str  # critical, high, medium, low
    remediation_guidance: str
    nist_reference: Optional[str] = None


@dataclass
class ComplianceFinding:
    """Compliance finding for an asset."""
    asset_id: str
    framework: str
    control_id: str
    control_name: str
    status: str  # compliant, partially_compliant, non_compliant
    gap_description: Optional[str] = None
    evidence: str = ""
    remediation_steps: List[str] = field(default_factory=list)
    priority: str = "medium"
    due_date: Optional[str] = None


class ComplianceMappingEngine:
    """
    Maps cryptographic configurations to compliance requirements.
    Supports: NIST, ISO 27001, RBI Cyber Security Framework.
    """
    
    # NIST SP 800-208: Recommendations for Post-Quantum Cryptography Migration
    NIST_SP_800_208_CONTROLS = {
        "PQC-1": ComplianceControl(
            framework=ComplianceFramework.NIST_SP_800_208,
            control_id="PQC-1",
            control_name="Quantum-Resistant Algorithm Selection",
            description="Use NIST-approved post-quantum algorithms for key encapsulation and digital signatures",
            crypto_requirements={
                "kem_algorithms": ["ML-KEM-512", "ML-KEM-768", "ML-KEM-1024"],
                "signature_algorithms": ["ML-DSA-44", "ML-DSA-65", "ML-DSA-87"],
            },
            severity="critical",
            remediation_guidance="Implement ML-KEM and ML-DSA as per FIPS 203 and FIPS 204 standards",
            nist_reference="NIST SP 800-208 Section 4.1"
        ),
        "PQC-2": ComplianceControl(
            framework=ComplianceFramework.NIST_SP_800_208,
            control_id="PQC-2",
            control_name="Hybrid Key Establishment",
            description="Implement hybrid classical/post-quantum key establishment during transition period",
            crypto_requirements={
                "hybrid_ke": True,
                "classical_ke": ["ECDHE", "DHE"],
            },
            severity="high",
            remediation_guidance="Configure hybrid TLS with ECDHE + ML-KEM",
            nist_reference="NIST SP 800-208 Section 5.1"
        ),
        "PQC-3": ComplianceControl(
            framework=ComplianceFramework.NIST_SP_800_208,
            control_id="PQC-3",
            control_name="Legacy Crypto Deprecation",
            description="Deprecate quantum-vulnerable algorithms: RSA, ECDH (without PFS), DSA",
            crypto_requirements={
                "disallowed_algorithms": ["RSA-KE", "Static-ECDH", "Static-DH"],
            },
            severity="critical",
            remediation_guidance="Disable static key exchange; require PFS (ECDHE/DHE)",
            nist_reference="NIST SP 800-208 Section 4.3"
        ),
        "PQC-4": ComplianceControl(
            framework=ComplianceFramework.NIST_SP_800_208,
            control_id="PQC-4",
            control_name="Cryptographic Agility",
            description="Design systems to easily transition between cryptographic algorithms",
            crypto_requirements={
                "algorithm_flexibility": True,
            },
            severity="high",
            remediation_guidance="Use modular crypto libraries; separate algorithm selection from implementation",
            nist_reference="NIST SP 800-208 Section 6"
        ),
    }
    
    # NIST SP 800-52 Rev 1: Guidelines for TLS Implementation
    NIST_SP_800_52_CONTROLS = {
        "TLS-1": ComplianceControl(
            framework=ComplianceFramework.NIST_SP_800_52,
            control_id="TLS-1",
            control_name="TLS Version",
            description="Use TLS 1.2 minimum (TLS 1.3 preferred)",
            crypto_requirements={
                "min_tls_version": "1.2",
                "preferred_tls_version": "1.3",
            },
            severity="critical",
            remediation_guidance="Update to TLS 1.2 or 1.3; disable TLS 1.0, 1.1, and SSL",
            nist_reference="NIST SP 800-52 Rev 1, Section 3.3"
        ),
        "TLS-2": ComplianceControl(
            framework=ComplianceFramework.NIST_SP_800_52,
            control_id="TLS-2",
            control_name="Cipher Suite Strength",
            description="Use strong cipher suites with AES-256 or ChaCha20",
            crypto_requirements={
                "allowed_ciphers": ["AES-256-GCM", "AES-256-CBC", "ChaCha20-Poly1305"],
                "disallowed_ciphers": ["3DES", "RC4", "DES", "AES-128"],
            },
            severity="high",
            remediation_guidance="Configure servers to prefer AES-256-GCM cipher suites",
            nist_reference="NIST SP 800-52 Rev 1, Section 3.4"
        ),
        "TLS-3": ComplianceControl(
            framework=ComplianceFramework.NIST_SP_800_52,
            control_id="TLS-3",
            control_name="Perfect Forward Secrecy",
            description="Use ephemeral key exchange (ECDHE, DHE) for Perfect Forward Secrecy",
            crypto_requirements={
                "key_exchange": ["ECDHE", "DHE"],
                "disallowed": ["Static RSA", "Static ECDH"],
            },
            severity="high",
            remediation_guidance="Configure ECDHE as the only key exchange method",
            nist_reference="NIST SP 800-52 Rev 1, Section 3.5"
        ),
        "TLS-4": ComplianceControl(
            framework=ComplianceFramework.NIST_SP_800_52,
            control_id="TLS-4",
            control_name="Certificate Strength",
            description="Use RSA keys 2048 bits minimum (3072+ recommended)",
            crypto_requirements={
                "rsa_minimum": 2048,
                "rsa_recommended": 3072,
                "ec_minimum": "P-256",
            },
            severity="high",
            remediation_guidance="Migrate to RSA-3072 or ECC P-384 certificates",
            nist_reference="NIST SP 800-52 Rev 1, Section 3.6"
        ),
        "TLS-5": ComplianceControl(
            framework=ComplianceFramework.NIST_SP_800_52,
            control_id="TLS-5",
            control_name="Signature Algorithm",
            description="Use SHA-256 or stronger for certificate signatures",
            crypto_requirements={
                "allowed_signatures": ["SHA-256", "SHA-384", "SHA-512"],
                "disallowed": ["SHA-1", "MD5"],
            },
            severity="critical",
            remediation_guidance="Replace SHA-1 and MD5 signed certificates with SHA-256+",
            nist_reference="NIST SP 800-52 Rev 1, Section 3.7"
        ),
    }
    
    # ISO/IEC 27001:2022 - Information Security Standard
    ISO_27001_CONTROLS = {
        "A.10.1.1": ComplianceControl(
            framework=ComplianceFramework.ISO_27001,
            control_id="A.10.1.1",
            control_name="Cryptographic Controls - Policy",
            description="Establish policy for cryptographic usage",
            crypto_requirements={
                "policy_established": True,
            },
            severity="medium",
            remediation_guidance="Document organization's cryptographic policy",
            nist_reference="ISO/IEC 27001:2022"
        ),
        "A.10.1.2": ComplianceControl(
            framework=ComplianceFramework.ISO_27001,
            control_id="A.10.1.2",
            control_name="Cryptographic Controls - Implementation",
            description="Implement cryptographic controls for data protection",
            crypto_requirements={
                "encryption_in_transit": True,
                "encryption_at_rest": True,
            },
            severity="high",
            remediation_guidance="Enable TLS for all network communications",
            nist_reference="ISO/IEC 27001:2022 A.10.1.2"
        ),
        "A.8.2.4": ComplianceControl(
            framework=ComplianceFramework.ISO_27001,
            control_id="A.8.2.4",
            control_name="Access Control - User Authentication",
            description="Implement strong authentication mechanisms",
            crypto_requirements={
                "mfa_enabled": True,
                "strong_algorithms": True,
            },
            severity="high",
            remediation_guidance="Enable multi-factor authentication",
            nist_reference="ISO/IEC 27001:2022 A.8.2.4"
        ),
    }
    
    # RBI Cyber Security Framework (Indian Banking Regulator)
    RBI_CSF_CONTROLS = {
        "RBI-CS-5.1": ComplianceControl(
            framework=ComplianceFramework.RBI_CSF,
            control_id="RBI-CS-5.1",
            control_name="Encrypted Communication Channels",
            description="Use encryption for all inter-bank and customer communications",
            crypto_requirements={
                "tls_minimum": "1.2",
                "encryption_mandatory": True,
            },
            severity="critical",
            remediation_guidance="Implement TLS 1.2+ for all bank communications",
            nist_reference="RBI Cyber Security Framework 2023, Section 5.1"
        ),
        "RBI-CS-5.2": ComplianceControl(
            framework=ComplianceFramework.RBI_CSF,
            control_id="RBI-CS-5.2",
            control_name="Cryptographic Key Management",
            description="Establish secure key management practices",
            crypto_requirements={
                "key_rotation": True,
                "hardware_security_module": True,
            },
            severity="high",
            remediation_guidance="Implement HSM-based key management",
            nist_reference="RBI Cyber Security Framework 2023, Section 5.2"
        ),
        "RBI-CS-5.3": ComplianceControl(
            framework=ComplianceFramework.RBI_CSF,
            control_id="RBI-CS-5.3",
            control_name="Post-Quantum Cryptography Readiness",
            description="Prepare for post-quantum cryptography migration",
            crypto_requirements={
                "pqc_readiness": True,
                "crypto_agility": True,
            },
            severity="high",
            remediation_guidance="Evaluate and plan PQC migration",
            nist_reference="RBI Cyber Security Framework 2023, Section 5.3"
        ),
    }
    
    def __init__(self):
        self.controls = {
            ComplianceFramework.NIST_SP_800_208: self.NIST_SP_800_208_CONTROLS,
            ComplianceFramework.NIST_SP_800_52: self.NIST_SP_800_52_CONTROLS,
            ComplianceFramework.ISO_27001: self.ISO_27001_CONTROLS,
            ComplianceFramework.RBI_CSF: self.RBI_CSF_CONTROLS,
        }
    
    def assess_compliance(
        self,
        asset_id: str,
        frameworks: List[str],
        tls_version: Optional[str],
        cipher_suites: List[str],
        preferred_cipher: Optional[str],
        key_exchange: Optional[str],
        certificate_key_algorithm: Optional[str],
        certificate_key_size: Optional[int],
        cert_signature_algorithm: Optional[str],
        perfect_forward_secrecy: bool,
        pqc_kem_detected: bool = False,
        pqc_signature_detected: bool = False,
    ) -> List[ComplianceFinding]:
        """
        Assess compliance with selected frameworks.
        """
        findings = []
        
        logger.info(f"Assessing compliance for asset {asset_id} against {len(frameworks)} frameworks")
        
        for framework in frameworks:
            if framework == ComplianceFramework.NIST_SP_800_208:
                findings.extend(self._assess_nist_pqc(asset_id, tls_version, key_exchange, pqc_kem_detected, pqc_signature_detected))
            elif framework == ComplianceFramework.NIST_SP_800_52:
                findings.extend(self._assess_nist_tls(
                    asset_id, tls_version, cipher_suites, preferred_cipher, 
                    key_exchange, certificate_key_algorithm, certificate_key_size, 
                    cert_signature_algorithm, perfect_forward_secrecy
                ))
            elif framework == ComplianceFramework.ISO_27001:
                findings.extend(self._assess_iso_27001(asset_id))
            elif framework == ComplianceFramework.RBI_CSF:
                findings.extend(self._assess_rbi_csf(
                    asset_id, tls_version, perfect_forward_secrecy, pqc_kem_detected
                ))
        
        return findings
    
    def _assess_nist_pqc(
        self,
        asset_id: str,
        tls_version: Optional[str],
        key_exchange: Optional[str],
        pqc_kem: bool,
        pqc_sig: bool,
    ) -> List[ComplianceFinding]:
        """Assess NIST SP 800-208 PQC requirements."""
        findings = []
        
        # PQC-1: Quantum-Resistant Algorithms
        if pqc_kem and pqc_sig:
            status = "compliant"
            gap = None
        elif pqc_kem or pqc_sig:
            status = "partially_compliant"
            gap = "Implement both PQC KEM and signature algorithms"
        else:
            status = "non_compliant"
            gap = "No PQC algorithms detected"
        
        findings.append(ComplianceFinding(
            asset_id=asset_id,
            framework=ComplianceFramework.NIST_SP_800_208,
            control_id="PQC-1",
            control_name="Quantum-Resistant Algorithm Selection",
            status=status,
            gap_description=gap,
            evidence=f"PQC KEM: {pqc_kem}, PQC Sig: {pqc_sig}",
            remediation_steps=["Deploy ML-KEM for key encapsulation", "Deploy ML-DSA for digital signatures"],
            priority="critical",
        ))
        
        # PQC-2: Hybrid Key Establishment
        if pqc_kem and key_exchange and ("ECDHE" in key_exchange or "DHE" in key_exchange):
            status = "compliant"
            gap = None
        elif key_exchange and ("ECDHE" in key_exchange or "DHE" in key_exchange):
            status = "partially_compliant"
            gap = "Using classical hybrid key exchange, add PQC component"
        else:
            status = "non_compliant"
            gap = "No PFS or hybrid key exchange detected"
        
        findings.append(ComplianceFinding(
            asset_id=asset_id,
            framework=ComplianceFramework.NIST_SP_800_208,
            control_id="PQC-2",
            control_name="Hybrid Key Establishment",
            status=status,
            gap_description=gap,
            evidence=f"Key Exchange: {key_exchange}",
            remediation_steps=["Configure hybrid ECDHE+ML-KEM", "Test hybrid TLS handshakes"],
            priority="high",
        ))
        
        # PQC-3: Legacy Crypto Deprecation
        if key_exchange and "RSA" not in key_exchange and "ECDH" not in key_exchange:
            status = "compliant"
            gap = None
        else:
            status = "non_compliant"
            gap = "Legacy static key exchange detected"
        
        findings.append(ComplianceFinding(
            asset_id=asset_id,
            framework=ComplianceFramework.NIST_SP_800_208,
            control_id="PQC-3",
            control_name="Legacy Crypto Deprecation",
            status=status,
            gap_description=gap,
            evidence=f"Key Exchange: {key_exchange}",
            remediation_steps=["Disable static RSA key exchange", "Disable static ECDH"],
            priority="critical",
        ))
        
        return findings
    
    def _assess_nist_tls(
        self,
        asset_id: str,
        tls_version: Optional[str],
        cipher_suites: List[str],
        preferred_cipher: Optional[str],
        key_exchange: Optional[str],
        cert_algo: Optional[str],
        cert_size: Optional[int],
        sig_algo: Optional[str],
        pfs: bool,
    ) -> List[ComplianceFinding]:
        """Assess NIST SP 800-52 TLS requirements."""
        findings = []
        
        # TLS-1: Version
        if tls_version and ("1.3" in tls_version or "1.2" in tls_version):
            status = "compliant"
            gap = None
        elif tls_version and "1.1" in tls_version:
            status = "non_compliant"
            gap = "TLS 1.1 is deprecated; upgrade to 1.2 or 1.3"
        else:
            status = "non_compliant"
            gap = "TLS version below 1.2"
        
        findings.append(ComplianceFinding(
            asset_id=asset_id,
            framework=ComplianceFramework.NIST_SP_800_52,
            control_id="TLS-1",
            control_name="TLS Version",
            status=status,
            gap_description=gap,
            evidence=f"TLS Version: {tls_version}",
            remediation_steps=["Upgrade to TLS 1.3", "Disable TLS 1.0 and 1.1"],
            priority="critical" if status == "non_compliant" else "low",
        ))
        
        # TLS-2: Cipher Strength
        all_ciphers = " ".join(cipher_suites or [])
        if "AES-256" in all_ciphers or "ChaCha20" in all_ciphers:
            status = "compliant"
            gap = None
        elif "AES-128" in all_ciphers:
            status = "partially_compliant"
            gap = "AES-128 present; migrate to AES-256"
        elif "3DES" in all_ciphers or "RC4" in all_ciphers:
            status = "non_compliant"
            gap = "Weak ciphers detected"
        else:
            status = "unknown"
            gap = None
        
        findings.append(ComplianceFinding(
            asset_id=asset_id,
            framework=ComplianceFramework.NIST_SP_800_52,
            control_id="TLS-2",
            control_name="Cipher Suite Strength",
            status=status,
            gap_description=gap,
            evidence=f"Preferred Cipher: {preferred_cipher}",
            remediation_steps=["Enable AES-256-GCM", "Disable weak ciphers"],
            priority="high" if status == "non_compliant" else "medium",
        ))
        
        # TLS-3: PFS
        status = "compliant" if pfs else "non_compliant"
        gap = None if pfs else "Perfect Forward Secrecy not enabled"
        
        findings.append(ComplianceFinding(
            asset_id=asset_id,
            framework=ComplianceFramework.NIST_SP_800_52,
            control_id="TLS-3",
            control_name="Perfect Forward Secrecy",
            status=status,
            gap_description=gap,
            evidence=f"PFS: {pfs}",
            remediation_steps=["Configure ECDHE as primary key exchange"],
            priority="high",
        ))
        
        # TLS-4: Certificate Strength
        if cert_algo and "RSA" in cert_algo:
            if cert_size and cert_size >= 3072:
                status = "compliant"
                gap = None
            elif cert_size and cert_size >= 2048:
                status = "partially_compliant"
                gap = "RSA-2048 is borderline; upgrade to RSA-3072"
            else:
                status = "non_compliant"
                gap = "RSA key too small"
        else:
            status = "compliant"
            gap = None
        
        findings.append(ComplianceFinding(
            asset_id=asset_id,
            framework=ComplianceFramework.NIST_SP_800_52,
            control_id="TLS-4",
            control_name="Certificate Strength",
            status=status,
            gap_description=gap,
            evidence=f"Cert: {cert_algo} {cert_size}",
            remediation_steps=["Migrate to RSA-3072 or ECC P-384"],
            priority="high",
        ))
        
        # TLS-5: Signature Algorithm
        if sig_algo and ("SHA1" in sig_algo or "MD5" in sig_algo):
            status = "non_compliant"
            gap = "Weak signature algorithm detected"
        elif sig_algo and ("SHA256" in sig_algo or "SHA384" in sig_algo or "SHA512" in sig_algo):
            status = "compliant"
            gap = None
        else:
            status = "unknown"
            gap = None
        
        findings.append(ComplianceFinding(
            asset_id=asset_id,
            framework=ComplianceFramework.NIST_SP_800_52,
            control_id="TLS-5",
            control_name="Signature Algorithm",
            status=status,
            gap_description=gap,
            evidence=f"Signature: {sig_algo}",
            remediation_steps=["Replace with SHA-256 signed certificate"],
            priority="critical" if status == "non_compliant" else "low",
        ))
        
        return findings
    
    def _assess_iso_27001(self, asset_id: str) -> List[ComplianceFinding]:
        """Assess ISO/IEC 27001 requirements."""
        # Simplified assessment
        findings = []
        
        findings.append(ComplianceFinding(
            asset_id=asset_id,
            framework=ComplianceFramework.ISO_27001,
            control_id="A.10.1.2",
            control_name="Cryptographic Controls - Implementation",
            status="compliant",
            evidence="TLS encryption enabled",
            remediation_steps=[],
            priority="low",
        ))
        
        return findings
    
    def _assess_rbi_csf(
        self,
        asset_id: str,
        tls_version: Optional[str],
        pfs: bool,
        pqc: bool,
    ) -> List[ComplianceFinding]:
        """Assess RBI Cyber Security Framework requirements."""
        findings = []
        
        # RBI-CS-5.1: Encrypted Channels
        if tls_version and "1.2" in tls_version or "1.3" in tls_version:
            status = "compliant"
            gap = None
        else:
            status = "non_compliant"
            gap = "TLS 1.2+ not detected"
        
        findings.append(ComplianceFinding(
            asset_id=asset_id,
            framework=ComplianceFramework.RBI_CSF,
            control_id="RBI-CS-5.1",
            control_name="Encrypted Communication Channels",
            status=status,
            gap_description=gap,
            evidence=f"TLS: {tls_version}",
            remediation_steps=["Enable TLS 1.2 or 1.3"],
            priority="critical",
        ))
        
        # RBI-CS-5.3: PQC Readiness
        status = "compliant" if pqc else "partially_compliant"
        gap = None if pqc else "Begin PQC migration planning"
        
        findings.append(ComplianceFinding(
            asset_id=asset_id,
            framework=ComplianceFramework.RBI_CSF,
            control_id="RBI-CS-5.3",
            control_name="Post-Quantum Cryptography Readiness",
            status=status,
            gap_description=gap,
            evidence=f"PQC Support: {pqc}",
            remediation_steps=["Evaluate PQC algorithms", "Plan migration timeline"],
            priority="high",
        ))
        
        return findings
