"""
Q-Shield Quantum-Safe Certificate Engine
Issues digitally verifiable Quantum-Safe Certificates.
"""

import secrets
import hashlib
import qrcode
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional, Dict, Any
from uuid import uuid4
import json
import base64
from io import BytesIO

from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger("certificate")


class CertificateLevel(str, Enum):
    """Quantum-Safe Certificate levels."""
    FULLY_QUANTUM_SAFE = "fully_quantum_safe"
    PQC_READY = "pqc_ready"


@dataclass
class QuantumSafeCertificateData:
    """Quantum-Safe Certificate data structure."""
    certificate_id: str
    issued_at: str
    expires_at: str
    level: str
    
    # Endpoint details
    hostname: str
    port: int
    asn: Optional[str]
    country_code: Optional[str]
    
    # Cryptographic status at issuance
    tls_version: str
    key_exchange: str
    cipher_suite: str
    pqc_algorithms: list
    certificate_public_key_algorithm: str
    certificate_public_key_size: int
    
    # Issuer details
    issuer: str = "Q-Shield Inc."
    issuer_url: str = "https://qshield.io"
    
    # Verification
    verification_url: str = "https://verify.qshield.io"
    
    # Metadata
    scan_timestamp: str = ""
    scan_id: str = ""
    risk_score: float = 0.0


class QuantumSafeCertificateEngine:
    """
    Issues digitally verifiable Quantum-Safe Certificates.
    Provides cryptographic proof of quantum-safe configuration at a point in time.
    """
    
    CERTIFICATE_VALIDITY_DAYS = 365
    
    # Certificate templates
    CERTIFICATE_TEMPLATES = {
        CertificateLevel.FULLY_QUANTUM_SAFE: {
            "title": "Quantum-Safe Certified",
            "description": "This endpoint is fully protected by NIST-standardized Post-Quantum Cryptography algorithms",
            "badge_color": "#27ae60",
            "icon": "🛡️",
        },
        CertificateLevel.PQC_READY: {
            "title": "Post-Quantum Ready",
            "description": "This endpoint meets prerequisites for PQC migration using TLS 1.3 and modern key exchange",
            "badge_color": "#f39c12",
            "icon": "⚙️",
        },
    }
    
    def __init__(self):
        self.logger = logger
    
    def issue_certificate(
        self,
        asset_id: str,
        hostname: str,
        port: int,
        pqc_readiness_level: str,
        tls_version: str,
        key_exchange: str,
        cipher_suite: str,
        pqc_algorithms: list,
        certificate_key_algo: str,
        certificate_key_size: int,
        asn: Optional[str] = None,
        country_code: Optional[str] = None,
        scan_timestamp: Optional[str] = None,
        scan_id: Optional[str] = None,
        risk_score: float = 0.0,
        sign_data_func=None,
    ) -> Dict[str, Any]:
        """
        Issue a Quantum-Safe Certificate for a compliant asset.
        """
        # Only issue for compliant assets
        if pqc_readiness_level not in [CertificateLevel.FULLY_QUANTUM_SAFE, CertificateLevel.PQC_READY]:
            raise ValueError(f"Invalid PQC readiness level: {pqc_readiness_level}")
        
        certificate_id = self._generate_certificate_id()
        issued_at = datetime.now(timezone.utc)
        expires_at = issued_at + timedelta(days=self.CERTIFICATE_VALIDITY_DAYS)
        
        self.logger.info(
            f"Issuing {pqc_readiness_level} certificate {certificate_id} for {hostname}:{port}"
        )
        
        # Create certificate data
        cert_data = QuantumSafeCertificateData(
            certificate_id=certificate_id,
            issued_at=issued_at.isoformat(),
            expires_at=expires_at.isoformat(),
            level=pqc_readiness_level,
            hostname=hostname,
            port=port,
            asn=asn,
            country_code=country_code,
            tls_version=tls_version,
            key_exchange=key_exchange,
            cipher_suite=cipher_suite,
            pqc_algorithms=pqc_algorithms or [],
            certificate_public_key_algorithm=certificate_key_algo,
            certificate_public_key_size=certificate_key_size,
            scan_timestamp=scan_timestamp or issued_at.isoformat(),
            scan_id=scan_id or "",
            risk_score=risk_score,
        )
        
        # Generate digital signature
        cert_dict = asdict(cert_data)
        cert_dict["verification_url"] = f"{cert_data.verification_url}/{certificate_id}"
        
        signature = None
        signature_algorithm = "RSA-PSS-SHA384"
        
        if sign_data_func:
            # Sign the certificate data
            cert_json = json.dumps(cert_dict, sort_keys=True).encode()
            signature_bytes = sign_data_func(cert_json)
            signature = base64.b64encode(signature_bytes).decode('utf-8')
            
            self.logger.info(f"Certificate {certificate_id} signed with {signature_algorithm}")
        
        # Generate QR code
        qr_data = f"{cert_data.verification_url}/{certificate_id}"
        qr_code_image = self._generate_qr_code(qr_data)
        qr_code_base64 = base64.b64encode(qr_code_image).decode('utf-8')
        
        # Generate HTML badge
        badge_html = self._generate_badge_html(cert_data)
        
        # Assemble certificate
        certificate = {
            "certificate_id": certificate_id,
            "data": cert_dict,
            "signature": signature,
            "signature_algorithm": signature_algorithm,
            "issue_timestamp": issued_at.isoformat(),
            "expiry_timestamp": expires_at.isoformat(),
            "validity_days": self.CERTIFICATE_VALIDITY_DAYS,
            "verification_url": f"{cert_data.verification_url}/{certificate_id}",
            "qr_code": qr_code_base64,
            "badge_html": badge_html,
            "badge_svg": self._generate_badge_svg(cert_data),
        }
        
        self.logger.info(f"Certificate {certificate_id} issued successfully")
        
        return certificate
    
    def verify_certificate(
        self,
        certificate: Dict[str, Any],
        verify_signature_func=None,
    ) -> Dict[str, Any]:
        """
        Verify a Quantum-Safe Certificate.
        """
        certificate_id = certificate.get("certificate_id")
        
        self.logger.info(f"Verifying certificate {certificate_id}")
        
        verification = {
            "certificate_id": certificate_id,
            "verified": False,
            "errors": [],
            "warnings": [],
        }
        
        # Check expiry
        expiry = datetime.fromisoformat(certificate.get("expiry_timestamp", ""))
        now = datetime.now(timezone.utc)
        
        if expiry < now:
            verification["errors"].append("Certificate has expired")
            verification["verified"] = False
            return verification
        
        days_until_expiry = (expiry - now).days
        if days_until_expiry < 30:
            verification["warnings"].append(f"Certificate expires in {days_until_expiry} days")
        
        # Verify signature if provided
        if certificate.get("signature") and verify_signature_func:
            cert_data = certificate.get("data", {})
            cert_json = json.dumps(cert_data, sort_keys=True).encode()
            
            try:
                signature_bytes = base64.b64decode(certificate.get("signature", ""))
                is_valid = verify_signature_func(cert_json, signature_bytes)
                
                if is_valid:
                    verification["verified"] = True
                    self.logger.info(f"Certificate {certificate_id} signature verified")
                else:
                    verification["errors"].append("Signature verification failed")
                    verification["verified"] = False
            except Exception as e:
                verification["errors"].append(f"Signature verification error: {str(e)}")
                verification["verified"] = False
        else:
            # No signature to verify
            verification["verified"] = True
        
        return verification
    
    def generate_certificate_report_html(
        self,
        certificate: Dict[str, Any],
    ) -> str:
        """
        Generate an HTML report for the certificate.
        Suitable for web display, printing, or email.
        """
        cert_id = certificate.get("certificate_id")
        cert_data = certificate.get("data", {})
        template = self.CERTIFICATE_TEMPLATES.get(cert_data.get("level", ""))
        
        if not template:
            raise ValueError(f"Unknown certificate level: {cert_data.get('level')}")
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quantum-Safe Certificate - {cert_data.get('hostname')}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            color: #333;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, {template['badge_color']} 0%, #333 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 32px;
            margin-bottom: 10px;
        }}
        .header p {{
            margin: 5px 0;
            font-size: 16px;
        }}
        .content {{
            padding: 40px;
        }}
        .certificate-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        .certificate-table td {{
            padding: 12px;
            border-bottom: 1px solid #ddd;
        }}
        .certificate-table .label {{
            font-weight: bold;
            width: 30%;
            background: #f5f5f5;
        }}
        .certificate-table .value {{
            font-family: 'Courier New', monospace;
            word-break: break-all;
        }}
        .qr-section {{
            text-align: center;
            margin: 30px 0;
            padding: 20px;
            background: #f5f5f5;
            border-radius: 5px;
        }}
        .qr-section img {{
            max-width: 200px;
            height: auto;
        }}
        .verification-url {{
            text-align: center;
            margin: 20px 0;
            padding: 15px;
            background: #e8f5e9;
            border-radius: 5px;
            border-left: 4px solid #27ae60;
        }}
        .verification-url a {{
            color: #27ae60;
            text-decoration: none;
            font-weight: bold;
        }}
        .footer {{
            background: #f5f5f5;
            padding: 20px;
            text-align: center;
            font-size: 12px;
            color: #666;
        }}
        .badge {{
            display: inline-block;
            margin: 10px;
        }}
        .cryptography-details {{
            background: #f5f5f5;
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
        }}
        .cryptography-details h3 {{
            margin-top: 0;
            color: #333;
        }}
        .crypto-item {{
            margin: 8px 0;
            font-family: 'Courier New', monospace;
            font-size: 13px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{template['icon']} {template['title']}</h1>
            <p>{template['description']}</p>
            <p style="font-size: 12px; margin-top: 10px;">Certificate ID: {cert_id}</p>
        </div>
        
        <div class="content">
            <h2>Certificate Details</h2>
            
            <table class="certificate-table">
                <tr>
                    <td class="label">Hostname</td>
                    <td class="value">{cert_data.get('hostname')}</td>
                </tr>
                <tr>
                    <td class="label">Port</td>
                    <td class="value">{cert_data.get('port')}</td>
                </tr>
                <tr>
                    <td class="label">Issued At</td>
                    <td class="value">{cert_data.get('issued_at')}</td>
                </tr>
                <tr>
                    <td class="label">Expires At</td>
                    <td class="value">{cert_data.get('expires_at')}</td>
                </tr>
                <tr>
                    <td class="label">Certificate ID</td>
                    <td class="value">{cert_id}</td>
                </tr>
            </table>
            
            <h3>Cryptographic Configuration</h3>
            <div class="cryptography-details">
                <div class="crypto-item"><strong>TLS Version:</strong> {cert_data.get('tls_version')}</div>
                <div class="crypto-item"><strong>Key Exchange:</strong> {cert_data.get('key_exchange')}</div>
                <div class="crypto-item"><strong>Cipher Suite:</strong> {cert_data.get('cipher_suite')}</div>
                <div class="crypto-item"><strong>Certificate Algorithm:</strong> {cert_data.get('certificate_public_key_algorithm')} ({cert_data.get('certificate_public_key_size')}-bit)</div>
                {f"<div class='crypto-item'><strong>PQC Algorithms:</strong> {', '.join(cert_data.get('pqc_algorithms', []))}</div>" if cert_data.get('pqc_algorithms') else ""}
            </div>
            
            <h3>Verification</h3>
            <div class="verification-url">
                <p>Verify this certificate at:</p>
                <a href="{certificate.get('verification_url')}" target="_blank">{certificate.get('verification_url')}</a>
            </div>
            
            <h3>Certificate Badge</h3>
            <div class="qr-section">
                <p><strong>Embed this badge on your website:</strong></p>
                <a href="{certificate.get('verification_url')}" target="_blank">
                    {certificate.get('badge_svg')}
                </a>
            </div>
            
            <h3>QR Code</h3>
            <div class="qr-section">
                <p><strong>Scan to verify certificate:</strong></p>
                <img src="data:image/png;base64,{certificate.get('qr_code')}" alt="Certificate QR Code" />
            </div>
        </div>
        
        <div class="footer">
            <p>Issued by Q-Shield Inc. | https://qshield.io</p>
            <p>This certificate verifies post-quantum cryptography readiness at the time of issuance.</p>
            <p>Based on NIST SP 800-208 and cryptographic standards.</p>
        </div>
    </div>
</body>
</html>
        """
        
        return html
    
    def _generate_certificate_id(self) -> str:
        """Generate unique certificate ID."""
        timestamp = datetime.now(timezone.utc).isoformat()
        random_suffix = secrets.token_hex(8)
        cert_id = f"qsc-{timestamp.replace(':', '').replace('.', '').replace('-', '')}-{random_suffix}"
        return cert_id[:50]  # Limit length
    
    def _generate_qr_code(self, data: str) -> bytes:
        """Generate QR code image as PNG bytes."""
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to PNG bytes
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            return buffer.getvalue()
        except Exception as e:
            self.logger.error(f"Failed to generate QR code: {e}")
            raise
    
    def _generate_badge_html(self, cert_data: QuantumSafeCertificateData) -> str:
        """Generate HTML badge for embedding."""
        cert_id = cert_data.certificate_id
        verification_url = f"{cert_data.verification_url}/{cert_id}"
        template = self.CERTIFICATE_TEMPLATES.get(cert_data.level, {})
        
        html = f"""
<a href="{verification_url}" target="_blank" style="text-decoration: none;">
    <div style="
        display: inline-block;
        background: {template.get('badge_color', '#27ae60')};
        color: white;
        padding: 10px 15px;
        border-radius: 5px;
        font-weight: bold;
        font-size: 13px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    ">
        {template.get('icon', '🛡️')} {template.get('title', '')}
    </div>
</a>
        """
        return html
    
    def _generate_badge_svg(self, cert_data: QuantumSafeCertificateData) -> str:
        """Generate SVG badge for embedding."""
        cert_id = cert_data.certificate_id
        verification_url = f"{cert_data.verification_url}/{cert_id}"
        # Simplified SVG badge
        svg = f"""
<svg width="200" height="60" xmlns="http://www.w3.org/2000/svg">
    <a href="{verification_url}" target="_blank">
        <rect width="200" height="60" fill="#27ae60" rx="5"/>
        <text x="100" y="40" font-family="Arial" font-size="16" fill="white" text-anchor="middle" font-weight="bold">
            Quantum-Safe
        </text>
    </a>
</svg>
        """
        return svg
