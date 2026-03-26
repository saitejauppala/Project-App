"""Middleware for logging, security, and request processing."""

import time
import uuid
import logging
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import settings

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests and responses."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        
        # Start timer
        start_time = time.time()
        
        # Get client info
        client_host = request.client.host if request.client else "unknown"
        
        # Log request
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_host": client_host,
                "user_agent": request.headers.get("user-agent", "unknown"),
            },
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log response
            logger.info(
                f"Request completed: {request.method} {request.url.path} - {response.status_code} in {duration:.3f}s",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                },
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as exc:
            # Calculate duration even for errors
            duration = time.time() - start_time
            
            # Log error
            logger.error(
                f"Request failed: {request.method} {request.url.path} - {type(exc).__name__} in {duration:.3f}s",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error_type": type(exc).__name__,
                    "duration_ms": round(duration * 1000, 2),
                },
                exc_info=True,
            )
            
            raise


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Strict transport security (HTTPS only)
        if not settings.DEBUG:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Content security policy
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response


class CriticalEventLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log critical events (auth, payments)."""
    
    CRITICAL_PATHS = [
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/payments/create-order",
        "/api/v1/payments/webhook",
        "/api/v1/bookings/create",
    ]
    
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        
        # Check if this is a critical path
        is_critical = any(path.startswith(cp) for cp in self.CRITICAL_PATHS)
        
        if is_critical:
            # Get user info if available
            user_id = getattr(request.state, "user_id", None)
            
            logger.warning(
                f"Critical endpoint accessed: {request.method} {path}",
                extra={
                    "event_type": "critical_endpoint_access",
                    "method": request.method,
                    "path": path,
                    "user_id": user_id,
                    "client_host": request.client.host if request.client else "unknown",
                },
            )
        
        response = await call_next(request)
        
        # Log auth failures
        if path.startswith("/api/v1/auth") and response.status_code == 401:
            logger.warning(
                f"Authentication failed: {request.method} {path}",
                extra={
                    "event_type": "auth_failure",
                    "method": request.method,
                    "path": path,
                    "client_host": request.client.host if request.client else "unknown",
                },
            )
        
        # Log payment events
        if path.startswith("/api/v1/payments"):
            event_type = "payment_success" if response.status_code < 400 else "payment_error"
            logger.warning(
                f"Payment event: {event_type} - {request.method} {path}",
                extra={
                    "event_type": event_type,
                    "method": request.method,
                    "path": path,
                    "status_code": response.status_code,
                },
            )
        
        return response


def setup_logging():
    """Configure logging for production."""
    import logging.config
    
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
            "json": {
                "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "default",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "default",
                "filename": "app.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "default",
                "filename": "error.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 10,
            },
        },
        "loggers": {
            "": {
                "level": "INFO",
                "handlers": ["console", "file", "error_file"],
                "propagate": False,
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "level": "WARNING" if not settings.DEBUG else "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
        },
    }
    
    logging.config.dictConfig(logging_config)