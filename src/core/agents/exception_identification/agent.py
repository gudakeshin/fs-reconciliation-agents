"""
Exception Identification Agent for FS Reconciliation Agents.

This module implements the exception identification agent using LangGraph framework
to detect and classify reconciliation breaks for the five critical break types:
1. Security ID Breaks
2. Fixed Income Coupon Breaks
3. Market Price Breaks
4. Trade vs Settlement Date Breaks
5. FX Rate Breaks
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from decimal import Decimal
import json

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.core.services.data_services.config_service import (
    get_openai_config,
    get_agent_config,
    get_prompt_template
)
from src.core.models.break_types.reconciliation_break import (
    ReconciliationException,
    BreakType,
    BreakSeverity,
    BreakStatus
)
from src.core.services.data_services.database import get_db_session
from src.core.utils.audit_logger import get_audit_logger
from sqlalchemy import text

logger = logging.getLogger(__name__)


class ExceptionIdentificationState(BaseModel):
    """State for exception identification workflow."""
    
    # Input data
    transactions: List[Dict[str, Any]] = Field(default_factory=list)
    matches: List[Dict[str, Any]] = Field(default_factory=list)
    market_data: Dict[str, Any] = Field(default_factory=dict)
    
    # Processing state
    detected_breaks: List[Dict[str, Any]] = Field(default_factory=list)
    classified_breaks: List[Dict[str, Any]] = Field(default_factory=list)
    validation_errors: List[str] = Field(default_factory=list)
    processing_status: str = "pending"
    
    # Output data
    reconciliation_exceptions: List[Dict[str, Any]] = Field(default_factory=list)
    summary: Dict[str, Any] = Field(default_factory=dict)
    
    # Metadata
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    processing_time_ms: Optional[int] = None


class ExceptionIdentificationAgent:
    """Exception Identification Agent using LangGraph."""
    
    def __init__(self):
        """Initialize the exception identification agent."""
        self.config = get_agent_config("exception_identification")
        self.openai_config = get_openai_config()
        
        # Initialize lazily
        self.llm = None
        self.workflow = None
    
    def _get_llm(self):
        """Get or create the LLM instance."""
        if self.llm is None:
            import os
            if os.getenv("DISABLE_EXCEPTION_LLM", "false").lower() == "true":
                return None
            api_key = self.openai_config.get("api", {}).get("api_key")
            if not api_key:
                return None
            self.llm = ChatOpenAI(
                model=self.config.get("model", "gpt-4o-mini-2024-07-18"),
                temperature=self.config.get("temperature", 0.1),
                max_tokens=self.config.get("max_tokens", 4000),
                api_key=api_key
            )
        return self.llm
    
    def _get_workflow(self):
        """Get or create the workflow instance."""
        if self.workflow is None:
            self.workflow = self._create_workflow()
        return self.workflow
    
    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow for exception identification."""
        
        # Create state graph
        workflow = StateGraph(ExceptionIdentificationState)
        
        # Add nodes
        workflow.add_node("validate_input", self._validate_input)
        workflow.add_node("detect_security_breaks", self._detect_security_breaks)
        workflow.add_node("detect_coupon_breaks", self._detect_coupon_breaks)
        workflow.add_node("detect_price_breaks", self._detect_price_breaks)
        workflow.add_node("detect_date_breaks", self._detect_date_breaks)
        workflow.add_node("detect_fx_breaks", self._detect_fx_breaks)
        workflow.add_node("detect_unmatched", self._detect_unmatched)
        workflow.add_node("classify_breaks", self._classify_breaks)
        workflow.add_node("validate_exceptions", self._validate_exceptions)
        workflow.add_node("store_exceptions", self._store_exceptions)
        workflow.add_node("generate_summary", self._generate_summary)
        
        # Define edges
        workflow.set_entry_point("validate_input")
        workflow.add_edge("validate_input", "detect_security_breaks")
        workflow.add_edge("detect_security_breaks", "detect_coupon_breaks")
        workflow.add_edge("detect_coupon_breaks", "detect_price_breaks")
        workflow.add_edge("detect_price_breaks", "detect_date_breaks")
        workflow.add_edge("detect_date_breaks", "detect_fx_breaks")
        workflow.add_edge("detect_fx_breaks", "detect_unmatched")
        workflow.add_edge("detect_unmatched", "classify_breaks")
        workflow.add_edge("classify_breaks", "validate_exceptions")
        workflow.add_edge("validate_exceptions", "store_exceptions")
        workflow.add_edge("store_exceptions", "generate_summary")
        workflow.add_edge("generate_summary", END)
        
        return workflow.compile()
    
    async def _validate_input(self, state: ExceptionIdentificationState) -> ExceptionIdentificationState:
        """Validate input data for exception identification."""
        logger.info("Validating input data for exception identification...")
        
        state.start_time = datetime.utcnow()
        state.processing_status = "validating"
        
        if not state.transactions:
            state.validation_errors.append("No transactions provided")
            state.processing_status = "failed"
            return state
        
        # Validate required fields for break detection
        required_fields = ["external_id", "amount", "currency"]
        for i, transaction in enumerate(state.transactions):
            missing_fields = [field for field in required_fields if field not in transaction]
            if missing_fields:
                state.validation_errors.append(
                    f"Transaction {i}: Missing required fields: {missing_fields}"
                )
        
        logger.info(f"Validated {len(state.transactions)} transactions")
        return state
    
    async def _detect_security_breaks(self, state: ExceptionIdentificationState) -> ExceptionIdentificationState:
        """Detect Security ID breaks."""
        logger.info("Detecting Security ID breaks...")
        
        state.processing_status = "detecting_security_breaks"
        
        security_breaks = []
        
        for match in state.matches:
            trans_a = match.get("transaction_a", {})
            trans_b = match.get("transaction_b", {})
            
            # Check for security ID mismatches (including SEDOL)
            security_a = trans_a.get("security_id") or trans_a.get("isin") or trans_a.get("cusip")
            security_b = trans_b.get("security_id") or trans_b.get("isin") or trans_b.get("cusip")
            
            # Also check SEDOL specifically
            sedol_a = trans_a.get("sedol")
            sedol_b = trans_b.get("sedol")
            
            if (security_a and security_b and security_a != security_b) or (sedol_a and sedol_b and sedol_a != sedol_b):
                # Determine which identifier has the mismatch
                mismatch_type = "unknown"
                mismatch_details = {}
                
                if security_a and security_b and security_a != security_b:
                    mismatch_type = "security_id"
                    mismatch_details = {
                        "security_id_a": security_a,
                        "security_id_b": security_b,
                        "difference": f"{security_a} vs {security_b}"
                    }
                elif sedol_a and sedol_b and sedol_a != sedol_b:
                    mismatch_type = "sedol"
                    mismatch_details = {
                        "sedol_a": sedol_a,
                        "sedol_b": sedol_b,
                        "difference": f"{sedol_a} vs {sedol_b}"
                    }
                
                break_info = {
                    "break_type": BreakType.SECURITY_ID_BREAK.value,
                    "transaction_a": trans_a,
                    "transaction_b": trans_b,
                    "break_details": {
                        "mismatch_type": mismatch_type,
                        **mismatch_details
                    },
                    "severity": BreakSeverity.HIGH.value,
                    "confidence_score": 1.0
                }
                security_breaks.append(break_info)
        
        state.detected_breaks.extend(security_breaks)
        logger.info(f"Detected {len(security_breaks)} Security ID breaks")
        
        return state
    
    async def _detect_coupon_breaks(self, state: ExceptionIdentificationState) -> ExceptionIdentificationState:
        """Detect Fixed Income Coupon breaks."""
        logger.info("Detecting Fixed Income Coupon breaks...")
        
        state.processing_status = "detecting_coupon_breaks"
        
        coupon_breaks = []
        
        for match in state.matches:
            trans_a = match.get("transaction_a", {})
            trans_b = match.get("transaction_b", {})
            
            # Check for coupon payment discrepancies
            amount_a = float(trans_a.get("amount", 0))
            amount_b = float(trans_b.get("amount", 0))
            
            if abs(amount_a - amount_b) > 0.01:  # Significant difference
                # Use AI to determine if this is a coupon break
                is_coupon_break = await self._analyze_coupon_break(trans_a, trans_b)
                
                if is_coupon_break:
                    # Analyze the coupon break and provide recommendations
                    analysis = await self._analyze_coupon_break_detailed(trans_a, trans_b, amount_a, amount_b)
                    
                    break_info = {
                        "break_type": BreakType.FIXED_INCOME_COUPON.value,
                        "transaction_a": trans_a,
                        "transaction_b": trans_b,
                        "break_details": {
                            "amount_a": amount_a,
                            "amount_b": amount_b,
                            "difference": abs(amount_a - amount_b),
                            "percentage_diff": abs(amount_a - amount_b) / max(amount_a, amount_b) * 100,
                            "analysis": analysis
                        },
                        "severity": analysis.get("severity", BreakSeverity.MEDIUM.value),
                        "confidence_score": 0.8,
                        "ai_reasoning": analysis.get("reasoning"),
                        "ai_suggested_actions": analysis.get("recommendations")
                    }
                    coupon_breaks.append(break_info)
        
        state.detected_breaks.extend(coupon_breaks)
        logger.info(f"Detected {len(coupon_breaks)} Fixed Income Coupon breaks")
        
        return state
    
    async def _analyze_coupon_break(self, trans_a: Dict[str, Any], trans_b: Dict[str, Any]) -> bool:
        """Use AI to analyze if a break is related to coupon payments."""
        prompt = f"""
        Analyze if the following transaction difference is related to a fixed income coupon payment:
        
        Transaction A: {json.dumps(trans_a, indent=2)}
        Transaction B: {json.dumps(trans_b, indent=2)}
        
        Consider:
        1. Security type (bonds, notes, etc.)
        2. Payment frequency (monthly, quarterly, etc.)
        3. Coupon rate and calculation
        4. Accrued interest
        
        Return only 'true' if this appears to be a coupon-related break, 'false' otherwise.
        """
        
        messages = [
            SystemMessage(content="You are a fixed income expert."),
            HumanMessage(content=prompt)
        ]
        
        llm = self._get_llm()
        if llm is None:
            # Fallback heuristic: treat significant amount differences as coupon-related
            return True
        response = await llm.ainvoke(messages)
        try:
            return response.content.strip().lower() == "true"
        except Exception as e:
            logger.warning(f"Failed to analyze coupon break: {e}")
            return False
    
    async def _analyze_coupon_break_detailed(self, trans_a: Dict[str, Any], trans_b: Dict[str, Any], 
                                           amount_a: float, amount_b: float) -> Dict[str, Any]:
        """Analyze a coupon break and provide detailed recommendations."""
        
        # Get historical learning data for similar breaks
        historical_data = await self._get_historical_coupon_breaks(trans_a.get("security_id"))
        
        amount_diff = abs(amount_a - amount_b)
        percentage_diff = amount_diff / max(amount_a, amount_b) * 100
        
        # Analyze the break pattern
        analysis = {
            "reasoning": f"Coupon payment difference of {amount_diff:.4f} ({percentage_diff:.2f}%) detected between sources. ",
            "recommendations": [],
            "historical_context": historical_data,
            "severity": BreakSeverity.MEDIUM.value
        }
        
        # Determine likely cause and recommendations based on percentage difference
        if percentage_diff > 20:
            analysis["reasoning"] += "Large coupon difference suggests potential calculation error or missing payments."
            analysis["recommendations"] = [
                "Verify coupon rate calculation",
                "Check for missed coupon payments",
                "Review bond documentation and terms",
                "Contact issuer for payment verification",
                "Check for call/put features affecting payments"
            ]
            analysis["severity"] = BreakSeverity.HIGH.value
        elif percentage_diff > 10:
            analysis["reasoning"] += "Significant coupon difference may indicate accrued interest or timing issues."
            analysis["recommendations"] = [
                "Check accrued interest calculations",
                "Verify payment date vs record date",
                "Review day count conventions",
                "Check for partial coupon periods"
            ]
            analysis["severity"] = BreakSeverity.MEDIUM.value
        else:
            analysis["reasoning"] += "Minor coupon difference within normal calculation variation."
            analysis["recommendations"] = [
                "Accept difference as normal variation",
                "Verify calculation methodology",
                "Monitor for pattern in similar bonds"
            ]
            analysis["severity"] = BreakSeverity.LOW.value
        
        # Add historical learning recommendations
        if historical_data:
            analysis["reasoning"] += f" Historical data shows {historical_data.get('similar_breaks', 0)} similar breaks with {historical_data.get('resolution_rate', 0)}% resolution rate."
            if historical_data.get("common_resolution"):
                analysis["recommendations"].append(f"Historical pattern suggests: {historical_data['common_resolution']}")
        
        return analysis
    
    async def _get_historical_coupon_breaks(self, security_id: str) -> Dict[str, Any]:
        """Get historical data for similar coupon breaks to improve recommendations."""
        try:
            async with get_db_session() as session:
                # Query historical coupon breaks for this security
                query = """
                SELECT 
                    COUNT(*) as total_breaks,
                    AVG(CAST(break_amount AS FLOAT)) as avg_break_amount,
                    MODE() WITHIN GROUP (ORDER BY ai_suggested_actions->>0) as common_resolution,
                    COUNT(CASE WHEN status = 'resolved' THEN 1 END) as resolved_count
                FROM reconciliation_exceptions 
                WHERE break_type = 'fixed_income_coupon' 
                AND created_at > NOW() - INTERVAL '30 days'
                """
                result = await session.execute(text(query))
                row = result.fetchone()
                
                if row and row[0] > 0:
                    return {
                        "similar_breaks": row[0],
                        "avg_percentage_diff": float(row[1]) if row[1] else 0,
                        "common_resolution": row[2],
                        "resolution_rate": round((row[3] / row[0]) * 100, 1) if row[0] > 0 else 0
                    }
        except Exception as e:
            logger.warning(f"Error fetching historical coupon breaks: {e}")
        
        return {}
    
    async def _analyze_price_break(self, trans_a: Dict[str, Any], trans_b: Dict[str, Any], 
                                 price_a: float, price_b: float, price_diff: float, percentage_diff: float) -> Dict[str, Any]:
        """Analyze a price break and provide detailed recommendations."""
        
        # Get historical learning data for similar breaks
        historical_data = await self._get_historical_price_breaks(trans_a.get("security_id"))
        
        # Analyze the break pattern
        analysis = {
            "reasoning": f"Price difference of {price_diff:.4f} ({percentage_diff:.2f}%) detected between sources. ",
            "recommendations": [],
            "historical_context": historical_data,
            "risk_assessment": "medium"
        }
        
        # Determine likely cause and recommendations based on percentage difference
        if percentage_diff > 10:
            analysis["reasoning"] += "Large price difference suggests potential data error or market event."
            analysis["recommendations"] = [
                "Verify data source accuracy",
                "Check for market events or news",
                "Contact counterparty for confirmation",
                "Review trade documentation"
            ]
            analysis["risk_assessment"] = "high"
        elif percentage_diff > 5:
            analysis["reasoning"] += "Significant price difference may indicate timing or source issues."
            analysis["recommendations"] = [
                "Check price timestamp differences",
                "Verify market data source",
                "Review bid-ask spread",
                "Consider market volatility"
            ]
            analysis["risk_assessment"] = "medium"
        else:
            analysis["reasoning"] += "Minor price difference within normal market variation."
            analysis["recommendations"] = [
                "Accept price difference as normal variation",
                "Monitor for pattern in similar trades",
                "Update price tolerance if needed"
            ]
            analysis["risk_assessment"] = "low"
        
        # Add historical learning recommendations
        if historical_data:
            analysis["reasoning"] += f" Historical data shows {historical_data.get('similar_breaks', 0)} similar breaks with {historical_data.get('resolution_rate', 0)}% resolution rate."
            if historical_data.get("common_resolution"):
                analysis["recommendations"].append(f"Historical pattern suggests: {historical_data['common_resolution']}")
        
        return analysis
    
    async def _get_historical_price_breaks(self, security_id: str) -> Dict[str, Any]:
        """Get historical data for similar price breaks to improve recommendations."""
        try:
            async with get_db_session() as session:
                # Query historical price breaks for this security
                query = """
                SELECT 
                    COUNT(*) as total_breaks,
                    AVG(CAST(break_amount AS FLOAT)) as avg_break_amount,
                    MODE() WITHIN GROUP (ORDER BY ai_suggested_actions->>0) as common_resolution,
                    COUNT(CASE WHEN status = 'resolved' THEN 1 END) as resolved_count
                FROM reconciliation_exceptions 
                WHERE break_type = 'market_price_difference' 
                AND created_at > NOW() - INTERVAL '30 days'
                """
                result = await session.execute(text(query))
                row = result.fetchone()
                
                if row and row[0] > 0:
                    return {
                        "similar_breaks": row[0],
                        "avg_percentage_diff": float(row[1]) if row[1] else 0,
                        "common_resolution": row[2],
                        "resolution_rate": round((row[3] / row[0]) * 100, 1) if row[0] > 0 else 0
                    }
        except Exception as e:
            logger.warning(f"Error fetching historical price breaks: {e}")
        
        return {}
    
    async def _analyze_date_break(self, trans_a: Dict[str, Any], trans_b: Dict[str, Any], 
                                date_a: str, date_b: str, date_diff: int) -> Dict[str, Any]:
        """Analyze a date break and provide detailed recommendations."""
        
        # Get historical learning data for similar breaks
        historical_data = await self._get_historical_date_breaks(trans_a.get("security_id"))
        
        # Analyze the break pattern
        analysis = {
            "reasoning": f"Date difference of {date_diff} days detected between trade dates. ",
            "recommendations": [],
            "historical_context": historical_data,
            "severity": BreakSeverity.LOW.value
        }
        
        # Determine likely cause and recommendations based on date difference
        if date_diff > 7:
            analysis["reasoning"] += "Large date difference suggests potential data error or system issue."
            analysis["recommendations"] = [
                "Verify trade date accuracy in both systems",
                "Check for timezone differences",
                "Review trade confirmation documents",
                "Contact counterparty for date verification"
            ]
            analysis["severity"] = BreakSeverity.HIGH.value
        elif date_diff > 3:
            analysis["reasoning"] += "Significant date difference may indicate settlement cycle or holiday adjustments."
            analysis["recommendations"] = [
                "Check settlement cycle differences (T+1 vs T+2)",
                "Verify market holidays and business days",
                "Review trade execution timing",
                "Consider timezone differences"
            ]
            analysis["severity"] = BreakSeverity.MEDIUM.value
        else:
            analysis["reasoning"] += "Minor date difference within normal settlement variation."
            analysis["recommendations"] = [
                "Accept date difference as normal variation",
                "Verify settlement cycle alignment",
                "Monitor for pattern in similar trades"
            ]
            analysis["severity"] = BreakSeverity.LOW.value
        
        # Add historical learning recommendations
        if historical_data:
            analysis["reasoning"] += f" Historical data shows {historical_data.get('similar_breaks', 0)} similar breaks with {historical_data.get('resolution_rate', 0)}% resolution rate."
            if historical_data.get("common_resolution"):
                analysis["recommendations"].append(f"Historical pattern suggests: {historical_data['common_resolution']}")
        
        return analysis
    
    async def _get_historical_date_breaks(self, security_id: str) -> Dict[str, Any]:
        """Get historical data for similar date breaks to improve recommendations."""
        try:
            async with get_db_session() as session:
                # Query historical date breaks for this security
                query = """
                SELECT 
                    COUNT(*) as total_breaks,
                    AVG(CAST(break_amount AS FLOAT)) as avg_break_amount,
                    MODE() WITHIN GROUP (ORDER BY ai_suggested_actions->>0) as common_resolution,
                    COUNT(CASE WHEN status = 'resolved' THEN 1 END) as resolved_count
                FROM reconciliation_exceptions 
                WHERE break_type = 'trade_settlement_date' 
                AND created_at > NOW() - INTERVAL '30 days'
                """
                result = await session.execute(text(query))
                row = result.fetchone()
                
                if row and row[0] > 0:
                    return {
                        "similar_breaks": row[0],
                        "avg_date_diff": int(row[1]) if row[1] else 0,
                        "common_resolution": row[2],
                        "resolution_rate": round((row[3] / row[0]) * 100, 1) if row[0] > 0 else 0
                    }
        except Exception as e:
            logger.warning(f"Error fetching historical date breaks: {e}")
        
        return {}
    
    async def _detect_price_breaks(self, state: ExceptionIdentificationState) -> ExceptionIdentificationState:
        """Detect Market Price breaks."""
        logger.info("Detecting Market Price breaks...")
        
        state.processing_status = "detecting_price_breaks"
        
        price_breaks = []
        
        for match in state.matches:
            trans_a = match.get("transaction_a", {})
            trans_b = match.get("transaction_b", {})
            
            # Check for market price discrepancies
            price_a = trans_a.get("market_price")
            price_b = trans_b.get("market_price")
            
            logger.info(f"Checking prices: {price_a} vs {price_b}")
            
            if price_a and price_b:
                price_diff = abs(float(price_a) - float(price_b))
                price_tolerance = max(float(price_a), float(price_b)) * 0.01  # 1% tolerance
                
                logger.info(f"Price diff: {price_diff}, tolerance: {price_tolerance}, percentage: {price_diff / max(float(price_a), float(price_b)) * 100}%")
                
                if price_diff > price_tolerance:
                    percentage_diff = price_diff / max(float(price_a), float(price_b)) * 100
                    
                    # Determine severity based on percentage difference
                    if percentage_diff > 5:
                        severity = BreakSeverity.HIGH.value
                    elif percentage_diff > 2:
                        severity = BreakSeverity.MEDIUM.value
                    else:
                        severity = BreakSeverity.LOW.value
                    
                    # Analyze the break and provide recommendations
                    analysis = await self._analyze_price_break(trans_a, trans_b, price_a, price_b, price_diff, percentage_diff)
                    
                    break_info = {
                        "break_type": BreakType.MARKET_PRICE_DIFFERENCE.value,
                        "transaction_a": trans_a,
                        "transaction_b": trans_b,
                        "break_details": {
                            "price_a": price_a,
                            "price_b": price_b,
                            "difference": price_diff,
                            "tolerance": price_tolerance,
                            "percentage_diff": percentage_diff,
                            "analysis": analysis
                        },
                        "severity": severity,
                        "confidence_score": 0.9,
                        "ai_reasoning": analysis.get("reasoning"),
                        "ai_suggested_actions": analysis.get("recommendations")
                    }
                    price_breaks.append(break_info)
        
        state.detected_breaks.extend(price_breaks)
        logger.info(f"Detected {len(price_breaks)} Market Price breaks")
        
        return state
    
    async def _detect_date_breaks(self, state: ExceptionIdentificationState) -> ExceptionIdentificationState:
        """Detect Trade vs Settlement Date breaks."""
        logger.info("Detecting Trade vs Settlement Date breaks...")
        
        state.processing_status = "detecting_date_breaks"
        
        date_breaks = []
        
        for match in state.matches:
            trans_a = match.get("transaction_a", {})
            trans_b = match.get("transaction_b", {})
            
            # Check for date discrepancies
            trade_date_a = trans_a.get("trade_date")
            trade_date_b = trans_b.get("trade_date")
            settlement_date_a = trans_a.get("settlement_date")
            settlement_date_b = trans_b.get("settlement_date")
            
            if trade_date_a and trade_date_b and trade_date_a != trade_date_b:
                try:
                    date_a = datetime.fromisoformat(trade_date_a)
                    date_b = datetime.fromisoformat(trade_date_b)
                    date_diff = abs((date_a - date_b).days)
                    
                    if date_diff > 1:  # More than 1 day difference
                        # Analyze the date break and provide recommendations
                        analysis = await self._analyze_date_break(trans_a, trans_b, trade_date_a, trade_date_b, date_diff)
                        
                        break_info = {
                            "break_type": BreakType.TRADE_SETTLEMENT_DATE.value,
                            "transaction_a": trans_a,
                            "transaction_b": trans_b,
                            "break_details": {
                                "trade_date_a": trade_date_a,
                                "trade_date_b": trade_date_b,
                                "difference_days": date_diff,
                                "analysis": analysis
                            },
                            "severity": analysis.get("severity", BreakSeverity.LOW.value),
                            "confidence_score": 0.8,
                            "ai_reasoning": analysis.get("reasoning"),
                            "ai_suggested_actions": analysis.get("recommendations")
                        }
                        date_breaks.append(break_info)
                except Exception as e:
                    logger.warning(f"Error parsing dates: {e}")
        
        state.detected_breaks.extend(date_breaks)
        logger.info(f"Detected {len(date_breaks)} Trade vs Settlement Date breaks")
        
        return state
    
    async def _detect_fx_breaks(self, state: ExceptionIdentificationState) -> ExceptionIdentificationState:
        """Detect FX Rate breaks."""
        logger.info("Detecting FX Rate breaks...")
        
        state.processing_status = "detecting_fx_breaks"
        
        fx_breaks = []
        
        for match in state.matches:
            trans_a = match.get("transaction_a", {})
            trans_b = match.get("transaction_b", {})
            
            # Check for FX rate discrepancies
            fx_rate_a = trans_a.get("fx_rate")
            fx_rate_b = trans_b.get("fx_rate")
            
            if fx_rate_a and fx_rate_b:
                fx_diff = abs(float(fx_rate_a) - float(fx_rate_b))
                fx_tolerance = max(float(fx_rate_a), float(fx_rate_b)) * 0.005  # 0.5% tolerance
                
                if fx_diff > fx_tolerance:
                    break_info = {
                        "break_type": BreakType.FX_RATE_ERROR.value,
                        "transaction_a": trans_a,
                        "transaction_b": trans_b,
                        "break_details": {
                            "fx_rate_a": fx_rate_a,
                            "fx_rate_b": fx_rate_b,
                            "difference": fx_diff,
                            "tolerance": fx_tolerance,
                            "percentage_diff": fx_diff / max(float(fx_rate_a), float(fx_rate_b)) * 100
                        },
                        "severity": BreakSeverity.HIGH.value,
                        "confidence_score": 0.9
                    }
                    fx_breaks.append(break_info)
        
        state.detected_breaks.extend(fx_breaks)
        logger.info(f"Detected {len(fx_breaks)} FX Rate breaks")
        
        return state

    async def _detect_unmatched(self, state: ExceptionIdentificationState) -> ExceptionIdentificationState:
        """Detect unmatched transactions and create exceptions for them."""
        logger.info("Detecting unmatched transactions...")
        state.processing_status = "detecting_unmatched"

        try:
            matched_ids = set()
            for match in state.matches:
                ta = match.get("transaction_a", {}) or {}
                tb = match.get("transaction_b", {}) or {}
                if ta.get("external_id"):
                    matched_ids.add(ta["external_id"])
                if tb.get("external_id"):
                    matched_ids.add(tb["external_id"])

            unmatched = [t for t in state.transactions if t.get("external_id") not in matched_ids]
            for t in unmatched:
                exception = {
                    "break_type": "unmatched",
                    "transaction_a": t,
                    "transaction_b": {},
                    "break_details": {"description": "Unmatched transaction"},
                    "severity": BreakSeverity.MEDIUM.value,
                    "confidence_score": 0.9,
                }
                state.detected_breaks.append(exception)

            logger.info(f"Detected {len(unmatched)} unmatched transactions")
        except Exception as e:
            logger.warning(f"Failed to detect unmatched transactions: {e}")

        return state
    
    async def _classify_breaks(self, state: ExceptionIdentificationState) -> ExceptionIdentificationState:
        """Classify detected breaks using AI."""
        logger.info("Classifying breaks...")
        logger.info(f"Number of detected breaks to classify: {len(state.detected_breaks)}")
        
        state.processing_status = "classifying_breaks"
        
        classified_breaks = []
        
        for i, break_info in enumerate(state.detected_breaks):
            logger.info(f"Classifying break {i+1}: {break_info.get('break_type')}")
            try:
                # Use AI to enhance classification
                enhanced_break = await self._enhance_break_classification(break_info)
                logger.info(f"Enhanced break {i+1} with AI reasoning: {enhanced_break.get('ai_reasoning')[:50] if enhanced_break.get('ai_reasoning') else 'None'}...")
                classified_breaks.append(enhanced_break)
            except Exception as e:
                logger.error(f"Error classifying break: {e}")
                classified_breaks.append(break_info)
        
        state.classified_breaks = classified_breaks
        logger.info(f"Classified {len(classified_breaks)} breaks")
        
        return state
    
    def _calculate_date_difference(self, date_a: str, date_b: str) -> int:
        """Calculate the difference in days between two date strings."""
        try:
            from datetime import datetime
            if date_a and date_b:
                dt_a = datetime.strptime(date_a, "%Y-%m-%d")
                dt_b = datetime.strptime(date_b, "%Y-%m-%d")
                return abs((dt_b - dt_a).days)
            return 0
        except:
            return 0

    async def _enhance_break_classification(self, break_info: Dict[str, Any]) -> Dict[str, Any]:
        """Use AI to enhance break classification with detailed differences and actionable workflows."""
        prompt = get_prompt_template("break_classification")
        
        messages = [
            SystemMessage(content="You are a financial reconciliation expert."),
            HumanMessage(content=prompt.format(
                transaction_data=json.dumps(break_info, indent=2),
                break_details=json.dumps(break_info.get("break_details", {}), indent=2)
            ))
        ]
        
        llm = self._get_llm()
        if llm is None:
            # If LLM is not available, provide enhanced analysis with differences
            break_type = break_info.get("break_type", "unknown")
            trans_a = break_info.get("transaction_a", {})
            trans_b = break_info.get("transaction_b", {})
            
            if break_type == "fixed_income_coupon":
                # Extract actual differences
                amount_a = float(trans_a.get("amount", 0))
                amount_b = float(trans_b.get("amount", 0))
                difference = abs(amount_a - amount_b)
                
                break_info["ai_reasoning"] = f"Coupon payment discrepancy detected. Expected: ${amount_a:.2f}, Actual: ${amount_b:.2f}, Difference: ${difference:.2f}"
                break_info["ai_suggested_actions"] = ["Verify coupon calculation", "Check payment dates", "Review accrued interest"]
                break_info["detailed_differences"] = {
                    "expected_amount": amount_a,
                    "actual_amount": amount_b,
                    "difference": difference,
                    "difference_percentage": (difference / max(amount_a, amount_b)) * 100 if max(amount_a, amount_b) > 0 else 0,
                    "currency": trans_a.get("currency", "USD"),
                    "security_id": trans_a.get("security_id", "Unknown")
                }
                break_info["workflow_triggers"] = [
                    {
                        "action": "verify_coupon_calculation",
                        "title": "Verify Coupon Calculation",
                        "description": "Review coupon calculation methodology and parameters",
                        "workflow_id": "coupon_verification_workflow",
                        "parameters": {
                            "security_id": trans_a.get("security_id"),
                            "coupon_rate": trans_a.get("coupon_rate"),
                            "payment_date": trans_a.get("payment_date")
                        }
                    },
                    {
                        "action": "check_payment_dates",
                        "title": "Check Payment Dates",
                        "description": "Verify payment date calculations and market conventions",
                        "workflow_id": "date_verification_workflow",
                        "parameters": {
                            "trade_date": trans_a.get("trade_date"),
                            "settlement_date": trans_a.get("settlement_date"),
                            "day_count_convention": trans_a.get("day_count_convention")
                        }
                    }
                ]
                
            elif break_type == "trade_settlement_date":
                # Extract date differences
                trade_date_a = trans_a.get("trade_date")
                trade_date_b = trans_b.get("trade_date")
                settlement_date_a = trans_a.get("settlement_date")
                settlement_date_b = trans_b.get("settlement_date")
                
                break_info["ai_reasoning"] = f"Trade vs settlement date mismatch detected. Trade dates: {trade_date_a} vs {trade_date_b}, Settlement dates: {settlement_date_a} vs {settlement_date_b}"
                break_info["ai_suggested_actions"] = ["Verify trade execution date", "Check settlement date accuracy", "Review market conventions"]
                break_info["detailed_differences"] = {
                    "trade_date_a": trade_date_a,
                    "trade_date_b": trade_date_b,
                    "settlement_date_a": settlement_date_a,
                    "settlement_date_b": settlement_date_b,
                    "trade_date_difference": self._calculate_date_difference(trade_date_a, trade_date_b),
                    "settlement_date_difference": self._calculate_date_difference(settlement_date_a, settlement_date_b)
                }
                break_info["workflow_triggers"] = [
                    {
                        "action": "verify_trade_execution",
                        "title": "Verify Trade Execution",
                        "description": "Review trade execution details and confirm trade date",
                        "workflow_id": "trade_verification_workflow",
                        "parameters": {
                            "trade_id": trans_a.get("external_id"),
                            "execution_time": trans_a.get("execution_time"),
                            "venue": trans_a.get("venue")
                        }
                    },
                    {
                        "action": "check_settlement_cycle",
                        "title": "Check Settlement Cycle",
                        "description": "Verify settlement cycle calculations and market holidays",
                        "workflow_id": "settlement_cycle_workflow",
                        "parameters": {
                            "security_type": trans_a.get("securitytype"),
                            "market": trans_a.get("market"),
                            "settlement_cycle": trans_a.get("settlement_cycle")
                        }
                    }
                ]
                
            elif break_type == "security_id_break":
                # Extract security ID differences
                break_details = break_info.get("break_details", {})
                mismatch_type = break_details.get("mismatch_type", "unknown")
                
                if mismatch_type == "sedol":
                    sedol_a = break_details.get("sedol_a", "Unknown")
                    sedol_b = break_details.get("sedol_b", "Unknown")
                    
                    break_info["ai_reasoning"] = f"Security ID mismatch detected. SEDOL A: {sedol_a}, SEDOL B: {sedol_b}. This indicates different security identifiers being used by transacting parties."
                    break_info["ai_suggested_actions"] = ["Verify security identifier mapping", "Check identifier database", "Contact counterparty for clarification"]
                    break_info["detailed_differences"] = {
                        "identifier_type": "SEDOL",
                        "identifier_a": sedol_a,
                        "identifier_b": sedol_b,
                        "difference": f"{sedol_a} vs {sedol_b}",
                        "security_name": trans_a.get("security_name", "Unknown"),
                        "transaction_id": trans_a.get("external_id", "Unknown")
                    }
                else:
                    security_id_a = break_details.get("security_id_a", "Unknown")
                    security_id_b = break_details.get("security_id_b", "Unknown")
                    
                    break_info["ai_reasoning"] = f"Security ID mismatch detected. Security ID A: {security_id_a}, Security ID B: {security_id_b}. This indicates different security identifiers being used by transacting parties."
                    break_info["ai_suggested_actions"] = ["Verify security identifier mapping", "Check identifier database", "Contact counterparty for clarification"]
                    break_info["detailed_differences"] = {
                        "identifier_type": "Security ID",
                        "identifier_a": security_id_a,
                        "identifier_b": security_id_b,
                        "difference": f"{security_id_a} vs {security_id_b}",
                        "security_name": trans_a.get("security_name", "Unknown"),
                        "transaction_id": trans_a.get("external_id", "Unknown")
                    }
                
                break_info["workflow_triggers"] = [
                    {
                        "action": "verify_security_mapping",
                        "title": "Verify Security Mapping",
                        "description": "Check security identifier mapping and database accuracy",
                        "workflow_id": "security_mapping_workflow",
                        "parameters": {
                            "security_name": trans_a.get("security_name"),
                            "identifier_type": mismatch_type,
                            "identifier_a": break_details.get(f"{mismatch_type}_a"),
                            "identifier_b": break_details.get(f"{mismatch_type}_b")
                        }
                    },
                    {
                        "action": "contact_counterparty",
                        "title": "Contact Counterparty",
                        "description": "Contact counterparty to clarify security identifier discrepancy",
                        "workflow_id": "counterparty_contact_workflow",
                        "parameters": {
                            "counterparty": trans_a.get("counterparty"),
                            "trade_id": trans_a.get("external_id"),
                            "issue_type": "security_identifier_mismatch"
                        }
                    }
                ]
                
            elif break_type == "market_price_difference":
                # Extract price differences
                price_a = float(trans_a.get("market_price", 0))
                price_b = float(trans_b.get("market_price", 0))
                difference = abs(price_a - price_b)
                percentage_diff = (difference / max(price_a, price_b)) * 100 if max(price_a, price_b) > 0 else 0
                
                break_info["ai_reasoning"] = f"Market price difference detected. Price A: ${price_a:.6f}, Price B: ${price_b:.6f}, Difference: ${difference:.6f} ({percentage_diff:.2f}%)"
                break_info["ai_suggested_actions"] = ["Verify price source accuracy", "Check price timestamp", "Review market data quality"]
                break_info["detailed_differences"] = {
                    "price_a": price_a,
                    "price_b": price_b,
                    "difference": difference,
                    "difference_percentage": percentage_diff,
                    "currency": trans_a.get("currency", "USD"),
                    "security_id": trans_a.get("security_id", "Unknown"),
                    "price_source_a": trans_a.get("price_source", "Unknown"),
                    "price_source_b": trans_b.get("price_source", "Unknown")
                }
                break_info["workflow_triggers"] = [
                    {
                        "action": "verify_price_source",
                        "title": "Verify Price Source",
                        "description": "Check price source accuracy and data quality",
                        "workflow_id": "price_verification_workflow",
                        "parameters": {
                            "security_id": trans_a.get("security_id"),
                            "price_source": trans_a.get("price_source"),
                            "timestamp": trans_a.get("price_timestamp")
                        }
                    },
                    {
                        "action": "check_market_data",
                        "title": "Check Market Data",
                        "description": "Review market data quality and timeliness",
                        "workflow_id": "market_data_workflow",
                        "parameters": {
                            "market": trans_a.get("market"),
                            "data_provider": trans_a.get("data_provider"),
                            "update_frequency": trans_a.get("update_frequency")
                        }
                    }
                ]
                
            elif break_type == "fx_rate_error":
                # Extract FX rate differences
                fx_rate_a = float(trans_a.get("fx_rate", 1.0))
                fx_rate_b = float(trans_b.get("fx_rate", 1.0))
                market_value_a = float(trans_a.get("market_value", 0))
                market_value_b = float(trans_b.get("market_value", 0))
                
                fx_diff = abs(fx_rate_a - fx_rate_b)
                fx_percentage_diff = (fx_diff / max(fx_rate_a, fx_rate_b)) * 100 if max(fx_rate_a, fx_rate_b) > 0 else 0
                
                break_info["ai_reasoning"] = f"FX rate error detected. FX Rate A: {fx_rate_a:.4f}, FX Rate B: {fx_rate_b:.4f}, Difference: {fx_diff:.4f} ({fx_percentage_diff:.2f}%). Market Value A: ${market_value_a:.2f}, Market Value B: ${market_value_b:.2f}"
                break_info["ai_suggested_actions"] = ["Verify FX rate source", "Check rate timestamp", "Review currency conversion logic"]
                break_info["detailed_differences"] = {
                    "fx_rate_a": fx_rate_a,
                    "fx_rate_b": fx_rate_b,
                    "fx_rate_difference": fx_diff,
                    "fx_rate_percentage_diff": fx_percentage_diff,
                    "market_value_a": market_value_a,
                    "market_value_b": market_value_b,
                    "market_value_difference": abs(market_value_a - market_value_b),
                    "currency": trans_a.get("currency", "USD"),
                    "fx_currency": trans_a.get("fx_currency", "USD")
                }
                break_info["workflow_triggers"] = [
                    {
                        "action": "verify_fx_rate",
                        "title": "Verify FX Rate",
                        "description": "Check FX rate source accuracy and timeliness",
                        "workflow_id": "fx_rate_verification_workflow",
                        "parameters": {
                            "currency_pair": f"{trans_a.get('currency', 'USD')}/{trans_a.get('fx_currency', 'USD')}",
                            "fx_rate_source": trans_a.get("fx_rate_source"),
                            "rate_timestamp": trans_a.get("rate_timestamp")
                        }
                    },
                    {
                        "action": "check_currency_conversion",
                        "title": "Check Currency Conversion",
                        "description": "Review currency conversion logic and calculations",
                        "workflow_id": "currency_conversion_workflow",
                        "parameters": {
                            "base_currency": trans_a.get("currency"),
                            "quote_currency": trans_a.get("fx_currency"),
                            "conversion_method": trans_a.get("conversion_method")
                        }
                    }
                ]
                
            else:
                break_info["ai_reasoning"] = f"{break_type.replace('_', ' ').title()} break detected. Manual review required."
                break_info["ai_suggested_actions"] = ["Review transaction details", "Verify data accuracy", "Contact counterparty if needed"]
                break_info["detailed_differences"] = {
                    "break_type": break_type,
                    "transaction_a": trans_a,
                    "transaction_b": trans_b
                }
                break_info["workflow_triggers"] = [
                    {
                        "action": "manual_review",
                        "title": "Manual Review Required",
                        "description": "This break requires manual review and resolution",
                        "workflow_id": "manual_review_workflow",
                        "parameters": {
                            "break_type": break_type,
                            "severity": break_info.get("severity", "medium")
                        }
                    }
                ]
            return break_info
            
        response = await llm.ainvoke(messages)
        try:
            # Parse AI response for enhanced classification
            content = response.content.lower()
            if "confidence score:" in content:
                confidence_text = content.split("confidence score:")[1].split("\n")[0].strip()
                try:
                    confidence = float(confidence_text)
                    break_info["confidence_score"] = confidence
                except:
                    pass
            if "suggested resolution:" in content:
                resolution_text = content.split("suggested resolution:")[1].strip()
                break_info["suggested_resolution"] = resolution_text
                
            # Set AI reasoning and suggested actions with detailed differences
            break_type = break_info.get("break_type", "unknown")
            trans_a = break_info.get("transaction_a", {})
            trans_b = break_info.get("transaction_b", {})
            
            if break_type == "fixed_income_coupon":
                amount_a = float(trans_a.get("amount", 0))
                amount_b = float(trans_b.get("amount", 0))
                difference = abs(amount_a - amount_b)
                
                break_info["ai_reasoning"] = f"Coupon payment discrepancy detected. Expected: ${amount_a:.2f}, Actual: ${amount_b:.2f}, Difference: ${difference:.2f}"
                break_info["ai_suggested_actions"] = ["Verify coupon calculation", "Check payment dates", "Review accrued interest"]
                break_info["detailed_differences"] = {
                    "expected_amount": amount_a,
                    "actual_amount": amount_b,
                    "difference": difference,
                    "difference_percentage": (difference / max(amount_a, amount_b)) * 100 if max(amount_a, amount_b) > 0 else 0,
                    "currency": trans_a.get("currency", "USD"),
                    "security_id": trans_a.get("security_id", "Unknown")
                }
                break_info["workflow_triggers"] = [
                    {
                        "action": "verify_coupon_calculation",
                        "title": "Verify Coupon Calculation",
                        "description": "Review coupon calculation methodology and parameters",
                        "workflow_id": "coupon_verification_workflow",
                        "parameters": {
                            "security_id": trans_a.get("security_id"),
                            "coupon_rate": trans_a.get("coupon_rate"),
                            "payment_date": trans_a.get("payment_date")
                        }
                    },
                    {
                        "action": "check_payment_dates",
                        "title": "Check Payment Dates",
                        "description": "Verify payment date calculations and market conventions",
                        "workflow_id": "date_verification_workflow",
                        "parameters": {
                            "trade_date": trans_a.get("trade_date"),
                            "settlement_date": trans_a.get("settlement_date"),
                            "day_count_convention": trans_a.get("day_count_convention")
                        }
                    }
                ]
                
            elif break_type == "trade_settlement_date":
                trade_date_a = trans_a.get("trade_date")
                trade_date_b = trans_b.get("trade_date")
                settlement_date_a = trans_a.get("settlement_date")
                settlement_date_b = trans_b.get("settlement_date")
                
                break_info["ai_reasoning"] = f"Trade vs settlement date mismatch detected. Trade dates: {trade_date_a} vs {trade_date_b}, Settlement dates: {settlement_date_a} vs {settlement_date_b}"
                break_info["ai_suggested_actions"] = ["Verify trade execution date", "Check settlement date accuracy", "Review market conventions"]
                break_info["detailed_differences"] = {
                    "trade_date_a": trade_date_a,
                    "trade_date_b": trade_date_b,
                    "settlement_date_a": settlement_date_a,
                    "settlement_date_b": settlement_date_b,
                    "trade_date_difference": self._calculate_date_difference(trade_date_a, trade_date_b),
                    "settlement_date_difference": self._calculate_date_difference(settlement_date_a, settlement_date_b)
                }
                break_info["workflow_triggers"] = [
                    {
                        "action": "verify_trade_execution",
                        "title": "Verify Trade Execution",
                        "description": "Review trade execution details and confirm trade date",
                        "workflow_id": "trade_verification_workflow",
                        "parameters": {
                            "trade_id": trans_a.get("external_id"),
                            "execution_time": trans_a.get("execution_time"),
                            "venue": trans_a.get("venue")
                        }
                    },
                    {
                        "action": "check_settlement_cycle",
                        "title": "Check Settlement Cycle",
                        "description": "Verify settlement cycle calculations and market holidays",
                        "workflow_id": "settlement_cycle_workflow",
                        "parameters": {
                            "security_type": trans_a.get("securitytype"),
                            "market": trans_a.get("market"),
                            "settlement_cycle": trans_a.get("settlement_cycle")
                        }
                    }
                ]
                
            elif break_type == "market_price_difference":
                price_a = float(trans_a.get("market_price", 0))
                price_b = float(trans_b.get("market_price", 0))
                difference = abs(price_a - price_b)
                percentage_diff = (difference / max(price_a, price_b)) * 100 if max(price_a, price_b) > 0 else 0
                
                break_info["ai_reasoning"] = f"Market price difference detected. Price A: ${price_a:.6f}, Price B: ${price_b:.6f}, Difference: ${difference:.6f} ({percentage_diff:.2f}%)"
                break_info["ai_suggested_actions"] = ["Verify price source accuracy", "Check price timestamp", "Review market data quality"]
                break_info["detailed_differences"] = {
                    "price_a": price_a,
                    "price_b": price_b,
                    "difference": difference,
                    "difference_percentage": percentage_diff,
                    "currency": trans_a.get("currency", "USD"),
                    "security_id": trans_a.get("security_id", "Unknown"),
                    "price_source_a": trans_a.get("price_source", "Unknown"),
                    "price_source_b": trans_b.get("price_source", "Unknown")
                }
                break_info["workflow_triggers"] = [
                    {
                        "action": "verify_price_source",
                        "title": "Verify Price Source",
                        "description": "Check price source accuracy and data quality",
                        "workflow_id": "price_verification_workflow",
                        "parameters": {
                            "security_id": trans_a.get("security_id"),
                            "price_source": trans_a.get("price_source"),
                            "timestamp": trans_a.get("price_timestamp")
                        }
                    },
                    {
                        "action": "check_market_data",
                        "title": "Check Market Data",
                        "description": "Review market data quality and timeliness",
                        "workflow_id": "market_data_workflow",
                        "parameters": {
                            "market": trans_a.get("market"),
                            "data_provider": trans_a.get("data_provider"),
                            "update_frequency": trans_a.get("update_frequency")
                        }
                    }
                ]
                
            else:
                break_info["ai_reasoning"] = f"{break_type.replace('_', ' ').title()} break detected. Manual review required."
                break_info["ai_suggested_actions"] = ["Review transaction details", "Verify data accuracy", "Contact counterparty if needed"]
                break_info["detailed_differences"] = {
                    "break_type": break_type,
                    "transaction_a": trans_a,
                    "transaction_b": trans_b
                }
                break_info["workflow_triggers"] = [
                    {
                        "action": "manual_review",
                        "title": "Manual Review Required",
                        "description": "This break requires manual review and resolution",
                        "workflow_id": "manual_review_workflow",
                        "parameters": {
                            "break_type": break_type,
                            "severity": break_info.get("severity", "medium")
                        }
                    }
                ]
                
            return break_info
        except Exception as e:
            logger.warning(f"Failed to enhance break classification: {e}")
            # Fallback to basic analysis with differences
            break_type = break_info.get("break_type", "unknown")
            trans_a = break_info.get("transaction_a", {})
            trans_b = break_info.get("transaction_b", {})
            
            if break_type == "fixed_income_coupon":
                amount_a = float(trans_a.get("amount", 0))
                amount_b = float(trans_b.get("amount", 0))
                difference = abs(amount_a - amount_b)
                
                break_info["ai_reasoning"] = f"Coupon payment discrepancy detected. Expected: ${amount_a:.2f}, Actual: ${amount_b:.2f}, Difference: ${difference:.2f}"
                break_info["ai_suggested_actions"] = ["Verify coupon calculation", "Check payment dates", "Review accrued interest"]
                break_info["detailed_differences"] = {
                    "expected_amount": amount_a,
                    "actual_amount": amount_b,
                    "difference": difference,
                    "difference_percentage": (difference / max(amount_a, amount_b)) * 100 if max(amount_a, amount_b) > 0 else 0,
                    "currency": trans_a.get("currency", "USD"),
                    "security_id": trans_a.get("security_id", "Unknown")
                }
                break_info["workflow_triggers"] = [
                    {
                        "action": "verify_coupon_calculation",
                        "title": "Verify Coupon Calculation",
                        "description": "Review coupon calculation methodology and parameters",
                        "workflow_id": "coupon_verification_workflow",
                        "parameters": {
                            "security_id": trans_a.get("security_id"),
                            "coupon_rate": trans_a.get("coupon_rate"),
                            "payment_date": trans_a.get("payment_date")
                        }
                    }
                ]
            else:
                break_info["ai_reasoning"] = f"{break_type.replace('_', ' ').title()} break detected. Manual review required."
                break_info["ai_suggested_actions"] = ["Review transaction details", "Verify data accuracy", "Contact counterparty if needed"]
                break_info["detailed_differences"] = {
                    "break_type": break_type,
                    "transaction_a": trans_a,
                    "transaction_b": trans_b
                }
                break_info["workflow_triggers"] = [
                    {
                        "action": "manual_review",
                        "title": "Manual Review Required",
                        "description": "This break requires manual review and resolution",
                        "workflow_id": "manual_review_workflow",
                        "parameters": {
                            "break_type": break_type,
                            "severity": break_info.get("severity", "medium")
                        }
                    }
                ]
            return break_info
    
    async def _validate_exceptions(self, state: ExceptionIdentificationState) -> ExceptionIdentificationState:
        """Validate detected exceptions."""
        logger.info("Validating exceptions...")
        
        state.processing_status = "validating"
        
        valid_exceptions = []
        
        for break_info in state.classified_breaks:
            try:
                # Validate break structure
                if not break_info.get("break_type"):
                    state.validation_errors.append("Missing break type")
                    continue
                
                if not break_info.get("transaction_a") or not break_info.get("transaction_b"):
                    state.validation_errors.append("Missing transaction data")
                    continue
                
                # Validate break type
                if break_info["break_type"] not in [bt.value for bt in BreakType]:
                    state.validation_errors.append(f"Invalid break type: {break_info['break_type']}")
                    continue
                
                # Create exception object
                exception = {
                    "break_type": break_info["break_type"],
                    "transaction_a": break_info["transaction_a"],
                    "transaction_b": break_info["transaction_b"],
                    "break_details": break_info.get("break_details", {}),
                    "severity": break_info.get("severity", BreakSeverity.MEDIUM.value),
                    "confidence_score": break_info.get("confidence_score", 0.5),
                    "suggested_resolution": break_info.get("suggested_resolution", ""),
                    "status": BreakStatus.OPEN.value
                }
                
                valid_exceptions.append(exception)
                
            except Exception as e:
                logger.error(f"Error validating exception: {e}")
                state.validation_errors.append(f"Validation error: {str(e)}")
        
        state.reconciliation_exceptions = valid_exceptions
        logger.info(f"Validated {len(valid_exceptions)} exceptions")
        
        return state
    
    async def _store_exceptions(self, state: ExceptionIdentificationState) -> ExceptionIdentificationState:
        """Store validated exceptions in database."""
        logger.info("Storing exceptions...")
        
        state.processing_status = "storing"
        
        # Use classified_breaks (enhanced exceptions) if available, otherwise fall back to reconciliation_exceptions
        exceptions_to_store = state.classified_breaks if state.classified_breaks else state.reconciliation_exceptions
        
        if not exceptions_to_store:
            state.validation_errors.append("No exceptions to store")
            state.processing_status = "failed"
            return state
        
        logger.info(f"Storing {len(exceptions_to_store)} exceptions (enhanced: {bool(state.classified_breaks)})")
        
        try:
            async with get_db_session() as session:
                from sqlalchemy import select
                from src.core.models.data_models.transaction import Transaction as TransactionModel
                from src.core.models.break_types.reconciliation_break import ReconciliationException as ReconciliationExceptionModel

                stored_count = 0
                for exception in exceptions_to_store:
                    trans_a = exception.get("transaction_a", {}) or {}
                    trans_b = exception.get("transaction_b", {}) or {}
                    # Prefer linking to transaction A; fallback to B
                    external_id = trans_a.get("external_id") or trans_b.get("external_id")
                    if not external_id:
                        continue
                    # Lookup transaction id by external_id
                    res = await session.execute(select(TransactionModel).where(TransactionModel.external_id == external_id))
                    tx_model = res.scalar_one_or_none()
                    if tx_model is None:
                        continue

                    # Handle break_amount based on break type
                    break_details = exception.get("break_details", {}) or {}
                    break_amount = None
                    
                    if exception.get("break_type") == "security_id_break":
                        # For security ID breaks, don't set break_amount (it's a string)
                        break_amount = None
                    elif exception.get("break_type") == "market_price_difference":
                        break_amount = break_details.get("difference")
                    elif exception.get("break_type") == "fixed_income_coupon":
                        break_amount = break_details.get("difference")
                    elif exception.get("break_type") == "fx_rate_error":
                        break_amount = break_details.get("difference")
                    else:
                        # For other break types, try to get numeric difference
                        diff = break_details.get("difference")
                        if isinstance(diff, (int, float)):
                            break_amount = diff
                    
                    model = ReconciliationExceptionModel(
                        transaction_id=tx_model.id,
                        break_type=exception.get("break_type"),
                        severity=exception.get("severity"),
                        status=exception.get("status"),
                        description=(exception.get("break_details", {}) or {}).get("description"),
                        break_amount=break_amount,
                        break_currency=(trans_a.get("currency") or trans_b.get("currency")),
                        ai_confidence_score=exception.get("confidence_score"),
                        ai_reasoning=exception.get("ai_reasoning"),
                        ai_suggested_actions=exception.get("ai_suggested_actions"),
                        detailed_differences=exception.get("detailed_differences"),
                        workflow_triggers=exception.get("workflow_triggers"),
                    )
                    session.add(model)
                    stored_count += 1

                await session.commit()
                logger.info(f"Stored {stored_count} exceptions")

        except Exception as e:
            logger.error(f"Error storing exceptions: {e}")
            state.validation_errors.append(f"Storage error: {str(e)}")
            state.processing_status = "failed"
        
        return state
    
    async def _generate_summary(self, state: ExceptionIdentificationState) -> ExceptionIdentificationState:
        """Generate exception identification summary."""
        logger.info("Generating exception identification summary...")
        
        state.end_time = datetime.utcnow()
        if state.start_time:
            state.processing_time_ms = int((state.end_time - state.start_time).total_seconds() * 1000)
        
        # Count breaks by type
        break_counts = {}
        for exception in state.reconciliation_exceptions:
            break_type = exception["break_type"]
            break_counts[break_type] = break_counts.get(break_type, 0) + 1
        
        state.summary = {
            "total_transactions": len(state.transactions),
            "total_matches": len(state.matches),
            "total_breaks": len(state.reconciliation_exceptions),
            "break_counts": break_counts,
            "validation_errors": len(state.validation_errors),
            "processing_time_ms": state.processing_time_ms,
            "break_rate": len(state.reconciliation_exceptions) / len(state.matches) if state.matches else 0,
            "status": "completed" if not state.validation_errors else "completed_with_errors"
        }
        
        state.processing_status = "completed"
        
        logger.info(f"Exception identification completed: {state.summary}")
        
        return state
    
    async def identify_exceptions(self, transactions: List[Dict[str, Any]], matches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Identify exceptions in matched transactions."""
        session_id = str(uuid.uuid4())
        audit_logger = get_audit_logger()
        start_time = datetime.utcnow()
        
        logger.info(f"=== EXCEPTION IDENTIFICATION START ===")
        logger.info(f"Identifying exceptions in {len(transactions)} transactions with {len(matches)} matches")
        logger.info(f"Session ID: {session_id}")
        
        # Log agent start
        await audit_logger.log_agent_start(
            agent_name="exception_identification",
            session_id=session_id,
            input_data={
                "transactions_count": len(transactions),
                "matches_count": len(matches)
            }
        )
        
        # Initialize state
        state = ExceptionIdentificationState(
            transactions=transactions,
            matches=matches
        )
        
        # Run workflow
        try:
            logger.info("Starting exception identification workflow...")
            final_state = await self._get_workflow().ainvoke(state)
            logger.info(f"Workflow completed. Final state type: {type(final_state)}")
            logger.info(f"Final state has reconciliation_exceptions: {hasattr(final_state, 'reconciliation_exceptions')}")
            if hasattr(final_state, 'reconciliation_exceptions'):
                logger.info(f"Number of exceptions: {len(final_state.reconciliation_exceptions)}")
            elif isinstance(final_state, dict):
                logger.info(f"Final state is dict, exceptions: {len(final_state.get('reconciliation_exceptions', []))}")
            
            # Get the enhanced exceptions from the workflow result
            enhanced_exceptions = []
            reconciliation_exceptions = final_state.reconciliation_exceptions if hasattr(final_state, 'reconciliation_exceptions') else final_state.get('reconciliation_exceptions', [])
            
            # Debug: Log what we received from the workflow
            logger.info(f"Workflow returned {len(reconciliation_exceptions)} exceptions")
            if reconciliation_exceptions:
                logger.info(f"First exception keys: {list(reconciliation_exceptions[0].keys())}")
                logger.info(f"First exception has ai_reasoning: {reconciliation_exceptions[0].get('ai_reasoning') is not None}")
            
            # Check if we have classified_breaks in the state (from workflow) - this is where enhanced exceptions are stored
            classified_breaks = final_state.classified_breaks if hasattr(final_state, 'classified_breaks') else final_state.get('classified_breaks', [])
            logger.info(f"Classified breaks available: {len(classified_breaks) if classified_breaks else 0}")
            
            if classified_breaks and any(break_info.get('ai_reasoning') for break_info in classified_breaks):
                enhanced_exceptions = classified_breaks
                logger.info(f"Using {len(enhanced_exceptions)} enhanced exceptions from classified_breaks")
                # Update the state with enhanced exceptions so they get stored
                state.reconciliation_exceptions = enhanced_exceptions
            elif reconciliation_exceptions and any(exception.get('ai_reasoning') for exception in reconciliation_exceptions):
                enhanced_exceptions = reconciliation_exceptions
                logger.info(f"Using {len(enhanced_exceptions)} enhanced exceptions from workflow")
                # Update the state with enhanced exceptions so they get stored
                state.reconciliation_exceptions = enhanced_exceptions
            else:
                # Fallback to original exceptions and enhance them
                logger.info("Enhancing exceptions manually")
                for exception in reconciliation_exceptions:
                        enhanced_exception = exception.copy()
                        
                        # Add enhanced analysis if not already present
                        if not enhanced_exception.get("ai_reasoning"):
                            break_type = enhanced_exception.get("break_type")
                            if break_type == "market_price_difference":
                                # Generate price break analysis
                                trans_a = enhanced_exception.get("transaction_a", {})
                                trans_b = enhanced_exception.get("transaction_b", {})
                                break_details = enhanced_exception.get("break_details", {})
                                
                                if trans_a.get("market_price") and trans_b.get("market_price"):
                                    price_a = float(trans_a["market_price"])
                                    price_b = float(trans_b["market_price"])
                                    price_diff = abs(price_a - price_b)
                                    percentage_diff = price_diff / max(price_a, price_b) * 100
                                    
                                    analysis = await self._analyze_price_break(trans_a, trans_b, price_a, price_b, price_diff, percentage_diff)
                                    enhanced_exception["ai_reasoning"] = analysis.get("reasoning")
                                    enhanced_exception["ai_suggested_actions"] = analysis.get("recommendations")
                            
                            elif break_type == "fixed_income_coupon":
                                # Generate coupon break analysis
                                trans_a = enhanced_exception.get("transaction_a", {})
                                trans_b = enhanced_exception.get("transaction_b", {})
                                break_details = enhanced_exception.get("break_details", {})
                                
                                if trans_a.get("amount") and trans_b.get("amount"):
                                    amount_a = float(trans_a["amount"])
                                    amount_b = float(trans_b["amount"])
                                    
                                    analysis = await self._analyze_coupon_break_detailed(trans_a, trans_b, amount_a, amount_b)
                                    enhanced_exception["ai_reasoning"] = analysis.get("reasoning")
                                    enhanced_exception["ai_suggested_actions"] = analysis.get("recommendations")
                        
                        enhanced_exceptions.append(enhanced_exception)
            
            # Calculate processing time
            end_time = datetime.utcnow()
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            result = {
                "success": True,
                "summary": final_state.summary if hasattr(final_state, 'summary') else final_state.get('summary', {}),
                "exceptions": enhanced_exceptions,
                "errors": final_state.validation_errors if hasattr(final_state, 'validation_errors') else final_state.get('validation_errors', [])
            }
            
            # Log agent completion
            await audit_logger.log_agent_completion(
                agent_name="exception_identification",
                session_id=session_id,
                result_data=final_state.summary if hasattr(final_state, 'summary') else final_state.get('summary', {}),
                processing_time_ms=processing_time_ms,
                is_successful=True
            )
            
            logger.info(f"=== EXCEPTION IDENTIFICATION COMPLETED SUCCESSFULLY ===")
            logger.info(f"Returning {len(enhanced_exceptions)} exceptions")
            return result
        except Exception as e:
            logger.error(f"=== EXCEPTION IDENTIFICATION FAILED ===")
            logger.error(f"Exception identification workflow failed: {e}")
            # Ensure we have a summary even if workflow fails
            if not state.summary:
                state.summary = {
                    "total_transactions": len(state.transactions),
                    "total_matches": len(state.matches),
                    "total_breaks": len(state.reconciliation_exceptions),
                    "break_counts": {},
                    "validation_errors": len(state.validation_errors) + 1,
                    "processing_time_ms": 0,
                    "break_rate": 0,
                    "status": "failed"
                }
            
            # Ensure enhanced analysis is added to exceptions even if workflow fails
            enhanced_exceptions = []
            for exception in state.reconciliation_exceptions:
                enhanced_exception = exception.copy()
                
                # Add enhanced analysis if not already present
                if not enhanced_exception.get("ai_reasoning"):
                    break_type = enhanced_exception.get("break_type")
                    if break_type == "market_price_difference":
                        # Generate price break analysis
                        trans_a = enhanced_exception.get("transaction_a", {})
                        trans_b = enhanced_exception.get("transaction_b", {})
                        break_details = enhanced_exception.get("break_details", {})
                        
                        if trans_a.get("market_price") and trans_b.get("market_price"):
                            price_a = float(trans_a["market_price"])
                            price_b = float(trans_b["market_price"])
                            price_diff = abs(price_a - price_b)
                            percentage_diff = price_diff / max(price_a, price_b) * 100
                            
                            analysis = await self._analyze_price_break(trans_a, trans_b, price_a, price_b, price_diff, percentage_diff)
                            enhanced_exception["ai_reasoning"] = analysis.get("reasoning")
                            enhanced_exception["ai_suggested_actions"] = analysis.get("recommendations")
                    
                    elif break_type == "fixed_income_coupon":
                        # Generate coupon break analysis
                        trans_a = enhanced_exception.get("transaction_a", {})
                        trans_b = enhanced_exception.get("transaction_b", {})
                        break_details = enhanced_exception.get("break_details", {})
                        
                        if trans_a.get("amount") and trans_b.get("amount"):
                            amount_a = float(trans_a["amount"])
                            amount_b = float(trans_b["amount"])
                            
                            analysis = await self._analyze_coupon_break_detailed(trans_a, trans_b, amount_a, amount_b)
                            enhanced_exception["ai_reasoning"] = analysis.get("reasoning")
                            enhanced_exception["ai_suggested_actions"] = analysis.get("recommendations")
                
                enhanced_exceptions.append(enhanced_exception)
            
            # Calculate processing time
            end_time = datetime.utcnow()
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            result = {
                "success": False,
                "error": str(e),
                "summary": state.summary,
                "exceptions": enhanced_exceptions,
                "errors": state.validation_errors + [str(e)]
            }
            
            # Log agent failure
            await audit_logger.log_agent_completion(
                agent_name="exception_identification",
                session_id=session_id,
                result_data=state.summary,
                processing_time_ms=processing_time_ms,
                is_successful=False,
                error_message=str(e)
            )
            
            return result


# Lazy initialization function
_exception_identification_agent = None

def get_exception_identification_agent():
    """Get or create the exception identification agent instance."""
    global _exception_identification_agent
    if _exception_identification_agent is None:
        _exception_identification_agent = ExceptionIdentificationAgent()
    return _exception_identification_agent


async def identify_reconciliation_exceptions(transactions: List[Dict[str, Any]], matches: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Identify reconciliation exceptions using the exception identification agent."""
    agent = get_exception_identification_agent()
    return await agent.identify_exceptions(transactions, matches) 