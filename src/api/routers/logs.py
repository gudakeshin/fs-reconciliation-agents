"""
Logs and Agent Flow Router for FS Reconciliation Agents API.

This module provides API endpoints for retrieving system logs, audit trails,
and agent flow information for monitoring and debugging purposes.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from src.core.models.audit_models.audit_trail import (
    AuditTrail, SystemLog, AuditActionType, AuditSeverity
)
from src.core.services.data_services.database import get_db_session_dependency

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/system")
async def get_system_logs(
    level: Optional[str] = Query(None, description="Log level filter"),
    component: Optional[str] = Query(None, description="Component filter"),
    start_time: Optional[datetime] = Query(None, description="Start time filter"),
    end_time: Optional[datetime] = Query(None, description="End time filter"),
    limit: int = Query(100, ge=1, le=1000, description="Number of logs to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db_session_dependency)
) -> Dict[str, Any]:
    """Get system logs with filtering and pagination."""
    try:
        # Build query
        query = select(SystemLog).order_by(desc(SystemLog.created_at))
        
        # Apply filters
        filters = []
        if level:
            filters.append(SystemLog.log_level == level.upper())
        if component:
            filters.append(SystemLog.component == component)
        if start_time:
            filters.append(SystemLog.created_at >= start_time)
        if end_time:
            filters.append(SystemLog.created_at <= end_time)
        
        if filters:
            query = query.where(and_(*filters))
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        logs = result.scalars().all()
        
        # Convert to dict format
        log_entries = []
        for log in logs:
            log_entries.append({
                "id": str(log.id),
                "level": log.log_level,
                "message": log.log_message,
                "component": log.component,
                "sub_component": log.sub_component,
                "function_name": log.function_name,
                "line_number": log.line_number,
                "exception_type": log.exception_type,
                "exception_message": log.exception_message,
                "stack_trace": log.stack_trace,
                "execution_time_ms": log.execution_time_ms,
                "memory_usage_mb": float(log.memory_usage_mb) if log.memory_usage_mb else None,
                "cpu_usage_percent": float(log.cpu_usage_percent) if log.cpu_usage_percent else None,
                "created_at": log.created_at.isoformat(),
                "log_data": log.log_data
            })
        
        return {
            "success": True,
            "logs": log_entries,
            "total_count": len(log_entries),
            "filters": {
                "level": level,
                "component": component,
                "start_time": start_time.isoformat() if start_time else None,
                "end_time": end_time.isoformat() if end_time else None
            },
            "pagination": {
                "limit": limit,
                "offset": offset
            }
        }
        
    except Exception as e:
        logger.error(f"Error retrieving system logs: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/audit")
async def get_audit_trail(
    action_type: Optional[str] = Query(None, description="Action type filter"),
    severity: Optional[str] = Query(None, description="Severity filter"),
    user_id: Optional[str] = Query(None, description="User ID filter"),
    entity_type: Optional[str] = Query(None, description="Entity type filter"),
    start_time: Optional[datetime] = Query(None, description="Start time filter"),
    end_time: Optional[datetime] = Query(None, description="End time filter"),
    limit: int = Query(100, ge=1, le=1000, description="Number of entries to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db_session_dependency)
) -> Dict[str, Any]:
    """Get audit trail entries with filtering and pagination."""
    try:
        # Build query
        query = select(AuditTrail).order_by(desc(AuditTrail.created_at))
        
        # Apply filters
        filters = []
        if action_type:
            filters.append(AuditTrail.action_type == action_type)
        if severity:
            filters.append(AuditTrail.severity == severity)
        if user_id:
            filters.append(AuditTrail.user_id == user_id)
        if entity_type:
            filters.append(AuditTrail.entity_type == entity_type)
        if start_time:
            filters.append(AuditTrail.created_at >= start_time)
        if end_time:
            filters.append(AuditTrail.created_at <= end_time)
        
        if filters:
            query = query.where(and_(*filters))
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        audit_entries = result.scalars().all()
        
        # Convert to dict format
        entries = []
        for entry in audit_entries:
            entries.append({
                "id": str(entry.id),
                "action_type": entry.action_type,
                "action_description": entry.action_description,
                "action_data": entry.action_data,
                "user_id": entry.user_id,
                "user_name": entry.user_name,
                "user_email": entry.user_email,
                "user_role": entry.user_role,
                "session_id": entry.session_id,
                "ip_address": entry.ip_address,
                "user_agent": entry.user_agent,
                "entity_type": entry.entity_type,
                "entity_id": str(entry.entity_id) if entry.entity_id else None,
                "entity_external_id": entry.entity_external_id,
                "processing_time_ms": entry.processing_time_ms,
                "memory_usage_mb": float(entry.memory_usage_mb) if entry.memory_usage_mb else None,
                "ai_model_used": entry.ai_model_used,
                "ai_confidence_score": float(entry.ai_confidence_score) if entry.ai_confidence_score else None,
                "ai_reasoning": entry.ai_reasoning,
                "regulatory_requirement": entry.regulatory_requirement,
                "compliance_category": entry.compliance_category,
                "data_classification": entry.data_classification,
                "severity": entry.severity,
                "is_successful": entry.is_successful,
                "error_message": entry.error_message,
                "error_code": entry.error_code,
                "created_at": entry.created_at.isoformat()
            })
        
        return {
            "success": True,
            "audit_entries": entries,
            "total_count": len(entries),
            "filters": {
                "action_type": action_type,
                "severity": severity,
                "user_id": user_id,
                "entity_type": entity_type,
                "start_time": start_time.isoformat() if start_time else None,
                "end_time": end_time.isoformat() if end_time else None
            },
            "pagination": {
                "limit": limit,
                "offset": offset
            }
        }
        
    except Exception as e:
        logger.error(f"Error retrieving audit trail: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/agents/flow")
async def get_agent_flow(
    session_id: Optional[str] = Query(None, description="Session ID filter"),
    start_time: Optional[datetime] = Query(None, description="Start time filter"),
    end_time: Optional[datetime] = Query(None, description="End time filter"),
    limit: int = Query(50, ge=1, le=500, description="Number of flows to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db_session_dependency)
) -> Dict[str, Any]:
    """Get agent flow information showing the control flow across agents."""
    try:
        # Build query for agent-related audit entries
        query = select(AuditTrail).where(
            AuditTrail.action_type.in_([
                AuditActionType.DATA_INGESTED,
                AuditActionType.DATA_NORMALIZED,
                AuditActionType.DATA_VALIDATED,
                AuditActionType.MATCH_ATTEMPTED,
                AuditActionType.MATCH_CREATED,
                AuditActionType.MATCH_REJECTED,
                AuditActionType.MATCH_APPROVED,
                AuditActionType.EXCEPTION_DETECTED,
                AuditActionType.EXCEPTION_CLASSIFIED,
                AuditActionType.EXCEPTION_ASSIGNED,
                AuditActionType.EXCEPTION_REVIEWED,
                AuditActionType.EXCEPTION_RESOLVED,
                AuditActionType.RESOLUTION_ATTEMPTED,
                AuditActionType.RESOLUTION_APPROVED,
                AuditActionType.RESOLUTION_REJECTED,
                AuditActionType.JOURNAL_ENTRY_CREATED,
                AuditActionType.AI_ANALYSIS_REQUESTED,
                AuditActionType.AI_ANALYSIS_COMPLETED,
                AuditActionType.AI_SUGGESTION_GENERATED,
                AuditActionType.AI_SUGGESTION_ACCEPTED,
                AuditActionType.AI_SUGGESTION_REJECTED
            ])
        ).order_by(desc(AuditTrail.created_at))
        
        # Apply filters
        filters = []
        if session_id:
            filters.append(AuditTrail.session_id == session_id)
        if start_time:
            filters.append(AuditTrail.created_at >= start_time)
        if end_time:
            filters.append(AuditTrail.created_at <= end_time)
        
        if filters:
            query = query.where(and_(*filters))
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        agent_entries = result.scalars().all()
        
        # Group by session to create flow sequences
        session_flows = {}
        for entry in agent_entries:
            session_key = entry.session_id or "default"
            if session_key not in session_flows:
                session_flows[session_key] = []
            
            session_flows[session_key].append({
                "id": str(entry.id),
                "action_type": entry.action_type,
                "action_description": entry.action_description,
                "action_data": entry.action_data,
                "entity_type": entry.entity_type,
                "entity_id": str(entry.entity_id) if entry.entity_id else None,
                "processing_time_ms": entry.processing_time_ms,
                "ai_model_used": entry.ai_model_used,
                "ai_confidence_score": float(entry.ai_confidence_score) if entry.ai_confidence_score else None,
                "ai_reasoning": entry.ai_reasoning,
                "severity": entry.severity,
                "is_successful": entry.is_successful,
                "error_message": entry.error_message,
                "created_at": entry.created_at.isoformat()
            })
        
        # Sort flows by creation time
        flows = []
        for session_id, flow_entries in session_flows.items():
            # Sort entries within each flow by creation time
            flow_entries.sort(key=lambda x: x["created_at"])
            
            flows.append({
                "session_id": session_id,
                "flow_entries": flow_entries,
                "total_steps": len(flow_entries),
                "successful_steps": len([e for e in flow_entries if e["is_successful"]]),
                "failed_steps": len([e for e in flow_entries if not e["is_successful"]]),
                "start_time": flow_entries[0]["created_at"] if flow_entries else None,
                "end_time": flow_entries[-1]["created_at"] if flow_entries else None,
                "total_processing_time_ms": sum(e["processing_time_ms"] or 0 for e in flow_entries)
            })
        
        return {
            "success": True,
            "agent_flows": flows,
            "total_flows": len(flows),
            "filters": {
                "session_id": session_id,
                "start_time": start_time.isoformat() if start_time else None,
                "end_time": end_time.isoformat() if end_time else None
            },
            "pagination": {
                "limit": limit,
                "offset": offset
            }
        }
        
    except Exception as e:
        logger.error(f"Error retrieving agent flow: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/agents/status")
async def get_agents_status(
    db: AsyncSession = Depends(get_db_session_dependency)
) -> Dict[str, Any]:
    """Get current status of all agents."""
    try:
        # Get recent activity for each agent type
        agent_status = {}
        
        # Define agent types and their corresponding audit action types
        agent_mapping = {
            "data_ingestion": [AuditActionType.DATA_INGESTED],
            "normalization": [AuditActionType.DATA_NORMALIZED],
            "matching": [AuditActionType.MATCH_ATTEMPTED, AuditActionType.MATCH_CREATED, AuditActionType.MATCH_REJECTED, AuditActionType.MATCH_APPROVED],
            "exception_identification": [AuditActionType.EXCEPTION_DETECTED, AuditActionType.EXCEPTION_CLASSIFIED],
            "resolution": [AuditActionType.RESOLUTION_ATTEMPTED, AuditActionType.RESOLUTION_APPROVED, AuditActionType.RESOLUTION_REJECTED],
            "reporting": [AuditActionType.AI_ANALYSIS_REQUESTED, AuditActionType.AI_ANALYSIS_COMPLETED],
            "human_in_loop": [AuditActionType.EXCEPTION_ASSIGNED, AuditActionType.EXCEPTION_REVIEWED, AuditActionType.EXCEPTION_RESOLVED]
        }
        
        for agent_name, action_types in agent_mapping.items():
            # Get recent activity for this agent
            recent_query = select(AuditTrail).where(
                AuditTrail.action_type.in_(action_types)
            ).order_by(desc(AuditTrail.created_at)).limit(1)
            
            result = await db.execute(recent_query)
            recent_entry = result.scalar_one_or_none()
            
            if recent_entry:
                # Check if agent was active in the last 5 minutes
                five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
                is_active = recent_entry.created_at > five_minutes_ago
                
                agent_status[agent_name] = {
                    "status": "active" if is_active else "idle",
                    "last_activity": recent_entry.created_at.isoformat(),
                    "last_action": recent_entry.action_type,
                    "success_rate": "high" if recent_entry.is_successful else "low"
                }
            else:
                agent_status[agent_name] = {
                    "status": "inactive",
                    "last_activity": None,
                    "last_action": None,
                    "success_rate": "unknown"
                }
        
        return {
            "success": True,
            "agents": agent_status,
            "overall_status": "operational" if any(agent["status"] == "active" for agent in agent_status.values()) else "idle"
        }
        
    except Exception as e:
        logger.error(f"Error retrieving agent status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/statistics")
async def get_log_statistics(
    time_range: str = Query("24h", description="Time range for statistics (1h, 24h, 7d, 30d)"),
    db: AsyncSession = Depends(get_db_session_dependency)
) -> Dict[str, Any]:
    """Get log statistics and metrics."""
    try:
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
        
        # Get system log statistics
        system_logs_query = select(SystemLog).where(SystemLog.created_at >= start_time)
        system_result = await db.execute(system_logs_query)
        system_logs = system_result.scalars().all()
        
        # Get audit trail statistics
        audit_query = select(AuditTrail).where(AuditTrail.created_at >= start_time)
        audit_result = await db.execute(audit_query)
        audit_entries = audit_result.scalars().all()
        
        # Calculate statistics
        log_levels = {}
        components = {}
        successful_actions = 0
        failed_actions = 0
        
        for log in system_logs:
            log_levels[log.log_level] = log_levels.get(log.log_level, 0) + 1
            if log.component:
                components[log.component] = components.get(log.component, 0) + 1
        
        for entry in audit_entries:
            if entry.is_successful:
                successful_actions += 1
            else:
                failed_actions += 1
        
        total_actions = successful_actions + failed_actions
        success_rate = (successful_actions / total_actions * 100) if total_actions > 0 else 0
        
        return {
            "success": True,
            "time_range": time_range,
            "statistics": {
                "system_logs": {
                    "total": len(system_logs),
                    "by_level": log_levels,
                    "by_component": components
                },
                "audit_trail": {
                    "total_entries": len(audit_entries),
                    "successful_actions": successful_actions,
                    "failed_actions": failed_actions,
                    "success_rate": round(success_rate, 2)
                },
                "performance": {
                    "avg_processing_time_ms": sum((e.processing_time_ms or 0) for e in audit_entries) / len(audit_entries) if audit_entries else 0,
                    "total_processing_time_ms": sum((e.processing_time_ms or 0) for e in audit_entries)
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error retrieving log statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
