import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routes.health import router as health_router
from app.routes.events import router as events_router

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
)
logger = logging.getLogger("cybersentinel")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name} v{settings.app_version} ({settings.app_env})")
    # Startup tasks (e.g. database connection in future phases)
    yield
    # Shutdown tasks
    logger.info(f"Shutting down {settings.app_name}")


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


# Include routers
app.include_router(health_router)
app.include_router(events_router)


@app.get("/")
def root():
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "docs_url": "/docs",
        "health_url": "/api/health",
    }
