"""Q-Shield API v1 endpoints with real scan and persistence workflows."""

from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple
import hashlib
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import oauth_router
from app.core.logging import get_logger
from app.db.database import get_session
from app.models.models import (
    Asset,
    AssetType,
    ExposureType,
    Scan,
    ScanResult,
    QuantumSafeCertificate,
)
from app.services.cbom.cbom_generator import CBOMGenerator
from app.services.certificate.certificate_engine import QuantumSafeCertificateEngine
from app.services.compliance.compliance_engine import ComplianceMappingEngine
from app.services.crypto.tls_fingerprint import TLSScanner
from app.services.discovery.asset_discovery import AssetDiscoveryEngine
from app.services.pqc.pqc_validator import PQCValidator
from app.services.risk.risk_scoring import RiskScoringEngine

logger = get_logger(__name__)
api_router = APIRouter(tags=["Q-Shield API"])
api_router.include_router(oauth_router)


def _as_text(value) -> Optional[str]:
    if value is None:
        return None
    return value.value if hasattr(value, "value") else str(value)


def _target_to_host_port(target: str) -> Tuple[str, int]:
    parts = target.split(":", 1)
    hostname = parts[0].strip()
    port = int(parts[1]) if len(parts) > 1 and parts[1].strip() else 443
    return hostname, port


NIST_PQC_PREFIXES = ("ML-KEM", "ML-DSA", "SLH-DSA")


def _is_nist_pqc_algorithm(name: Optional[str]) -> bool:
    if not name:
        return False
    upper = name.upper()
    return any(prefix in upper for prefix in NIST_PQC_PREFIXES)


def _quantum_safe_label(readiness: Optional[str], kem: Optional[str], signature: Optional[str]) -> Optional[str]:
    if readiness == "fully_quantum_safe" and _is_nist_pqc_algorithm(kem) and _is_nist_pqc_algorithm(signature):
        return "Fully Quantum Safe"
    if readiness == "pqc_ready" and (_is_nist_pqc_algorithm(kem) or _is_nist_pqc_algorithm(signature)):
        return "PQC Ready"
    return None


def _classify_asset_type(hostname: str, port: int, protocol: Optional[str]) -> AssetType:
    host = (hostname or "").lower()
    proto = (protocol or "").upper()
    vpn_ports = {500, 1194, 1701, 1723, 4500}

    if "VPN" in proto or port in vpn_ports or any(token in host for token in ["vpn", "ipsec", "openvpn", "wireguard", "remote"]):
        return AssetType.VPN_SERVER
    if any(token in host for token in ["api", "gateway", "graphql", "grpc", "rest"]):
        return AssetType.API_ENDPOINT
    return AssetType.WEB_SERVER


async def _get_or_create_asset(session: AsyncSession, hostname: str, port: int) -> Asset:
    asset_res = await session.execute(
        select(Asset).where((Asset.hostname == hostname) & (Asset.port == port))
    )
    asset = asset_res.scalar_one_or_none()
    if asset:
        return asset

    asset = Asset(hostname=hostname, port=port, protocol="HTTPS", pqc_readiness="unknown")
    session.add(asset)
    await session.flush()
    return asset


async def _run_single_assessment(hostname: str, port: int):
    scanner = TLSScanner()
    validator = PQCValidator()
    scorer = RiskScoringEngine()

    tls_config = await scanner.scan(hostname, port)
    leaf = tls_config.certificates[0] if tls_config.certificates else None

    pqc_assessment = validator.assess_tls_configuration(
        tls_version=_as_text(tls_config.tls_version),
        cipher_suites=tls_config.cipher_suites,
        preferred_cipher=tls_config.preferred_cipher,
        key_exchange=tls_config.key_exchange,
        certificate_key_algorithm=leaf.public_key_algorithm if leaf else None,
        certificate_key_size=leaf.public_key_size if leaf else None,
        signature_algorithm=leaf.signature_algorithm if leaf else None,
        perfect_forward_secrecy=tls_config.perfect_forward_secrecy,
        pqc_kem=tls_config.pqc_key_encapsulation,
        pqc_signature=tls_config.pqc_signature,
        asset_id=f"{hostname}:{port}",
    )

    risk = scorer.calculate_score(
        tls_version=_as_text(tls_config.tls_version),
        cipher_suites=tls_config.cipher_suites,
        preferred_cipher=tls_config.preferred_cipher,
        key_exchange=tls_config.key_exchange,
        certificate_key_algorithm=leaf.public_key_algorithm if leaf else None,
        certificate_key_size=leaf.public_key_size if leaf else None,
        cert_signature_algorithm=leaf.signature_algorithm if leaf else None,
        cert_not_after=leaf.not_after if leaf else None,
        perfect_forward_secrecy=tls_config.perfect_forward_secrecy,
        ocsp_stapling=tls_config.ocsp_stapling,
        hsts_enabled=tls_config.hsts_enabled,
        hsts_preload=tls_config.hsts_preload,
        self_signed=leaf.is_self_signed if leaf else False,
        pqc_supported=bool(pqc_assessment.pqc_kem_detected or pqc_assessment.pqc_signature_detected),
    )

    return tls_config, pqc_assessment, risk


@api_router.get("/assets", response_model=dict)
async def list_assets(
    session: AsyncSession = Depends(get_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
):
    try:
        result = await session.execute(select(Asset).offset(skip).limit(limit))
        assets = result.scalars().all()
        return {
            "assets": [
                {
                    "id": str(a.uuid),
                    "hostname": a.hostname,
                    "port": a.port,
                    "asset_type": _as_text(a.asset_type),
                    "exposure_type": _as_text(a.exposure_type),
                    "pqc_readiness": _as_text(a.pqc_readiness),
                    "risk_score": a.risk_score,
                    "last_scanned": a.last_scanned.isoformat() if a.last_scanned else None,
                }
                for a in assets
            ]
        }
    except Exception as exc:
        logger.error(f"Error listing assets: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list assets")


@api_router.post("/assets", response_model=dict, status_code=201)
async def create_asset(
    hostname: str = Query(...),
    port: int = Query(443, ge=1, le=65535),
    session: AsyncSession = Depends(get_session),
):
    try:
        existing = await session.execute(
            select(Asset).where((Asset.hostname == hostname) & (Asset.port == port))
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Asset already exists")

        asset = Asset(hostname=hostname, port=port, protocol="HTTPS", pqc_readiness="unknown")
        session.add(asset)
        await session.flush()
        return {"id": str(asset.uuid), "hostname": asset.hostname, "port": asset.port}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error creating asset: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create asset")


@api_router.post("/discovery/public-facing", response_model=dict)
async def discover_public_facing_assets(
    domains: List[str] = Query(default=[]),
    ip_ranges: List[str] = Query(default=[]),
    include_subdomains: bool = Query(True),
    ports: List[int] = Query(default=[443, 8443, 9443, 500, 1194, 1701, 1723, 4500]),
    session: AsyncSession = Depends(get_session),
):
    if not domains and not ip_ranges:
        raise HTTPException(status_code=400, detail="At least one domain or ip_range is required")

    engine = AssetDiscoveryEngine()
    discovered_assets = []

    try:
        for domain in [d.strip() for d in domains if d and d.strip()]:
            discovered_assets.extend(
                await engine.discover_domain(
                    domain,
                    include_subdomains=include_subdomains,
                    ports=ports,
                )
            )

        for cidr in [r.strip() for r in ip_ranges if r and r.strip()]:
            discovered_assets.extend(await engine.discover_ip_range(cidr, ports=ports))
    finally:
        await engine.close()

    created = 0
    updated = 0
    category_counts = {
        "tls_certificate": 0,
        "tls_based_vpn": 0,
        "apis": 0,
    }
    persisted = []

    for item in discovered_assets:
        asset_type = _classify_asset_type(item.hostname, item.port, item.protocol)
        existing_res = await session.execute(
            select(Asset).where((Asset.hostname == item.hostname) & (Asset.port == item.port))
        )
        existing = existing_res.scalar_one_or_none()

        if existing:
            existing.ip_address = item.ip_address
            existing.protocol = item.protocol or existing.protocol
            existing.asset_type = asset_type
            existing.exposure_type = ExposureType.PUBLIC
            existing.discovery_source = item.discovery_source or existing.discovery_source
            existing.asn = item.asn
            existing.asn_name = item.asn_name
            existing.country_code = item.country_code
            existing.cloud_provider = item.cloud_provider
            asset = existing
            updated += 1
        else:
            asset = Asset(
                hostname=item.hostname,
                ip_address=item.ip_address,
                port=item.port,
                protocol=item.protocol or "HTTPS",
                asset_type=asset_type,
                exposure_type=ExposureType.PUBLIC,
                discovery_source=item.discovery_source,
                asn=item.asn,
                asn_name=item.asn_name,
                country_code=item.country_code,
                cloud_provider=item.cloud_provider,
                pqc_readiness="unknown",
            )
            session.add(asset)
            await session.flush()
            created += 1

        if asset_type == AssetType.VPN_SERVER:
            category_counts["tls_based_vpn"] += 1
        elif asset_type == AssetType.API_ENDPOINT:
            category_counts["apis"] += 1

        if item.port in {443, 8443, 9443}:
            category_counts["tls_certificate"] += 1

        persisted.append(
            {
                "hostname": item.hostname,
                "ip_address": item.ip_address,
                "port": item.port,
                "protocol": item.protocol,
                "asset_type": _as_text(asset_type),
                "exposure_type": "public",
                "discovery_source": item.discovery_source,
            }
        )

    return {
        "status": "complete",
        "discovered_total": len(discovered_assets),
        "created": created,
        "updated": updated,
        "inventory": category_counts,
        "assets": persisted,
    }


@api_router.get("/assets/{asset_id}", response_model=dict)
async def get_asset(asset_id: str, session: AsyncSession = Depends(get_session)):
    try:
        result = await session.execute(select(Asset).where(Asset.uuid == uuid.UUID(asset_id)))
        asset = result.scalar_one_or_none()
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        return {
            "id": str(asset.uuid),
            "hostname": asset.hostname,
            "port": asset.port,
            "asset_type": _as_text(asset.asset_type),
            "exposure_type": _as_text(asset.exposure_type),
            "pqc_readiness": _as_text(asset.pqc_readiness),
            "risk_score": asset.risk_score,
            "last_scanned": asset.last_scanned.isoformat() if asset.last_scanned else None,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error getting asset: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve asset")


@api_router.delete("/assets/{asset_id}", status_code=204)
async def delete_asset(asset_id: str, session: AsyncSession = Depends(get_session)):
    try:
        result = await session.execute(select(Asset).where(Asset.uuid == uuid.UUID(asset_id)))
        asset = result.scalar_one_or_none()
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        await session.delete(asset)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error deleting asset: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete asset")


@api_router.post("/scans", response_model=dict, status_code=202)
async def initiate_scan(
    targets: List[str] = Query(...),
    scan_type: str = Query("full", pattern="^(full|tls|pqc|compliance)$"),
    session: AsyncSession = Depends(get_session),
):
    try:
        scan = Scan(scan_type=scan_type, total_targets=len(targets), status="running", targets=targets)
        scan.started_at = datetime.now(timezone.utc)
        session.add(scan)
        await session.flush()

        completed = 0
        failed = 0

        for target in targets:
            try:
                hostname, port = _target_to_host_port(target)
                asset = await _get_or_create_asset(session, hostname, port)
                tls_config, pqc_assessment, risk = await _run_single_assessment(hostname, port)
                leaf = tls_config.certificates[0] if tls_config.certificates else None

                scan_result = ScanResult(
                    scan_id=scan.id,
                    asset_id=asset.id,
                    tls_version=_as_text(tls_config.tls_version),
                    cipher_suites=tls_config.cipher_suites,
                    preferred_cipher=tls_config.preferred_cipher,
                    key_exchange=tls_config.key_exchange,
                    perfect_forward_secrecy=tls_config.perfect_forward_secrecy,
                    session_resumption=tls_config.session_resumption,
                    ocsp_stapling=tls_config.ocsp_stapling,
                    hsts_enabled=tls_config.hsts_enabled,
                    hsts_max_age=tls_config.hsts_max_age,
                    alpn_protocols=tls_config.alpn_protocols,
                    cert_public_key_algorithm=leaf.public_key_algorithm if leaf else None,
                    cert_key_size=leaf.public_key_size if leaf else None,
                    cert_signature_algorithm=leaf.signature_algorithm if leaf else None,
                    cert_issuer=leaf.issuer if leaf else None,
                    cert_subject=leaf.subject if leaf else None,
                    cert_not_before=leaf.not_before if leaf else None,
                    cert_not_after=leaf.not_after if leaf else None,
                    cert_san=leaf.san if leaf else [],
                    cert_chain_valid=tls_config.chain_valid,
                    cert_revocation_status=tls_config.ocsp_status,
                    cert_fingerprint_sha256=leaf.fingerprint_sha256 if leaf else None,
                    pqc_key_encapsulation=_as_text(pqc_assessment.pqc_kem_detected),
                    pqc_signature=_as_text(pqc_assessment.pqc_signature_detected),
                    hybrid_tls_detected=bool(tls_config.hybrid_mode),
                    hybrid_tls_details={
                        "detected": bool(tls_config.hybrid_mode),
                        "pqc_kem": tls_config.pqc_key_encapsulation,
                        "pqc_signature": tls_config.pqc_signature,
                    },
                    risk_score=risk.total_score,
                    pqc_readiness=_as_text(pqc_assessment.readiness_level),
                    vulnerabilities=[
                        {
                            "name": t.name,
                            "description": t.description,
                            "severity": t.severity,
                        }
                        for t in pqc_assessment.threats
                    ],
                    compliance_findings={"pending": True},
                    raw_handshake_data=tls_config.raw_handshake,
                    raw_certificate_chain=[cert.raw_pem for cert in tls_config.certificates],
                    scan_duration_ms=tls_config.scan_duration_ms,
                    scan_error=tls_config.error_message,
                )
                session.add(scan_result)

                asset.risk_score = risk.total_score
                asset.pqc_readiness = _as_text(pqc_assessment.readiness_level)
                asset.last_scanned = datetime.now(timezone.utc)

                completed += 1
            except Exception as inner_exc:
                logger.error(f"Scan target failed for {target}: {inner_exc}", exc_info=True)
                failed += 1

        scan.completed_targets = completed
        scan.failed_targets = failed
        scan.progress = 1.0
        scan.completed_at = datetime.now(timezone.utc)
        scan.status = "completed" if failed == 0 else "failed"

        return {
            "scan_id": str(scan.uuid),
            "status": _as_text(scan.status),
            "scan_type": scan.scan_type,
            "targets": scan.total_targets,
            "completed": scan.completed_targets,
            "failed": scan.failed_targets,
        }
    except Exception as exc:
        logger.error(f"Error initiating scan: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to initiate scan")


@api_router.get("/scans/{scan_id}", response_model=dict)
async def get_scan_status(scan_id: str, session: AsyncSession = Depends(get_session)):
    try:
        result = await session.execute(select(Scan).where(Scan.uuid == uuid.UUID(scan_id)))
        scan = result.scalar_one_or_none()
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")

        return {
            "scan_id": str(scan.uuid),
            "status": _as_text(scan.status),
            "scan_type": scan.scan_type,
            "progress": scan.progress,
            "total": scan.total_targets,
            "completed": scan.completed_targets,
            "failed": scan.failed_targets,
            "started_at": scan.started_at.isoformat() if scan.started_at else None,
            "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error getting scan status: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve scan status")


@api_router.post("/assess/crypto", response_model=dict)
async def assess_crypto(
    hostname: str = Query(...),
    port: int = Query(443, ge=1, le=65535),
):
    try:
        tls_config, pqc_assessment, risk = await _run_single_assessment(hostname, port)
        readiness = _as_text(pqc_assessment.readiness_level)
        pqc_kem = _as_text(pqc_assessment.pqc_kem_detected)
        pqc_signature = _as_text(pqc_assessment.pqc_signature_detected)

        return {
            "hostname": hostname,
            "port": port,
            "accessible": tls_config.is_accessible,
            "tls_version": _as_text(tls_config.tls_version),
            "preferred_cipher": tls_config.preferred_cipher,
            "key_exchange": tls_config.key_exchange,
            "pfs": tls_config.perfect_forward_secrecy,
            "pqc_readiness": readiness,
            "pqc_kem": pqc_kem,
            "pqc_signature": pqc_signature,
            "risk_score": risk.total_score,
            "severity": _as_text(risk.severity_level),
            "quantum_safe_label": _quantum_safe_label(readiness, pqc_kem, pqc_signature),
            "label_eligible": _quantum_safe_label(readiness, pqc_kem, pqc_signature) is not None,
            "recommendations": pqc_assessment.remediation_steps,
            "threats": [
                {
                    "id": threat.threat_id,
                    "name": threat.name,
                    "severity": threat.severity,
                    "hndl_risk": threat.harvest_now_decrypt_later_risk,
                }
                for threat in pqc_assessment.threats
            ],
            "scan_duration_ms": tls_config.scan_duration_ms,
            "error_message": tls_config.error_message,
        }
    except Exception as exc:
        logger.error(f"Assessment failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Assessment failed")


@api_router.get("/inventory/public-facing", response_model=dict)
async def public_facing_crypto_inventory(
    session: AsyncSession = Depends(get_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    validator = PQCValidator()
    assets_res = await session.execute(
        select(Asset)
        .where(Asset.exposure_type == ExposureType.PUBLIC)
        .offset(skip)
        .limit(limit)
    )
    assets = assets_res.scalars().all()

    inventory = {
        "tls_certificate_inventory": [],
        "tls_based_vpn_inventory": [],
        "api_inventory": [],
        "all_public_assets": [],
    }

    for asset in assets:
        latest_res = await session.execute(
            select(ScanResult)
            .where(ScanResult.asset_id == asset.id)
            .order_by(ScanResult.created_at.desc())
            .limit(1)
        )
        latest = latest_res.scalar_one_or_none()

        recommendations = [
            "Run a fresh scan to generate TLS and PQC control evidence",
            "Enable TLS 1.3 and PFS for all public endpoints",
            "Pilot ML-KEM and ML-DSA based hybrid TLS",
        ]
        readiness = _as_text(asset.pqc_readiness)
        pqc_kem = None
        pqc_signature = None
        risk_score = asset.risk_score
        crypto_controls = {
            "tls_version": None,
            "cipher_suites": [],
            "preferred_cipher": None,
            "key_exchange": None,
            "certificate": None,
        }

        if latest:
            pqc_assessment = validator.assess_tls_configuration(
                tls_version=latest.tls_version,
                cipher_suites=latest.cipher_suites or [],
                preferred_cipher=latest.preferred_cipher,
                key_exchange=latest.key_exchange,
                certificate_key_algorithm=latest.cert_public_key_algorithm,
                certificate_key_size=latest.cert_key_size,
                signature_algorithm=latest.cert_signature_algorithm,
                perfect_forward_secrecy=bool(latest.perfect_forward_secrecy),
                pqc_kem=latest.pqc_key_encapsulation,
                pqc_signature=latest.pqc_signature,
                asset_id=str(asset.uuid),
            )
            recommendations = pqc_assessment.remediation_steps
            readiness = _as_text(latest.pqc_readiness) or _as_text(pqc_assessment.readiness_level)
            pqc_kem = latest.pqc_key_encapsulation
            pqc_signature = latest.pqc_signature
            risk_score = latest.risk_score
            crypto_controls = {
                "tls_version": latest.tls_version,
                "cipher_suites": latest.cipher_suites,
                "preferred_cipher": latest.preferred_cipher,
                "key_exchange": latest.key_exchange,
                "certificate": {
                    "subject": latest.cert_subject,
                    "issuer": latest.cert_issuer,
                    "public_key_algorithm": latest.cert_public_key_algorithm,
                    "key_size": latest.cert_key_size,
                    "signature_algorithm": latest.cert_signature_algorithm,
                    "valid_from": latest.cert_not_before.isoformat() if latest.cert_not_before else None,
                    "valid_to": latest.cert_not_after.isoformat() if latest.cert_not_after else None,
                },
            }

        label = _quantum_safe_label(readiness, pqc_kem, pqc_signature)
        asset_view = {
            "id": str(asset.uuid),
            "hostname": asset.hostname,
            "ip_address": asset.ip_address,
            "port": asset.port,
            "protocol": asset.protocol,
            "asset_type": _as_text(asset.asset_type),
            "exposure_type": _as_text(asset.exposure_type),
            "pqc_readiness": readiness,
            "quantum_safe_label": label,
            "label_eligible": label is not None,
            "risk_score": risk_score,
            "crypto_controls": crypto_controls,
            "recommendations": recommendations,
            "last_scanned": asset.last_scanned.isoformat() if asset.last_scanned else None,
        }

        inventory["all_public_assets"].append(asset_view)

        if asset.asset_type == AssetType.VPN_SERVER:
            inventory["tls_based_vpn_inventory"].append(asset_view)
        if asset.asset_type == AssetType.API_ENDPOINT:
            inventory["api_inventory"].append(asset_view)
        if asset.port in {443, 8443, 9443}:
            inventory["tls_certificate_inventory"].append(asset_view)

    return {
        "status": "complete",
        "scope": "public_facing",
        "counts": {
            "total": len(inventory["all_public_assets"]),
            "tls_certificates": len(inventory["tls_certificate_inventory"]),
            "tls_based_vpn": len(inventory["tls_based_vpn_inventory"]),
            "apis": len(inventory["api_inventory"]),
        },
        "inventory": inventory,
    }


@api_router.post("/cbom/generate", response_model=dict)
async def generate_cbom(
    assets: List[str] = Query(...),
    format: str = Query("json", pattern="^(json|pdf|csv|jws)$"),
    session: AsyncSession = Depends(get_session),
):
    try:
        scan_payload = []
        for hostname in assets:
            asset_res = await session.execute(select(Asset).where(Asset.hostname == hostname))
            asset = asset_res.scalars().first()
            if not asset:
                continue

            result_res = await session.execute(
                select(ScanResult)
                .where(ScanResult.asset_id == asset.id)
                .order_by(ScanResult.created_at.desc())
                .limit(1)
            )
            latest = result_res.scalar_one_or_none()
            if not latest:
                continue

            scan_payload.append(
                {
                    "uuid": str(asset.uuid),
                    "hostname": asset.hostname,
                    "ip_address": asset.ip_address,
                    "port": asset.port,
                    "protocol": asset.protocol,
                    "discovery_source": asset.discovery_source,
                    "tls_version": latest.tls_version,
                    "preferred_cipher": latest.preferred_cipher,
                    "cipher_suites": latest.cipher_suites,
                    "key_exchange": latest.key_exchange,
                    "perfect_forward_secrecy": latest.perfect_forward_secrecy,
                    "cert_subject": latest.cert_subject,
                    "cert_issuer": latest.cert_issuer,
                    "cert_public_key_algorithm": latest.cert_public_key_algorithm,
                    "cert_key_size": latest.cert_key_size,
                    "cert_signature_algorithm": latest.cert_signature_algorithm,
                    "cert_not_before": latest.cert_not_before,
                    "cert_not_after": latest.cert_not_after,
                    "cert_san": latest.cert_san,
                    "pqc_key_encapsulation": latest.pqc_key_encapsulation,
                    "pqc_signature": latest.pqc_signature,
                    "pqc_readiness": _as_text(latest.pqc_readiness),
                    "risk_score": latest.risk_score,
                    "scan_timestamp": latest.created_at,
                }
            )

        if not scan_payload:
            raise HTTPException(status_code=404, detail="No scanned assets found for CBOM generation")

        generator = CBOMGenerator()
        cbom = generator.generate_cbom(scan_payload, organization="Q-Shield", generated_by="Q-Shield API")

        if format == "json":
            exported = generator.export_json(cbom)
        elif format == "csv":
            exported = generator.export_csv(cbom)
        elif format == "jws":
            exported = generator.export_jws(
                cbom,
                sign_data_func=lambda data: hashlib.sha256(data).digest(),
            )
        else:
            exported = generator.export_pdf(cbom).decode("latin-1", errors="ignore")

        return {
            "cbom_id": cbom.cbom_id,
            "format": format,
            "total_assets": cbom.total_assets,
            "assets_quantum_safe": cbom.assets_fully_quantum_safe,
            "assets_pqc_ready": cbom.assets_pqc_ready,
            "assets_vulnerable": cbom.assets_vulnerable,
            "status": "generated",
            "document_preview": exported[:2000],
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"CBOM generation failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="CBOM generation failed")


@api_router.post("/certificates/issue", response_model=dict, status_code=201)
async def issue_certificate(
    hostname: str = Query(...),
    port: int = Query(443, ge=1, le=65535),
    session: AsyncSession = Depends(get_session),
):
    try:
        asset = await _get_or_create_asset(session, hostname, port)
        tls_config, pqc_assessment, risk = await _run_single_assessment(hostname, port)

        readiness = _as_text(pqc_assessment.readiness_level)
        label = _quantum_safe_label(
            readiness,
            _as_text(pqc_assessment.pqc_kem_detected),
            _as_text(pqc_assessment.pqc_signature_detected),
        )
        if readiness not in {"fully_quantum_safe", "pqc_ready"} or label is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Asset readiness is '{readiness}'. Certificate requires NIST-backed "
                    "fully_quantum_safe or pqc_ready posture."
                ),
            )

        leaf = tls_config.certificates[0] if tls_config.certificates else None
        if not leaf:
            raise HTTPException(status_code=400, detail="No certificate data available from TLS scan")

        cert_engine = QuantumSafeCertificateEngine()
        cert_blob = cert_engine.issue_certificate(
            asset_id=str(asset.uuid),
            hostname=hostname,
            port=port,
            pqc_readiness_level=readiness,
            tls_version=_as_text(tls_config.tls_version) or "unknown",
            key_exchange=tls_config.key_exchange or "unknown",
            cipher_suite=tls_config.preferred_cipher or "unknown",
            pqc_algorithms=[a for a in [_as_text(pqc_assessment.pqc_kem_detected), _as_text(pqc_assessment.pqc_signature_detected)] if a],
            certificate_key_algo=leaf.public_key_algorithm,
            certificate_key_size=leaf.public_key_size,
            asn=asset.asn,
            country_code=asset.country_code,
            risk_score=risk.total_score,
            sign_data_func=lambda data: hashlib.sha256(data).digest(),
        )

        level = "fully_quantum_safe" if readiness == "fully_quantum_safe" else "pqc_ready"
        cert_record = QuantumSafeCertificate(
            certificate_id=cert_blob["certificate_id"],
            asset_id=asset.id,
            level=level,
            tls_version=_as_text(tls_config.tls_version) or "unknown",
            key_exchange=tls_config.key_exchange or "unknown",
            cipher_suite=tls_config.preferred_cipher or "unknown",
            pqc_algorithms=cert_blob["data"].get("pqc_algorithms", []),
            issued_at=datetime.fromisoformat(cert_blob["issue_timestamp"]),
            expires_at=datetime.fromisoformat(cert_blob["expiry_timestamp"]),
            signature=base64_to_bytes(cert_blob.get("signature")) if cert_blob.get("signature") else hashlib.sha256(cert_blob["certificate_id"].encode()).digest(),
            signature_algorithm=cert_blob.get("signature_algorithm") or "RSA-PSS-SHA384",
            verification_url=cert_blob["verification_url"],
            qr_code_data=cert_blob.get("qr_code"),
            is_valid=True,
            cert_metadata={"risk_score": risk.total_score, "readiness": readiness},
        )
        session.add(cert_record)

        return {
            "certificate_id": cert_record.certificate_id,
            "hostname": hostname,
            "port": port,
            "level": level,
            "verification_url": cert_record.verification_url,
            "expires_at": cert_record.expires_at.isoformat(),
            "status": "issued",
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Certificate issuance failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Certificate issuance failed")


def base64_to_bytes(value: str) -> bytes:
    import base64
    return base64.b64decode(value)


@api_router.get("/certificates/{certificate_id}", response_model=dict)
async def get_certificate(certificate_id: str, session: AsyncSession = Depends(get_session)):
    try:
        result = await session.execute(
            select(QuantumSafeCertificate).where(QuantumSafeCertificate.certificate_id == certificate_id)
        )
        cert = result.scalar_one_or_none()
        if not cert:
            raise HTTPException(status_code=404, detail="Certificate not found")

        is_expired = cert.expires_at < datetime.now(timezone.utc)
        status = "expired" if is_expired else "valid"
        return {
            "certificate_id": cert.certificate_id,
            "status": status,
            "level": _as_text(cert.level),
            "hostname": cert.asset.hostname if cert.asset else None,
            "issued_at": cert.issued_at.isoformat(),
            "expires_at": cert.expires_at.isoformat(),
            "verification_url": cert.verification_url,
            "is_valid": cert.is_valid and not is_expired,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error retrieving certificate: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve certificate")


@api_router.post("/compliance/check", response_model=dict)
async def check_compliance(
    assets: List[str] = Query(...),
    frameworks: List[str] = Query(["nist_sp_800_208", "nist_sp_800_52"]),
    session: AsyncSession = Depends(get_session),
):
    try:
        engine = ComplianceMappingEngine()
        findings_payload = []
        compliant_assets = 0

        for hostname in assets:
            asset_res = await session.execute(select(Asset).where(Asset.hostname == hostname))
            asset = asset_res.scalars().first()
            if not asset:
                continue

            latest_res = await session.execute(
                select(ScanResult)
                .where(ScanResult.asset_id == asset.id)
                .order_by(ScanResult.created_at.desc())
                .limit(1)
            )
            latest = latest_res.scalar_one_or_none()
            if not latest:
                continue

            finding_list = engine.assess_compliance(
                asset_id=str(asset.uuid),
                frameworks=frameworks,
                tls_version=latest.tls_version,
                cipher_suites=latest.cipher_suites,
                preferred_cipher=latest.preferred_cipher,
                key_exchange=latest.key_exchange,
                certificate_key_algorithm=latest.cert_public_key_algorithm,
                certificate_key_size=latest.cert_key_size,
                cert_signature_algorithm=latest.cert_signature_algorithm,
                perfect_forward_secrecy=bool(latest.perfect_forward_secrecy),
                pqc_kem_detected=bool(latest.pqc_key_encapsulation),
                pqc_signature_detected=bool(latest.pqc_signature),
            )

            compliant = all(item.status == "compliant" for item in finding_list)
            compliant_assets += 1 if compliant else 0
            findings_payload.append(
                {
                    "asset": asset.hostname,
                    "asset_id": str(asset.uuid),
                    "fully_compliant": compliant,
                    "findings": [
                        {
                            "framework": item.framework,
                            "control_id": item.control_id,
                            "control_name": item.control_name,
                            "status": item.status,
                            "gap_description": item.gap_description,
                            "priority": item.priority,
                            "evidence": item.evidence,
                        }
                        for item in finding_list
                    ],
                }
            )

        return {
            "assessment_id": str(uuid.uuid4()),
            "frameworks": frameworks,
            "total_assets": len(findings_payload),
            "compliant": compliant_assets,
            "status": "complete",
            "results": findings_payload,
        }
    except Exception as exc:
        logger.error(f"Compliance check failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Compliance check failed")


@api_router.get("/health", include_in_schema=False)
async def health_check(session: AsyncSession = Depends(get_session)):
    try:
        await session.execute(select(1))
        return {"status": "healthy", "service": "q-shield-api"}
    except Exception as exc:
        logger.error(f"Health check failed: {exc}", exc_info=True)
        raise HTTPException(status_code=503, detail="Service unhealthy")


__all__ = ["api_router"]
