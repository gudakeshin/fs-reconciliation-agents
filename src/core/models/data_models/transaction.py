"""
Transaction data models for the FS Reconciliation Agents application.

This module defines the core data structures for financial transactions,
including various types of reconciliation data and their relationships.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator
from sqlalchemy import Column, String, DateTime, Numeric, Text, Boolean, ForeignKey, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship

from src.core.models import Base


class TransactionType(str, Enum):
    """Enumeration of transaction types."""
    TRADE = "trade"
    SETTLEMENT = "settlement"
    COUPON_PAYMENT = "coupon_payment"
    PRINCIPAL_PAYMENT = "principal_payment"
    FX_TRADE = "fx_trade"
    INTEREST_PAYMENT = "interest_payment"
    FEE = "fee"
    ADJUSTMENT = "adjustment"


class TransactionStatus(str, Enum):
    """Enumeration of transaction statuses."""
    PENDING = "pending"
    MATCHED = "matched"
    UNMATCHED = "unmatched"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


class DataSource(str, Enum):
    """Enumeration of data sources."""
    BLOOMBERG = "bloomberg"
    REUTERS = "reuters"
    BANK_STATEMENT = "bank_statement"
    TRADE_SLIP = "trade_slip"
    SWIFT_MESSAGE = "swift_message"
    GENERAL_LEDGER = "general_ledger"
    SECURITY_MASTER = "security_master"
    INTERNAL_SYSTEM = "internal_system"


class Transaction(Base):
    """SQLAlchemy model for transactions."""
    __tablename__ = "transactions"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    external_id = Column(String(255), unique=True, nullable=False, index=True)
    transaction_type = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default=TransactionStatus.PENDING.value)
    
    # Financial data
    amount = Column(Numeric(20, 4), nullable=False)
    currency = Column(String(3), nullable=False)
    quantity = Column(Numeric(20, 6), nullable=True)
    
    # Security information
    security_id = Column(String(100), nullable=True, index=True)
    security_name = Column(String(255), nullable=True)
    isin = Column(String(12), nullable=True, index=True)
    cusip = Column(String(9), nullable=True, index=True)
    sedol = Column(String(7), nullable=True, index=True)
    
    # Dates
    trade_date = Column(DateTime, nullable=True)
    settlement_date = Column(DateTime, nullable=True)
    value_date = Column(DateTime, nullable=True)
    
    # FX information
    fx_rate = Column(Numeric(20, 6), nullable=True)
    fx_currency = Column(String(3), nullable=True)
    
    # Market data
    market_price = Column(Numeric(20, 6), nullable=True)
    market_value = Column(Numeric(20, 4), nullable=True)
    
    # Source information
    data_source = Column(String(50), nullable=False)
    source_file = Column(String(255), nullable=True)
    source_line = Column(Integer, nullable=True)
    
    # Metadata
    raw_data = Column(JSON, nullable=True)
    processed_data = Column(JSON, nullable=True)
    confidence_score = Column(Numeric(5, 4), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    matches = relationship(
        "TransactionMatch",
        foreign_keys="TransactionMatch.transaction_id",
        back_populates="transaction",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    matched_by = relationship(
        "TransactionMatch",
        foreign_keys="TransactionMatch.matched_transaction_id",
        back_populates="matched_transaction",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    # Remove cross-registry relationship to avoid mapper initialization issues
    # exceptions = relationship("ReconciliationException", back_populates="transaction")


class TransactionMatch(Base):
    """SQLAlchemy model for transaction matches."""
    __tablename__ = "transaction_matches"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    transaction_id = Column(PostgresUUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)
    matched_transaction_id = Column(PostgresUUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)
    
    # Match information
    match_type = Column(String(50), nullable=False)  # exact, fuzzy, manual
    confidence_score = Column(Numeric(5, 4), nullable=False)
    match_criteria = Column(JSON, nullable=True)
    
    # Status
    status = Column(String(50), nullable=False, default="pending")
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    transaction = relationship(
        "Transaction",
        foreign_keys=[transaction_id],
        back_populates="matches",
    )
    matched_transaction = relationship(
        "Transaction",
        foreign_keys=[matched_transaction_id],
        back_populates="matched_by",
    )


# Pydantic models for API
class TransactionBase(BaseModel):
    """Base Pydantic model for transactions."""
    external_id: str = Field(..., description="External transaction identifier")
    transaction_type: TransactionType = Field(..., description="Type of transaction")
    amount: Decimal = Field(..., description="Transaction amount")
    currency: str = Field(..., min_length=3, max_length=3, description="Currency code")
    quantity: Optional[Decimal] = Field(None, description="Quantity of securities")
    security_id: Optional[str] = Field(None, description="Security identifier")
    security_name: Optional[str] = Field(None, description="Security name")
    isin: Optional[str] = Field(None, description="ISIN code")
    cusip: Optional[str] = Field(None, description="CUSIP code")
    sedol: Optional[str] = Field(None, description="SEDOL code")
    trade_date: Optional[datetime] = Field(None, description="Trade date")
    settlement_date: Optional[datetime] = Field(None, description="Settlement date")
    value_date: Optional[datetime] = Field(None, description="Value date")
    fx_rate: Optional[Decimal] = Field(None, description="Foreign exchange rate")
    fx_currency: Optional[str] = Field(None, min_length=3, max_length=3, description="FX currency")
    market_price: Optional[Decimal] = Field(None, description="Market price")
    market_value: Optional[Decimal] = Field(None, description="Market value")
    data_source: DataSource = Field(..., description="Data source")
    source_file: Optional[str] = Field(None, description="Source file name")
    source_line: Optional[int] = Field(None, description="Source file line number")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Raw transaction data")
    processed_data: Optional[Dict[str, Any]] = Field(None, description="Processed transaction data")
    confidence_score: Optional[Decimal] = Field(None, ge=0, le=1, description="Confidence score")

    @validator('currency', 'fx_currency')
    def validate_currency_codes(cls, v):
        if v and not v.isalpha():
            raise ValueError('Currency code must be alphabetic')
        return v.upper() if v else v

    @validator('isin')
    def validate_isin(cls, v):
        if v and len(v) != 12:
            raise ValueError('ISIN must be exactly 12 characters')
        return v.upper() if v else v

    @validator('cusip')
    def validate_cusip(cls, v):
        if v and len(v) != 9:
            raise ValueError('CUSIP must be exactly 9 characters')
        return v.upper() if v else v

    @validator('sedol')
    def validate_sedol(cls, v):
        if v and len(v) != 7:
            raise ValueError('SEDOL must be exactly 7 characters')
        return v.upper() if v else v


class TransactionCreate(TransactionBase):
    """Pydantic model for creating transactions."""
    pass


class TransactionUpdate(BaseModel):
    """Pydantic model for updating transactions."""
    status: Optional[TransactionStatus] = Field(None, description="Transaction status")
    confidence_score: Optional[Decimal] = Field(None, ge=0, le=1, description="Confidence score")
    processed_data: Optional[Dict[str, Any]] = Field(None, description="Processed transaction data")


class TransactionResponse(TransactionBase):
    """Pydantic model for transaction responses."""
    id: UUID = Field(..., description="Transaction ID")
    status: TransactionStatus = Field(..., description="Transaction status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class TransactionMatchBase(BaseModel):
    """Base Pydantic model for transaction matches."""
    matched_transaction_id: UUID = Field(..., description="ID of matched transaction")
    match_type: str = Field(..., description="Type of match")
    confidence_score: Decimal = Field(..., ge=0, le=1, description="Confidence score")
    match_criteria: Optional[Dict[str, Any]] = Field(None, description="Match criteria used")


class TransactionMatchCreate(TransactionMatchBase):
    """Pydantic model for creating transaction matches."""
    pass


class TransactionMatchResponse(TransactionMatchBase):
    """Pydantic model for transaction match responses."""
    id: UUID = Field(..., description="Match ID")
    transaction_id: UUID = Field(..., description="Transaction ID")
    status: str = Field(..., description="Match status")
    reviewed_by: Optional[str] = Field(None, description="Reviewer")
    reviewed_at: Optional[datetime] = Field(None, description="Review timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True 