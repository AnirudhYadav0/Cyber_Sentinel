import logging
import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import db_manager
from app.routes.health import router as health_router
from app.routes.events import router as events_router
from app.routes.alerts import router as alerts_router
from app.routes.incidents import router as incidents_router
from app.routes.detection import router as detection_router
from app.routes.analytics import router as analytics_router
from app.routes.auth import router as auth_router

# Configure structured application logging without credential output
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
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
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# CORS middleware configured for frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "Retry-After", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
)


# Security Headers & Request Tracking Middleware
@app.middleware("http")
async def security_and_tracking_middleware(request: Request, call_next):
    # 1. Generate or extract X-Request-ID
    req_id = request.headers.get("x-request-id")
    if not req_id or len(req_id) > 64:
        req_id = f"req_{uuid.uuid4().hex[:12]}"
    request.state.request_id = req_id

    # 2. Check Content-Length to guard against memory exhaustion
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            length = int(content_length)
            if length > settings.max_request_body_bytes:
                return JSONResponse(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    content={
                        "detail": f"Request body exceeds maximum allowed size of {settings.max_request_body_bytes // (1024 * 1024)}MB.",
                        "status": "error",
                    },
                    headers={"X-Request-ID": req_id},
                )
        except ValueError:
            pass

    # 3. Process request and measure duration
    start_time = time.time()
    try:
        response: Response = await call_next(request)
    except Exception as exc:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        logger.error(
            f"Unhandled exception on {request.method} {request.url.path} "
            f"[{req_id}] after {duration_ms}ms: {exc.__class__.__name__}"
        )
        response = JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An internal server error occurred.",
                "request_id": req_id,
                "status": "error",
            },
        )

    # 4. Attach Security Headers
    response.headers["X-Request-ID"] = req_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"

    # Log completion without recording sensitive request bodies
    duration_ms = round((time.time() - start_time) * 1000, 2)
    client_host = request.client.host if request.client else "unknown"
    logger.info(
        f"{request.method} {request.url.path} {response.status_code} "
        f"({duration_ms}ms) [{client_host}] req_id={req_id}"
    )

    return response


# Global exception handler for unhandled errors ensuring zero stack trace disclosure
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"Global exception handler caught {request.method} {request.url.path} [{req_id}]: {exc.__class__.__name__}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred. Please contact the administrator.",
            "request_id": req_id,
            "status": "error",
        },
    )


# Include all routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(events_router)
app.include_router(alerts_router)
app.include_router(incidents_router)
app.include_router(detection_router)
app.include_router(analytics_router)


@app.get("/healthz", tags=["Health & Status"])
def healthz():
    """Lightweight health probe endpoint for deployment container orchestrators."""
    return {"status": "ok", "service": settings.app_name}


@app.get("/")
def root():
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "docs_url": "/docs" if settings.debug else "disabled",
        "health_url": "/api/health",
        "readiness_url": "/api/ready",
    }
