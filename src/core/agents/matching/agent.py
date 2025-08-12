"""
Matching Engine Agent for FS Reconciliation Agents.

This module implements the matching engine agent using LangGraph framework
to perform deterministic and probabilistic matching of financial transactions
across different data sources.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Tuple
from decimal import Decimal
import json
import hashlib
import uuid

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.core.services.data_services.config_service import (
    get_openai_config,
    get_agent_config,
    get_prompt_template
)
from src.core.models.data_models.transaction import Transaction, TransactionMatch
from src.core.services.data_services.database import get_db_session
from src.core.utils.audit_logger import get_audit_logger

logger = logging.getLogger(__name__)


class MatchingState(BaseModel):
    """State for matching engine workflow."""
    
    # Input data
    transactions_a: List[Dict[str, Any]] = Field(default_factory=list)
    transactions_b: List[Dict[str, Any]] = Field(default_factory=list)
    matching_rules: Dict[str, Any] = Field(default_factory=dict)
    
    # Processing state
    deterministic_matches: List[Dict[str, Any]] = Field(default_factory=list)
    probabilistic_matches: List[Dict[str, Any]] = Field(default_factory=list)
    unmatched_transactions: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    matching_errors: List[str] = Field(default_factory=list)
    processing_status: str = "pending"
    
    # Output data
    final_matches: List[Dict[str, Any]] = Field(default_factory=list)
    summary: Dict[str, Any] = Field(default_factory=dict)
    
    # Metadata
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    processing_time_ms: Optional[int] = None


class MatchingEngineAgent:
    """Matching Engine Agent using LangGraph."""
    
    def __init__(self):
        """Initialize the matching engine agent."""
        self.config = get_agent_config("matching_engine")
        self.openai_config = get_openai_config()
        
        # Initialize lazily
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
                max_tokens=self.config.get("max_tokens", 2000),
                api_key=api_key
            )
        return self.llm
    
    def _get_workflow(self):
        """Get or create the workflow instance."""
        if self.workflow is None:
            self.workflow = self._create_workflow()
        return self.workflow
    
    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow for matching."""
        
        # Create state graph
        workflow = StateGraph(MatchingState)
        
        # Add nodes
        workflow.add_node("validate_input", self._validate_input)
        workflow.add_node("deterministic_matching", self._deterministic_matching)
        workflow.add_node("probabilistic_matching", self._probabilistic_matching)
        workflow.add_node("ai_enhanced_matching", self._ai_enhanced_matching)
        workflow.add_node("validate_matches", self._validate_matches)
        workflow.add_node("store_matches", self._store_matches)
        workflow.add_node("generate_summary", self._generate_summary)
        
        # Define edges
        workflow.set_entry_point("validate_input")
        workflow.add_edge("validate_input", "deterministic_matching")
        workflow.add_edge("deterministic_matching", "probabilistic_matching")
        workflow.add_edge("probabilistic_matching", "ai_enhanced_matching")
        workflow.add_edge("ai_enhanced_matching", "validate_matches")
        workflow.add_edge("validate_matches", "store_matches")
        workflow.add_edge("store_matches", "generate_summary")
        workflow.add_edge("generate_summary", END)
        
        return workflow.compile()
    
    async def _validate_input(self, state: MatchingState) -> MatchingState:
        """Validate input data for matching."""
        logger.info("Validating input data for matching...")
        
        state.start_time = datetime.utcnow()
        state.processing_status = "validating"
        
        if not state.transactions_a or not state.transactions_b:
            state.matching_errors.append("Both transaction lists must be provided")
            state.processing_status = "failed"
            return state
        
        # Validate required fields for matching
        required_fields = ["external_id", "amount", "currency"]
        for i, transaction in enumerate(state.transactions_a):
            missing_fields = [field for field in required_fields if field not in transaction]
            if missing_fields:
                state.matching_errors.append(
                    f"Transaction A {i}: Missing required fields: {missing_fields}"
                )
        
        for i, transaction in enumerate(state.transactions_b):
            missing_fields = [field for field in required_fields if field not in transaction]
            if missing_fields:
                state.matching_errors.append(
                    f"Transaction B {i}: Missing required fields: {missing_fields}"
                )
        
        logger.info(f"Validated {len(state.transactions_a)} and {len(state.transactions_b)} transactions")
        return state
    
    async def _deterministic_matching(self, state: MatchingState) -> MatchingState:
        """Perform deterministic matching based on exact field matches."""
        logger.info("Performing deterministic matching...")
        
        state.processing_status = "deterministic_matching"
        
        matches = []
        matched_a = set()
        matched_b = set()
        
        for i, trans_a in enumerate(state.transactions_a):
            for j, trans_b in enumerate(state.transactions_b):
                if i in matched_a or j in matched_b:
                    continue
                
                # Check for exact matches
                if self._is_exact_match(trans_a, trans_b):
                    match = {
                        "transaction_a": trans_a,
                        "transaction_b": trans_b,
                        "match_type": "deterministic",
                        "confidence_score": 1.0,
                        "matching_criteria": ["exact_match"],
                        "match_reason": "Exact field match"
                    }
                    matches.append(match)
                    matched_a.add(i)
                    matched_b.add(j)
        
        state.deterministic_matches = matches
        logger.info(f"Found {len(matches)} deterministic matches")
        
        return state
    
    def _is_exact_match(self, trans_a: Dict[str, Any], trans_b: Dict[str, Any]) -> bool:
        """Check if two transactions are an exact match."""
        # Check external ID match
        if (trans_a.get("external_id") and trans_b.get("external_id") and
            trans_a["external_id"] == trans_b["external_id"]):
            return True
        
        # Check amount and currency match
        if (trans_a.get("amount") and trans_b.get("amount") and
            trans_a.get("currency") and trans_b.get("currency") and
            abs(float(trans_a["amount"]) - float(trans_b["amount"])) < 0.01 and
            trans_a["currency"] == trans_b["currency"]):
            
            # Additional checks for security and dates
            if (trans_a.get("security_id") and trans_b.get("security_id") and
                trans_a["security_id"] == trans_b["security_id"]):
                return True
            
            if (trans_a.get("trade_date") and trans_b.get("trade_date") and
                trans_a["trade_date"] == trans_b["trade_date"]):
                return True
        
        return False
    
    async def _probabilistic_matching(self, state: MatchingState) -> MatchingState:
        """Perform probabilistic matching based on fuzzy criteria."""
        logger.info("Performing probabilistic matching...")
        
        state.processing_status = "probabilistic_matching"
        
        # Get unmatched transactions
        matched_a_indices = {match["transaction_a"]["external_id"] for match in state.deterministic_matches}
        matched_b_indices = {match["transaction_b"]["external_id"] for match in state.deterministic_matches}
        
        unmatched_a = [t for t in state.transactions_a if t.get("external_id") not in matched_a_indices]
        unmatched_b = [t for t in state.transactions_b if t.get("external_id") not in matched_b_indices]
        
        matches = []
        
        for trans_a in unmatched_a:
            best_match = None
            best_score = 0.0
            
            for trans_b in unmatched_b:
                score = await self._calculate_similarity_score(trans_a, trans_b)
                
                if score > best_score and score >= 0.7:  # Threshold for probabilistic match
                    best_score = score
                    best_match = trans_b
            
            if best_match:
                match = {
                    "transaction_a": trans_a,
                    "transaction_b": best_match,
                    "match_type": "probabilistic",
                    "confidence_score": best_score,
                    "matching_criteria": ["fuzzy_match"],
                    "match_reason": f"Probabilistic match with {best_score:.2f} confidence"
                }
                matches.append(match)
        
        state.probabilistic_matches = matches
        logger.info(f"Found {len(matches)} probabilistic matches")
        
        return state
    
    async def _calculate_similarity_score(self, trans_a: Dict[str, Any], trans_b: Dict[str, Any]) -> float:
        """Calculate similarity score between two transactions."""
        score = 0.0
        total_weight = 0.0
        
        # Amount similarity (weight: 0.4)
        if trans_a.get("amount") and trans_b.get("amount"):
            amount_diff = abs(float(trans_a["amount"]) - float(trans_b["amount"]))
            amount_similarity = max(0, 1 - (amount_diff / max(float(trans_a["amount"]), float(trans_b["amount"]))))
            score += amount_similarity * 0.4
            total_weight += 0.4
        
        # Currency match (weight: 0.2)
        if trans_a.get("currency") and trans_b.get("currency"):
            currency_match = 1.0 if trans_a["currency"] == trans_b["currency"] else 0.0
            score += currency_match * 0.2
            total_weight += 0.2
        
        # Security ID similarity (weight: 0.2)
        if trans_a.get("security_id") and trans_b.get("security_id"):
            security_match = 1.0 if trans_a["security_id"] == trans_b["security_id"] else 0.0
            score += security_match * 0.2
            total_weight += 0.2
        
        # Date similarity (weight: 0.2)
        if trans_a.get("trade_date") and trans_b.get("trade_date"):
            try:
                date_a = datetime.fromisoformat(trans_a["trade_date"])
                date_b = datetime.fromisoformat(trans_b["trade_date"])
                date_diff = abs((date_a - date_b).days)
                date_similarity = max(0, 1 - (date_diff / 30))  # Within 30 days
                score += date_similarity * 0.2
                total_weight += 0.2
            except:
                pass
        
        return score / total_weight if total_weight > 0 else 0.0
    
    async def _ai_enhanced_matching(self, state: MatchingState) -> MatchingState:
        """Use AI to enhance matching for complex cases."""
        logger.info("Performing AI-enhanced matching...")
        
        state.processing_status = "ai_enhanced_matching"
        import os
        if os.getenv("DISABLE_MATCHING_LLM", "false").lower() == "true":
            # Skip AI step if disabled
            state.final_matches = state.deterministic_matches + state.probabilistic_matches
            matched_a_ids = {match["transaction_a"]["external_id"] for match in state.final_matches}
            matched_b_ids = {match["transaction_b"]["external_id"] for match in state.final_matches}
            state.unmatched_transactions = {
                "unmatched_a": [t for t in state.transactions_a if t.get("external_id") not in matched_a_ids],
                "unmatched_b": [t for t in state.transactions_b if t.get("external_id") not in matched_b_ids],
            }
            return state
        
        # Get remaining unmatched transactions
        all_matched_a = {match["transaction_a"]["external_id"] for match in state.deterministic_matches + state.probabilistic_matches}
        all_matched_b = {match["transaction_b"]["external_id"] for match in state.deterministic_matches + state.probabilistic_matches}
        
        unmatched_a = [t for t in state.transactions_a if t.get("external_id") not in all_matched_a]
        unmatched_b = [t for t in state.transactions_b if t.get("external_id") not in all_matched_b]
        
        ai_matches = []
        
        # Use AI to analyze potential matches
        for trans_a in unmatched_a[:10]:  # Limit for performance
            for trans_b in unmatched_b[:10]:
                ai_score = await self._ai_match_analysis(trans_a, trans_b)
                
                if ai_score > 0.8:  # High confidence threshold for AI matches
                    match = {
                        "transaction_a": trans_a,
                        "transaction_b": trans_b,
                        "match_type": "ai_enhanced",
                        "confidence_score": ai_score,
                        "matching_criteria": ["ai_analysis"],
                        "match_reason": f"AI-enhanced match with {ai_score:.2f} confidence"
                    }
                    ai_matches.append(match)
        
        # Combine all matches
        state.final_matches = state.deterministic_matches + state.probabilistic_matches + ai_matches
        
        # Track unmatched transactions
        matched_a_ids = {match["transaction_a"]["external_id"] for match in state.final_matches}
        matched_b_ids = {match["transaction_b"]["external_id"] for match in state.final_matches}
        
        state.unmatched_transactions = {
            "unmatched_a": [t for t in state.transactions_a if t.get("external_id") not in matched_a_ids],
            "unmatched_b": [t for t in state.transactions_b if t.get("external_id") not in matched_b_ids]
        }
        
        logger.info(f"AI enhanced matching completed. Total matches: {len(state.final_matches)}")
        
        return state
    
    async def _ai_match_analysis(self, trans_a: Dict[str, Any], trans_b: Dict[str, Any]) -> float:
        """Use AI to analyze potential match between two transactions."""
        prompt = get_prompt_template("matching_suggestion")
        
        messages = [
            SystemMessage(content="You are a financial transaction matching expert."),
            HumanMessage(content=prompt.format(
                transaction_a=json.dumps(trans_a, indent=2),
                transaction_b=json.dumps(trans_b, indent=2)
            ))
        ]
        
        response = await self._get_llm().ainvoke(messages)
        
        try:
            # Parse AI response for confidence score
            content = response.content.lower()
            if "confidence score:" in content:
                score_text = content.split("confidence score:")[1].split("\n")[0].strip()
                return float(score_text)
            elif "confidence:" in content:
                score_text = content.split("confidence:")[1].split("\n")[0].strip()
                return float(score_text)
            else:
                # Default to low confidence if can't parse
                return 0.3
        except Exception as e:
            logger.warning(f"Failed to parse AI match analysis: {e}")
            return 0.3
    
    async def _validate_matches(self, state: MatchingState) -> MatchingState:
        """Validate generated matches."""
        logger.info("Validating matches...")
        
        state.processing_status = "validating"
        
        valid_matches = []
        
        for match in state.final_matches:
            try:
                # Validate match structure
                if not match.get("transaction_a") or not match.get("transaction_b"):
                    state.matching_errors.append("Invalid match structure")
                    continue
                
                # Validate confidence score
                if not match.get("confidence_score") or match["confidence_score"] < 0:
                    state.matching_errors.append("Invalid confidence score")
                    continue
                
                # Validate match type
                if match.get("match_type") not in ["deterministic", "probabilistic", "ai_enhanced"]:
                    state.matching_errors.append("Invalid match type")
                    continue
                
                valid_matches.append(match)
                
            except Exception as e:
                logger.error(f"Error validating match: {e}")
                state.matching_errors.append(f"Match validation error: {str(e)}")
        
        state.final_matches = valid_matches
        logger.info(f"Validated {len(valid_matches)} matches")
        
        return state
    
    async def _store_matches(self, state: MatchingState) -> MatchingState:
        """Store validated matches in database."""
        logger.info("Storing matches...")
        
        state.processing_status = "storing"
        
        if not state.final_matches:
            state.matching_errors.append("No matches to store")
            state.processing_status = "failed"
            return state
        
        try:
            async with get_db_session() as session:
                from sqlalchemy import text
                # Mark matched transactions in DB
                for match in state.final_matches:
                    for ext_id in (match['transaction_a'].get('external_id'), match['transaction_b'].get('external_id')):
                        if not ext_id:
                            continue
                        await session.execute(
                            text("UPDATE transactions SET status='matched', updated_at=now() WHERE external_id = :ext_id"),
                            {"ext_id": ext_id}
                        )
                # Mark remaining as unmatched
                for t in state.unmatched_transactions.get("unmatched_a", []):
                    if t.get('external_id'):
                        await session.execute(
                            text("UPDATE transactions SET status='unmatched', updated_at=now() WHERE external_id = :ext_id"),
                            {"ext_id": t['external_id']}
                        )
                for t in state.unmatched_transactions.get("unmatched_b", []):
                    if t.get('external_id'):
                        await session.execute(
                            text("UPDATE transactions SET status='unmatched', updated_at=now() WHERE external_id = :ext_id"),
                            {"ext_id": t['external_id']}
                        )
                await session.commit()
                logger.info(f"Stored {len(state.final_matches)} matches and updated statuses")

        except Exception as e:
            logger.error(f"Error storing matches: {e}")
            state.matching_errors.append(f"Storage error: {str(e)}")
            state.processing_status = "failed"
        
        return state
    
    async def _generate_summary(self, state: MatchingState) -> MatchingState:
        """Generate matching summary."""
        logger.info("Generating matching summary...")
        
        state.end_time = datetime.utcnow()
        if state.start_time:
            state.processing_time_ms = int((state.end_time - state.start_time).total_seconds() * 1000)
        
        # Count matches by type
        deterministic_count = len([m for m in state.final_matches if m["match_type"] == "deterministic"])
        probabilistic_count = len([m for m in state.final_matches if m["match_type"] == "probabilistic"])
        ai_enhanced_count = len([m for m in state.final_matches if m["match_type"] == "ai_enhanced"])
        
        state.summary = {
            "total_transactions_a": len(state.transactions_a),
            "total_transactions_b": len(state.transactions_b),
            "total_matches": len(state.final_matches),
            "deterministic_matches": deterministic_count,
            "probabilistic_matches": probabilistic_count,
            "ai_enhanced_matches": ai_enhanced_count,
            "unmatched_a": len(state.unmatched_transactions.get("unmatched_a", [])),
            "unmatched_b": len(state.unmatched_transactions.get("unmatched_b", [])),
            "matching_errors": len(state.matching_errors),
            "processing_time_ms": state.processing_time_ms,
            "match_rate": len(state.final_matches) / max(len(state.transactions_a), len(state.transactions_b)) if max(len(state.transactions_a), len(state.transactions_b)) > 0 else 0,
            "status": "completed" if not state.matching_errors else "completed_with_errors"
        }
        
        state.processing_status = "completed"
        
        logger.info(f"Matching completed: {state.summary}")
        
        return state
    
    async def match_transactions(self, transactions_a: List[Dict[str, Any]], transactions_b: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Match two sets of transactions."""
        session_id = str(uuid.uuid4())
        audit_logger = get_audit_logger()
        start_time = datetime.utcnow()
        
        logger.info(f"Matching {len(transactions_a)} and {len(transactions_b)} transactions")
        
        # Log agent start
        await audit_logger.log_agent_start(
            agent_name="matching",
            session_id=session_id,
            input_data={
                "transactions_a_count": len(transactions_a),
                "transactions_b_count": len(transactions_b)
            }
        )
        
        # Initialize state
        state = MatchingState(
            transactions_a=transactions_a,
            transactions_b=transactions_b
        )
        
        # Run workflow
        try:
            final_state = await self._get_workflow().ainvoke(state)
            # Support both state object and dict return types
            if hasattr(final_state, "summary"):
                summary = final_state.summary
                matches = final_state.final_matches
                unmatched = final_state.unmatched_transactions
                errors = final_state.matching_errors
            elif isinstance(final_state, dict):
                summary = final_state.get("summary", {})
                matches = final_state.get("final_matches", [])
                unmatched = final_state.get("unmatched_transactions", {})
                errors = final_state.get("matching_errors", [])
            else:
                summary = {}
                matches = []
                unmatched = {}
                errors = []
            
            # Calculate processing time
            end_time = datetime.utcnow()
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            result = {
                "success": True,
                "summary": summary,
                "matches": matches,
                "unmatched": unmatched,
                "errors": errors
            }
            
            # Log agent completion
            await audit_logger.log_agent_completion(
                agent_name="matching",
                session_id=session_id,
                result_data=summary,
                processing_time_ms=processing_time_ms,
                is_successful=True
            )
            
            return result
        except Exception as e:
            logger.error(f"Matching workflow failed: {e}")
            
            # Calculate processing time
            end_time = datetime.utcnow()
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Log agent failure
            await audit_logger.log_agent_completion(
                agent_name="matching",
                session_id=session_id,
                result_data={"error": str(e)},
                processing_time_ms=processing_time_ms,
                is_successful=False,
                error_message=str(e)
            )
            
            return {
                "success": False,
                "error": str(e),
                "summary": state.summary
            }


# Lazy initialization function
_matching_engine_agent = None

def get_matching_engine_agent():
    """Get or create the matching engine agent instance."""
    global _matching_engine_agent
    if _matching_engine_agent is None:
        _matching_engine_agent = MatchingEngineAgent()
    return _matching_engine_agent


async def match_financial_transactions(transactions_a: List[Dict[str, Any]], transactions_b: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Match financial transactions using the matching engine agent."""
    agent = get_matching_engine_agent()
    return await agent.match_transactions(transactions_a, transactions_b) 