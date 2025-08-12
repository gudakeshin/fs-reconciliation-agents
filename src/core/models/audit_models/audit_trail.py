"""
Audit trail models for the FS Reconciliation Agents application.

This module defines the data structures for comprehensive audit trails,
ensuring full traceability of all reconciliation activities for compliance.
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


class AuditActionType(str, Enum):
    """Enumeration of audit action types."""
    # Data operations
    DATA_INGESTED = "data_ingested"
    DATA_NORMALIZED = "data_normalized"
    DATA_VALIDATED = "data_validated"
    
    # Matching operations
    MATCH_ATTEMPTED = "match_attempted"
    MATCH_CREATED = "match_created"
    MATCH_REJECTED = "match_rejected"
    MATCH_APPROVED = "match_approved"
    
    # Exception operations
    EXCEPTION_DETECTED = "exception_detected"
    EXCEPTION_CLASSIFIED = "exception_classified"
    EXCEPTION_ASSIGNED = "exception_assigned"
    EXCEPTION_REVIEWED = "exception_reviewed"
    EXCEPTION_RESOLVED = "exception_resolved"
    
    # Resolution operations
    RESOLUTION_ATTEMPTED = "resolution_attempted"
    RESOLUTION_APPROVED = "resolution_approved"
    RESOLUTION_REJECTED = "resolution_rejected"
    JOURNAL_ENTRY_CREATED = "journal_entry_created"
    
    # System operations
    SYSTEM_CONFIGURATION_CHANGED = "system_configuration_changed"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_PERMISSION_CHANGED = "user_permission_changed"
    
    # AI operations
    AI_ANALYSIS_REQUESTED = "ai_analysis_requested"
    AI_ANALYSIS_COMPLETED = "ai_analysis_completed"
    AI_SUGGESTION_GENERATED = "ai_suggestion_generated"
    AI_SUGGESTION_ACCEPTED = "ai_suggestion_accepted"
    AI_SUGGESTION_REJECTED = "ai_suggestion_rejected"


class AuditSeverity(str, Enum):
    """Enumeration of audit severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditTrail(Base):
    """SQLAlchemy model for comprehensive audit trail."""
    __tablename__ = "audit_trail"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Action details
    action_type = Column(String(100), nullable=False)
    action_description = Column(Text, nullable=True)
    action_data = Column(JSON, nullable=True)
    
    # User information
    user_id = Column(String(100), nullable=True)
    user_name = Column(String(255), nullable=True)
    user_email = Column(String(255), nullable=True)
    user_role = Column(String(50), nullable=True)
    
    # System information
    session_id = Column(String(100), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    
    # Entity information
    entity_type = Column(String(50), nullable=True)  # transaction, exception, match, etc.
    entity_id = Column(PostgresUUID(as_uuid=True), nullable=True)
    entity_external_id = Column(String(255), nullable=True)
    
    # Performance metrics
    processing_time_ms = Column(Integer, nullable=True)
    memory_usage_mb = Column(Numeric(10, 2), nullable=True)
    
    # AI-specific fields
    ai_model_used = Column(String(100), nullable=True)
    ai_confidence_score = Column(Numeric(5, 4), nullable=True)
    ai_reasoning = Column(JSON, nullable=True)
    
    # Compliance fields
    regulatory_requirement = Column(String(100), nullable=True)
    compliance_category = Column(String(50), nullable=True)
    data_classification = Column(String(50), nullable=True)
    
    # Severity and status
    severity = Column(String(20), nullable=False, default=AuditSeverity.INFO.value)
    is_successful = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Indexes for performance
    __table_args__ = (
        # Index for querying by action type
        {'postgresql_partition_by': 'LIST (action_type)'}
    )


class DataLineage(Base):
    """SQLAlchemy model for data lineage tracking."""
    __tablename__ = "data_lineage"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Source information
    source_system = Column(String(100), nullable=False)
    source_file = Column(String(255), nullable=True)
    source_record_id = Column(String(255), nullable=True)
    source_timestamp = Column(DateTime, nullable=True)
    
    # Processing information
    processing_step = Column(String(100), nullable=False)
    processing_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    processing_user = Column(String(100), nullable=True)
    
    # Data transformation
    transformation_type = Column(String(50), nullable=True)  # normalize, validate, enrich, etc.
    transformation_rules = Column(JSON, nullable=True)
    transformation_result = Column(JSON, nullable=True)
    
    # Quality metrics
    data_quality_score = Column(Numeric(5, 4), nullable=True)
    validation_errors = Column(JSON, nullable=True)
    data_quality_issues = Column(JSON, nullable=True)
    
    # Relationships
    parent_lineage_id = Column(PostgresUUID(as_uuid=True), ForeignKey("data_lineage.id"), nullable=True)
    children = relationship("DataLineage", backref="parent", remote_side="DataLineage.id")
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserActivity(Base):
    """SQLAlchemy model for user activity tracking."""
    __tablename__ = "user_activity"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # User information
    user_id = Column(String(100), nullable=False, index=True)
    user_name = Column(String(255), nullable=True)
    user_email = Column(String(255), nullable=True)
    user_role = Column(String(50), nullable=True)
    
    # Session information
    session_id = Column(String(100), nullable=False, index=True)
    login_timestamp = Column(DateTime, nullable=True)
    logout_timestamp = Column(DateTime, nullable=True)
    session_duration_seconds = Column(Integer, nullable=True)
    
    # Activity details
    activity_type = Column(String(100), nullable=False)
    activity_description = Column(Text, nullable=True)
    activity_data = Column(JSON, nullable=True)
    
    # System information
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    device_type = Column(String(50), nullable=True)
    
    # Performance metrics
    response_time_ms = Column(Integer, nullable=True)
    page_load_time_ms = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class SystemLog(Base):
    """SQLAlchemy model for system-level logging."""
    __tablename__ = "system_logs"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Log details
    log_level = Column(String(20), nullable=False)  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    log_message = Column(Text, nullable=False)
    log_data = Column(JSON, nullable=True)
    
    # Component information
    component = Column(String(100), nullable=True)  # api, agent, ui, database, etc.
    sub_component = Column(String(100), nullable=True)
    function_name = Column(String(255), nullable=True)
    line_number = Column(Integer, nullable=True)
    
    # Error information
    exception_type = Column(String(100), nullable=True)
    exception_message = Column(Text, nullable=True)
    stack_trace = Column(Text, nullable=True)
    
    # Performance metrics
    execution_time_ms = Column(Integer, nullable=True)
    memory_usage_mb = Column(Numeric(10, 2), nullable=True)
    cpu_usage_percent = Column(Numeric(5, 2), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ComplianceRecord(Base):
    """SQLAlchemy model for compliance-specific records."""
    __tablename__ = "compliance_records"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Compliance information
    regulatory_framework = Column(String(100), nullable=False)  # SOX, GDPR, Basel III, etc.
    compliance_requirement = Column(String(255), nullable=False)
    compliance_category = Column(String(100), nullable=True)
    
    # Record details
    record_type = Column(String(100), nullable=False)  # audit_trail, data_lineage, user_activity
    record_id = Column(PostgresUUID(as_uuid=True), nullable=False)
    record_summary = Column(Text, nullable=True)
    
    # Compliance status
    compliance_status = Column(String(50), nullable=False, default="pending")
    compliance_score = Column(Numeric(5, 4), nullable=True)
    compliance_notes = Column(Text, nullable=True)
    
    # Review information
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


# Pydantic models for API
class AuditTrailBase(BaseModel):
    """Base Pydantic model for audit trail."""
    action_type: AuditActionType = Field(..., description="Type of audit action")
    action_description: Optional[str] = Field(None, description="Action description")
    action_data: Optional[Dict[str, Any]] = Field(None, description="Action data")
    user_id: Optional[str] = Field(None, description="User ID")
    user_name: Optional[str] = Field(None, description="User name")
    user_email: Optional[str] = Field(None, description="User email")
    user_role: Optional[str] = Field(None, description="User role")
    session_id: Optional[str] = Field(None, description="Session ID")
    ip_address: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    entity_type: Optional[str] = Field(None, description="Entity type")
    entity_id: Optional[UUID] = Field(None, description="Entity ID")
    entity_external_id: Optional[str] = Field(None, description="Entity external ID")
    processing_time_ms: Optional[int] = Field(None, description="Processing time in milliseconds")
    memory_usage_mb: Optional[Decimal] = Field(None, description="Memory usage in MB")
    ai_model_used: Optional[str] = Field(None, description="AI model used")
    ai_confidence_score: Optional[Decimal] = Field(None, ge=0, le=1, description="AI confidence score")
    ai_reasoning: Optional[Dict[str, Any]] = Field(None, description="AI reasoning")
    regulatory_requirement: Optional[str] = Field(None, description="Regulatory requirement")
    compliance_category: Optional[str] = Field(None, description="Compliance category")
    data_classification: Optional[str] = Field(None, description="Data classification")
    severity: AuditSeverity = Field(..., description="Audit severity")
    is_successful: bool = Field(..., description="Whether the action was successful")
    error_message: Optional[str] = Field(None, description="Error message")
    error_code: Optional[str] = Field(None, description="Error code")


class AuditTrailCreate(AuditTrailBase):
    """Pydantic model for creating audit trail entries."""
    pass


class AuditTrailResponse(AuditTrailBase):
    """Pydantic model for audit trail responses."""
    id: UUID = Field(..., description="Audit trail entry ID")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True


class DataLineageBase(BaseModel):
    """Base Pydantic model for data lineage."""
    source_system: str = Field(..., description="Source system")
    source_file: Optional[str] = Field(None, description="Source file")
    source_record_id: Optional[str] = Field(None, description="Source record ID")
    source_timestamp: Optional[datetime] = Field(None, description="Source timestamp")
    processing_step: str = Field(..., description="Processing step")
    processing_user: Optional[str] = Field(None, description="Processing user")
    transformation_type: Optional[str] = Field(None, description="Transformation type")
    transformation_rules: Optional[Dict[str, Any]] = Field(None, description="Transformation rules")
    transformation_result: Optional[Dict[str, Any]] = Field(None, description="Transformation result")
    data_quality_score: Optional[Decimal] = Field(None, ge=0, le=1, description="Data quality score")
    validation_errors: Optional[Dict[str, Any]] = Field(None, description="Validation errors")
    data_quality_issues: Optional[Dict[str, Any]] = Field(None, description="Data quality issues")


class DataLineageCreate(DataLineageBase):
    """Pydantic model for creating data lineage entries."""
    parent_lineage_id: Optional[UUID] = Field(None, description="Parent lineage ID")


class DataLineageResponse(DataLineageBase):
    """Pydantic model for data lineage responses."""
    id: UUID = Field(..., description="Data lineage entry ID")
    parent_lineage_id: Optional[UUID] = Field(None, description="Parent lineage ID")
    processing_timestamp: datetime = Field(..., description="Processing timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class UserActivityBase(BaseModel):
    """Base Pydantic model for user activity."""
    user_id: str = Field(..., description="User ID")
    user_name: Optional[str] = Field(None, description="User name")
    user_email: Optional[str] = Field(None, description="User email")
    user_role: Optional[str] = Field(None, description="User role")
    session_id: str = Field(..., description="Session ID")
    login_timestamp: Optional[datetime] = Field(None, description="Login timestamp")
    logout_timestamp: Optional[datetime] = Field(None, description="Logout timestamp")
    session_duration_seconds: Optional[int] = Field(None, description="Session duration in seconds")
    activity_type: str = Field(..., description="Activity type")
    activity_description: Optional[str] = Field(None, description="Activity description")
    activity_data: Optional[Dict[str, Any]] = Field(None, description="Activity data")
    ip_address: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    device_type: Optional[str] = Field(None, description="Device type")
    response_time_ms: Optional[int] = Field(None, description="Response time in milliseconds")
    page_load_time_ms: Optional[int] = Field(None, description="Page load time in milliseconds")


class UserActivityCreate(UserActivityBase):
    """Pydantic model for creating user activity entries."""
    pass


class UserActivityResponse(UserActivityBase):
    """Pydantic model for user activity responses."""
    id: UUID = Field(..., description="User activity entry ID")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True


class ComplianceRecordBase(BaseModel):
    """Base Pydantic model for compliance records."""
    regulatory_framework: str = Field(..., description="Regulatory framework")
    compliance_requirement: str = Field(..., description="Compliance requirement")
    compliance_category: Optional[str] = Field(None, description="Compliance category")
    record_type: str = Field(..., description="Record type")
    record_id: UUID = Field(..., description="Record ID")
    record_summary: Optional[str] = Field(None, description="Record summary")
    compliance_status: str = Field(..., description="Compliance status")
    compliance_score: Optional[Decimal] = Field(None, ge=0, le=1, description="Compliance score")
    compliance_notes: Optional[str] = Field(None, description="Compliance notes")
    reviewed_by: Optional[str] = Field(None, description="Reviewed by")
    review_notes: Optional[str] = Field(None, description="Review notes")


class ComplianceRecordCreate(ComplianceRecordBase):
    """Pydantic model for creating compliance records."""
    pass


class ComplianceRecordUpdate(BaseModel):
    """Pydantic model for updating compliance records."""
    compliance_status: Optional[str] = Field(None, description="Compliance status")
    compliance_score: Optional[Decimal] = Field(None, ge=0, le=1, description="Compliance score")
    compliance_notes: Optional[str] = Field(None, description="Compliance notes")
    reviewed_by: Optional[str] = Field(None, description="Reviewed by")
    review_notes: Optional[str] = Field(None, description="Review notes")


class ComplianceRecordResponse(ComplianceRecordBase):
    """Pydantic model for compliance record responses."""
    id: UUID = Field(..., description="Compliance record ID")
    reviewed_at: Optional[datetime] = Field(None, description="Review timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True 