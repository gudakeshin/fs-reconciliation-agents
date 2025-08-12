#!/usr/bin/env python3
"""
Script to generate sample log data for testing the UI components in Docker.

This script creates sample audit trail and system log entries to populate
the database with realistic data for testing the log viewer and agent flow components.
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
import random
import uuid

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration for Docker
DATABASE_URL = "postgresql://reconciliation_user:reconciliation_password@database:5432/reconciliation_db"

# Sample data for generating realistic logs
SAMPLE_USERS = [
    {"id": "user_001", "name": "John Smith", "email": "john.smith@company.com", "role": "admin"},
    {"id": "user_002", "name": "Jane Doe", "email": "jane.doe@company.com", "role": "analyst"},
    {"id": "user_003", "name": "Bob Johnson", "email": "bob.johnson@company.com", "role": "manager"},
]

SAMPLE_COMPONENTS = [
    "api", "data_ingestion", "normalization", "matching", "exception_identification", 
    "resolution", "reporting", "ui", "database", "auth"
]

SAMPLE_ACTION_TYPES = [
    "data_ingested", "data_normalized", "data_validated", "match_attempted", 
    "match_created", "match_rejected", "match_approved", "exception_detected", 
    "exception_classified", "exception_assigned", "exception_reviewed", 
    "exception_resolved", "resolution_attempted", "resolution_approved", 
    "resolution_rejected", "journal_entry_created", "ai_analysis_requested", 
    "ai_analysis_completed", "ai_suggestion_generated", "ai_suggestion_accepted", 
    "ai_suggestion_rejected"
]

SAMPLE_AI_MODELS = [
    "gpt-4", "gpt-3.5-turbo", "claude-3-opus", "claude-3-sonnet", "claude-3-haiku"
]

SAMPLE_ENTITY_TYPES = [
    "transaction", "exception", "match", "journal_entry", "reconciliation_batch"
]

def generate_sample_system_logs(num_logs: int = 100) -> List[Dict[str, Any]]:
    """Generate sample system log entries."""
    logs = []
    log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    
    for i in range(num_logs):
        timestamp = datetime.utcnow() - timedelta(
            hours=random.randint(0, 24),
            minutes=random.randint(0, 60),
            seconds=random.randint(0, 60)
        )
        
        level = random.choices(log_levels, weights=[0.1, 0.6, 0.2, 0.08, 0.02])[0]
        component = random.choice(SAMPLE_COMPONENTS)
        
        # Generate realistic log messages based on component and level
        if component == "data_ingestion":
            messages = [
                "Processing CSV file: trades_2024_01_15.csv",
                "Validating file format and structure",
                "Extracted 1,247 records from source file",
                "Data validation completed successfully",
                "Error parsing CSV header row",
                "File upload completed in 2.3 seconds"
            ]
        elif component == "matching":
            messages = [
                "Attempting to match transaction ID: TXN-2024-001",
                "Found potential match with 95% confidence",
                "Match rejected due to amount discrepancy",
                "Match approved and committed to database",
                "No matches found for transaction",
                "Matching algorithm completed for batch"
            ]
        elif component == "exception_identification":
            messages = [
                "Detected exception in transaction processing",
                "Exception classified as 'amount_mismatch'",
                "Exception assigned to analyst for review",
                "Exception resolved with manual adjustment",
                "New exception pattern detected",
                "Exception processing completed"
            ]
        else:
            messages = [
                "Request processed successfully",
                "Database connection established",
                "User authentication successful",
                "API endpoint called",
                "Configuration loaded",
                "Background task started"
            ]
        
        log = {
            "id": str(uuid.uuid4()),
            "log_level": level,
            "log_message": random.choice(messages),
            "component": component,
            "sub_component": f"{component}_sub" if random.random() > 0.7 else None,
            "function_name": f"process_{component}" if random.random() > 0.5 else None,
            "line_number": random.randint(1, 500) if random.random() > 0.3 else None,
            "exception_type": "ValueError" if level in ["ERROR", "CRITICAL"] and random.random() > 0.7 else None,
            "exception_message": "Invalid data format" if level in ["ERROR", "CRITICAL"] and random.random() > 0.7 else None,
            "stack_trace": "Traceback (most recent call last):..." if level in ["ERROR", "CRITICAL"] and random.random() > 0.7 else None,
            "execution_time_ms": random.randint(10, 5000) if random.random() > 0.3 else None,
            "memory_usage_mb": round(random.uniform(50, 500), 2) if random.random() > 0.5 else None,
            "cpu_usage_percent": round(random.uniform(1, 80), 2) if random.random() > 0.5 else None,
            "created_at": timestamp,
            "log_data": json.dumps({"source": "sample_generator"}) if random.random() > 0.8 else None
        }
        logs.append(log)
    
    return logs

def generate_sample_audit_trail(num_entries: int = 150) -> List[Dict[str, Any]]:
    """Generate sample audit trail entries."""
    entries = []
    severities = ["info", "warning", "error", "critical"]
    
    for i in range(num_entries):
        timestamp = datetime.utcnow() - timedelta(
            hours=random.randint(0, 24),
            minutes=random.randint(0, 60),
            seconds=random.randint(0, 60)
        )
        
        user = random.choice(SAMPLE_USERS)
        action_type = random.choice(SAMPLE_ACTION_TYPES)
        entity_type = random.choice(SAMPLE_ENTITY_TYPES)
        severity = random.choices(severities, weights=[0.7, 0.2, 0.08, 0.02])[0]
        is_successful = random.random() > 0.1  # 90% success rate
        
        # Generate realistic action descriptions
        if action_type == "data_ingested":
            descriptions = [
                "Processed financial data file",
                "Ingested trade settlement data",
                "Loaded reconciliation batch",
                "Imported transaction records"
            ]
        elif action_type == "match_created":
            descriptions = [
                "Created match between trade and settlement",
                "Matched transaction with counterparty record",
                "Established reconciliation match",
                "Linked related transactions"
            ]
        elif action_type == "exception_detected":
            descriptions = [
                "Detected amount mismatch in transaction",
                "Found missing settlement record",
                "Identified duplicate transaction",
                "Discovered data quality issue"
            ]
        else:
            descriptions = [
                "Processed reconciliation request",
                "Updated transaction status",
                "Applied business rules",
                "Executed workflow step"
            ]
        
        entry = {
            "id": str(uuid.uuid4()),
            "action_type": action_type,
            "action_description": random.choice(descriptions),
            "action_data": json.dumps({
                "source_file": f"data_{random.randint(1, 100)}.csv",
                "record_count": random.randint(100, 10000),
                "processing_time": random.randint(100, 5000)
            }) if random.random() > 0.5 else None,
            "user_id": user["id"],
            "user_name": user["name"],
            "user_email": user["email"],
            "user_role": user["role"],
            "session_id": f"session_{random.randint(1, 10)}",
            "ip_address": f"192.168.1.{random.randint(1, 255)}",
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "entity_type": entity_type,
            "entity_id": str(uuid.uuid4()) if random.random() > 0.3 else None,
            "entity_external_id": f"EXT-{random.randint(1000, 9999)}" if random.random() > 0.5 else None,
            "processing_time_ms": random.randint(50, 3000),
            "memory_usage_mb": round(random.uniform(10, 200), 2),
            "ai_model_used": random.choice(SAMPLE_AI_MODELS) if random.random() > 0.6 else None,
            "ai_confidence_score": round(random.uniform(0.7, 0.99), 3) if random.random() > 0.7 else None,
            "ai_reasoning": json.dumps({
                "confidence_factors": ["amount_match", "date_match", "counterparty_match"],
                "decision_logic": "fuzzy_matching_algorithm"
            }) if random.random() > 0.8 else None,
            "regulatory_requirement": "SOX_404" if random.random() > 0.8 else None,
            "compliance_category": "financial_reporting" if random.random() > 0.8 else None,
            "data_classification": "confidential" if random.random() > 0.8 else None,
            "severity": severity,
            "is_successful": is_successful,
            "error_message": "Processing failed due to invalid data format" if not is_successful and random.random() > 0.5 else None,
            "error_code": "E001" if not is_successful and random.random() > 0.5 else None,
            "created_at": timestamp
        }
        entries.append(entry)
    
    return entries

async def insert_sample_data():
    """Insert sample data into the database."""
    try:
        # Create database engine
        engine = create_engine(DATABASE_URL)
        
        # Generate sample data
        logger.info("Generating sample system logs...")
        system_logs = generate_sample_system_logs(200)
        
        logger.info("Generating sample audit trail...")
        audit_entries = generate_sample_audit_trail(300)
        
        # Insert system logs
        logger.info("Inserting system logs...")
        with engine.connect() as conn:
            for log in system_logs:
                conn.execute(text("""
                    INSERT INTO system_logs (
                        id, log_level, log_message, component, sub_component, 
                        function_name, line_number, exception_type, exception_message, 
                        stack_trace, execution_time_ms, memory_usage_mb, cpu_usage_percent, 
                        created_at, log_data
                    ) VALUES (
                        :id, :log_level, :log_message, :component, :sub_component,
                        :function_name, :line_number, :exception_type, :exception_message,
                        :stack_trace, :execution_time_ms, :memory_usage_mb, :cpu_usage_percent,
                        :created_at, :log_data
                    )
                """), log)
            conn.commit()
        
        # Insert audit trail
        logger.info("Inserting audit trail entries...")
        with engine.connect() as conn:
            for entry in audit_entries:
                conn.execute(text("""
                    INSERT INTO audit_trail (
                        id, action_type, action_description, action_data, user_id, user_name,
                        user_email, user_role, session_id, ip_address, user_agent, entity_type,
                        entity_id, entity_external_id, processing_time_ms, memory_usage_mb,
                        ai_model_used, ai_confidence_score, ai_reasoning, regulatory_requirement,
                        compliance_category, data_classification, severity, is_successful,
                        error_message, error_code, created_at
                    ) VALUES (
                        :id, :action_type, :action_description, :action_data, :user_id, :user_name,
                        :user_email, :user_role, :session_id, :ip_address, :user_agent, :entity_type,
                        :entity_id, :entity_external_id, :processing_time_ms, :memory_usage_mb,
                        :ai_model_used, :ai_confidence_score, :ai_reasoning, :regulatory_requirement,
                        :compliance_category, :data_classification, :severity, :is_successful,
                        :error_message, :error_code, :created_at
                    )
                """), entry)
            conn.commit()
        
        logger.info("Sample data inserted successfully!")
        logger.info(f"Inserted {len(system_logs)} system logs")
        logger.info(f"Inserted {len(audit_entries)} audit trail entries")
        
    except Exception as e:
        logger.error(f"Error inserting sample data: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(insert_sample_data())
