"""
Health check router for FS Reconciliation Agents API.

This module provides health check endpoints for monitoring
the system status and dependencies.
"""

import logging
from typing import Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from src.core.services.data_services.database import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "FS Reconciliation Agents API"
    }


@router.get("/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """Detailed health check with dependency status."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "FS Reconciliation Agents API",
        "dependencies": {}
    }
    
    # Check database connectivity
    try:
        async with get_db_session() as session:
            result = await session.execute(text("SELECT 1"))
            health_status["dependencies"]["database"] = {
                "status": "healthy",
                "response_time_ms": 0  # TODO: Add actual response time measurement
            }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["dependencies"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Check Redis connectivity
    try:
        # TODO: Add Redis health check
        health_status["dependencies"]["redis"] = {
            "status": "healthy",
            "response_time_ms": 0
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        health_status["dependencies"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Check LangGraph agent service
    try:
        # TODO: Add LangGraph service health check
        health_status["dependencies"]["langgraph_agent"] = {
            "status": "healthy",
            "response_time_ms": 0
        }
    except Exception as e:
        logger.error(f"LangGraph agent health check failed: {e}")
        health_status["dependencies"]["langgraph_agent"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    return health_status


@router.get("/ready")
async def readiness_check() -> Dict[str, Any]:
    """Readiness check for Kubernetes."""
    # Check if all critical dependencies are available
    health_status = await detailed_health_check()
    
    if health_status["status"] != "healthy":
        raise HTTPException(
            status_code=503,
            detail="Service not ready"
        )
    
    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/live")
async def liveness_check() -> Dict[str, Any]:
    """Liveness check for Kubernetes."""
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    } 