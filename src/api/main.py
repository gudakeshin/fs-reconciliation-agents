"""
Main FastAPI application for the FS Reconciliation Agents API.

This module sets up the FastAPI application with all necessary middleware,
routers, and configuration for the reconciliation system.
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.utils.security_utils.authentication import get_current_user
from src.api.routers import exceptions, data_upload, reports, health, logs, auth, settings, metrics, actions, database
from src.api.routers.workflows import router as workflows_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting FS Reconciliation Agents API...")
    
    # Initialize database connections
    # Initialize AI models
    # Initialize external service connections
    
    yield
    
    # Shutdown
    logger.info("Shutting down FS Reconciliation Agents API...")


# Create FastAPI application
app = FastAPI(
    title="FS Reconciliation Agents API",
    description="Agentic AI application for automated bank reconciliation using LangGraph framework",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add middleware
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


# Exception handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "path": request.url.path
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation exceptions."""
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error",
            "details": exc.errors(),
            "path": request.url.path
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "path": request.url.path
        }
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "FS Reconciliation Agents API",
        "version": "1.0.0"
    }


# Include routers
app.include_router(
    health.router,
    prefix="/health",
    tags=["health"]
)

app.include_router(
    data_upload.router,
    prefix="/api/v1/upload",
    tags=["data-upload"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    exceptions.router,
    prefix="/api/v1/exceptions",
    tags=["exceptions"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    reports.router,
    prefix="/api/v1",
    tags=["reports"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    logs.router,
    prefix="/api/v1/logs",
    tags=["logs"]
)

app.include_router(
    settings.router,
    prefix="/api/v1",
    tags=["settings"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    auth.router,
    prefix="/api/v1",
    tags=["auth"]
)

app.include_router(
    metrics.router,
    prefix="/api/v1/metrics",
    tags=["metrics"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    actions.router,
    prefix="/api/v1/actions",
    tags=["actions"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    workflows_router,
    prefix="/api/v1",
    tags=["workflows"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    database.router,
    prefix="/api/v1",
    tags=["database"],
    dependencies=[Depends(get_current_user)]
)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "FS Reconciliation Agents API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    ) 