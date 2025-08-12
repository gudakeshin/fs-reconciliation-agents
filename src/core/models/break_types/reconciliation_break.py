"""
Reconciliation break models for the FS Reconciliation Agents application.

This module defines the data structures for the five critical types of reconciliation breaks:
1. Security ID Breaks
2. Fixed Income Coupon Payments
3. Market Price Differences
4. Trade Date vs. Settlement Date
5. FX Rate Errors
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator
from sqlalchemy import Column, String, DateTime, Numeric, Text, Boolean, ForeignKey, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship

from src.core.models import Base


class BreakType(str, Enum):
    """Enumeration of reconciliation break types."""
    SECURITY_ID_BREAK = "security_id_break"
    FIXED_INCOME_COUPON = "fixed_income_coupon"
    MARKET_PRICE_DIFFERENCE = "market_price_difference"
    TRADE_SETTLEMENT_DATE = "trade_settlement_date"
    FX_RATE_ERROR = "fx_rate_error"
    UNMATCHED = "unmatched"


class BreakSeverity(str, Enum):
    """Enumeration of break severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BreakStatus(str, Enum):
    """Enumeration of break statuses."""
    OPEN = "open"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    CLOSED = "closed"
    ESCALATED = "escalated"


class ReconciliationException(Base):
    """SQLAlchemy model for reconciliation exceptions/breaks."""
    __tablename__ = "reconciliation_exceptions"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    transaction_id = Column(PostgresUUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)
    
    # Break classification
    break_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False, default=BreakSeverity.MEDIUM.value)
    status = Column(String(20), nullable=False, default=BreakStatus.OPEN.value)
    
    # Break details
    description = Column(Text, nullable=True)
    root_cause = Column(Text, nullable=True)
    suggested_resolution = Column(Text, nullable=True)
    
    # Financial impact
    break_amount = Column(Numeric(20, 4), nullable=True)
    break_currency = Column(String(3), nullable=True)
    
    # AI analysis
    ai_confidence_score = Column(Numeric(5, 4), nullable=True)
    ai_reasoning = Column(JSON, nullable=True)
    ai_suggested_actions = Column(JSON, nullable=True)
    
    # Enhanced analysis
    detailed_differences = Column(JSON, nullable=True)
    workflow_triggers = Column(JSON, nullable=True)
    
    # Manual review
    assigned_to = Column(String(100), nullable=True)
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)
    
    # Resolution
    resolution_method = Column(String(100), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships (avoid cross-registry mapping to Transaction)
    audit_trail = relationship("BreakAuditTrail", back_populates="exception")


class BreakAuditTrail(Base):
    """SQLAlchemy model for break audit trail."""
    __tablename__ = "break_audit_trail"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    exception_id = Column(PostgresUUID(as_uuid=True), ForeignKey("reconciliation_exceptions.id"), nullable=False)
    
    # Action details
    action_type = Column(String(50), nullable=False)  # created, updated, assigned, resolved, etc.
    action_by = Column(String(100), nullable=False)
    action_description = Column(Text, nullable=True)
    action_data = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    exception = relationship("ReconciliationException", back_populates="audit_trail")


# Specific break type models
class SecurityIDBreak(Base):
    """SQLAlchemy model for Security ID breaks."""
    __tablename__ = "security_id_breaks"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    exception_id = Column(PostgresUUID(as_uuid=True), ForeignKey("reconciliation_exceptions.id"), nullable=False)
    
    # Security identifiers
    expected_security_id = Column(String(100), nullable=True)
    actual_security_id = Column(String(100), nullable=True)
    expected_isin = Column(String(12), nullable=True)
    actual_isin = Column(String(12), nullable=True)
    expected_cusip = Column(String(9), nullable=True)
    actual_cusip = Column(String(9), nullable=True)
    expected_sedol = Column(String(7), nullable=True)
    actual_sedol = Column(String(7), nullable=True)
    
    # Cross-reference data
    bloomberg_id = Column(String(100), nullable=True)
    reuters_id = Column(String(100), nullable=True)
    internal_security_id = Column(String(100), nullable=True)
    
    # Resolution
    resolved_security_id = Column(String(100), nullable=True)
    resolution_source = Column(String(50), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class FixedIncomeCouponBreak(Base):
    """SQLAlchemy model for Fixed Income Coupon Payment breaks."""
    __tablename__ = "fixed_income_coupon_breaks"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    exception_id = Column(PostgresUUID(as_uuid=True), ForeignKey("reconciliation_exceptions.id"), nullable=False)
    
    # Coupon details
    coupon_rate = Column(Numeric(10, 6), nullable=True)
    coupon_frequency = Column(String(20), nullable=True)  # annual, semi-annual, quarterly, etc.
    day_count_convention = Column(String(20), nullable=True)  # actual/actual, 30/360, actual/365
    
    # Payment details
    expected_payment = Column(Numeric(20, 4), nullable=True)
    actual_payment = Column(Numeric(20, 4), nullable=True)
    payment_difference = Column(Numeric(20, 4), nullable=True)
    
    # Date calculations
    last_coupon_date = Column(DateTime, nullable=True)
    next_coupon_date = Column(DateTime, nullable=True)
    payment_date = Column(DateTime, nullable=True)
    
    # Accrued interest
    expected_accrued_interest = Column(Numeric(20, 4), nullable=True)
    actual_accrued_interest = Column(Numeric(20, 4), nullable=True)
    accrued_interest_difference = Column(Numeric(20, 4), nullable=True)
    
    # Resolution
    corrected_payment = Column(Numeric(20, 4), nullable=True)
    correction_reason = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class MarketPriceBreak(Base):
    """SQLAlchemy model for Market Price Difference breaks."""
    __tablename__ = "market_price_breaks"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    exception_id = Column(PostgresUUID(as_uuid=True), ForeignKey("reconciliation_exceptions.id"), nullable=False)
    
    # Price data
    expected_price = Column(Numeric(20, 6), nullable=True)
    actual_price = Column(Numeric(20, 6), nullable=True)
    price_difference = Column(Numeric(20, 6), nullable=True)
    price_difference_percentage = Column(Numeric(10, 4), nullable=True)
    
    # Market data sources
    bloomberg_price = Column(Numeric(20, 6), nullable=True)
    reuters_price = Column(Numeric(20, 6), nullable=True)
    internal_price = Column(Numeric(20, 6), nullable=True)
    
    # Tolerance settings
    price_tolerance = Column(Numeric(10, 4), nullable=True)
    tolerance_exceeded = Column(Boolean, nullable=True)
    
    # Bid-ask spread
    bid_price = Column(Numeric(20, 6), nullable=True)
    ask_price = Column(Numeric(20, 6), nullable=True)
    spread = Column(Numeric(20, 6), nullable=True)
    
    # Resolution
    accepted_price = Column(Numeric(20, 6), nullable=True)
    price_source = Column(String(50), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class TradeSettlementDateBreak(Base):
    """SQLAlchemy model for Trade Date vs Settlement Date breaks."""
    __tablename__ = "trade_settlement_date_breaks"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    exception_id = Column(PostgresUUID(as_uuid=True), ForeignKey("reconciliation_exceptions.id"), nullable=False)
    
    # Date information
    expected_trade_date = Column(DateTime, nullable=True)
    actual_trade_date = Column(DateTime, nullable=True)
    expected_settlement_date = Column(DateTime, nullable=True)
    actual_settlement_date = Column(DateTime, nullable=True)
    
    # Settlement cycle
    expected_settlement_cycle = Column(String(10), nullable=True)  # T+1, T+2, T+3, etc.
    actual_settlement_cycle = Column(String(10), nullable=True)
    
    # Timing differences
    trade_date_difference = Column(Integer, nullable=True)  # days
    settlement_date_difference = Column(Integer, nullable=True)  # days
    
    # Market calendar
    market_holidays = Column(JSON, nullable=True)
    business_days_calculation = Column(Boolean, nullable=True)
    
    # Resolution
    corrected_trade_date = Column(DateTime, nullable=True)
    corrected_settlement_date = Column(DateTime, nullable=True)
    correction_reason = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class FXRateBreak(Base):
    """SQLAlchemy model for FX Rate Error breaks."""
    __tablename__ = "fx_rate_breaks"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    exception_id = Column(PostgresUUID(as_uuid=True), ForeignKey("reconciliation_exceptions.id"), nullable=False)
    
    # FX rate data
    expected_fx_rate = Column(Numeric(20, 6), nullable=True)
    actual_fx_rate = Column(Numeric(20, 6), nullable=True)
    rate_difference = Column(Numeric(20, 6), nullable=True)
    rate_difference_percentage = Column(Numeric(10, 4), nullable=True)
    
    # Currency information
    base_currency = Column(String(3), nullable=True)
    quote_currency = Column(String(3), nullable=True)
    
    # Rate sources
    bloomberg_rate = Column(Numeric(20, 6), nullable=True)
    reuters_rate = Column(Numeric(20, 6), nullable=True)
    central_bank_rate = Column(Numeric(20, 6), nullable=True)
    internal_rate = Column(Numeric(20, 6), nullable=True)
    
    # Rate type
    rate_type = Column(String(20), nullable=True)  # spot, forward, historical
    rate_date = Column(DateTime, nullable=True)
    
    # Tolerance settings
    rate_tolerance = Column(Numeric(10, 4), nullable=True)
    tolerance_exceeded = Column(Boolean, nullable=True)
    
    # Resolution
    accepted_rate = Column(Numeric(20, 6), nullable=True)
    rate_source = Column(String(50), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


# Pydantic models for API
class ReconciliationExceptionBase(BaseModel):
    """Base Pydantic model for reconciliation exceptions."""
    break_type: BreakType = Field(..., description="Type of reconciliation break")
    severity: BreakSeverity = Field(..., description="Severity level of the break")
    description: Optional[str] = Field(None, description="Description of the break")
    root_cause: Optional[str] = Field(None, description="Root cause analysis")
    suggested_resolution: Optional[str] = Field(None, description="Suggested resolution")
    break_amount: Optional[Decimal] = Field(None, description="Financial impact amount")
    break_currency: Optional[str] = Field(None, min_length=3, max_length=3, description="Currency of break amount")
    ai_confidence_score: Optional[Decimal] = Field(None, ge=0, le=1, description="AI confidence score")
    ai_reasoning: Optional[Dict[str, Any]] = Field(None, description="AI reasoning for the break")
    ai_suggested_actions: Optional[Dict[str, Any]] = Field(None, description="AI suggested actions")
    detailed_differences: Optional[Dict[str, Any]] = Field(None, description="Detailed differences between sources")
    workflow_triggers: Optional[List[Dict[str, Any]]] = Field(None, description="Workflow triggers for resolution")


class ReconciliationExceptionCreate(ReconciliationExceptionBase):
    """Pydantic model for creating reconciliation exceptions."""
    transaction_id: UUID = Field(..., description="Associated transaction ID")


class ReconciliationExceptionUpdate(BaseModel):
    """Pydantic model for updating reconciliation exceptions."""
    status: Optional[BreakStatus] = Field(None, description="Break status")
    assigned_to: Optional[str] = Field(None, description="Assigned user")
    review_notes: Optional[str] = Field(None, description="Review notes")
    resolution_method: Optional[str] = Field(None, description="Resolution method")
    resolution_notes: Optional[str] = Field(None, description="Resolution notes")


class ReconciliationExceptionResponse(ReconciliationExceptionBase):
    """Pydantic model for reconciliation exception responses."""
    id: UUID = Field(..., description="Exception ID")
    transaction_id: UUID = Field(..., description="Associated transaction ID")
    status: BreakStatus = Field(..., description="Break status")
    assigned_to: Optional[str] = Field(None, description="Assigned user")
    reviewed_by: Optional[str] = Field(None, description="Reviewer")
    reviewed_at: Optional[datetime] = Field(None, description="Review timestamp")
    resolved_at: Optional[datetime] = Field(None, description="Resolution timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class BreakAuditTrailBase(BaseModel):
    """Base Pydantic model for break audit trail."""
    action_type: str = Field(..., description="Type of action")
    action_by: str = Field(..., description="User who performed the action")
    action_description: Optional[str] = Field(None, description="Action description")
    action_data: Optional[Dict[str, Any]] = Field(None, description="Action data")


class BreakAuditTrailCreate(BreakAuditTrailBase):
    """Pydantic model for creating break audit trail entries."""
    exception_id: UUID = Field(..., description="Associated exception ID")


class BreakAuditTrailResponse(BreakAuditTrailBase):
    """Pydantic model for break audit trail responses."""
    id: UUID = Field(..., description="Audit trail entry ID")
    exception_id: UUID = Field(..., description="Associated exception ID")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True 