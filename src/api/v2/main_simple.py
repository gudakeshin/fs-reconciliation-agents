"""
Simplified FastAPI application for FS Reconciliation Agents API v2.

This module provides an improved API with:
- Better error handling and validation
- Enhanced documentation
- WebSocket support for real-time updates
- Comprehensive logging and monitoring
"""

import os
import logging
import time
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.utils.security_utils.authentication import get_current_user
from src.core.services.caching.redis_cache import initialize_cache_service, CacheConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class APIVersionMiddleware(BaseHTTPMiddleware):
    """Middleware to handle API versioning."""
    
    async def dispatch(self, request: Request, call_next):
        # Add API version to request state
        request.state.api_version = "v2"
        request.state.start_time = time.time()
        
        response = await call_next(request)
        
        # Add API version to response headers
        response.headers["X-API-Version"] = "2.0.0"
        response.headers["X-Response-Time"] = str(time.time() - request.state.start_time)
        
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Enhanced application lifespan manager."""
    # Startup
    logger.info("Starting FS Reconciliation Agents API v2...")
    
    # Initialize cache service
    cache_config = CacheConfig(
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
        default_ttl=int(os.getenv("CACHE_DEFAULT_TTL", "300")),
        api_response_ttl=int(os.getenv("CACHE_API_TTL", "300")),
        query_cache_ttl=int(os.getenv("CACHE_QUERY_TTL", "600")),
        session_ttl=int(os.getenv("CACHE_SESSION_TTL", "1800")),
        file_cache_ttl=int(os.getenv("CACHE_FILE_TTL", "3600")),
        analytics_ttl=int(os.getenv("CACHE_ANALYTICS_TTL", "7200"))
    )
    await initialize_cache_service(cache_config)
    
    logger.info("API v2 startup complete")
    yield
    
    # Shutdown
    logger.info("Shutting down FS Reconciliation Agents API v2...")


# Create enhanced FastAPI application
app = FastAPI(
    title="FS Reconciliation Agents API v2",
    description="""
    Enhanced API for automated bank reconciliation using LangGraph framework.
    
    ## Features
    - **AI-Powered Reconciliation**: Advanced exception detection and classification
    - **Real-time Processing**: Fast transaction matching and reconciliation
    - **Comprehensive Audit Trail**: Full traceability of all activities
    - **Advanced Exception Management**: Intelligent break detection and resolution
    
    ## Authentication
    Most endpoints require authentication. Use the `/auth/token` endpoint to obtain a JWT token.
    
    ## Enhanced Features
    - Better error handling and validation
    - Comprehensive logging and monitoring
    - Caching support for improved performance
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    contact={
        "name": "FS Reconciliation Team",
        "email": "support@fs-reconciliation.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# Add middleware
app.add_middleware(APIVersionMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=os.getenv("ALLOWED_HOSTS", "*").split(",")
)


# Enhanced exception handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Enhanced HTTP exception handler."""
    error_response = {
        "error": {
            "type": "http_error",
            "code": exc.status_code,
            "message": exc.detail,
            "path": request.url.path,
            "method": request.method,
            "timestamp": time.time(),
            "request_id": getattr(request.state, "request_id", None)
        }
    }
    
    # Add additional context for specific error types
    if exc.status_code == 404:
        error_response["error"]["suggestions"] = [
            "Check the API documentation at /docs",
            "Verify the endpoint URL and HTTP method",
            "Ensure you're using the correct API version"
        ]
    elif exc.status_code == 401:
        error_response["error"]["suggestions"] = [
            "Obtain a valid JWT token from /auth/token",
            "Include the token in the Authorization header",
            "Check if your token has expired"
        ]
    elif exc.status_code == 403:
        error_response["error"]["suggestions"] = [
            "Check your user permissions",
            "Contact your administrator for access",
            "Verify your role has the required privileges"
        ]
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Enhanced validation exception handler."""
    error_response = {
        "error": {
            "type": "validation_error",
            "code": 422,
            "message": "Request validation failed",
            "details": [
                {
                    "field": error["loc"][-1] if error["loc"] else "unknown",
                    "message": error["msg"],
                    "type": error["type"],
                    "value": error.get("input")
                }
                for error in exc.errors()
            ],
            "path": request.url.path,
            "method": request.method,
            "timestamp": time.time(),
            "request_id": getattr(request.state, "request_id", None)
        }
    }
    
    return JSONResponse(
        status_code=422,
        content=error_response
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Enhanced general exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    error_response = {
        "error": {
            "type": "internal_error",
            "code": 500,
            "message": "An unexpected error occurred",
            "path": request.url.path,
            "method": request.method,
            "timestamp": time.time(),
            "request_id": getattr(request.state, "request_id", None)
        }
    }
    
    # Add error ID for tracking in development
    if os.getenv("ENVIRONMENT") == "development":
        import uuid
        error_response["error"]["error_id"] = str(uuid.uuid4())
        error_response["error"]["details"] = str(exc)
    
    return JSONResponse(
        status_code=500,
        content=error_response
    )


# Enhanced health check endpoint
@app.get("/health", tags=["health"])
async def health_check(request: Request):
    """Enhanced health check endpoint with detailed status."""
    try:
        # Check cache service
        from src.core.services.caching.redis_cache import get_cache_service
        cache_service = get_cache_service()
        cache_healthy = await cache_service.exists("health_check")
        
        # Check database connection
        from src.core.services.data_services.database import get_db_session
        db_healthy = False
        try:
            async with get_db_session() as session:
                await session.execute("SELECT 1")
                db_healthy = True
        except Exception:
            pass
        
        health_status = "healthy" if cache_healthy and db_healthy else "degraded"
        
        return {
            "status": health_status,
            "service": "FS Reconciliation Agents API v2",
            "version": "2.0.0",
            "timestamp": time.time(),
            "components": {
                "cache": "healthy" if cache_healthy else "unhealthy",
                "database": "healthy" if db_healthy else "unhealthy",
                "api": "healthy"
            },
            "uptime": time.time() - getattr(app.state, "start_time", time.time())
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "FS Reconciliation Agents API v2",
                "version": "2.0.0",
                "timestamp": time.time(),
                "error": str(e)
            }
        )


# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    
    # Add global security requirement
    openapi_schema["security"] = [{"BearerAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Enhanced root endpoint
@app.get("/", tags=["root"])
async def root(request: Request):
    """Enhanced root endpoint with API information."""
    return {
        "message": "FS Reconciliation Agents API v2",
        "version": "2.0.0",
        "status": "operational",
        "timestamp": time.time(),
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/health",
            "openapi": "/openapi.json"
        },
        "features": [
            "AI-powered reconciliation",
            "Real-time processing",
            "Comprehensive audit trail",
            "Advanced exception management",
            "Enhanced error handling",
            "Caching support"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.v2.main_simple:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
