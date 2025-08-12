"""
Data Ingestion Agent for FS Reconciliation Agents.

This module implements the data ingestion agent using LangGraph framework
to process financial data from various sources including Bloomberg, Reuters,
bank statements, trade slips, and SWIFT messages.
"""

import asyncio
import os
import logging
from datetime import datetime
from uuid import uuid4
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
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
from src.core.models.data_models.transaction import (
    TransactionCreate,
    DataSource,
    TransactionType,
    Transaction as TransactionModel,
)
from src.core.models.audit_models.audit_trail import (
    AuditTrail,
    AuditActionType,
    AuditSeverity,
)
from src.core.services.data_services.database import get_db_session

logger = logging.getLogger(__name__)


class DataIngestionState(BaseModel):
    """State for data ingestion workflow."""
    
    # Input data
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    file_path: Optional[str] = None
    data_source: Optional[str] = None
    file_type: Optional[str] = None
    
    # Processing state
    parsed_data: List[Dict[str, Any]] = Field(default_factory=list)
    validation_errors: List[str] = Field(default_factory=list)
    processing_status: str = "pending"
    
    # Output data
    transactions: List[TransactionCreate] = Field(default_factory=list)
    summary: Dict[str, Any] = Field(default_factory=dict)
    
    # Metadata
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    processing_time_ms: Optional[int] = None
    # Tracking
    session_id: Optional[str] = None


class DataIngestionAgent:
    """Data Ingestion Agent using LangGraph."""
    
    def __init__(self):
        """Initialize the data ingestion agent."""
        self.config = get_agent_config("data_ingestion")
        self.openai_config = get_openai_config()
        
        # Initialize lazily
        self.llm = None
        self.workflow = None
    
    def _get_llm(self):
        """Get or create the LLM instance."""
        if self.llm is None:
            # Allow disabling LLM usage for ingestion via env flag to avoid long-running uploads
            if os.getenv("DISABLE_INGESTION_LLM", "false").lower() == "true":
                return None
            api_key = self.openai_config.get("api", {}).get("api_key")
            if not api_key:
                # Soft-disable LLM usage when not configured
                return None
            
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
        """Create the LangGraph workflow for data ingestion."""
        
        # Create state graph
        workflow = StateGraph(DataIngestionState)
        
        # Add nodes
        workflow.add_node("validate_input", self._validate_input)
        workflow.add_node("parse_data", self._parse_data)
        workflow.add_node("normalize_data", self._normalize_data)
        workflow.add_node("validate_transactions", self._validate_transactions)
        workflow.add_node("store_transactions", self._store_transactions)
        workflow.add_node("generate_summary", self._generate_summary)
        
        # Define edges
        workflow.set_entry_point("validate_input")
        workflow.add_edge("validate_input", "parse_data")
        workflow.add_edge("parse_data", "normalize_data")
        workflow.add_edge("normalize_data", "validate_transactions")
        workflow.add_edge("validate_transactions", "store_transactions")
        workflow.add_edge("store_transactions", "generate_summary")
        workflow.add_edge("generate_summary", END)
        
        return workflow.compile()
    
    async def _validate_input(self, state: DataIngestionState) -> DataIngestionState:
        """Validate input data and file format."""
        logger.info("Validating input data...")
        # Initialize session id for audit trail
        if not state.session_id:
            state.session_id = f"upload_{uuid4()}"
        
        state.start_time = datetime.utcnow()
        state.processing_status = "validating"
        
        # Validate file path
        if state.file_path and not Path(state.file_path).exists():
            state.validation_errors.append(f"File not found: {state.file_path}")
            state.processing_status = "failed"
            return state
        
        # Validate data source (fallback to INTERNAL_SYSTEM for unknown sources)
        if state.data_source and state.data_source not in [ds.value for ds in DataSource]:
            logger.warning(f"Unknown data_source '{state.data_source}', defaulting to INTERNAL_SYSTEM")
            state.data_source = DataSource.INTERNAL_SYSTEM.value
        
        # Validate file type
        supported_types = ['.csv', '.xlsx', '.xls', '.xml', '.pdf', '.txt']
        if state.file_path:
            file_ext = Path(state.file_path).suffix.lower()
            if file_ext not in supported_types:
                state.validation_errors.append(f"Unsupported file type: {file_ext}")
                state.processing_status = "failed"
                return state
        
        logger.info("Input validation completed successfully")
        # Audit: data_ingested
        async with get_db_session() as session:
            session.add(AuditTrail(
                action_type=AuditActionType.DATA_INGESTED.value,
                action_description=f"File uploaded: {state.file_path}",
                action_data={"data_source": state.data_source, "file_type": state.file_type},
                session_id=state.session_id,
                entity_type="file",
                severity=AuditSeverity.INFO.value,
                is_successful=True,
            ))
            await session.flush()
        return state
    
    async def _parse_data(self, state: DataIngestionState) -> DataIngestionState:
        """Parse raw data based on file type."""
        logger.info("Parsing data...")
        
        state.processing_status = "parsing"
        
        if not state.file_path:
            state.validation_errors.append("No file path provided")
            state.processing_status = "failed"
            return state
        
        try:
            file_ext = Path(state.file_path).suffix.lower()
            
            if file_ext == '.csv':
                state.parsed_data = await self._parse_csv(state.file_path)
            elif file_ext in ['.xlsx', '.xls']:
                state.parsed_data = await self._parse_excel(state.file_path)
            elif file_ext == '.xml':
                state.parsed_data = await self._parse_xml(state.file_path)
            elif file_ext == '.pdf':
                state.parsed_data = await self._parse_pdf(state.file_path)
            elif file_ext == '.txt':
                state.parsed_data = await self._parse_swift(state.file_path)
            else:
                state.validation_errors.append(f"Unsupported file type: {file_ext}")
                state.processing_status = "failed"
                return state
            
            logger.info(f"Parsed {len(state.parsed_data)} records")
            # Audit: parsed
            async with get_db_session() as session:
                session.add(AuditTrail(
                    action_type=AuditActionType.DATA_NORMALIZED.value,
                    action_description="Parsing completed",
                    action_data={"records": len(state.parsed_data)},
                    session_id=state.session_id,
                    entity_type="file",
                    severity=AuditSeverity.INFO.value,
                    is_successful=True,
                ))
                await session.flush()
            
        except Exception as e:
            logger.error(f"Error parsing data: {e}")
            state.validation_errors.append(f"Parsing error: {str(e)}")
            state.processing_status = "failed"
        
        return state
    
    async def _parse_csv(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse CSV file."""
        # Try pandas first; fallback to csv module
        try:
            import pandas as pd
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            records = df.to_dict('records')
        except Exception as e:
            logger.warning(f"pandas read_csv failed ({e}); using csv module fallback")
            import csv
            records: List[Dict[str, Any]] = []
            with open(file_path, 'r', encoding='utf-8-sig', newline='') as f:
                try:
                    sample = f.read(4096)
                    f.seek(0)
                    dialect = csv.Sniffer().sniff(sample)
                except Exception:
                    dialect = csv.excel
                reader = csv.DictReader(f, dialect=dialect)
                for row in reader:
                    records.append(row)
        # Canonicalize headers and common synonyms
        canonicalized: List[Dict[str, Any]] = []
        for row in records:
            new_row: Dict[str, Any] = {}
            for k, v in row.items():
                key = (k or "").strip().lower().replace(" ", "_")
                key = key.replace("-", "_")
                # Map known synonyms
                if key in ("transactionid", "transaction_id", "externalid"):
                    key = "external_id"
                elif key in ("securityid", "security_id"):
                    key = "security_id"
                elif key in ("qty", "quantity"):
                    key = "quantity"
                elif key in ("price", "market_price"):
                    key = "market_price"
                elif key in ("amount", "notional"):
                    key = "amount"
                elif key in ("ccy", "currency"):
                    key = "currency"
                elif key in ("tradedate", "trade_date"):
                    key = "trade_date"
                elif key in ("settlementdate", "settlement_date"):
                    key = "settlement_date"
                new_row[key] = v
            canonicalized.append(new_row)
        return canonicalized
    
    async def _parse_excel(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse Excel file."""
        import pandas as pd
        
        df = pd.read_excel(file_path)
        return df.to_dict('records')
    
    async def _parse_xml(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse XML file."""
        import xml.etree.ElementTree as ET
        
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Extract transaction data from XML
        transactions = []
        for elem in root.findall('.//transaction'):
            transaction = {}
            for child in elem:
                transaction[child.tag] = child.text
            transactions.append(transaction)
        
        return transactions
    
    async def _parse_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse PDF file."""
        import pdfplumber
        
        transactions = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                # Use LLM to extract structured data from PDF text
                extracted_data = await self._extract_from_text(text)
                transactions.extend(extracted_data)
        
        return transactions
    
    async def _parse_swift(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse SWIFT message file."""
        transactions = []
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Parse SWIFT MT messages
        messages = content.split('\n')
        for message in messages:
            if message.startswith('{'):
                # Use LLM to parse SWIFT message
                parsed_message = await self._parse_swift_message(message)
                if parsed_message:
                    transactions.append(parsed_message)
        
        return transactions
    
    async def _extract_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract structured data from text using LLM."""
        prompt = get_prompt_template("data_cleansing")
        
        messages = [
            SystemMessage(content="You are a financial data extraction expert."),
            HumanMessage(content=f"{prompt}\n\nText to extract from:\n{text}")
        ]
        
        response = await self._get_llm().ainvoke(messages)
        
        try:
            # Parse JSON response
            extracted_data = json.loads(response.content)
            return [extracted_data] if isinstance(extracted_data, dict) else extracted_data
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM response as JSON")
            return []
    
    async def _parse_swift_message(self, message: str) -> Optional[Dict[str, Any]]:
        """Parse individual SWIFT message."""
        prompt = """
        Parse the following SWIFT MT message and extract transaction details:
        {message}
        
        Return JSON with fields:
        - external_id: Transaction reference
        - amount: Transaction amount
        - currency: Currency code
        - trade_date: Trade date
        - settlement_date: Settlement date
        - security_id: Security identifier
        """
        
        messages = [
            SystemMessage(content="You are a SWIFT message parsing expert."),
            HumanMessage(content=prompt.format(message=message))
        ]
        
        response = await self._get_llm().ainvoke(messages)
        
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            logger.warning("Failed to parse SWIFT message")
            return None
    
    async def _normalize_data(self, state: DataIngestionState) -> DataIngestionState:
        """Normalize parsed data using LLM."""
        logger.info("Normalizing data...")
        
        state.processing_status = "normalizing"
        
        if not state.parsed_data:
            state.validation_errors.append("No data to normalize")
            state.processing_status = "failed"
            return state
        
        normalized_data = []
        
        for record in state.parsed_data:
            try:
                normalized_record = await self._normalize_record(record)
                if normalized_record:
                    normalized_data.append(normalized_record)
            except Exception as e:
                logger.error(f"Error normalizing record: {e}")
                state.validation_errors.append(f"Normalization error: {str(e)}")
        
        state.parsed_data = normalized_data
        logger.info(f"Normalized {len(normalized_data)} records")
        
        return state
    
    async def _normalize_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Normalize individual record using LLM."""
        prompt = get_prompt_template("data_cleansing")
        
        messages = [
            SystemMessage(content="You are a financial data normalization expert."),
            HumanMessage(content=f"{prompt}\n\nRaw data:\n{json.dumps(record, indent=2)}")
        ]
        
        llm = self._get_llm()
        if llm is None:
            # Fallback: pass-through
            return record
        response = await llm.ainvoke(messages)
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            logger.warning("Failed to parse normalized data as JSON; using original record")
            return record
    
    async def _validate_transactions(self, state: DataIngestionState) -> DataIngestionState:
        """Validate normalized transactions."""
        logger.info("Validating transactions...")
        
        state.processing_status = "validating"
        
        if not state.parsed_data:
            state.validation_errors.append("No data to validate")
            state.processing_status = "failed"
            return state
        
        valid_transactions = []
        
        for record in state.parsed_data:
            try:
                # Calculate amount from quantity and market_price if not provided
                amount = record.get("amount")
                market_price = record.get("market_price")
                quantity = record.get("quantity")
                
                if amount is None and market_price and quantity:
                    try:
                        amount = float(market_price) * float(quantity)
                    except (ValueError, TypeError):
                        amount = 0
                elif amount is None:
                    amount = 0
                else:
                    amount = float(amount)
                
                # Create TransactionCreate object for validation
                transaction = TransactionCreate(
                    external_id=record.get("external_id", ""),
                    transaction_type=TransactionType.TRADE,
                    amount=amount,
                    currency=record.get("currency", "USD"),
                    quantity=float(record.get("quantity", 0)) if record.get("quantity") else None,
                    security_id=record.get("security_id"),
                    security_name=record.get("security_name"),
                    isin=record.get("isin"),
                    cusip=record.get("cusip"),
                    sedol=record.get("sedol"),
                    trade_date=datetime.fromisoformat(record.get("trade_date")) if record.get("trade_date") else None,
                    settlement_date=datetime.fromisoformat(record.get("settlement_date")) if record.get("settlement_date") else None,
                    fx_rate=float(record.get("fx_rate")) if record.get("fx_rate") else None,
                    fx_currency=record.get("fx_currency"),
                    market_price=float(market_price) if market_price else None,
                    market_value=float(record.get("market_value")) if record.get("market_value") else None,
                    data_source=DataSource(state.data_source) if state.data_source in [ds.value for ds in DataSource] else DataSource.INTERNAL_SYSTEM,
                    source_file=state.file_path,
                    raw_data=record
                )
                
                valid_transactions.append(transaction)
                
            except Exception as e:
                logger.error(f"Error validating transaction: {e}")
                state.validation_errors.append(f"Validation error: {str(e)}")
        
        state.transactions = valid_transactions
        # Audit: validated
        async with get_db_session() as session:
            session.add(AuditTrail(
                action_type=AuditActionType.DATA_VALIDATED.value,
                action_description="Validation completed",
                action_data={"valid_transactions": len(valid_transactions), "errors": len(state.validation_errors)},
                session_id=state.session_id,
                entity_type="file",
                severity=AuditSeverity.INFO.value,
                is_successful=len(state.validation_errors) == 0,
            ))
            await session.flush()
        logger.info(f"Validated {len(valid_transactions)} transactions")
        
        return state
    
    async def _store_transactions(self, state: DataIngestionState) -> DataIngestionState:
        """Store validated transactions in database."""
        logger.info("Storing transactions...")
        
        state.processing_status = "storing"
        
        if not state.transactions:
            state.validation_errors.append("No transactions to store")
            state.processing_status = "failed"
            return state
        
        try:
            async with get_db_session() as session:
                stored = 0
                # Import ORM model here to avoid circulars
                from sqlalchemy import select
                from src.core.models.data_models.transaction import Transaction as TransactionModel
                for tx in state.transactions:
                    external_id = tx.external_id or str(uuid4())
                    # Skip if already present
                    exists = await session.execute(select(TransactionModel).where(TransactionModel.external_id == external_id))
                    if exists.scalar_one_or_none() is not None:
                        continue
                    model = TransactionModel(
                        external_id=external_id,
                        transaction_type=tx.transaction_type.value,
                        status="pending",
                        amount=tx.amount,
                        currency=(tx.currency or "USD")[:3].upper(),
                        quantity=tx.quantity,
                        security_id=tx.security_id,
                        security_name=tx.security_name,
                        isin=tx.isin,
                        cusip=tx.cusip,
                        sedol=tx.sedol,
                        trade_date=tx.trade_date,
                        settlement_date=tx.settlement_date,
                        fx_rate=tx.fx_rate,
                        fx_currency=tx.fx_currency,
                        market_price=tx.market_price,
                        market_value=tx.market_value,
                        data_source=state.data_source or DataSource.INTERNAL_SYSTEM.value,
                        source_file=state.file_path,
                        raw_data=tx.raw_data,
                        processed_data=None,
                        confidence_score=None,
                    )
                    session.add(model)
                    stored += 1
                # Audit: stored
                session.add(AuditTrail(
                    action_type=AuditActionType.DATA_INGESTED.value,
                    action_description="Transactions stored",
                    action_data={"stored": stored},
                    session_id=state.session_id,
                    entity_type="file",
                    severity=AuditSeverity.INFO.value,
                    is_successful=True,
                ))
                await session.commit()
                logger.info(f"Stored {stored} transactions")
        except Exception as e:
            logger.error(f"Error storing transactions: {e}")
            state.validation_errors.append(f"Storage error: {str(e)}")
            state.processing_status = "failed"
        
        return state
    
    async def _generate_summary(self, state: DataIngestionState) -> DataIngestionState:
        """Generate processing summary."""
        logger.info("Generating summary...")
        
        state.end_time = datetime.utcnow()
        if state.start_time:
            state.processing_time_ms = int((state.end_time - state.start_time).total_seconds() * 1000)
        
        state.summary = {
            "total_records": len(state.parsed_data),
            "valid_transactions": len(state.transactions),
            "validation_errors": len(state.validation_errors),
            "processing_time_ms": state.processing_time_ms,
            "data_source": state.data_source,
            "file_path": state.file_path,
            # Placeholders for UI chips
            "matches_found": 0,
            "exceptions_found": 0,
            "status": "completed" if not state.validation_errors else "completed_with_errors"
        }
        
        state.processing_status = "completed"
        
        logger.info(f"Processing completed: {state.summary}")
        
        return state
    
    async def process_file(self, file_path: str, data_source: str = None) -> Dict[str, Any]:
        """Process a file through the data ingestion workflow."""
        logger.info(f"Processing file: {file_path}")
        
        # Initialize state
        state = DataIngestionState(
            file_path=file_path,
            data_source=data_source,
            file_type=Path(file_path).suffix.lower()
        )
        
        # Run workflow
        try:
            final_state = await self._get_workflow().ainvoke(state)

            # Support both object and dict returns from LangGraph
            if hasattr(final_state, "summary"):
                summary = getattr(final_state, "summary", {}) or {}
                transactions_count = len(getattr(final_state, "transactions", []) or [])
                processed_records = summary.get("total_records") or len(getattr(final_state, "parsed_data", []) or [])
                errors = getattr(final_state, "validation_errors", []) or []
            elif isinstance(final_state, dict):
                summary = final_state.get("summary", {}) or {}
                transactions_count = len(final_state.get("transactions", []) or [])
                processed_records = summary.get("total_records") or len(final_state.get("parsed_data", []) or [])
                errors = final_state.get("validation_errors", []) or []
            else:
                summary = {}
                transactions_count = 0
                processed_records = 0
                errors = []

            return {
                "success": True,
                "processed_records": int(processed_records or 0),
                "summary": summary,
                "transactions": int(transactions_count or 0),
                "errors": errors,
            }
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "summary": state.summary
            }


# Lazy initialization function
_data_ingestion_agent = None

def get_data_ingestion_agent():
    """Get or create the data ingestion agent instance."""
    global _data_ingestion_agent
    if _data_ingestion_agent is None:
        _data_ingestion_agent = DataIngestionAgent()
    return _data_ingestion_agent


async def process_financial_file(file_path: str, data_source: str = None) -> Dict[str, Any]:
    """Process a financial file using the data ingestion agent."""
    agent = get_data_ingestion_agent()
    return await agent.process_file(file_path, data_source) 