"""
Data Normalization Agent for FS Reconciliation Agents.

This module implements the data normalization agent using LangGraph framework
to clean and standardize financial data, including date formats, currency codes,
security identifiers, and entity names.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from decimal import Decimal
import json
import re

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.core.services.data_services.config_service import (
    get_openai_config,
    get_agent_config,
    get_prompt_template
)
from src.core.models.data_models.transaction import Transaction
from src.core.services.data_services.database import get_db_session

logger = logging.getLogger(__name__)


class NormalizationState(BaseModel):
    """State for data normalization workflow."""
    
    # Input data
    raw_transactions: List[Dict[str, Any]] = Field(default_factory=list)
    normalization_rules: Dict[str, Any] = Field(default_factory=dict)
    
    # Processing state
    normalized_transactions: List[Dict[str, Any]] = Field(default_factory=list)
    normalization_errors: List[str] = Field(default_factory=list)
    processing_status: str = "pending"
    
    # Output data
    cleaned_transactions: List[Dict[str, Any]] = Field(default_factory=list)
    summary: Dict[str, Any] = Field(default_factory=dict)
    
    # Metadata
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    processing_time_ms: Optional[int] = None


class DataNormalizationAgent:
    """Data Normalization Agent using LangGraph."""
    
    def __init__(self):
        """Initialize the data normalization agent."""
        self.config = get_agent_config("data_normalization")
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
        """Create the LangGraph workflow for data normalization."""
        
        # Create state graph
        workflow = StateGraph(NormalizationState)
        
        # Add nodes
        workflow.add_node("validate_input", self._validate_input)
        workflow.add_node("normalize_dates", self._normalize_dates)
        workflow.add_node("normalize_currencies", self._normalize_currencies)
        workflow.add_node("normalize_securities", self._normalize_securities)
        workflow.add_node("normalize_entities", self._normalize_entities)
        workflow.add_node("deduplicate_data", self._deduplicate_data)
        workflow.add_node("validate_normalized", self._validate_normalized)
        workflow.add_node("generate_summary", self._generate_summary)
        
        # Define edges
        workflow.set_entry_point("validate_input")
        workflow.add_edge("validate_input", "normalize_dates")
        workflow.add_edge("normalize_dates", "normalize_currencies")
        workflow.add_edge("normalize_currencies", "normalize_securities")
        workflow.add_edge("normalize_securities", "normalize_entities")
        workflow.add_edge("normalize_entities", "deduplicate_data")
        workflow.add_edge("deduplicate_data", "validate_normalized")
        workflow.add_edge("validate_normalized", "generate_summary")
        workflow.add_edge("generate_summary", END)
        
        return workflow.compile()
    
    async def _validate_input(self, state: NormalizationState) -> NormalizationState:
        """Validate input data for normalization."""
        logger.info("Validating input data for normalization...")
        
        state.start_time = datetime.utcnow()
        state.processing_status = "validating"
        
        if not state.raw_transactions:
            state.normalization_errors.append("No transactions to normalize")
            state.processing_status = "failed"
            return state
        
        # Validate required fields
        required_fields = ["external_id", "amount", "currency"]
        for i, transaction in enumerate(state.raw_transactions):
            missing_fields = [field for field in required_fields if field not in transaction]
            if missing_fields:
                state.normalization_errors.append(
                    f"Transaction {i}: Missing required fields: {missing_fields}"
                )
        
        logger.info(f"Validated {len(state.raw_transactions)} transactions")
        return state
    
    async def _normalize_dates(self, state: NormalizationState) -> NormalizationState:
        """Normalize date formats."""
        logger.info("Normalizing date formats...")
        
        state.processing_status = "normalizing_dates"
        
        normalized_transactions = []
        
        for transaction in state.raw_transactions:
            try:
                normalized_transaction = transaction.copy()
                
                # Normalize trade date
                if "trade_date" in transaction:
                    normalized_transaction["trade_date"] = await self._normalize_date(
                        transaction["trade_date"]
                    )
                
                # Normalize settlement date
                if "settlement_date" in transaction:
                    normalized_transaction["settlement_date"] = await self._normalize_date(
                        transaction["settlement_date"]
                    )
                
                # Normalize value date
                if "value_date" in transaction:
                    normalized_transaction["value_date"] = await self._normalize_date(
                        transaction["value_date"]
                    )
                
                normalized_transactions.append(normalized_transaction)
                
            except Exception as e:
                logger.error(f"Error normalizing dates for transaction: {e}")
                state.normalization_errors.append(f"Date normalization error: {str(e)}")
        
        state.normalized_transactions = normalized_transactions
        logger.info(f"Normalized dates for {len(normalized_transactions)} transactions")
        
        return state
    
    async def _normalize_date(self, date_value: Any) -> Optional[str]:
        """Normalize date value to ISO format."""
        if not date_value:
            return None
        
        # If already a datetime object
        if isinstance(date_value, datetime):
            return date_value.isoformat()
        
        # If already a string in ISO format
        if isinstance(date_value, str) and re.match(r'\d{4}-\d{2}-\d{2}', date_value):
            return date_value
        
        # Use LLM to parse and normalize date
        prompt = f"""
        Parse and normalize the following date value to ISO format (YYYY-MM-DD):
        Date: {date_value}
        
        Return only the normalized date in ISO format, or null if invalid.
        """
        
        messages = [
            SystemMessage(content="You are a date normalization expert."),
            HumanMessage(content=prompt)
        ]
        
        response = await self.llm.ainvoke(messages)
        
        try:
            normalized_date = response.content.strip()
            if normalized_date.lower() == "null":
                return None
            return normalized_date
        except Exception as e:
            logger.warning(f"Failed to normalize date {date_value}: {e}")
            return None
    
    async def _normalize_currencies(self, state: NormalizationState) -> NormalizationState:
        """Normalize currency codes."""
        logger.info("Normalizing currency codes...")
        
        state.processing_status = "normalizing_currencies"
        
        normalized_transactions = []
        
        for transaction in state.normalized_transactions:
            try:
                normalized_transaction = transaction.copy()
                
                # Normalize currency code
                if "currency" in transaction:
                    normalized_transaction["currency"] = await self._normalize_currency(
                        transaction["currency"]
                    )
                
                # Normalize FX currency
                if "fx_currency" in transaction:
                    normalized_transaction["fx_currency"] = await self._normalize_currency(
                        transaction["fx_currency"]
                    )
                
                normalized_transactions.append(normalized_transaction)
                
            except Exception as e:
                logger.error(f"Error normalizing currencies for transaction: {e}")
                state.normalization_errors.append(f"Currency normalization error: {str(e)}")
        
        state.normalized_transactions = normalized_transactions
        logger.info(f"Normalized currencies for {len(normalized_transactions)} transactions")
        
        return state
    
    async def _normalize_currency(self, currency_value: Any) -> str:
        """Normalize currency code to 3-letter format."""
        if not currency_value:
            return "USD"
        
        # If already a 3-letter code
        if isinstance(currency_value, str) and len(currency_value) == 3:
            return currency_value.upper()
        
        # Use LLM to normalize currency
        prompt = f"""
        Normalize the following currency value to a 3-letter ISO currency code:
        Currency: {currency_value}
        
        Return only the 3-letter currency code (e.g., USD, EUR, GBP).
        """
        
        messages = [
            SystemMessage(content="You are a currency code normalization expert."),
            HumanMessage(content=prompt)
        ]
        
        response = await self.llm.ainvoke(messages)
        
        try:
            normalized_currency = response.content.strip().upper()
            return normalized_currency
        except Exception as e:
            logger.warning(f"Failed to normalize currency {currency_value}: {e}")
            return "USD"
    
    async def _normalize_securities(self, state: NormalizationState) -> NormalizationState:
        """Normalize security identifiers."""
        logger.info("Normalizing security identifiers...")
        
        state.processing_status = "normalizing_securities"
        
        normalized_transactions = []
        
        for transaction in state.normalized_transactions:
            try:
                normalized_transaction = transaction.copy()
                
                # Normalize ISIN
                if "isin" in transaction:
                    normalized_transaction["isin"] = await self._normalize_isin(
                        transaction["isin"]
                    )
                
                # Normalize CUSIP
                if "cusip" in transaction:
                    normalized_transaction["cusip"] = await self._normalize_cusip(
                        transaction["cusip"]
                    )
                
                # Normalize SEDOL
                if "sedol" in transaction:
                    normalized_transaction["sedol"] = await self._normalize_sedol(
                        transaction["sedol"]
                    )
                
                # Normalize security ID
                if "security_id" in transaction:
                    normalized_transaction["security_id"] = await self._normalize_security_id(
                        transaction["security_id"]
                    )
                
                normalized_transactions.append(normalized_transaction)
                
            except Exception as e:
                logger.error(f"Error normalizing securities for transaction: {e}")
                state.normalization_errors.append(f"Security normalization error: {str(e)}")
        
        state.normalized_transactions = normalized_transactions
        logger.info(f"Normalized securities for {len(normalized_transactions)} transactions")
        
        return state
    
    async def _normalize_isin(self, isin_value: Any) -> Optional[str]:
        """Normalize ISIN code."""
        if not isin_value:
            return None
        
        # If already a 12-character ISIN
        if isinstance(isin_value, str) and len(isin_value) == 12:
            return isin_value.upper()
        
        # Use LLM to normalize ISIN
        prompt = f"""
        Normalize the following ISIN code to a 12-character ISIN format:
        ISIN: {isin_value}
        
        Return only the normalized ISIN code, or null if invalid.
        """
        
        messages = [
            SystemMessage(content="You are an ISIN code normalization expert."),
            HumanMessage(content=prompt)
        ]
        
        response = await self.llm.ainvoke(messages)
        
        try:
            normalized_isin = response.content.strip().upper()
            if normalized_isin.lower() == "null":
                return None
            return normalized_isin
        except Exception as e:
            logger.warning(f"Failed to normalize ISIN {isin_value}: {e}")
            return None
    
    async def _normalize_cusip(self, cusip_value: Any) -> Optional[str]:
        """Normalize CUSIP code."""
        if not cusip_value:
            return None
        
        # If already a 9-character CUSIP
        if isinstance(cusip_value, str) and len(cusip_value) == 9:
            return cusip_value.upper()
        
        # Use LLM to normalize CUSIP
        prompt = f"""
        Normalize the following CUSIP code to a 9-character CUSIP format:
        CUSIP: {cusip_value}
        
        Return only the normalized CUSIP code, or null if invalid.
        """
        
        messages = [
            SystemMessage(content="You are a CUSIP code normalization expert."),
            HumanMessage(content=prompt)
        ]
        
        response = await self.llm.ainvoke(messages)
        
        try:
            normalized_cusip = response.content.strip().upper()
            if normalized_cusip.lower() == "null":
                return None
            return normalized_cusip
        except Exception as e:
            logger.warning(f"Failed to normalize CUSIP {cusip_value}: {e}")
            return None
    
    async def _normalize_sedol(self, sedol_value: Any) -> Optional[str]:
        """Normalize SEDOL code."""
        if not sedol_value:
            return None
        
        # If already a 7-character SEDOL
        if isinstance(sedol_value, str) and len(sedol_value) == 7:
            return sedol_value.upper()
        
        # Use LLM to normalize SEDOL
        prompt = f"""
        Normalize the following SEDOL code to a 7-character SEDOL format:
        SEDOL: {sedol_value}
        
        Return only the normalized SEDOL code, or null if invalid.
        """
        
        messages = [
            SystemMessage(content="You are a SEDOL code normalization expert."),
            HumanMessage(content=prompt)
        ]
        
        response = await self.llm.ainvoke(messages)
        
        try:
            normalized_sedol = response.content.strip().upper()
            if normalized_sedol.lower() == "null":
                return None
            return normalized_sedol
        except Exception as e:
            logger.warning(f"Failed to normalize SEDOL {sedol_value}: {e}")
            return None
    
    async def _normalize_security_id(self, security_id_value: Any) -> Optional[str]:
        """Normalize security ID."""
        if not security_id_value:
            return None
        
        # Use LLM to normalize security ID
        prompt = f"""
        Normalize the following security identifier to a standard format:
        Security ID: {security_id_value}
        
        Return only the normalized security ID, or null if invalid.
        """
        
        messages = [
            SystemMessage(content="You are a security identifier normalization expert."),
            HumanMessage(content=prompt)
        ]
        
        response = await self.llm.ainvoke(messages)
        
        try:
            normalized_id = response.content.strip()
            if normalized_id.lower() == "null":
                return None
            return normalized_id
        except Exception as e:
            logger.warning(f"Failed to normalize security ID {security_id_value}: {e}")
            return None
    
    async def _normalize_entities(self, state: NormalizationState) -> NormalizationState:
        """Normalize entity names and identifiers."""
        logger.info("Normalizing entity names...")
        
        state.processing_status = "normalizing_entities"
        
        normalized_transactions = []
        
        for transaction in state.normalized_transactions:
            try:
                normalized_transaction = transaction.copy()
                
                # Normalize security name
                if "security_name" in transaction:
                    normalized_transaction["security_name"] = await self._normalize_entity_name(
                        transaction["security_name"]
                    )
                
                # Normalize counterparty name
                if "counterparty" in transaction:
                    normalized_transaction["counterparty"] = await self._normalize_entity_name(
                        transaction["counterparty"]
                    )
                
                normalized_transactions.append(normalized_transaction)
                
            except Exception as e:
                logger.error(f"Error normalizing entities for transaction: {e}")
                state.normalization_errors.append(f"Entity normalization error: {str(e)}")
        
        state.normalized_transactions = normalized_transactions
        logger.info(f"Normalized entities for {len(normalized_transactions)} transactions")
        
        return state
    
    async def _normalize_entity_name(self, entity_name: Any) -> Optional[str]:
        """Normalize entity name."""
        if not entity_name:
            return None
        
        # Use LLM to normalize entity name
        prompt = f"""
        Normalize the following entity name to a standard format:
        Entity Name: {entity_name}
        
        Return only the normalized entity name, or null if invalid.
        """
        
        messages = [
            SystemMessage(content="You are an entity name normalization expert."),
            HumanMessage(content=prompt)
        ]
        
        response = await self.llm.ainvoke(messages)
        
        try:
            normalized_name = response.content.strip()
            if normalized_name.lower() == "null":
                return None
            return normalized_name
        except Exception as e:
            logger.warning(f"Failed to normalize entity name {entity_name}: {e}")
            return None
    
    async def _deduplicate_data(self, state: NormalizationState) -> NormalizationState:
        """Remove duplicate transactions."""
        logger.info("Deduplicating data...")
        
        state.processing_status = "deduplicating"
        
        # Create a set to track seen external IDs
        seen_ids = set()
        unique_transactions = []
        
        for transaction in state.normalized_transactions:
            external_id = transaction.get("external_id", "")
            
            if external_id and external_id not in seen_ids:
                seen_ids.add(external_id)
                unique_transactions.append(transaction)
            elif not external_id:
                # For transactions without external ID, use a hash of key fields
                key_fields = f"{transaction.get('amount')}_{transaction.get('currency')}_{transaction.get('trade_date')}"
                if key_fields not in seen_ids:
                    seen_ids.add(key_fields)
                    unique_transactions.append(transaction)
        
        state.normalized_transactions = unique_transactions
        logger.info(f"Deduplicated to {len(unique_transactions)} unique transactions")
        
        return state
    
    async def _validate_normalized(self, state: NormalizationState) -> NormalizationState:
        """Validate normalized data."""
        logger.info("Validating normalized data...")
        
        state.processing_status = "validating"
        
        valid_transactions = []
        
        for transaction in state.normalized_transactions:
            try:
                # Validate required fields
                if not transaction.get("external_id"):
                    state.normalization_errors.append("Missing external_id")
                    continue
                
                if not transaction.get("amount"):
                    state.normalization_errors.append("Missing amount")
                    continue
                
                if not transaction.get("currency"):
                    state.normalization_errors.append("Missing currency")
                    continue
                
                valid_transactions.append(transaction)
                
            except Exception as e:
                logger.error(f"Error validating normalized transaction: {e}")
                state.normalization_errors.append(f"Validation error: {str(e)}")
        
        state.cleaned_transactions = valid_transactions
        logger.info(f"Validated {len(valid_transactions)} normalized transactions")
        
        return state
    
    async def _generate_summary(self, state: NormalizationState) -> NormalizationState:
        """Generate normalization summary."""
        logger.info("Generating normalization summary...")
        
        state.end_time = datetime.utcnow()
        if state.start_time:
            state.processing_time_ms = int((state.end_time - state.start_time).total_seconds() * 1000)
        
        state.summary = {
            "total_input": len(state.raw_transactions),
            "total_output": len(state.cleaned_transactions),
            "duplicates_removed": len(state.raw_transactions) - len(state.normalized_transactions),
            "validation_errors": len(state.normalization_errors),
            "processing_time_ms": state.processing_time_ms,
            "status": "completed" if not state.normalization_errors else "completed_with_errors"
        }
        
        state.processing_status = "completed"
        
        logger.info(f"Normalization completed: {state.summary}")
        
        return state
    
    async def normalize_transactions(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Normalize a list of transactions."""
        logger.info(f"Normalizing {len(transactions)} transactions")
        
        # Initialize state
        state = NormalizationState(raw_transactions=transactions)
        
        # Run workflow
        try:
            final_state = await self._get_workflow().ainvoke(state)
            return {
                "success": True,
                "summary": final_state.summary,
                "normalized_transactions": final_state.cleaned_transactions,
                "errors": final_state.normalization_errors
            }
        except Exception as e:
            logger.error(f"Normalization workflow failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "summary": state.summary
            }


# Lazy initialization function
_data_normalization_agent = None

def get_data_normalization_agent():
    """Get or create the data normalization agent instance."""
    global _data_normalization_agent
    if _data_normalization_agent is None:
        _data_normalization_agent = DataNormalizationAgent()
    return _data_normalization_agent


async def normalize_financial_data(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Normalize financial data using the normalization agent."""
    agent = get_data_normalization_agent()
    return await agent.normalize_transactions(transactions) 