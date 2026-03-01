"""
Q-Shield TLS/Cryptographic Fingerprinting Engine
Performs real TLS handshakes and extracts cryptographic configurations.
"""

import asyncio
import ssl
import socket
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import struct

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec, dsa, ed25519, ed448
from cryptography.x509.oid import ExtensionOID, NameOID
import OpenSSL.SSL
import OpenSSL.crypto

from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger("crypto.fingerprint")


class TLSVersion(str, Enum):
    SSL_3_0 = "SSLv3"
    TLS_1_0 = "TLSv1.0"
    TLS_1_1 = "TLSv1.1"
    TLS_1_2 = "TLSv1.2"
    TLS_1_3 = "TLSv1.3"
    UNKNOWN = "Unknown"


@dataclass
class CertificateInfo:
    """Parsed certificate information."""
    subject: str
    issuer: str
    serial_number: str
    not_before: datetime
    not_after: datetime
    public_key_algorithm: str
    public_key_size: int
    signature_algorithm: str
    san: List[str] = field(default_factory=list)
    fingerprint_sha256: str = ""
    is_self_signed: bool = False
    is_expired: bool = False
    days_until_expiry: int = 0
    key_usage: List[str] = field(default_factory=list)
    extended_key_usage: List[str] = field(default_factory=list)
    raw_pem: str = ""


@dataclass
class TLSConfiguration:
    """Complete TLS configuration of a target."""
    hostname: str
    ip_address: str
    port: int
    
    # Connection status
    is_accessible: bool = False
    error_message: Optional[str] = None
    
    # TLS Version
    tls_version: Optional[TLSVersion] = None
    supported_tls_versions: List[TLSVersion] = field(default_factory=list)
    
    # Cipher suites
    cipher_suites: List[str] = field(default_factory=list)
    preferred_cipher: Optional[str] = None
    
    # Key exchange
    key_exchange: Optional[str] = None
    key_exchange_group: Optional[str] = None
    key_exchange_strength: Optional[int] = None
    
    # Security features
    perfect_forward_secrecy: bool = False
    session_resumption: Optional[str] = None  # "tickets", "ids", "both", "none"
    ocsp_stapling: bool = False
    
    # HTTP security
    hsts_enabled: bool = False
    hsts_max_age: Optional[int] = None
    hsts_include_subdomains: bool = False
    hsts_preload: bool = False
    
    # ALPN
    alpn_protocols: List[str] = field(default_factory=list)
    
    # Certificate chain
    certificates: List[CertificateInfo] = field(default_factory=list)
    chain_valid: bool = False
    chain_issues: List[str] = field(default_factory=list)
    
    # OCSP status
    ocsp_status: Optional[str] = None  # "good", "revoked", "unknown"
    
    # PQC indicators (populated by PQC engine)
    pqc_key_encapsulation: Optional[str] = None
    pqc_signature: Optional[str] = None
    hybrid_mode: bool = False
    
    # Raw data for detailed analysis
    raw_handshake: Dict = field(default_factory=dict)
    
    # Scan metadata
    scan_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    scan_duration_ms: int = 0


class CipherSuiteAnalyzer:
    """Analyze cipher suite security properties."""
    
    # Cipher suite components classification
    KEY_EXCHANGE_STRENGTH = {
        "ECDHE": {"pfs": True, "strength": "strong"},
        "DHE": {"pfs": True, "strength": "strong"},
        "ECDH": {"pfs": False, "strength": "medium"},
        "DH": {"pfs": False, "strength": "medium"},
        "RSA": {"pfs": False, "strength": "weak"},
        "PSK": {"pfs": False, "strength": "varies"},
    }
    
    BULK_CIPHER_STRENGTH = {
        "AES_256_GCM": "strong",
        "AES_128_GCM": "strong",
        "CHACHA20_POLY1305": "strong",
        "AES_256_CBC": "medium",
        "AES_128_CBC": "medium",
        "3DES_EDE_CBC": "weak",
        "DES_CBC": "critical",
        "RC4": "critical",
        "NULL": "critical",
    }
    
    HASH_STRENGTH = {
        "SHA384": "strong",
        "SHA256": "strong",
        "SHA": "weak",  # SHA-1
        "MD5": "critical",
    }
    
    # PQC cipher suites (TLS 1.3 with hybrid key exchange)
    PQC_INDICATORS = [
        "X25519MLKEM768",
        "MLKEM768",
        "MLKEM1024", 
        "P256_MLKEM768",
        "P384_MLKEM1024",
        "X25519Kyber768",  # Pre-standardization name
        "Kyber512",
        "Kyber768",
        "Kyber1024",
    ]
    
    @classmethod
    def parse_cipher_suite(cls, cipher_name: str) -> Dict[str, Any]:
        """Parse a cipher suite name into components."""
        result = {
            "name": cipher_name,
            "key_exchange": None,
            "authentication": None,
            "encryption": None,
            "mac": None,
            "pfs": False,
            "strength": "unknown",
            "is_pqc": False,
            "pqc_algorithm": None,
        }
        
        # Check for PQC indicators
        for pqc_algo in cls.PQC_INDICATORS:
            if pqc_algo.lower() in cipher_name.lower():
                result["is_pqc"] = True
                result["pqc_algorithm"] = pqc_algo
                break
        
        # Parse key exchange
        for kex, props in cls.KEY_EXCHANGE_STRENGTH.items():
            if kex in cipher_name.upper():
                result["key_exchange"] = kex
                result["pfs"] = props["pfs"]
                break
        
        # Parse bulk cipher
        for cipher, strength in cls.BULK_CIPHER_STRENGTH.items():
            if cipher.replace("_", "") in cipher_name.upper().replace("_", "").replace("-", ""):
                result["encryption"] = cipher
                result["strength"] = strength
                break
        
        # Parse hash/MAC
        for hash_name, strength in cls.HASH_STRENGTH.items():
            if hash_name in cipher_name.upper():
                result["mac"] = hash_name
                if strength == "critical" and result["strength"] not in ["critical"]:
                    result["strength"] = strength
                break
        
        return result
    
    @classmethod
    def analyze_suite_list(cls, cipher_suites: List[str]) -> Dict[str, Any]:
        """Analyze a list of cipher suites."""
        analysis = {
            "total_count": len(cipher_suites),
            "strong_count": 0,
            "medium_count": 0,
            "weak_count": 0,
            "critical_count": 0,
            "pfs_supported": False,
            "pqc_supported": False,
            "pqc_algorithms": [],
            "vulnerabilities": [],
        }
        
        for suite in cipher_suites:
            parsed = cls.parse_cipher_suite(suite)
            
            if parsed["strength"] == "strong":
                analysis["strong_count"] += 1
            elif parsed["strength"] == "medium":
                analysis["medium_count"] += 1
            elif parsed["strength"] == "weak":
                analysis["weak_count"] += 1
            elif parsed["strength"] == "critical":
                analysis["critical_count"] += 1
                analysis["vulnerabilities"].append(f"Critical cipher: {suite}")
            
            if parsed["pfs"]:
                analysis["pfs_supported"] = True
            
            if parsed["is_pqc"]:
                analysis["pqc_supported"] = True
                if parsed["pqc_algorithm"] not in analysis["pqc_algorithms"]:
                    analysis["pqc_algorithms"].append(parsed["pqc_algorithm"])
        
        return analysis


class CertificateParser:
    """Parse X.509 certificates."""
    
    @staticmethod
    def parse_certificate(cert_pem: bytes) -> CertificateInfo:
        """Parse a PEM-encoded certificate."""
        cert = x509.load_pem_x509_certificate(cert_pem)
        
        # Extract public key info
        public_key = cert.public_key()
        if isinstance(public_key, rsa.RSAPublicKey):
            pk_algorithm = "RSA"
            pk_size = public_key.key_size
        elif isinstance(public_key, ec.EllipticCurvePublicKey):
            pk_algorithm = f"ECDSA-{public_key.curve.name}"
            pk_size = public_key.key_size
        elif isinstance(public_key, ed25519.Ed25519PublicKey):
            pk_algorithm = "Ed25519"
            pk_size = 256
        elif isinstance(public_key, ed448.Ed448PublicKey):
            pk_algorithm = "Ed448"
            pk_size = 448
        elif isinstance(public_key, dsa.DSAPublicKey):
            pk_algorithm = "DSA"
            pk_size = public_key.key_size
        else:
            pk_algorithm = "Unknown"
            pk_size = 0
        
        # Extract SANs
        san_list = []
        try:
            san_ext = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
            for name in san_ext.value:
                san_list.append(str(name.value))
        except x509.ExtensionNotFound:
            pass
        
        # Extract key usage
        key_usage = []
        try:
            ku_ext = cert.extensions.get_extension_for_oid(ExtensionOID.KEY_USAGE)
            ku = ku_ext.value
            if ku.digital_signature:
                key_usage.append("digitalSignature")
            if ku.key_encipherment:
                key_usage.append("keyEncipherment")
            if ku.key_agreement:
                key_usage.append("keyAgreement")
            if ku.key_cert_sign:
                key_usage.append("keyCertSign")
            if ku.crl_sign:
                key_usage.append("cRLSign")
        except (x509.ExtensionNotFound, ValueError):
            pass
        
        # Extract extended key usage
        ext_key_usage = []
        try:
            eku_ext = cert.extensions.get_extension_for_oid(ExtensionOID.EXTENDED_KEY_USAGE)
            for usage in eku_ext.value:
                ext_key_usage.append(usage._name)
        except x509.ExtensionNotFound:
            pass
        
        # Calculate fingerprint
        fingerprint = cert.fingerprint(hashes.SHA256()).hex()
        
        # Check expiry
        now = datetime.now(timezone.utc)
        not_after = cert.not_valid_after_utc if hasattr(cert, 'not_valid_after_utc') else cert.not_valid_after.replace(tzinfo=timezone.utc)
        not_before = cert.not_valid_before_utc if hasattr(cert, 'not_valid_before_utc') else cert.not_valid_before.replace(tzinfo=timezone.utc)
        is_expired = now > not_after
        days_until_expiry = (not_after - now).days
        
        # Check if self-signed
        is_self_signed = cert.issuer == cert.subject
        
        # Get signature algorithm
        sig_algo = cert.signature_algorithm_oid._name
        
        return CertificateInfo(
            subject=cert.subject.rfc4514_string(),
            issuer=cert.issuer.rfc4514_string(),
            serial_number=format(cert.serial_number, 'x'),
            not_before=not_before,
            not_after=not_after,
            public_key_algorithm=pk_algorithm,
            public_key_size=pk_size,
            signature_algorithm=sig_algo,
            san=san_list,
            fingerprint_sha256=fingerprint,
            is_self_signed=is_self_signed,
            is_expired=is_expired,
            days_until_expiry=days_until_expiry,
            key_usage=key_usage,
            extended_key_usage=ext_key_usage,
            raw_pem=cert_pem.decode('utf-8', errors='ignore'),
        )


class TLSScanner:
    """
    Core TLS scanner that performs real handshakes.
    """
    
    # TLS version to OpenSSL method mapping
    TLS_METHODS = {
        TLSVersion.TLS_1_0: ssl.TLSVersion.TLSv1,
        TLSVersion.TLS_1_1: ssl.TLSVersion.TLSv1_1,
        TLSVersion.TLS_1_2: ssl.TLSVersion.TLSv1_2,
        TLSVersion.TLS_1_3: ssl.TLSVersion.TLSv1_3,
    }
    
    def __init__(self, timeout: int = None):
        self.timeout = timeout or settings.SCAN_TIMEOUT_SECONDS
    
    async def scan(
        self,
        hostname: str,
        port: int = 443,
        ip_address: str = None
    ) -> TLSConfiguration:
        """
        Perform a complete TLS scan of a target.
        """
        start_time = datetime.now(timezone.utc)
        
        config = TLSConfiguration(
            hostname=hostname,
            ip_address=ip_address or hostname,
            port=port,
        )
        
        try:
            # Run scans in parallel where possible
            results = await asyncio.gather(
                self._probe_tls_versions(hostname, port),
                self._get_certificate_chain(hostname, port),
                self._check_http_security(hostname, port),
                return_exceptions=True
            )
            
            # Process TLS version probe results
            if not isinstance(results[0], Exception):
                version_info = results[0]
                config.tls_version = version_info.get("negotiated_version")
                config.supported_tls_versions = version_info.get("supported_versions", [])
                config.cipher_suites = version_info.get("cipher_suites", [])
                config.preferred_cipher = version_info.get("preferred_cipher")
                config.key_exchange = version_info.get("key_exchange")
                config.alpn_protocols = version_info.get("alpn_protocols", [])
                config.session_resumption = version_info.get("session_resumption")
                config.raw_handshake = version_info.get("raw_data", {})
                config.is_accessible = True
                
                # Analyze PFS
                if config.preferred_cipher:
                    parsed = CipherSuiteAnalyzer.parse_cipher_suite(config.preferred_cipher)
                    config.perfect_forward_secrecy = parsed["pfs"]
                    
                    # Check for PQC
                    if parsed["is_pqc"]:
                        config.pqc_key_encapsulation = parsed["pqc_algorithm"]
                        config.hybrid_mode = "X25519" in config.preferred_cipher or "P256" in config.preferred_cipher
            else:
                config.error_message = str(results[0])
            
            # Process certificate chain
            if not isinstance(results[1], Exception) and results[1]:
                cert_info = results[1]
                config.certificates = cert_info.get("certificates", [])
                config.chain_valid = cert_info.get("chain_valid", False)
                config.chain_issues = cert_info.get("issues", [])
                config.ocsp_stapling = cert_info.get("ocsp_stapling", False)
                config.ocsp_status = cert_info.get("ocsp_status")
            
            # Process HTTP security headers
            if not isinstance(results[2], Exception) and results[2]:
                http_info = results[2]
                config.hsts_enabled = http_info.get("hsts_enabled", False)
                config.hsts_max_age = http_info.get("hsts_max_age")
                config.hsts_include_subdomains = http_info.get("hsts_include_subdomains", False)
                config.hsts_preload = http_info.get("hsts_preload", False)
        
        except Exception as e:
            logger.error(f"TLS scan failed for {hostname}:{port}: {e}")
            config.error_message = str(e)
        
        # Calculate scan duration
        config.scan_duration_ms = int(
            (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        )
        
        return config
    
    async def _probe_tls_versions(
        self,
        hostname: str,
        port: int
    ) -> Dict[str, Any]:
        """Probe supported TLS versions and cipher suites."""
        result = {
            "negotiated_version": None,
            "supported_versions": [],
            "cipher_suites": [],
            "preferred_cipher": None,
            "key_exchange": None,
            "alpn_protocols": [],
            "session_resumption": None,
            "raw_data": {},
        }
        
        # Test each TLS version
        for tls_version, ssl_version in reversed(list(self.TLS_METHODS.items())):
            try:
                version_result = await self._test_tls_version(
                    hostname, port, ssl_version
                )
                if version_result["success"]:
                    result["supported_versions"].append(tls_version)
                    
                    # Use highest version as negotiated
                    if result["negotiated_version"] is None:
                        result["negotiated_version"] = tls_version
                        result["preferred_cipher"] = version_result.get("cipher")
                        result["cipher_suites"] = version_result.get("cipher_suites", [])
                        result["alpn_protocols"] = version_result.get("alpn", [])
                        
                        # Extract key exchange from cipher
                        cipher = version_result.get("cipher", "")
                        for kex in ["ECDHE", "DHE", "ECDH", "DH", "RSA"]:
                            if kex in cipher:
                                result["key_exchange"] = kex
                                break
            
            except Exception as e:
                logger.debug(f"TLS {tls_version} probe failed for {hostname}: {e}")
        
        # Get full cipher suite list using OpenSSL
        full_ciphers = await self._enumerate_ciphers(hostname, port)
        if full_ciphers:
            result["cipher_suites"] = full_ciphers
        
        return result
    
    async def _test_tls_version(
        self,
        hostname: str,
        port: int,
        tls_version: ssl.TLSVersion
    ) -> Dict[str, Any]:
        """Test if a specific TLS version is supported."""
        result = {"success": False}
        
        def blocking_connect():
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.minimum_version = tls_version
            context.maximum_version = tls_version
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            # Enable ALPN
            context.set_alpn_protocols(["h2", "http/1.1"])
            
            with socket.create_connection((hostname, port), timeout=self.timeout) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    return {
                        "success": True,
                        "cipher": ssock.cipher()[0] if ssock.cipher() else None,
                        "version": ssock.version(),
                        "alpn": ssock.selected_alpn_protocol(),
                    }
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, blocking_connect)
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    async def _enumerate_ciphers(
        self,
        hostname: str,
        port: int
    ) -> List[str]:
        """Enumerate all supported cipher suites using OpenSSL."""
        ciphers = []
        
        def blocking_enumerate():
            cipher_list = []
            
            # Get all available ciphers
            ctx = OpenSSL.SSL.Context(OpenSSL.SSL.TLS_CLIENT_METHOD)
            all_ciphers = ctx.get_cipher_list()
            
            for cipher in all_ciphers:
                try:
                    test_ctx = OpenSSL.SSL.Context(OpenSSL.SSL.TLS_CLIENT_METHOD)
                    test_ctx.set_cipher_list(cipher.encode())
                    
                    sock = socket.create_connection((hostname, port), timeout=5)
                    conn = OpenSSL.SSL.Connection(test_ctx, sock)
                    conn.set_tlsext_host_name(hostname.encode())
                    conn.set_connect_state()
                    
                    try:
                        conn.do_handshake()
                        negotiated = conn.get_cipher_name()
                        if negotiated and negotiated not in cipher_list:
                            cipher_list.append(negotiated)
                    except OpenSSL.SSL.Error:
                        pass
                    finally:
                        conn.shutdown()
                        sock.close()
                
                except Exception:
                    pass
            
            return cipher_list
        
        try:
            loop = asyncio.get_event_loop()
            ciphers = await asyncio.wait_for(
                loop.run_in_executor(None, blocking_enumerate),
                timeout=60
            )
        except asyncio.TimeoutError:
            logger.warning(f"Cipher enumeration timed out for {hostname}")
        except Exception as e:
            logger.debug(f"Cipher enumeration failed: {e}")
        
        return ciphers
    
    async def _get_certificate_chain(
        self,
        hostname: str,
        port: int
    ) -> Dict[str, Any]:
        """Retrieve and parse the certificate chain."""
        result = {
            "certificates": [],
            "chain_valid": False,
            "issues": [],
            "ocsp_stapling": False,
            "ocsp_status": None,
        }
        
        def blocking_get_certs():
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            with socket.create_connection((hostname, port), timeout=self.timeout) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    # Get peer certificate
                    cert_der = ssock.getpeercert(binary_form=True)
                    cert_dict = ssock.getpeercert()
                    
                    return {
                        "cert_der": cert_der,
                        "cert_dict": cert_dict,
                    }
        
        try:
            loop = asyncio.get_event_loop()
            cert_data = await loop.run_in_executor(None, blocking_get_certs)
            
            if cert_data and cert_data.get("cert_der"):
                # Convert DER to PEM
                cert_pem = ssl.DER_cert_to_PEM_cert(cert_data["cert_der"]).encode()
                
                # Parse certificate
                cert_info = CertificateParser.parse_certificate(cert_pem)
                result["certificates"].append(cert_info)
                
                # Check for issues
                if cert_info.is_expired:
                    result["issues"].append("Certificate is expired")
                elif cert_info.days_until_expiry < 30:
                    result["issues"].append(f"Certificate expires in {cert_info.days_until_expiry} days")
                
                if cert_info.is_self_signed:
                    result["issues"].append("Certificate is self-signed")
                
                if cert_info.public_key_size < 2048 and "RSA" in cert_info.public_key_algorithm:
                    result["issues"].append(f"Weak RSA key size: {cert_info.public_key_size} bits")
                
                # Check signature algorithm
                weak_sigs = ["md5", "sha1"]
                if any(weak in cert_info.signature_algorithm.lower() for weak in weak_sigs):
                    result["issues"].append(f"Weak signature algorithm: {cert_info.signature_algorithm}")
                
                result["chain_valid"] = len(result["issues"]) == 0
        
        except Exception as e:
            logger.debug(f"Certificate retrieval failed for {hostname}: {e}")
            result["issues"].append(f"Failed to retrieve certificate: {str(e)}")
        
        return result
    
    async def _check_http_security(
        self,
        hostname: str,
        port: int
    ) -> Dict[str, Any]:
        """Check HTTP security headers (HSTS, etc.)."""
        result = {
            "hsts_enabled": False,
            "hsts_max_age": None,
            "hsts_include_subdomains": False,
            "hsts_preload": False,
        }
        
        try:
            import aiohttp
            
            timeout = aiohttp.ClientTimeout(total=10)
            connector = aiohttp.TCPConnector(ssl=False)
            
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                url = f"https://{hostname}:{port}/" if port != 443 else f"https://{hostname}/"
                
                async with session.head(url, allow_redirects=False) as response:
                    hsts = response.headers.get("Strict-Transport-Security", "")
                    
                    if hsts:
                        result["hsts_enabled"] = True
                        
                        # Parse max-age
                        import re
                        max_age_match = re.search(r'max-age=(\d+)', hsts, re.IGNORECASE)
                        if max_age_match:
                            result["hsts_max_age"] = int(max_age_match.group(1))
                        
                        result["hsts_include_subdomains"] = "includesubdomains" in hsts.lower()
                        result["hsts_preload"] = "preload" in hsts.lower()
        
        except Exception as e:
            logger.debug(f"HTTP security check failed for {hostname}: {e}")
        
        return result


class CryptoFingerprintEngine:
    """
    Main cryptographic fingerprinting engine.
    Orchestrates TLS scanning and analysis.
    """
    
    def __init__(self):
        self.tls_scanner = TLSScanner()
        self.cipher_analyzer = CipherSuiteAnalyzer()
    
    async def fingerprint(
        self,
        hostname: str,
        port: int = 443,
        ip_address: str = None
    ) -> TLSConfiguration:
        """
        Perform complete cryptographic fingerprinting of a target.
        """
        logger.info(f"Starting crypto fingerprint for {hostname}:{port}")
        
        config = await self.tls_scanner.scan(hostname, port, ip_address)
        
        # Additional analysis
        if config.cipher_suites:
            suite_analysis = self.cipher_analyzer.analyze_suite_list(config.cipher_suites)
            config.raw_handshake["cipher_analysis"] = suite_analysis
            
            # Check for PQC support
            if suite_analysis["pqc_supported"]:
                config.pqc_key_encapsulation = suite_analysis["pqc_algorithms"][0]
        
        logger.info(
            f"Crypto fingerprint complete for {hostname}:{port} - "
            f"TLS {config.tls_version}, Cipher: {config.preferred_cipher}"
        )
        
        return config
    
    async def batch_fingerprint(
        self,
        targets: List[Tuple[str, int]],
        max_concurrent: int = None
    ) -> List[TLSConfiguration]:
        """
        Fingerprint multiple targets concurrently.
        """
        max_concurrent = max_concurrent or settings.SCAN_MAX_CONCURRENT
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def scan_with_semaphore(hostname: str, port: int) -> TLSConfiguration:
            async with semaphore:
                return await self.fingerprint(hostname, port)
        
        tasks = [scan_with_semaphore(h, p) for h, p in targets]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error configs
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                hostname, port = targets[i]
                config = TLSConfiguration(
                    hostname=hostname,
                    ip_address=hostname,
                    port=port,
                    is_accessible=False,
                    error_message=str(result)
                )
                final_results.append(config)
            else:
                final_results.append(result)
        
        return final_results
