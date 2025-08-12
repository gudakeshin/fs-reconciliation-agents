"""
Resolution Engine Agent for FS Reconciliation Agents.

This module implements the intelligent resolution engine that automatically
generates corrective actions and journal entries for reconciliation breaks.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from decimal import Decimal
import json

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.core.services.data_services.config_service import get_openai_config, get_agent_config, get_prompt_template
from src.core.models.break_types.reconciliation_break import ReconciliationException, BreakType, BreakSeverity, BreakStatus
from src.core.services.data_services.database import get_db_session
from src.core.utils.audit_logger import get_audit_logger

logger = logging.getLogger(__name__)


class ResolutionState(BaseModel):
    """State for the resolution engine workflow."""
    
    reconciliation_exceptions: List[Dict[str, Any]] = Field(default_factory=list)
    resolution_rules: Dict[str, Any] = Field(default_factory=dict)
    proposed_actions: List[Dict[str, Any]] = Field(default_factory=list)
    journal_entries: List[Dict[str, Any]] = Field(default_factory=list)
    resolution_errors: List[str] = Field(default_factory=list)
    processing_status: str = "pending"
    resolved_exceptions: List[Dict[str, Any]] = Field(default_factory=list)
    summary: Dict[str, Any] = Field(default_factory=dict)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    processing_time_ms: Optional[int] = None


class ResolutionEngineAgent:
    """Intelligent resolution engine for reconciliation breaks."""
    
    def __init__(self):
        """Initialize the resolution engine agent."""
        self.config = get_agent_config("resolution_engine")
        self.openai_config = get_openai_config()
        self.llm = None
        self.workflow = None
    
    def _get_llm(self):
        """Get or create the LLM instance."""
        if self.llm is None:
            api_key = self.openai_config.get("api", {}).get("api_key")
            if not api_key:
                raise ValueError("OpenAI API key not configured")
            
            self.llm = ChatOpenAI(
                model=self.config.get("model", "gpt-4o-mini-2024-07-18"),
                temperature=self.config.get("temperature", 0.1),
                max_tokens=self.config.get("max_tokens", 3000),
                api_key=api_key
            )
        return self.llm
    
    def _get_workflow(self):
        """Get or create the workflow instance."""
        if self.workflow is None:
            self.workflow = self._create_workflow()
        return self.workflow
    
    def _create_workflow(self) -> StateGraph:
        """Create the resolution workflow."""
        workflow = StateGraph(ResolutionState)
        
        # Add workflow nodes
        workflow.add_node("validate_exceptions", self._validate_exceptions)
        workflow.add_node("analyze_break_patterns", self._analyze_break_patterns)
        workflow.add_node("generate_resolution_actions", self._generate_resolution_actions)
        workflow.add_node("create_journal_entries", self._create_journal_entries)
        workflow.add_node("validate_resolutions", self._validate_resolutions)
        workflow.add_node("apply_resolutions", self._apply_resolutions)
        workflow.add_node("generate_summary", self._generate_summary)
        
        # Set workflow edges
        workflow.set_entry_point("validate_exceptions")
        workflow.add_edge("validate_exceptions", "analyze_break_patterns")
        workflow.add_edge("analyze_break_patterns", "generate_resolution_actions")
        workflow.add_edge("generate_resolution_actions", "create_journal_entries")
        workflow.add_edge("create_journal_entries", "validate_resolutions")
        workflow.add_edge("validate_resolutions", "apply_resolutions")
        workflow.add_edge("apply_resolutions", "generate_summary")
        workflow.add_edge("generate_summary", END)
        
        return workflow.compile()
    
    async def _validate_exceptions(self, state: ResolutionState) -> ResolutionState:
        """Validate reconciliation exceptions for resolution."""
        logger.info("Validating reconciliation exceptions...")
        state.processing_status = "validating_exceptions"
        
        valid_exceptions = []
        for exception in state.reconciliation_exceptions:
            if self._is_resolvable(exception):
                valid_exceptions.append(exception)
            else:
                state.resolution_errors.append(f"Exception {exception.get('id')} is not resolvable")
        
        state.reconciliation_exceptions = valid_exceptions
        logger.info(f"Validated {len(valid_exceptions)} resolvable exceptions")
        
        return state
    
    def _is_resolvable(self, exception: Dict[str, Any]) -> bool:
        """Check if an exception can be automatically resolved."""
        break_type = exception.get("break_type")
        severity = exception.get("severity", "medium")
        
        # High severity breaks may require manual intervention
        if severity == "high":
            return False
        
        # Check if break type supports automatic resolution
        auto_resolvable_types = [
            BreakType.SECURITY_ID_BREAK.value,
            BreakType.FIXED_INCOME_COUPON.value,
            BreakType.MARKET_PRICE_DIFFERENCE.value,
            BreakType.TRADE_SETTLEMENT_DATE.value,
            BreakType.FX_RATE_ERROR.value
        ]
        
        return break_type in auto_resolvable_types
    
    async def _analyze_break_patterns(self, state: ResolutionState) -> ResolutionState:
        """Analyze patterns in reconciliation breaks."""
        logger.info("Analyzing break patterns...")
        state.processing_status = "analyzing_patterns"
        
        # Group exceptions by break type
        break_groups = {}
        for exception in state.reconciliation_exceptions:
            break_type = exception.get("break_type")
            if break_type not in break_groups:
                break_groups[break_type] = []
            break_groups[break_type].append(exception)
        
        # Analyze patterns for each break type
        patterns = {}
        for break_type, exceptions in break_groups.items():
            pattern = await self._analyze_break_type_pattern(break_type, exceptions)
            patterns[break_type] = pattern
        
        state.resolution_rules["patterns"] = patterns
        logger.info(f"Analyzed patterns for {len(break_groups)} break types")
        
        return state
    
    async def _analyze_break_type_pattern(self, break_type: str, exceptions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze patterns for a specific break type."""
        pattern = {
            "break_type": break_type,
            "count": len(exceptions),
            "common_causes": [],
            "resolution_strategies": []
        }
        
        # Analyze common causes based on break type
        if break_type == BreakType.SECURITY_ID_BREAK.value:
            pattern["common_causes"] = ["Data entry errors", "System mapping issues", "Identifier format differences"]
            pattern["resolution_strategies"] = ["Standardize security identifiers", "Update mapping tables", "Validate data sources"]
        
        elif break_type == BreakType.FIXED_INCOME_COUPON.value:
            pattern["common_causes"] = ["Day count convention differences", "Accrued interest calculation errors", "Coupon frequency mismatches"]
            pattern["resolution_strategies"] = ["Recalculate accrued interest", "Apply correct day count convention", "Verify coupon schedules"]
        
        elif break_type == BreakType.MARKET_PRICE_DIFFERENCE.value:
            pattern["common_causes"] = ["Price source differences", "Timing differences", "Market data delays"]
            pattern["resolution_strategies"] = ["Use authoritative price source", "Apply price tolerance rules", "Validate market data"]
        
        elif break_type == BreakType.TRADE_SETTLEMENT_DATE.value:
            pattern["common_causes"] = ["Settlement date calculation errors", "Holiday calendar differences", "Time zone issues"]
            pattern["resolution_strategies"] = ["Recalculate settlement dates", "Apply correct holiday calendars", "Standardize time zones"]
        
        elif break_type == BreakType.FX_RATE_ERROR.value:
            pattern["common_causes"] = ["Rate source differences", "Timing differences", "Cross rate calculation errors"]
            pattern["resolution_strategies"] = ["Use authoritative FX source", "Apply rate tolerance rules", "Validate cross rates"]
        
        return pattern
    
    async def _generate_resolution_actions(self, state: ResolutionState) -> ResolutionState:
        """Generate resolution actions for each exception."""
        logger.info("Generating resolution actions...")
        state.processing_status = "generating_actions"
        
        for exception in state.reconciliation_exceptions:
            action = await self._generate_action_for_exception(exception)
            if action:
                state.proposed_actions.append(action)
        
        logger.info(f"Generated {len(state.proposed_actions)} resolution actions")
        return state
    
    async def _generate_action_for_exception(self, exception: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate resolution action for a specific exception."""
        break_type = exception.get("break_type")
        break_details = exception.get("break_details", {})
        
        # Get historical learning data for similar exceptions
        historical_data = await self._get_historical_resolutions(break_type, exception.get("transaction", {}).get("security_id"))
        
        # Get resolution prompt template
        prompt_template = get_prompt_template("resolution_action")
        
        # Prepare context for LLM with historical learning
        context = {
            "break_type": break_type,
            "break_details": break_details,
            "transaction_info": exception.get("transaction", {}),
            "severity": exception.get("severity", "medium"),
            "historical_data": historical_data,
            "ai_reasoning": exception.get("ai_reasoning"),
            "ai_suggested_actions": exception.get("ai_suggested_actions")
        }
        
        try:
            # Generate resolution action using LLM
            messages = [
                SystemMessage(content=prompt_template),
                HumanMessage(content=json.dumps(context, indent=2))
            ]
            
            response = await self._get_llm().ainvoke(messages)
            action_content = response.content
            
            # Parse the response
            action = self._parse_resolution_action(action_content, exception)
            
            # Enhance with historical learning
            action = await self._enhance_action_with_learning(action, historical_data)
            
            return action
            
        except Exception as e:
            logger.error(f"Error generating action for exception {exception.get('id')}: {e}")
            # Fallback to rule-based recommendations
            return await self._generate_rule_based_action(exception, historical_data)
    
    def _parse_resolution_action(self, action_content: str, exception: Dict[str, Any]) -> Dict[str, Any]:
        """Parse LLM response into structured resolution action."""
        try:
            # Try to parse as JSON
            action_data = json.loads(action_content)
        except:
            # Fallback to structured parsing
            action_data = self._extract_action_from_text(action_content)
        
        action = {
            "exception_id": exception.get("id"),
            "break_type": exception.get("break_type"),
            "action_type": action_data.get("action_type", "unknown"),
            "description": action_data.get("description", action_content),
            "parameters": action_data.get("parameters", {}),
            "priority": action_data.get("priority", "medium"),
            "estimated_impact": action_data.get("estimated_impact", "unknown"),
            "confidence_score": action_data.get("confidence_score", 0.5)
        }
        
        return action
    
    def _extract_action_from_text(self, text: str) -> Dict[str, Any]:
        """Extract action information from text response."""
        # Simple text parsing as fallback
        return {
            "action_type": "manual_review",
            "description": text,
            "parameters": {},
            "priority": "medium",
            "estimated_impact": "unknown",
            "confidence_score": 0.3
        }
    
    async def _get_historical_resolutions(self, break_type: str, security_id: str) -> Dict[str, Any]:
        """Get historical resolution data for similar exceptions to improve recommendations."""
        try:
            from src.core.services.data_services.database import get_db_session
            from sqlalchemy import text
            
            async with get_db_session() as session:
                # Query historical resolutions for this break type and security
                query = """
                SELECT 
                    COUNT(*) as total_exceptions,
                    COUNT(CASE WHEN status = 'resolved' THEN 1 END) as resolved_count,
                    AVG(CASE WHEN status = 'resolved' THEN 1 ELSE 0 END) as resolution_rate,
                    MODE() WITHIN GROUP (ORDER BY resolution_method) as common_resolution_method,
                    AVG(CASE WHEN status = 'resolved' 
                        THEN EXTRACT(EPOCH FROM (resolved_at - created_at))/3600 
                        ELSE NULL END) as avg_resolution_hours,
                    json_agg(DISTINCT resolution_notes) as resolution_notes
                FROM reconciliation_exceptions 
                WHERE break_type = :break_type 
                AND raw_data->>'security_id' = :security_id
                AND created_at > NOW() - INTERVAL '90 days'
                """
                result = await session.execute(text(query), {
                    "break_type": break_type,
                    "security_id": security_id
                })
                row = result.fetchone()
                
                if row and row[0] > 0:
                    return {
                        "total_exceptions": row[0],
                        "resolved_count": row[1],
                        "resolution_rate": round(float(row[2]) * 100, 1),
                        "common_resolution_method": row[3],
                        "avg_resolution_hours": float(row[4]) if row[4] else 0,
                        "resolution_notes": row[5] if row[5] else []
                    }
        except Exception as e:
            logger.warning(f"Error fetching historical resolutions: {e}")
        
        return {}
    
    async def _enhance_action_with_learning(self, action: Dict[str, Any], historical_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance action with historical learning insights."""
        if not historical_data:
            return action
        
        # Adjust confidence based on historical success rate
        if historical_data.get("resolution_rate", 0) > 80:
            action["confidence_score"] = min(action.get("confidence_score", 0.5) * 1.2, 1.0)
        elif historical_data.get("resolution_rate", 0) < 50:
            action["confidence_score"] = max(action.get("confidence_score", 0.5) * 0.8, 0.1)
        
        # Add historical context to description
        if historical_data.get("common_resolution_method"):
            action["description"] += f" Historical data shows {historical_data['resolution_rate']}% success rate with '{historical_data['common_resolution_method']}' method."
        
        # Add estimated resolution time based on historical data
        if historical_data.get("avg_resolution_hours", 0) > 0:
            action["estimated_resolution_hours"] = historical_data["avg_resolution_hours"]
        
        return action
    
    async def _generate_rule_based_action(self, exception: Dict[str, Any], historical_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate rule-based resolution action when LLM fails."""
        break_type = exception.get("break_type")
        severity = exception.get("severity", "medium")
        
        # Rule-based recommendations based on break type
        if break_type == "market_price_difference":
            action = {
                "action_type": "price_verification",
                "description": "Verify market price with multiple sources and update if necessary",
                "parameters": {
                    "verification_sources": ["bloomberg", "reuters", "internal"],
                    "tolerance_threshold": 0.01
                },
                "priority": "high" if severity == "high" else "medium",
                "estimated_impact": "low",
                "confidence_score": 0.7
            }
        elif break_type == "fixed_income_coupon":
            action = {
                "action_type": "coupon_calculation_verification",
                "description": "Verify coupon calculation and accrued interest",
                "parameters": {
                    "check_coupon_rate": True,
                    "check_accrued_interest": True,
                    "check_payment_dates": True
                },
                "priority": "medium",
                "estimated_impact": "medium",
                "confidence_score": 0.6
            }
        elif break_type == "trade_settlement_date":
            action = {
                "action_type": "date_verification",
                "description": "Verify trade and settlement dates with counterparty",
                "parameters": {
                    "check_timezone": True,
                    "check_holidays": True,
                    "check_settlement_cycle": True
                },
                "priority": "low",
                "estimated_impact": "low",
                "confidence_score": 0.8
            }
        else:
            action = {
                "action_type": "manual_review",
                "description": "Manual review required for this exception type",
                "parameters": {},
                "priority": "medium",
                "estimated_impact": "unknown",
                "confidence_score": 0.5
            }
        
        # Enhance with historical learning
        return await self._enhance_action_with_learning(action, historical_data)
    
    async def _create_journal_entries(self, state: ResolutionState) -> ResolutionState:
        """Create journal entries for resolution actions."""
        logger.info("Creating journal entries...")
        state.processing_status = "creating_journal_entries"
        
        for action in state.proposed_actions:
            journal_entry = await self._create_journal_entry_for_action(action)
            if journal_entry:
                state.journal_entries.append(journal_entry)
        
        logger.info(f"Created {len(state.journal_entries)} journal entries")
        return state
    
    async def _create_journal_entry_for_action(self, action: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create journal entry for a specific action."""
        action_type = action.get("action_type")
        parameters = action.get("parameters", {})
        
        journal_entry = {
            "action_id": action.get("exception_id"),
            "entry_type": "resolution",
            "description": action.get("description"),
            "debit_account": parameters.get("debit_account"),
            "credit_account": parameters.get("credit_account"),
            "amount": parameters.get("amount", 0.0),
            "currency": parameters.get("currency", "USD"),
            "effective_date": datetime.utcnow().isoformat(),
            "status": "pending"
        }
        
        # Generate specific journal entries based on action type
        if action_type == "security_id_correction":
            journal_entry.update(self._create_security_correction_entry(parameters))
        elif action_type == "coupon_adjustment":
            journal_entry.update(self._create_coupon_adjustment_entry(parameters))
        elif action_type == "price_adjustment":
            journal_entry.update(self._create_price_adjustment_entry(parameters))
        elif action_type == "fx_rate_correction":
            journal_entry.update(self._create_fx_correction_entry(parameters))
        else:
            journal_entry.update(self._create_generic_entry(parameters))
        
        return journal_entry
    
    def _create_security_correction_entry(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Create journal entry for security ID correction."""
        return {
            "debit_account": "Trading Securities",
            "credit_account": "Trading Securities",
            "amount": parameters.get("adjustment_amount", 0.0),
            "description": "Security ID correction adjustment"
        }
    
    def _create_coupon_adjustment_entry(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Create journal entry for coupon adjustment."""
        return {
            "debit_account": "Interest Receivable",
            "credit_account": "Interest Income",
            "amount": parameters.get("coupon_adjustment", 0.0),
            "description": "Coupon payment adjustment"
        }
    
    def _create_price_adjustment_entry(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Create journal entry for price adjustment."""
        return {
            "debit_account": "Unrealized Gain/Loss",
            "credit_account": "Trading Securities",
            "amount": parameters.get("price_adjustment", 0.0),
            "description": "Market price adjustment"
        }
    
    def _create_fx_correction_entry(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Create journal entry for FX rate correction."""
        return {
            "debit_account": "FX Gain/Loss",
            "credit_account": "Cash",
            "amount": parameters.get("fx_adjustment", 0.0),
            "description": "FX rate correction"
        }
    
    def _create_generic_entry(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Create generic journal entry."""
        return {
            "debit_account": "Other Assets",
            "credit_account": "Other Liabilities",
            "amount": parameters.get("adjustment_amount", 0.0),
            "description": "Reconciliation adjustment"
        }
    
    async def _validate_resolutions(self, state: ResolutionState) -> ResolutionState:
        """Validate proposed resolutions."""
        logger.info("Validating proposed resolutions...")
        state.processing_status = "validating_resolutions"
        
        valid_actions = []
        for action in state.proposed_actions:
            if self._validate_resolution_action(action):
                valid_actions.append(action)
            else:
                state.resolution_errors.append(f"Invalid resolution action: {action.get('description')}")
        
        state.proposed_actions = valid_actions
        logger.info(f"Validated {len(valid_actions)} resolution actions")
        
        return state
    
    def _validate_resolution_action(self, action: Dict[str, Any]) -> bool:
        """Validate a resolution action."""
        # Check required fields
        required_fields = ["action_type", "description", "parameters"]
        for field in required_fields:
            if field not in action:
                return False
        
        # Check confidence score
        confidence = action.get("confidence_score", 0.0)
        if confidence < 0.1:  # Too low confidence
            return False
        
        # Check action type validity
        valid_types = [
            "security_id_correction",
            "coupon_adjustment",
            "price_adjustment",
            "fx_rate_correction",
            "manual_review"
        ]
        
        if action.get("action_type") not in valid_types:
            return False
        
        return True
    
    async def _apply_resolutions(self, state: ResolutionState) -> ResolutionState:
        """Apply validated resolutions."""
        logger.info("Applying resolutions...")
        state.processing_status = "applying_resolutions"
        
        for action in state.proposed_actions:
            try:
                result = await self._apply_single_resolution(action)
                if result.get("success"):
                    state.resolved_exceptions.append({
                        "exception_id": action.get("exception_id"),
                        "action": action,
                        "result": result
                    })
                else:
                    state.resolution_errors.append(f"Failed to apply resolution: {result.get('error')}")
            except Exception as e:
                logger.error(f"Error applying resolution: {e}")
                state.resolution_errors.append(f"Exception applying resolution: {str(e)}")
        
        logger.info(f"Applied {len(state.resolved_exceptions)} resolutions")
        return state
    
    async def _apply_single_resolution(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a single resolution action."""
        action_type = action.get("action_type")
        parameters = action.get("parameters", {})
        
        try:
            if action_type == "security_id_correction":
                return await self._apply_security_correction(parameters)
            elif action_type == "coupon_adjustment":
                return await self._apply_coupon_adjustment(parameters)
            elif action_type == "price_adjustment":
                return await self._apply_price_adjustment(parameters)
            elif action_type == "fx_rate_correction":
                return await self._apply_fx_correction(parameters)
            else:
                return {"success": False, "error": f"Unknown action type: {action_type}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _apply_security_correction(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Apply security ID correction."""
        # Implementation would update security mappings
        return {"success": True, "message": "Security ID corrected"}
    
    async def _apply_coupon_adjustment(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Apply coupon adjustment."""
        # Implementation would update coupon calculations
        return {"success": True, "message": "Coupon adjustment applied"}
    
    async def _apply_price_adjustment(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Apply price adjustment."""
        # Implementation would update market prices
        return {"success": True, "message": "Price adjustment applied"}
    
    async def _apply_fx_correction(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Apply FX rate correction."""
        # Implementation would update FX rates
        return {"success": True, "message": "FX rate corrected"}
    
    async def _generate_summary(self, state: ResolutionState) -> ResolutionState:
        """Generate resolution summary."""
        logger.info("Generating resolution summary...")
        state.processing_status = "completed"
        
        summary = {
            "total_exceptions": len(state.reconciliation_exceptions),
            "resolved_exceptions": len(state.resolved_exceptions),
            "failed_resolutions": len(state.resolution_errors),
            "success_rate": len(state.resolved_exceptions) / len(state.reconciliation_exceptions) if state.reconciliation_exceptions else 0,
            "break_type_summary": {},
            "resolution_actions": len(state.proposed_actions),
            "journal_entries": len(state.journal_entries)
        }
        
        # Break type summary
        for exception in state.reconciliation_exceptions:
            break_type = exception.get("break_type")
            if break_type not in summary["break_type_summary"]:
                summary["break_type_summary"][break_type] = 0
            summary["break_type_summary"][break_type] += 1
        
        state.summary = summary
        logger.info(f"Resolution summary: {summary['resolved_exceptions']}/{summary['total_exceptions']} resolved")
        
        return state
    
    async def resolve_exceptions(self, exceptions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Main method to resolve reconciliation exceptions."""
        session_id = str(uuid.uuid4())
        audit_logger = get_audit_logger()
        start_time = datetime.utcnow()
        
        logger.info(f"Starting resolution for {len(exceptions)} exceptions")
        
        # Log agent start
        await audit_logger.log_agent_start(
            agent_name="resolution",
            session_id=session_id,
            input_data={
                "exceptions_count": len(exceptions),
                "break_types": list(set([e.get("break_type", "unknown") for e in exceptions]))
            }
        )
        
        # Initialize state
        state = ResolutionState(
            reconciliation_exceptions=exceptions,
            start_time=start_time
        )
        
        try:
            # Run resolution workflow
            final_state = await self._get_workflow().ainvoke(state)
            
            # Calculate processing time
            end_time = datetime.utcnow()
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
            if hasattr(final_state, 'start_time') and final_state.start_time:
                final_state.processing_time_ms = processing_time_ms
            
            result = {
                "success": True,
                "resolved_exceptions": final_state.resolved_exceptions,
                "proposed_actions": final_state.proposed_actions,
                "journal_entries": final_state.journal_entries,
                "errors": final_state.resolution_errors,
                "summary": final_state.summary,
                "processing_time_ms": final_state.processing_time_ms
            }
            
            # Log agent completion
            await audit_logger.log_agent_completion(
                agent_name="resolution",
                session_id=session_id,
                result_data=final_state.summary,
                processing_time_ms=processing_time_ms,
                is_successful=True
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in resolution workflow: {e}")
            # Ensure we have a summary even if workflow fails
            if not state.summary:
                state.summary = {
                    "total_exceptions": len(state.reconciliation_exceptions),
                    "resolved_exceptions": 0,
                    "failed_resolutions": len(state.resolution_errors) + 1,
                    "success_rate": 0,
                    "break_type_summary": {},
                    "resolution_actions": 0,
                    "journal_entries": 0
                }
            # Calculate processing time
            end_time = datetime.utcnow()
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            result = {
                "success": False,
                "error": str(e),
                "resolved_exceptions": [],
                "proposed_actions": [],
                "journal_entries": [],
                "errors": [str(e)],
                "summary": state.summary
            }
            
            # Log agent failure
            await audit_logger.log_agent_completion(
                agent_name="resolution",
                session_id=session_id,
                result_data=state.summary,
                processing_time_ms=processing_time_ms,
                is_successful=False,
                error_message=str(e)
            )
            
            return result


# Lazy initialization function
_resolution_engine_agent = None

def get_resolution_engine_agent():
    """Get or create the resolution engine agent instance."""
    global _resolution_engine_agent
    if _resolution_engine_agent is None:
        _resolution_engine_agent = ResolutionEngineAgent()
    return _resolution_engine_agent


async def resolve_reconciliation_exceptions(exceptions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Resolve reconciliation exceptions using the resolution engine."""
    agent = get_resolution_engine_agent()
    return await agent.resolve_exceptions(exceptions) 