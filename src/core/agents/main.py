"""
LangGraph Agent Service Main Entry Point.

This module provides the main entry point for the LangGraph agent service,
which orchestrates the various AI agents for financial reconciliation.
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting FS Reconciliation LangGraph Agent Service...")
    
    # Initialize agent connections
    # Initialize AI models
    # Initialize external service connections
    
    yield
    
    # Shutdown
    logger.info("Shutting down FS Reconciliation LangGraph Agent Service...")


# Create FastAPI application
app = FastAPI(
    title="FS Reconciliation LangGraph Agent Service",
    description="LangGraph-based AI agent service for financial reconciliation",
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


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "FS Reconciliation LangGraph Agent Service",
        "version": "1.0.0"
    }


# Agent status endpoint
@app.get("/agents/status")
async def get_agents_status():
    """Get status of all agents."""
    return {
        "agents": {
            "data_ingestion": "available",
            "normalization": "available", 
            "matching": "available",
            "exception_identification": "available",
            "resolution": "available",
            "reporting": "available",
            "human_in_loop": "available"
        },
        "status": "operational"
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "message": "FS Reconciliation LangGraph Agent Service",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "agents": "/agents/status"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.core.agents.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    ) 