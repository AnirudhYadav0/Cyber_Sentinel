from datetime import datetime, timezone
from fastapi import APIRouter, Response, status
from app.config import settings
from app.database import db_manager

router = APIRouter(tags=["Health & Status"])


@router.get("/api/health")
def get_health():
    """Health check endpoint to verify API process availability."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/api/ready")
def get_readiness(response: Response):
    """Readiness endpoint verifying status of required dependencies (e.g. MongoDB)."""
    db_ready = db_manager.is_connected() and db_manager.ping()
    if not db_ready:
        # Return degraded readiness status without throwing unhandled exceptions
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "degraded",
            "ready": False,
            "database": "disconnected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "Database is not connected. Configure MONGODB_URI in .env to connect to MongoDB Atlas.",
        }

    return {
        "status": "ready",
        "ready": True,
        "database": "connected",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
