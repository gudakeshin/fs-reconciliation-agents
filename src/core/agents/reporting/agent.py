"""
Reporting Agent for FS Reconciliation Agents.

This module provides reporting functionality for reconciliation results,
including summary reports, detailed analysis, and actionable insights.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from src.core.utils.audit_logger import get_audit_logger

logger = logging.getLogger(__name__)


class ReportingState(BaseModel):
    """State for reporting workflow."""
    
    # Input data
    match_result: Dict[str, Any] = Field(default_factory=dict)
    exceptions_result: Dict[str, Any] = Field(default_factory=dict)
    resolution_result: Dict[str, Any] = Field(default_factory=dict)
    
    # Processing state
    report_sections: List[Dict[str, Any]] = Field(default_factory=list)
    validation_errors: List[str] = Field(default_factory=list)
    processing_status: str = "pending"
    
    # Output data
    final_report: Dict[str, Any] = Field(default_factory=dict)
    summary: Dict[str, Any] = Field(default_factory=dict)
    
    # Metadata
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    processing_time_ms: Optional[int] = None


class ReportingAgent:
    """Reporting agent for generating reconciliation reports."""
    
    def __init__(self):
        """Initialize the reporting agent."""
        self.name = "Reporting Agent"
        logger.info(f"Initialized {self.name}")
    
    async def generate_reconciliation_report(
        self, 
        match_result: Dict[str, Any],
        exceptions_result: Dict[str, Any], 
        resolution_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate comprehensive reconciliation report."""
        session_id = str(uuid.uuid4())
        audit_logger = get_audit_logger()
        start_time = datetime.utcnow()
        
        logger.info("Generating reconciliation report...")
        
        # Log agent start
        await audit_logger.log_agent_start(
            agent_name="reporting",
            session_id=session_id,
            input_data={
                "match_result_keys": list(match_result.keys()),
                "exceptions_result_keys": list(exceptions_result.keys()),
                "resolution_result_keys": list(resolution_result.keys())
            }
        )
        
        # Initialize state
        state = ReportingState(
            match_result=match_result,
            exceptions_result=exceptions_result,
            resolution_result=resolution_result
        )
        
        try:
            # Generate executive summary
            executive_summary = await self._generate_executive_summary(state)
            
            # Generate detailed analysis
            detailed_analysis = await self._generate_detailed_analysis(state)
            
            # Generate recommendations
            recommendations = await self._generate_recommendations(state)
            
            # Generate risk assessment
            risk_assessment = await self._generate_risk_assessment(state)
            
            # Compile final report
            end_time = datetime.utcnow()
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            final_report = {
                "executive_summary": executive_summary,
                "detailed_analysis": detailed_analysis,
                "recommendations": recommendations,
                "risk_assessment": risk_assessment,
                "metadata": {
                    "generated_at": end_time.isoformat(),
                    "report_version": "1.0",
                    "agent": self.name
                }
            }
            
            result = {
                "success": True,
                "report": final_report,
                "summary": {
                    "total_sections": 4,
                    "processing_time_ms": processing_time_ms,
                    "status": "completed"
                }
            }
            
            # Log agent completion
            await audit_logger.log_agent_completion(
                agent_name="reporting",
                session_id=session_id,
                result_data={"total_sections": 4, "status": "completed"},
                processing_time_ms=processing_time_ms,
                is_successful=True
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            
            # Calculate processing time
            end_time = datetime.utcnow()
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            result = {
                "success": False,
                "error": str(e),
                "summary": {
                    "total_sections": 0,
                    "processing_time_ms": processing_time_ms,
                    "status": "failed"
                }
            }
            
            # Log agent failure
            await audit_logger.log_agent_completion(
                agent_name="reporting",
                session_id=session_id,
                result_data={"total_sections": 0, "status": "failed"},
                processing_time_ms=processing_time_ms,
                is_successful=False,
                error_message=str(e)
            )
            
            return result
    
    async def _generate_executive_summary(self, state: ReportingState) -> Dict[str, Any]:
        """Generate executive summary of reconciliation results."""
        logger.info("Generating executive summary...")
        
        match_summary = state.match_result.get("summary", {})
        exceptions_summary = state.exceptions_result.get("summary", {})
        resolution_summary = state.resolution_result.get("summary", {})
        
        total_transactions = match_summary.get("total_transactions", 0)
        total_matches = match_summary.get("total_matches", 0)
        total_breaks = exceptions_summary.get("total_breaks", 0)
        resolved_breaks = resolution_summary.get("resolved_count", 0)
        
        break_rate = (total_breaks / total_matches * 100) if total_matches > 0 else 0
        resolution_rate = (resolved_breaks / total_breaks * 100) if total_breaks > 0 else 0
        
        return {
            "overview": f"Reconciliation completed for {total_transactions} transactions",
            "key_metrics": {
                "total_transactions": total_transactions,
                "successful_matches": total_matches,
                "reconciliation_breaks": total_breaks,
                "resolved_breaks": resolved_breaks,
                "break_rate_percent": round(break_rate, 2),
                "resolution_rate_percent": round(resolution_rate, 2)
            },
            "status": "completed" if total_breaks == 0 else "requires_attention",
            "priority_actions": self._identify_priority_actions(state)
        }
    
    async def _generate_detailed_analysis(self, state: ReportingState) -> Dict[str, Any]:
        """Generate detailed analysis of reconciliation results."""
        logger.info("Generating detailed analysis...")
        
        exceptions = state.exceptions_result.get("exceptions", [])
        break_types = {}
        severity_distribution = {}
        
        for exception in exceptions:
            # Count break types
            break_type = exception.get("break_type", "unknown")
            break_types[break_type] = break_types.get(break_type, 0) + 1
            
            # Count severity levels
            severity = exception.get("severity", "medium")
            severity_distribution[severity] = severity_distribution.get(severity, 0) + 1
        
        return {
            "break_analysis": {
                "break_types": break_types,
                "severity_distribution": severity_distribution,
                "total_exceptions": len(exceptions)
            },
            "matching_analysis": {
                "match_types": state.match_result.get("summary", {}).get("match_types", {}),
                "confidence_scores": self._analyze_confidence_scores(state)
            },
            "resolution_analysis": {
                "resolution_methods": self._analyze_resolution_methods(state),
                "resolution_timeline": self._analyze_resolution_timeline(state)
            }
        }
    
    async def _generate_recommendations(self, state: ReportingState) -> Dict[str, Any]:
        """Generate actionable recommendations."""
        logger.info("Generating recommendations...")
        
        recommendations = []
        exceptions = state.exceptions_result.get("exceptions", [])
        
        # Analyze patterns and generate recommendations
        if exceptions:
            # High severity exceptions
            high_severity = [e for e in exceptions if e.get("severity") in ["high", "critical"]]
            if high_severity:
                recommendations.append({
                    "category": "urgent",
                    "title": "Address High Severity Breaks",
                    "description": f"Review and resolve {len(high_severity)} high/critical severity breaks immediately",
                    "priority": "high",
                    "estimated_effort": "2-4 hours"
                })
            
            # Price breaks
            price_breaks = [e for e in exceptions if e.get("break_type") == "market_price_difference"]
            if price_breaks:
                recommendations.append({
                    "category": "data_quality",
                    "title": "Review Price Data Sources",
                    "description": f"Investigate {len(price_breaks)} price discrepancies between data sources",
                    "priority": "medium",
                    "estimated_effort": "1-2 hours"
                })
            
            # Unmatched transactions
            unmatched = [e for e in exceptions if e.get("break_type") == "unmatched"]
            if unmatched:
                recommendations.append({
                    "category": "process_improvement",
                    "title": "Improve Matching Criteria",
                    "description": f"Review matching logic for {len(unmatched)} unmatched transactions",
                    "priority": "medium",
                    "estimated_effort": "3-5 hours"
                })
        
        return {
            "recommendations": recommendations,
            "total_recommendations": len(recommendations),
            "priority_distribution": self._analyze_priority_distribution(recommendations)
        }
    
    async def _generate_risk_assessment(self, state: ReportingState) -> Dict[str, Any]:
        """Generate risk assessment."""
        logger.info("Generating risk assessment...")
        
        exceptions = state.exceptions_result.get("exceptions", [])
        total_exceptions = len(exceptions)
        
        # Calculate risk scores
        critical_risk = len([e for e in exceptions if e.get("severity") == "critical"])
        high_risk = len([e for e in exceptions if e.get("severity") == "high"])
        medium_risk = len([e for e in exceptions if e.get("severity") == "medium"])
        low_risk = len([e for e in exceptions if e.get("severity") == "low"])
        
        # Overall risk level
        if critical_risk > 0:
            overall_risk = "critical"
        elif high_risk > 0:
            overall_risk = "high"
        elif medium_risk > 0:
            overall_risk = "medium"
        else:
            overall_risk = "low"
        
        return {
            "overall_risk_level": overall_risk,
            "risk_breakdown": {
                "critical": critical_risk,
                "high": high_risk,
                "medium": medium_risk,
                "low": low_risk
            },
            "total_risk_items": total_exceptions,
            "risk_mitigation": self._generate_risk_mitigation_plan(state)
        }
    
    def _identify_priority_actions(self, state: ReportingState) -> List[str]:
        """Identify priority actions based on reconciliation results."""
        actions = []
        exceptions = state.exceptions_result.get("exceptions", [])
        
        if not exceptions:
            actions.append("No immediate action required - reconciliation successful")
            return actions
        
        critical_exceptions = [e for e in exceptions if e.get("severity") == "critical"]
        if critical_exceptions:
            actions.append(f"Immediate attention required for {len(critical_exceptions)} critical breaks")
        
        high_exceptions = [e for e in exceptions if e.get("severity") == "high"]
        if high_exceptions:
            actions.append(f"Review {len(high_exceptions)} high severity breaks within 24 hours")
        
        return actions
    
    def _analyze_confidence_scores(self, state: ReportingState) -> Dict[str, Any]:
        """Analyze confidence scores from matching."""
        matches = state.match_result.get("matches", [])
        if not matches:
            return {"average_confidence": 0, "confidence_distribution": {}}
        
        scores = [m.get("confidence_score", 0) for m in matches]
        avg_confidence = sum(scores) / len(scores) if scores else 0
        
        return {
            "average_confidence": round(avg_confidence, 3),
            "confidence_distribution": {
                "high": len([s for s in scores if s >= 0.8]),
                "medium": len([s for s in scores if 0.5 <= s < 0.8]),
                "low": len([s for s in scores if s < 0.5])
            }
        }
    
    def _analyze_resolution_methods(self, state: ReportingState) -> Dict[str, int]:
        """Analyze resolution methods used."""
        resolutions = state.resolution_result.get("proposed_actions", [])
        methods = {}
        
        for resolution in resolutions:
            method = resolution.get("method", "unknown")
            methods[method] = methods.get(method, 0) + 1
        
        return methods
    
    def _analyze_resolution_timeline(self, state: ReportingState) -> Dict[str, Any]:
        """Analyze resolution timeline."""
        return {
            "immediate": 0,  # 0-1 hour
            "short_term": 0,  # 1-24 hours
            "medium_term": 0,  # 1-7 days
            "long_term": 0   # >7 days
        }
    
    def _analyze_priority_distribution(self, recommendations: List[Dict[str, Any]]) -> Dict[str, int]:
        """Analyze priority distribution of recommendations."""
        distribution = {"high": 0, "medium": 0, "low": 0}
        
        for rec in recommendations:
            priority = rec.get("priority", "medium")
            distribution[priority] = distribution.get(priority, 0) + 1
        
        return distribution
    
    def _generate_risk_mitigation_plan(self, state: ReportingState) -> List[Dict[str, Any]]:
        """Generate risk mitigation plan."""
        plan = []
        exceptions = state.exceptions_result.get("exceptions", [])
        
        if not exceptions:
            plan.append({
                "risk_type": "none",
                "mitigation": "No risks identified",
                "timeline": "N/A"
            })
            return plan
        
        # Add mitigation strategies based on break types
        break_types = set(e.get("break_type") for e in exceptions)
        
        if "market_price_difference" in break_types:
            plan.append({
                "risk_type": "price_discrepancy",
                "mitigation": "Implement real-time price validation and source reconciliation",
                "timeline": "1-2 weeks"
            })
        
        if "unmatched" in break_types:
            plan.append({
                "risk_type": "matching_failure",
                "mitigation": "Enhance matching algorithms and data quality controls",
                "timeline": "2-4 weeks"
            })
        
        return plan


# Lazy initialization function
_reporting_agent = None

def get_reporting_agent():
    """Get or create the reporting agent instance."""
    global _reporting_agent
    if _reporting_agent is None:
        _reporting_agent = ReportingAgent()
    return _reporting_agent


async def generate_reconciliation_report(
    match_result: Dict[str, Any],
    exceptions_result: Dict[str, Any],
    resolution_result: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate reconciliation report using the reporting agent."""
    agent = get_reporting_agent()
    return await agent.generate_reconciliation_report(match_result, exceptions_result, resolution_result)
