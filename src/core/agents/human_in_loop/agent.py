"""
Human-in-Loop Agent for FS Reconciliation Agents.

This module provides human-in-loop functionality for reviewing and approving
reconciliation results, exceptions, and resolutions.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from src.core.utils.audit_logger import get_audit_logger

logger = logging.getLogger(__name__)


class HumanReviewState(BaseModel):
    """State for human-in-loop review workflow."""
    
    # Input data
    exceptions: List[Dict[str, Any]] = Field(default_factory=list)
    resolutions: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Processing state
    review_items: List[Dict[str, Any]] = Field(default_factory=list)
    validation_errors: List[str] = Field(default_factory=list)
    processing_status: str = "pending"
    
    # Output data
    review_results: List[Dict[str, Any]] = Field(default_factory=list)
    summary: Dict[str, Any] = Field(default_factory=dict)
    
    # Metadata
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    processing_time_ms: Optional[int] = None


class HumanInLoopAgent:
    """Human-in-loop agent for reviewing reconciliation results."""
    
    def __init__(self):
        """Initialize the human-in-loop agent."""
        self.name = "Human-in-Loop Agent"
        logger.info(f"Initialized {self.name}")
    
    async def human_in_loop_review(
        self, 
        exceptions: List[Dict[str, Any]],
        resolutions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Perform human-in-loop review of reconciliation results."""
        session_id = str(uuid.uuid4())
        audit_logger = get_audit_logger()
        start_time = datetime.utcnow()
        
        logger.info("Starting human-in-loop review...")
        
        # Log agent start
        await audit_logger.log_agent_start(
            agent_name="human_in_loop",
            session_id=session_id,
            input_data={
                "exceptions_count": len(exceptions),
                "resolutions_count": len(resolutions)
            }
        )
        
        # Initialize state
        state = HumanReviewState(
            exceptions=exceptions,
            resolutions=resolutions
        )
        
        try:
            # Prepare review items
            review_items = await self._prepare_review_items(state)
            
            # Generate review recommendations
            review_recommendations = await self._generate_review_recommendations(state)
            
            # Create approval workflow
            approval_workflow = await self._create_approval_workflow(state)
            
            # Compile review results
            end_time = datetime.utcnow()
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            review_results = {
                "review_items": review_items,
                "recommendations": review_recommendations,
                "approval_workflow": approval_workflow,
                "requires_human_approval": len(review_items) > 0,
                "metadata": {
                    "generated_at": end_time.isoformat(),
                    "agent": self.name,
                    "total_items_for_review": len(review_items)
                }
            }
            
            result = {
                "success": True,
                "review_results": review_results,
                "summary": {
                    "total_review_items": len(review_items),
                    "requires_approval": len(review_items) > 0,
                    "processing_time_ms": processing_time_ms,
                    "status": "completed"
                }
            }
            
            # Log agent completion
            await audit_logger.log_agent_completion(
                agent_name="human_in_loop",
                session_id=session_id,
                result_data={"total_review_items": len(review_items), "status": "completed"},
                processing_time_ms=processing_time_ms,
                is_successful=True
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Human-in-loop review failed: {e}")
            
            # Calculate processing time
            end_time = datetime.utcnow()
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            result = {
                "success": False,
                "error": str(e),
                "summary": {
                    "total_review_items": 0,
                    "requires_approval": False,
                    "processing_time_ms": processing_time_ms,
                    "status": "failed"
                }
            }
            
            # Log agent failure
            await audit_logger.log_agent_completion(
                agent_name="human_in_loop",
                session_id=session_id,
                result_data={"total_review_items": 0, "status": "failed"},
                processing_time_ms=processing_time_ms,
                is_successful=False,
                error_message=str(e)
            )
            
            return result
    
    async def _prepare_review_items(self, state: HumanReviewState) -> List[Dict[str, Any]]:
        """Prepare items that require human review."""
        logger.info("Preparing review items...")
        
        review_items = []
        
        # Add high severity exceptions for review
        for exception in state.exceptions:
            severity = exception.get("severity", "medium")
            if severity in ["high", "critical"]:
                review_items.append({
                    "type": "exception_review",
                    "id": exception.get("id"),
                    "break_type": exception.get("break_type"),
                    "severity": severity,
                    "description": exception.get("description"),
                    "ai_reasoning": exception.get("ai_reasoning"),
                    "ai_suggested_actions": exception.get("ai_suggested_actions"),
                    "priority": "high" if severity == "critical" else "medium",
                    "action_required": "manual_review",
                    "estimated_review_time": "5-10 minutes"
                })
        
        # Add complex resolutions for approval
        for resolution in state.resolutions:
            confidence = resolution.get("confidence_score", 0)
            if confidence < 0.7:  # Low confidence resolutions need review
                review_items.append({
                    "type": "resolution_approval",
                    "id": resolution.get("id"),
                    "action": resolution.get("action"),
                    "confidence_score": confidence,
                    "reasoning": resolution.get("reasoning"),
                    "priority": "medium",
                    "action_required": "approval",
                    "estimated_review_time": "3-5 minutes"
                })
        
        return review_items
    
    async def _generate_review_recommendations(self, state: HumanReviewState) -> Dict[str, Any]:
        """Generate recommendations for human review process."""
        logger.info("Generating review recommendations...")
        
        recommendations = []
        
        # Analyze exceptions for review patterns
        critical_exceptions = [e for e in state.exceptions if e.get("severity") == "critical"]
        high_exceptions = [e for e in state.exceptions if e.get("severity") == "high"]
        
        if critical_exceptions:
            recommendations.append({
                "category": "urgent_review",
                "title": "Immediate Review Required",
                "description": f"Review {len(critical_exceptions)} critical exceptions immediately",
                "priority": "critical",
                "timeline": "within 1 hour"
            })
        
        if high_exceptions:
            recommendations.append({
                "category": "priority_review",
                "title": "Priority Review",
                "description": f"Review {len(high_exceptions)} high severity exceptions",
                "priority": "high",
                "timeline": "within 4 hours"
            })
        
        # Analyze resolution patterns
        low_confidence_resolutions = [r for r in state.resolutions if r.get("confidence_score", 0) < 0.7]
        if low_confidence_resolutions:
            recommendations.append({
                "category": "resolution_approval",
                "title": "Resolution Approval Required",
                "description": f"Approve {len(low_confidence_resolutions)} low confidence resolutions",
                "priority": "medium",
                "timeline": "within 24 hours"
            })
        
        return {
            "recommendations": recommendations,
            "total_recommendations": len(recommendations),
            "review_workflow": self._create_review_workflow(state)
        }
    
    async def _create_approval_workflow(self, state: HumanReviewState) -> Dict[str, Any]:
        """Create approval workflow for human review."""
        logger.info("Creating approval workflow...")
        
        workflow_steps = []
        
        # Step 1: Critical Exception Review
        critical_exceptions = [e for e in state.exceptions if e.get("severity") == "critical"]
        if critical_exceptions:
            workflow_steps.append({
                "step": 1,
                "title": "Critical Exception Review",
                "description": "Review and approve critical exceptions",
                "items_count": len(critical_exceptions),
                "estimated_time": f"{len(critical_exceptions) * 5} minutes",
                "required_role": "senior_analyst",
                "auto_approve": False
            })
        
        # Step 2: High Severity Exception Review
        high_exceptions = [e for e in state.exceptions if e.get("severity") == "high"]
        if high_exceptions:
            workflow_steps.append({
                "step": 2,
                "title": "High Severity Exception Review",
                "description": "Review high severity exceptions",
                "items_count": len(high_exceptions),
                "estimated_time": f"{len(high_exceptions) * 3} minutes",
                "required_role": "analyst",
                "auto_approve": False
            })
        
        # Step 3: Resolution Approval
        low_confidence_resolutions = [r for r in state.resolutions if r.get("confidence_score", 0) < 0.7]
        if low_confidence_resolutions:
            workflow_steps.append({
                "step": 3,
                "title": "Resolution Approval",
                "description": "Approve proposed resolutions",
                "items_count": len(low_confidence_resolutions),
                "estimated_time": f"{len(low_confidence_resolutions) * 2} minutes",
                "required_role": "analyst",
                "auto_approve": False
            })
        
        return {
            "workflow_steps": workflow_steps,
            "total_steps": len(workflow_steps),
            "estimated_total_time": self._calculate_total_time(workflow_steps),
            "workflow_status": "pending" if workflow_steps else "completed"
        }
    
    def _create_review_workflow(self, state: HumanReviewState) -> Dict[str, Any]:
        """Create review workflow."""
        return {
            "review_phases": [
                {
                    "phase": 1,
                    "name": "Exception Review",
                    "description": "Review and validate identified exceptions",
                    "items": [e for e in state.exceptions if e.get("severity") in ["high", "critical"]]
                },
                {
                    "phase": 2,
                    "name": "Resolution Approval",
                    "description": "Approve proposed resolutions",
                    "items": [r for r in state.resolutions if r.get("confidence_score", 0) < 0.7]
                },
                {
                    "phase": 3,
                    "name": "Final Approval",
                    "description": "Final approval of reconciliation results",
                    "items": []
                }
            ],
            "approval_chain": [
                "analyst",
                "senior_analyst", 
                "manager"
            ]
        }
    
    def _calculate_total_time(self, workflow_steps: List[Dict[str, Any]]) -> str:
        """Calculate total estimated time for workflow."""
        total_minutes = 0
        for step in workflow_steps:
            time_str = step.get("estimated_time", "0 minutes")
            try:
                minutes = int(time_str.split()[0])
                total_minutes += minutes
            except:
                pass
        
        if total_minutes < 60:
            return f"{total_minutes} minutes"
        else:
            hours = total_minutes // 60
            remaining_minutes = total_minutes % 60
            return f"{hours}h {remaining_minutes}m"


# Lazy initialization function
_human_in_loop_agent = None

def get_human_in_loop_agent():
    """Get or create the human-in-loop agent instance."""
    global _human_in_loop_agent
    if _human_in_loop_agent is None:
        _human_in_loop_agent = HumanInLoopAgent()
    return _human_in_loop_agent


async def human_in_loop_review(
    exceptions: List[Dict[str, Any]],
    resolutions: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Perform human-in-loop review using the human-in-loop agent."""
    agent = get_human_in_loop_agent()
    return await agent.human_in_loop_review(exceptions, resolutions)
