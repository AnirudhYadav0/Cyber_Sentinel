import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import db_manager
from app.routes.health import router as health_router
from app.routes.events import router as events_router
from app.routes.alerts import router as alerts_router
from app.routes.incidents import router as incidents_router
from app.routes.detection import router as detection_router

# Configure logging without sensitive credential output
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
)
logger = logging.getLogger("cybersentinel")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name} v{settings.app_version} ({settings.app_env})")
    # Connect database if configured
    try:
        db_manager.connect()
    except Exception as err:
        logger.warning(f"Database connection skipped or failed: {err.__class__.__name__}")
    yield
    # Clean shutdown
    logger.info(f"Shutting down {settings.app_name} and closing database connection...")
    db_manager.disconnect()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="CyberSentinel Security Operations Center Backend API",
    lifespan=lifespan,
)

# CORS middleware configured for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler for unhandled errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error processing {request.method} {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred.", "status": "error"},
    )


# Include all routers
app.include_router(health_router)
app.include_router(events_router)
app.include_router(alerts_router)
app.include_router(incidents_router)
app.include_router(detection_router)


@app.get("/")
def root():
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "docs_url": "/docs",
        "health_url": "/api/health",
        "readiness_url": "/api/ready",
    }
