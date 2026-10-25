from datetime import datetime, timezone
from fastapi import APIRouter
from app.config import settings
from app.database import db_manager

router = APIRouter(tags=["Health & Status"])


@router.get("/api/health")
def get_health():
    """Health check endpoint to verify API availability."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/api/ready")
def get_readiness():
    """Readiness endpoint verifying status of dependencies."""
    db_ready = db_manager.is_connected()
    return {
        "status": "ready" if db_ready else "degraded",
        "ready": db_ready,
        "database": "connected" if db_ready else "disconnected",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
