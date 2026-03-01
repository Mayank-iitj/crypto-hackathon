"""
Q-Shield Cryptographic Bill of Materials (CBOM) Generator
Generates machine-readable and human-readable CBOM documents.
"""

import json
import hashlib
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import UUID

from app.core.logging import get_logger

logger = get_logger("cbom.generator")


class CBOMFormat(str, Enum):
    JSON = "json"
    JWS = "jws"  # JSON Web Signature
    PDF = "pdf"
    CSV = "csv"


@dataclass
class CryptographicAsset:
    """Single asset entry in CBOM."""
    asset_id: str
    hostname: str
    ip_address: Optional[str]
    port: int
    protocol: str
    discovery_source: str
    
    # Cryptographic details
    tls_version: Optional[str]
    preferred_cipher: Optional[str]
    cipher_suite_count: int
    key_exchange: Optional[str]
    perfect_forward_secrecy: bool
    
    # Certificate details
    certificate_subject: Optional[str]
    certificate_issuer: Optional[str]
    certificate_key_algorithm: Optional[str]
    certificate_key_size: Optional[int]
    certificate_signature_algorithm: Optional[str]
    certificate_not_before: Optional[str]
    certificate_not_after: Optional[str]
    certificate_san: List[str] = field(default_factory=list)
    
    # PQC Assessment
    pqc_kem_detected: Optional[str] = None
    pqc_signature_detected: Optional[str] = None
    pqc_readiness: str = "unknown"
    
    # Risk Assessment
    risk_score: float = 0.0
    risk_severity: str = "unknown"
    
    # Compliance
    nist_sp_800_208_compliant: bool = False
    iso_27001_compliant: bool = False
    rbi_csf_compliant: bool = False
    
    # Remediation
    critical_issues: List[str] = field(default_factory=list)
    remediation_steps: List[str] = field(default_factory=list)
    
    # Timestamps
    scan_timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    # Metadata
    metadata: Dict = field(default_factory=dict)


@dataclass
class CBOMDocument:
    """Complete CBOM document."""
    cbom_id: str
    generated_at: str
    generated_by: str
    organization: str
    scan_period: Optional[str] = None
    
    # Statistics
    total_assets: int = 0
    assets_fully_quantum_safe: int = 0
    assets_pqc_ready: int = 0
    assets_vulnerable: int = 0
    critical_issues_count: int = 0
    
    # Assets
    assets: List[CryptographicAsset] = field(default_factory=list)
    
    # Executive Summary
    executive_summary: str = ""
    
    # Signature (for JWS)
    signature: Optional[str] = None
    signature_algorithm: str = "RSA-PSS-SHA384"
    
    # Metadata
    version: str = "1.0"
    schema_uri: str = "https://qshield.io/cbom/schema/1.0"


class CBOMGenerator:
    """
    Generates Cryptographic Bill of Materials in multiple formats.
    Supports JSON, JWS (signed), PDF, and CSV output.
    """
    
    def __init__(self):
        self.logger = logger
    
    def generate_cbom(
        self,
        scan_results: List[Dict[str, Any]],
        organization: str,
        generated_by: str = "Q-Shield API",
        cbom_id: Optional[str] = None,
        scan_period: Optional[str] = None,
    ) -> CBOMDocument:
        """
        Generate a CBOM document from scan results.
        """
        cbom_id = cbom_id or self._generate_cbom_id()
        
        self.logger.info(f"Generating CBOM {cbom_id} with {len(scan_results)} assets")
        
        # Convert scan results to CBOM assets
        assets = []
        stats = {
            "total": len(scan_results),
            "fully_quantum_safe": 0,
            "pqc_ready": 0,
            "vulnerable": 0,
            "critical_issues": 0,
        }
        
        for result in scan_results:
            asset = self._convert_to_cbom_asset(result)
            assets.append(asset)
            
            # Update statistics
            if asset.pqc_readiness == "fully_quantum_safe":
                stats["fully_quantum_safe"] += 1
            elif asset.pqc_readiness == "pqc_ready":
                stats["pqc_ready"] += 1
            elif asset.pqc_readiness == "vulnerable":
                stats["vulnerable"] += 1
            
            stats["critical_issues"] += len(asset.critical_issues)
        
        # Generate executive summary
        summary = self._generate_executive_summary(assets, stats)
        
        # Create CBOM document
        cbom = CBOMDocument(
            cbom_id=cbom_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
            generated_by=generated_by,
            organization=organization,
            scan_period=scan_period,
            total_assets=stats["total"],
            assets_fully_quantum_safe=stats["fully_quantum_safe"],
            assets_pqc_ready=stats["pqc_ready"],
            assets_vulnerable=stats["vulnerable"],
            critical_issues_count=stats["critical_issues"],
            assets=assets,
            executive_summary=summary,
        )
        
        self.logger.info(
            f"CBOM generated: {cbom_id} - "
            f"{stats['fully_quantum_safe']} fully safe, "
            f"{stats['pqc_ready']} PQC ready, "
            f"{stats['vulnerable']} vulnerable"
        )
        
        return cbom
    
    def export_json(self, cbom: CBOMDocument) -> str:
        """Export CBOM as JSON."""
        self.logger.debug(f"Exporting CBOM {cbom.cbom_id} as JSON")
        
        # Convert to dict, handling datetime fields
        cbom_dict = asdict(cbom)
        
        return json.dumps(cbom_dict, indent=2, default=str)
    
    def export_jws(
        self,
        cbom: CBOMDocument,
        sign_data_func
    ) -> str:
        """
        Export CBOM as JSON Web Signature (JWS).
        Provides tamper-proof, digitally signed export.
        
        Args:
            cbom: CBOM document to sign
            sign_data_func: Function(data: bytes) -> signature: bytes
        """
        self.logger.info(f"Exporting CBOM {cbom.cbom_id} as JWS")
        
        # Create JWS header
        header = {
            "alg": "PS384",
            "typ": "CBOM",
            "version": cbom.version,
        }
        
        # Create payload
        payload = asdict(cbom)
        payload["signature"] = None  # Remove placeholder signature
        
        # Encode header and payload
        import base64
        header_json = json.dumps(header, separators=(',', ':'))
        payload_json = json.dumps(payload, separators=(',', ':'), default=str)
        
        header_b64 = self._base64url_encode(header_json.encode())
        payload_b64 = self._base64url_encode(payload_json.encode())
        
        # Create signature
        signature_input = f"{header_b64}.{payload_b64}".encode()
        signature_bytes = sign_data_func(signature_input)
        signature_b64 = self._base64url_encode(signature_bytes)
        
        # Assemble JWS
        jws = f"{header_b64}.{payload_b64}.{signature_b64}"
        
        self.logger.info(f"CBOM signed successfully with RSA-PSS-SHA384")
        
        return jws
    
    def export_csv(self, cbom: CBOMDocument) -> str:
        """
        Export CBOM as CSV for spreadsheet applications.
        """
        self.logger.debug(f"Exporting CBOM {cbom.cbom_id} as CSV")
        
        import csv
        from io import StringIO
        
        output = StringIO()
        
        if not cbom.assets:
            return ""
        
        # Get all field names
        fieldnames = [
            "asset_id",
            "hostname",
            "ip_address",
            "port",
            "protocol",
            "tls_version",
            "preferred_cipher",
            "key_exchange",
            "perfect_forward_secrecy",
            "certificate_key_algorithm",
            "certificate_key_size",
            "certificate_signature_algorithm",
            "certificate_not_before",
            "certificate_not_after",
            "pqc_kem_detected",
            "pqc_signature_detected",
            "pqc_readiness",
            "risk_score",
            "risk_severity",
            "nist_sp_800_208_compliant",
            "iso_27001_compliant",
            "rbi_csf_compliant",
            "critical_issues",
            "scan_timestamp",
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for asset in cbom.assets:
            row = asdict(asset)
            # Convert lists to semicolon-separated strings
            row["certificate_san"] = ";".join(row.get("certificate_san", []))
            row["critical_issues"] = ";".join(row.get("critical_issues", []))
            row["remediation_steps"] = ";".join(row.get("remediation_steps", []))
            writer.writerow(row)
        
        return output.getvalue()
    
    def export_pdf(self, cbom: CBOMDocument) -> bytes:
        """
        Export CBOM as PDF executive report.
        Requires reportlab library.
        """
        self.logger.info(f"Exporting CBOM {cbom.cbom_id} as PDF")
        
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter, landscape
            from reportlab.platypus import (
                SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
                PageBreak, KeepTogether
            )
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from io import BytesIO
        except ImportError:
            self.logger.error("reportlab not installed - PDF export unavailable")
            raise ImportError("reportlab required for PDF export")
        
        # Create PDF buffer
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=landscape(letter))
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a5276'),
            spaceAfter=30,
            alignment=1,  # center
        )
        title = Paragraph(f"Cryptographic Bill of Materials (CBOM)", title_style)
        story.append(title)
        
        # Metadata
        metadata_data = [
            ["CBOM ID:", cbom.cbom_id],
            ["Organization:", cbom.organization],
            ["Generated:", cbom.generated_at],
            ["Generated By:", cbom.generated_by],
            ["Total Assets:", str(cbom.total_assets)],
        ]
        
        metadata_table = Table(metadata_data, colWidths=[2*inch, 4*inch])
        metadata_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        story.append(metadata_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Executive Summary
        summary_title = Paragraph("Executive Summary", styles['Heading2'])
        story.append(summary_title)
        story.append(Paragraph(cbom.executive_summary, styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        # Statistics
        stats_title = Paragraph("Statistics", styles['Heading2'])
        story.append(stats_title)
        
        stats_data = [
            ["Metric", "Count"],
            ["Fully Quantum Safe", str(cbom.assets_fully_quantum_safe)],
            ["PQC Ready", str(cbom.assets_pqc_ready)],
            ["Vulnerable", str(cbom.assets_vulnerable)],
            ["Critical Issues", str(cbom.critical_issues_count)],
        ]
        
        stats_table = Table(stats_data, colWidths=[3*inch, 2*inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(stats_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Asset Details
        story.append(PageBreak())
        assets_title = Paragraph("Asset-by-Asset Analysis", styles['Heading2'])
        story.append(assets_title)
        
        for asset in cbom.assets[:20]:  # Limit to first 20 for PDF
            asset_section = self._create_asset_pdf_section(asset, styles)
            story.append(asset_section)
            story.append(Spacer(1, 0.15*inch))
        
        if len(cbom.assets) > 20:
            more_text = Paragraph(
                f"<i>+ {len(cbom.assets) - 20} more assets (see full CSV/JSON export)</i>",
                styles['Normal']
            )
            story.append(more_text)
        
        # Build PDF
        doc.build(story)
        pdf_buffer.seek(0)
        return pdf_buffer.read()
    
    def _convert_to_cbom_asset(self, scan_result: Dict[str, Any]) -> CryptographicAsset:
        """Convert scan result to CBOM asset."""
        return CryptographicAsset(
            asset_id=str(scan_result.get("uuid", "")),
            hostname=scan_result.get("hostname", ""),
            ip_address=scan_result.get("ip_address"),
            port=scan_result.get("port", 443),
            protocol=scan_result.get("protocol", "HTTPS"),
            discovery_source=scan_result.get("discovery_source", "unknown"),
            tls_version=scan_result.get("tls_version"),
            preferred_cipher=scan_result.get("preferred_cipher"),
            cipher_suite_count=len(scan_result.get("cipher_suites", [])),
            key_exchange=scan_result.get("key_exchange"),
            perfect_forward_secrecy=scan_result.get("pfs", False),
            certificate_subject=scan_result.get("cert_subject"),
            certificate_issuer=scan_result.get("cert_issuer"),
            certificate_key_algorithm=scan_result.get("cert_key_algo"),
            certificate_key_size=scan_result.get("cert_key_size"),
            certificate_signature_algorithm=scan_result.get("cert_sig_algo"),
            certificate_not_before=scan_result.get("cert_not_before"),
            certificate_not_after=scan_result.get("cert_not_after"),
            certificate_san=scan_result.get("cert_san", []),
            pqc_kem_detected=scan_result.get("pqc_kem"),
            pqc_signature_detected=scan_result.get("pqc_signature"),
            pqc_readiness=scan_result.get("pqc_readiness", "unknown"),
            risk_score=scan_result.get("risk_score", 0.0),
            risk_severity=scan_result.get("risk_severity", "unknown"),
            nist_sp_800_208_compliant=scan_result.get("nist_compliant", False),
            iso_27001_compliant=scan_result.get("iso_compliant", False),
            rbi_csf_compliant=scan_result.get("rbi_compliant", False),
            critical_issues=scan_result.get("critical_issues", []),
            remediation_steps=scan_result.get("remediation", []),
            metadata=scan_result.get("metadata", {}),
        )
    
    def _generate_executive_summary(
        self,
        assets: List[CryptographicAsset],
        stats: Dict[str, int]
    ) -> str:
        """Generate executive summary text."""
        total = stats["total"]
        safe = stats["fully_quantum_safe"]
        ready = stats["pqc_ready"]
        vulnerable = stats["vulnerable"]
        critical = stats["critical_issues"]
        
        safe_pct = round((safe / total * 100)) if total else 0
        ready_pct = round((ready / total * 100)) if total else 0
        vuln_pct = round((vulnerable / total * 100)) if total else 0
        
        summary = f"""
This Cryptographic Bill of Materials analyzes {total} internet-facing assets for Post-Quantum Cryptography (PQC) readiness.

<b>Key Findings:</b>
• {safe} assets ({safe_pct}%) are fully quantum-safe, utilizing NIST-standardized PQC algorithms
• {ready} assets ({ready_pct}%) are PQC-ready: supporting TLS 1.3 and ECDHE-based key exchange
• {vulnerable} assets ({vuln_pct}%) are vulnerable to quantum-era threats, using weak cryptography
• {critical} critical cryptographic issues identified across the portfolio

<b>Quantum-Era Threat Timeline:</b>
Conservative estimates project functional Cryptographically Relevant Quantum Computers (CRQCs) 
within 15-20 years. Assets using RSA, DH, or ECDH without post-quantum hybrid modes face 
"harvest now, decrypt later" risks - encrypted communications can be decrypted once quantum 
computers become available.

<b>Recommended Actions:</b>
1. <b>Immediate (0-30 days):</b> Remediate TLS 1.1 and earlier, migrate SHA-1 certificates
2. <b>Short-term (30-90 days):</b> Deploy TLS 1.3, ECDHE key exchange, AES-256
3. <b>Medium-term (90-180 days):</b> Begin ML-KEM (Kyber) hybrid key exchange pilots
4. <b>Long-term (6-24 months):</b> Full ML-KEM and ML-DSA (Dilithium) deployment

All findings are based on NIST SP 800-208, NIST SP 800-52, and current cryptographic standards.
        """.strip()
        
        return summary
    
    def _create_asset_pdf_section(
        self,
        asset: CryptographicAsset,
        styles
    ) -> Any:
        """Create PDF section for single asset."""
        from reportlab.platypus import Table, TableStyle, Paragraph, Spacer, KeepTogether
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        
        # Asset header
        header = f"{asset.hostname}:{asset.port} ({asset.ip_address})"
        
        # Asset details table
        details = [
            ["Field", "Value"],
            ["TLS Version", asset.tls_version or "Unknown"],
            ["Cipher", asset.preferred_cipher or "Unknown"],
            ["Key Exchange", asset.key_exchange or "Unknown"],
            ["Cert Key", f"{asset.certificate_key_algorithm} {asset.certificate_key_size}b"],
            ["PQC Readiness", asset.pqc_readiness],
            ["Risk Score", f"{asset.risk_score:.1f} ({asset.risk_severity})"],
        ]
        
        table = Table(details, colWidths=[2*inch, 4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        
        return KeepTogether([
            Paragraph(f"<b>{header}</b>", styles['Heading3']),
            table,
        ])
    
    def _generate_cbom_id(self) -> str:
        """Generate unique CBOM ID."""
        timestamp = datetime.now(timezone.utc).isoformat()
        data = f"{timestamp}-{timestamp}".encode()
        hash_val = hashlib.sha256(data).hexdigest()[:12]
        return f"cbom-{hash_val}"
    
    @staticmethod
    def _base64url_encode(data: bytes) -> str:
        """Base64URL encode without padding."""
        import base64
        return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')
