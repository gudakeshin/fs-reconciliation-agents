"""
Audit Logger Utility for FS Reconciliation Agents.

This module provides utilities for logging agent activities to the audit trail
for transparency and monitoring purposes.
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.models.audit_models.audit_trail import (
    AuditTrail, AuditActionType, AuditSeverity
)
from src.core.services.data_services.database import get_db_session

logger = logging.getLogger(__name__)


class AuditLogger:
    """Audit logger for agent activities."""
    
    def __init__(self):
        self.session_id = None
        self.user_id = "system"
        self.user_name = "System"
        self.user_role = "admin"
    
    def set_session(self, session_id: str):
        """Set the session ID for tracking."""
        self.session_id = session_id
    
    def set_user(self, user_id: str, user_name: str, user_role: str = "user"):
        """Set user information."""
        self.user_id = user_id
        self.user_name = user_name
        self.user_role = user_role
    
    async def log_agent_activity(
        self,
        action_type: AuditActionType,
        action_description: str,
        action_data: Optional[Dict[str, Any]] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        entity_external_id: Optional[str] = None,
        processing_time_ms: Optional[int] = None,
        ai_model_used: Optional[str] = None,
        ai_confidence_score: Optional[float] = None,
        ai_reasoning: Optional[str] = None,
        severity: AuditSeverity = AuditSeverity.INFO,
        is_successful: bool = True,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None
    ):
        """Log agent activity to audit trail."""
        try:
            async with get_db_session() as db:
                audit_entry = AuditTrail(
                    action_type=action_type,
                    action_description=action_description,
                    action_data=action_data,
                    user_id=self.user_id,
                    user_name=self.user_name,
                    user_role=self.user_role,
                    session_id=self.session_id,
                    ip_address="127.0.0.1",  # System activity
                    user_agent="FS-Reconciliation-Agent",
                    entity_type=entity_type,
                    entity_id=entity_id,
                    entity_external_id=entity_external_id,
                    processing_time_ms=processing_time_ms,
                    memory_usage_mb=None,  # Could be added later
                    ai_model_used=ai_model_used,
                    ai_confidence_score=ai_confidence_score,
                    ai_reasoning=ai_reasoning,
                    regulatory_requirement=None,
                    compliance_category=None,
                    data_classification=None,
                    severity=severity,
                    is_successful=is_successful,
                    error_message=error_message,
                    error_code=error_code,
                    created_at=datetime.utcnow()
                )
                
                db.add(audit_entry)
                await db.commit()
                
                logger.info(f"Audit logged: {action_type} - {action_description}")
                
        except Exception as e:
            logger.error(f"Failed to log audit entry: {e}")
    
    async def log_agent_start(self, agent_name: str, session_id: str, input_data: Optional[Dict[str, Any]] = None):
        """Log agent start activity."""
        self.set_session(session_id)
        
        action_type_map = {
            "matching": AuditActionType.MATCH_ATTEMPTED,
            "exception_identification": AuditActionType.EXCEPTION_DETECTED,
            "resolution": AuditActionType.RESOLUTION_ATTEMPTED,
            "reporting": AuditActionType.AI_ANALYSIS_REQUESTED,
            "human_in_loop": AuditActionType.EXCEPTION_ASSIGNED
        }
        
        action_type = action_type_map.get(agent_name, AuditActionType.AI_ANALYSIS_REQUESTED)
        
        await self.log_agent_activity(
            action_type=action_type,
            action_description=f"{agent_name.replace('_', ' ').title()} agent started",
            action_data=input_data,
            entity_type="agent_workflow",
            entity_id=session_id,
            severity=AuditSeverity.INFO,
            is_successful=True
        )
    
    async def log_agent_completion(
        self, 
        agent_name: str, 
        session_id: str, 
        result_data: Optional[Dict[str, Any]] = None,
        processing_time_ms: Optional[int] = None,
        is_successful: bool = True,
        error_message: Optional[str] = None
    ):
        """Log agent completion activity."""
        self.set_session(session_id)
        
        action_type_map = {
            "matching": AuditActionType.MATCH_CREATED,
            "exception_identification": AuditActionType.EXCEPTION_CLASSIFIED,
            "resolution": AuditActionType.RESOLUTION_APPROVED,
            "reporting": AuditActionType.AI_ANALYSIS_COMPLETED,
            "human_in_loop": AuditActionType.EXCEPTION_RESOLVED
        }
        
        action_type = action_type_map.get(agent_name, AuditActionType.AI_ANALYSIS_COMPLETED)
        
        await self.log_agent_activity(
            action_type=action_type,
            action_description=f"{agent_name.replace('_', ' ').title()} agent completed",
            action_data=result_data,
            entity_type="agent_workflow",
            entity_id=session_id,
            processing_time_ms=processing_time_ms,
            severity=AuditSeverity.INFO if is_successful else AuditSeverity.ERROR,
            is_successful=is_successful,
            error_message=error_message
        )
    
    async def log_ai_analysis(
        self,
        session_id: str,
        analysis_type: str,
        reasoning: str,
        suggestions: List[str],
        confidence_score: float,
        ai_model: str
    ):
        """Log AI analysis activity."""
        self.set_session(session_id)
        
        await self.log_agent_activity(
            action_type=AuditActionType.AI_SUGGESTION_GENERATED,
            action_description=f"AI analysis completed for {analysis_type}",
            action_data={
                "analysis_type": analysis_type,
                "suggestions": suggestions,
                "confidence_score": confidence_score
            },
            entity_type="ai_analysis",
            entity_id=session_id,
            ai_model_used=ai_model,
            ai_confidence_score=confidence_score,
            ai_reasoning=reasoning,
            severity=AuditSeverity.INFO,
            is_successful=True
        )
    
    async def log_action_execution(
        self,
        session_id: str,
        action_type: str,
        action_description: str,
        action_data: Optional[Dict[str, Any]] = None,
        is_successful: bool = True,
        error_message: Optional[str] = None
    ):
        """Log action execution (Execute/Review buttons)."""
        self.set_session(session_id)
        
        await self.log_agent_activity(
            action_type=AuditActionType.AI_SUGGESTION_ACCEPTED if is_successful else AuditActionType.AI_SUGGESTION_REJECTED,
            action_description=f"Action executed: {action_description}",
            action_data=action_data,
            entity_type="user_action",
            entity_id=session_id,
            severity=AuditSeverity.INFO if is_successful else AuditSeverity.WARNING,
            is_successful=is_successful,
            error_message=error_message
        )


# Global audit logger instance
audit_logger = AuditLogger()


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance."""
    return audit_logger
