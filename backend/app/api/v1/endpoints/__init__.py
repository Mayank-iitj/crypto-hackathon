"""Q-Shield API v1 Router"""
from fastapi import APIRouter

router = APIRouter()

# Import endpoints
from .endpoints import assets, scanning, assessment, cbom, certificates, compliance

# Include sub-routers
router.include_router(assets.router, prefix="/assets", tags=["Assets"])
router.include_router(scanning.router, prefix="/scans", tags=["Scanning"])
router.include_router(assessment.router, prefix="/assess", tags=["Assessment"])
router.include_router(cbom.router, prefix="/cbom", tags=["CBOM"])
router.include_router(certificates.router, prefix="/certificates", tags=["Certificates"])
router.include_router(compliance.router, prefix="/compliance", tags=["Compliance"])

# Main API router to be imported in main.py
api_router = router
