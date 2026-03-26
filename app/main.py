from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.redis import redis_client
from app.core.exceptions import register_exception_handlers
from app.core.middleware import (
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
    CriticalEventLoggingMiddleware,
    setup_logging,
)
from app.db.database import init_db, close_db
from app.api.routes import api_router

# Setup logging on import
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    await init_db()
    await redis_client.connect()
    yield
    # Shutdown
    await redis_client.disconnect()
    await close_db()


app = FastAPI(
    title=settings.APP_NAME,
    description="A production-grade home services marketplace API",
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# Register exception handlers
register_exception_handlers(app)

# Security headers middleware (must be early)
app.add_middleware(SecurityHeadersMiddleware)

# Request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Critical event logging middleware
app.add_middleware(CriticalEventLoggingMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Request-ID",
        "X-Requested-With",
    ],
    expose_headers=["X-Request-ID"],
    max_age=600,  # 10 minutes
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "message": "Welcome to Home Services Marketplace API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}