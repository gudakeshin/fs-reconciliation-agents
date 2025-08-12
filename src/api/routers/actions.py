"""
Actions Router for FS Reconciliation Agents API.

This module provides API endpoints for executing actions on exceptions,
including AI-suggested actions and human review workflows.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel

from src.core.services.data_services.database import get_db_session_dependency
from src.core.utils.audit_logger import get_audit_logger

logger = logging.getLogger(__name__)
router = APIRouter()


class ActionRequest(BaseModel):
    """Request model for action execution."""
    action_type: str  # "execute" or "review"
    action_description: str
    exception_id: str
    action_data: Optional[Dict[str, Any]] = None


class ActionResponse(BaseModel):
    """Response model for action execution."""
    success: bool
    action_id: str
    status: str
    message: str
    execution_time_ms: Optional[int] = None
    result_data: Optional[Dict[str, Any]] = None


@router.post("/execute", response_model=ActionResponse)
async def execute_action(
    request: ActionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session_dependency)
) -> ActionResponse:
    """Execute an action on an exception."""
    try:
        action_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        audit_logger = get_audit_logger()
        
        logger.info(f"Executing action: {request.action_type} - {request.action_description}")
        
        # Log action start
        await audit_logger.log_action_execution(
            session_id=session_id,
            action_type=request.action_type,
            action_description=f"Starting: {request.action_description}",
            action_data=request.action_data,
            is_successful=True
        )
        
        # Simulate action execution based on type
        if request.action_type == "execute":
            # Simulate automatic execution
            result_data = {
                "action_type": "automatic_execution",
                "status": "completed",
                "changes_applied": [
                    "Updated transaction records",
                    "Applied price corrections",
                    "Updated reconciliation status"
                ],
                "affected_records": 1,
                "execution_time_ms": 1500
            }
            
            # Simulate processing time
            import asyncio
            await asyncio.sleep(1.5)
            
        elif request.action_type == "review":
            # Simulate human review workflow
            result_data = {
                "action_type": "human_review",
                "status": "pending_review",
                "review_steps": [
                    "Action queued for human review",
                    "Review notification sent",
                    "Awaiting approval"
                ],
                "estimated_review_time": "2-4 hours",
                "review_priority": "medium"
            }
            
            # Simulate processing time
            import asyncio
            await asyncio.sleep(0.8)
            
        else:
            raise HTTPException(status_code=400, detail="Invalid action type")
        
        # Calculate execution time
        end_time = datetime.utcnow()
        execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
        
        # Log action completion
        action_data_with_result = {
            **(request.action_data or {}),
            "result": result_data,
            "execution_time_ms": execution_time_ms
        }
        
        await audit_logger.log_action_execution(
            session_id=session_id,
            action_type=request.action_type,
            action_description=f"Completed: {request.action_description}",
            action_data=action_data_with_result,
            is_successful=True
        )
        
        return ActionResponse(
            success=True,
            action_id=action_id,
            status="completed",
            message=f"Successfully {request.action_type}d: {request.action_description}",
            execution_time_ms=execution_time_ms,
            result_data=result_data
        )
        
    except Exception as e:
        logger.error(f"Action execution failed: {e}")
        
        # Log action failure
        await audit_logger.log_action_execution(
            session_id=session_id if 'session_id' in locals() else str(uuid.uuid4()),
            action_type=request.action_type,
            action_description=f"Failed: {request.action_description}",
            action_data=request.action_data,
            is_successful=False,
            error_message=str(e)
        )
        
        raise HTTPException(status_code=500, detail=f"Action execution failed: {str(e)}")


@router.get("/history")
async def get_action_history(
    exception_id: Optional[str] = None,
    action_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db_session_dependency)
) -> Dict[str, Any]:
    """Get action execution history."""
    try:
        from src.core.models.audit_models.audit_trail import AuditTrail, AuditActionType
        from sqlalchemy import select, desc, and_
        
        # Build query for action-related audit entries
        query = select(AuditTrail).where(
            AuditTrail.action_type.in_([
                AuditActionType.AI_SUGGESTION_ACCEPTED,
                AuditActionType.AI_SUGGESTION_REJECTED
            ])
        ).order_by(desc(AuditTrail.created_at))
        
        # Apply filters
        filters = []
        if exception_id:
            filters.append(AuditTrail.entity_id == exception_id)
        if action_type:
            filters.append(AuditTrail.action_type == action_type)
        
        if filters:
            query = query.where(and_(*filters))
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        action_entries = result.scalars().all()
        
        # Convert to response format
        actions = []
        for entry in action_entries:
            actions.append({
                "id": str(entry.id),
                "action_type": entry.action_type,
                "action_description": entry.action_description,
                "action_data": entry.action_data,
                "entity_id": str(entry.entity_id) if entry.entity_id else None,
                "processing_time_ms": entry.processing_time_ms,
                "ai_model_used": entry.ai_model_used,
                "ai_confidence_score": float(entry.ai_confidence_score) if entry.ai_confidence_score else None,
                "severity": entry.severity,
                "is_successful": entry.is_successful,
                "error_message": entry.error_message,
                "created_at": entry.created_at.isoformat()
            })
        
        return {
            "success": True,
            "actions": actions,
            "total_count": len(actions),
            "pagination": {
                "limit": limit,
                "offset": offset
            }
        }
        
    except Exception as e:
        logger.error(f"Error retrieving action history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/statistics")
async def get_action_statistics(
    time_range: str = "24h",
    db: AsyncSession = Depends(get_db_session_dependency)
) -> Dict[str, Any]:
    """Get action execution statistics."""
    try:
        from src.core.models.audit_models.audit_trail import AuditTrail, AuditActionType
        from sqlalchemy import select, func
        from datetime import timedelta
        
        # Calculate time range
        now = datetime.utcnow()
        if time_range == "1h":
            start_time = now - timedelta(hours=1)
        elif time_range == "24h":
            start_time = now - timedelta(days=1)
        elif time_range == "7d":
            start_time = now - timedelta(days=7)
        elif time_range == "30d":
            start_time = now - timedelta(days=30)
        else:
            start_time = now - timedelta(days=1)
        
        # Get action statistics
        query = select(
            AuditTrail.action_type,
            func.count(AuditTrail.id).label("count"),
            func.avg(AuditTrail.processing_time_ms).label("avg_processing_time"),
            func.sum(AuditTrail.processing_time_ms).label("total_processing_time")
        ).where(
            AuditTrail.action_type.in_([
                AuditActionType.AI_SUGGESTION_ACCEPTED,
                AuditActionType.AI_SUGGESTION_REJECTED
            ]),
            AuditTrail.created_at >= start_time
        ).group_by(AuditTrail.action_type)
        
        result = await db.execute(query)
        stats = result.all()
        
        # Calculate success rate
        success_query = select(
            func.count(AuditTrail.id).label("total"),
            func.sum(func.case((AuditTrail.is_successful == True, 1), else_=0)).label("successful")
        ).where(
            AuditTrail.action_type.in_([
                AuditActionType.AI_SUGGESTION_ACCEPTED,
                AuditActionType.AI_SUGGESTION_REJECTED
            ]),
            AuditTrail.created_at >= start_time
        )
        
        success_result = await db.execute(success_query)
        success_stats = success_result.first()
        
        total_actions = success_stats.total or 0
        successful_actions = success_stats.successful or 0
        success_rate = (successful_actions / total_actions * 100) if total_actions > 0 else 0
        
        return {
            "success": True,
            "time_range": time_range,
            "statistics": {
                "total_actions": total_actions,
                "successful_actions": successful_actions,
                "failed_actions": total_actions - successful_actions,
                "success_rate": round(success_rate, 2),
                "by_action_type": [
                    {
                        "action_type": stat.action_type,
                        "count": stat.count,
                        "avg_processing_time_ms": round(stat.avg_processing_time or 0, 2),
                        "total_processing_time_ms": stat.total_processing_time or 0
                    }
                    for stat in stats
                ]
            }
        }
        
    except Exception as e:
        logger.error(f"Error retrieving action statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
