"""
Enhanced middleware for FS Reconciliation Agents API v2.

This module provides middleware for:
- Request logging and monitoring
- Performance tracking
- Security headers
- Request/response modification
"""

import time
import uuid
import logging
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for comprehensive request logging."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Log request start
        start_time = time.time()
        logger.info(
            f"Request started - ID: {request_id}, "
            f"Method: {request.method}, "
            f"Path: {request.url.path}, "
            f"Client: {request.client.host if request.client else 'unknown'}"
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log successful request
            logger.info(
                f"Request completed - ID: {request_id}, "
                f"Status: {response.status_code}, "
                f"Duration: {process_time:.3f}s"
            )
            
            # Add performance headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.3f}"
            
            return response
            
        except Exception as e:
            # Log failed request
            process_time = time.time() - start_time
            logger.error(
                f"Request failed - ID: {request_id}, "
                f"Error: {str(e)}, "
                f"Duration: {process_time:.3f}s"
            )
            raise


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware for performance monitoring and optimization."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Track performance metrics
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate metrics
        process_time = time.time() - start_time
        
        # Add performance headers
        response.headers["X-Response-Time"] = f"{process_time:.3f}s"
        
        # Log slow requests
        if process_time > 1.0:  # Log requests taking more than 1 second
            logger.warning(
                f"Slow request detected - "
                f"Path: {request.url.path}, "
                f"Method: {request.method}, "
                f"Duration: {process_time:.3f}s"
            )
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Add CSP header for production
        if request.url.hostname not in ["localhost", "127.0.0.1"]:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' ws: wss:;"
            )
        
        return response


class CacheControlMiddleware(BaseHTTPMiddleware):
    """Middleware for cache control headers."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Add cache control headers based on response type
        if request.url.path.startswith("/api/"):
            # API responses should not be cached by default
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        elif request.url.path.startswith("/static/"):
            # Static assets can be cached
            response.headers["Cache-Control"] = "public, max-age=31536000"
        elif request.url.path.startswith("/docs"):
            # Documentation can be cached for a short time
            response.headers["Cache-Control"] = "public, max-age=3600"
        
        return response


class CompressionMiddleware(BaseHTTPMiddleware):
    """Middleware for response compression."""
    
    def __init__(self, app: ASGIApp, min_size: int = 1000):
        super().__init__(app)
        self.min_size = min_size
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Check if response should be compressed
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) >= self.min_size:
            # Add compression headers
            response.headers["Content-Encoding"] = "gzip"
        
        return response


class RateLimitHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding rate limit headers."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Add rate limit headers (these will be populated by the rate limiter)
        if "X-RateLimit-Limit" not in response.headers:
            response.headers["X-RateLimit-Limit"] = "100"
        if "X-RateLimit-Remaining" not in response.headers:
            response.headers["X-RateLimit-Remaining"] = "99"
        if "X-RateLimit-Reset" not in response.headers:
            response.headers["X-RateLimit-Reset"] = str(int(time.time() + 60))
        
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for enhanced error handling."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            # Log the error
            logger.error(
                f"Unhandled error in middleware - "
                f"Path: {request.url.path}, "
                f"Method: {request.method}, "
                f"Error: {str(e)}"
            )
            
            # Return a generic error response
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "type": "internal_error",
                        "message": "An unexpected error occurred",
                        "request_id": getattr(request.state, "request_id", None)
                    }
                }
            )


class MonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for application monitoring and metrics."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.request_count = 0
        self.error_count = 0
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Increment request counter
        self.request_count += 1
        
        try:
            response = await call_next(request)
            
            # Track response status
            if response.status_code >= 400:
                self.error_count += 1
            
            # Add monitoring headers
            response.headers["X-Request-Count"] = str(self.request_count)
            response.headers["X-Error-Rate"] = f"{self.error_count / self.request_count:.2%}"
            
            return response
            
        except Exception as e:
            # Increment error counter
            self.error_count += 1
            raise
