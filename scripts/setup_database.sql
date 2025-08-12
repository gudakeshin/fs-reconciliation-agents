-- Database setup script for FS Reconciliation Agents
-- This script creates the necessary tables for audit trail and system logs

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create audit_trail table
CREATE TABLE IF NOT EXISTS audit_trail (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    action_type VARCHAR(100) NOT NULL,
    action_description TEXT,
    action_data JSONB,
    user_id VARCHAR(100),
    user_name VARCHAR(255),
    user_email VARCHAR(255),
    user_role VARCHAR(50),
    session_id VARCHAR(100),
    ip_address VARCHAR(45),
    user_agent TEXT,
    entity_type VARCHAR(50),
    entity_id UUID,
    entity_external_id VARCHAR(255),
    processing_time_ms INTEGER,
    memory_usage_mb NUMERIC(10, 2),
    ai_model_used VARCHAR(100),
    ai_confidence_score NUMERIC(5, 4),
    ai_reasoning JSONB,
    regulatory_requirement VARCHAR(100),
    compliance_category VARCHAR(50),
    data_classification VARCHAR(50),
    severity VARCHAR(20) NOT NULL DEFAULT 'info',
    is_successful BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT,
    error_code VARCHAR(50),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create system_logs table
CREATE TABLE IF NOT EXISTS system_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    log_level VARCHAR(20) NOT NULL,
    log_message TEXT NOT NULL,
    log_data JSONB,
    component VARCHAR(100),
    sub_component VARCHAR(100),
    function_name VARCHAR(255),
    line_number INTEGER,
    exception_type VARCHAR(100),
    exception_message TEXT,
    stack_trace TEXT,
    execution_time_ms INTEGER,
    memory_usage_mb NUMERIC(10, 2),
    cpu_usage_percent NUMERIC(5, 2),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create data_lineage table
CREATE TABLE IF NOT EXISTS data_lineage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_system VARCHAR(100) NOT NULL,
    source_file VARCHAR(255),
    source_record_id VARCHAR(255),
    source_timestamp TIMESTAMP,
    processing_step VARCHAR(100) NOT NULL,
    processing_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    processing_user VARCHAR(100),
    transformation_type VARCHAR(50),
    transformation_rules JSONB,
    transformation_result JSONB,
    data_quality_score NUMERIC(5, 4),
    validation_errors JSONB,
    data_quality_issues JSONB,
    parent_lineage_id UUID REFERENCES data_lineage(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create user_activity table
CREATE TABLE IF NOT EXISTS user_activity (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(100) NOT NULL,
    user_name VARCHAR(255),
    user_email VARCHAR(255),
    user_role VARCHAR(50),
    session_id VARCHAR(100) NOT NULL,
    login_timestamp TIMESTAMP,
    logout_timestamp TIMESTAMP,
    session_duration_seconds INTEGER,
    activity_type VARCHAR(100) NOT NULL,
    activity_description TEXT,
    activity_data JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    device_type VARCHAR(50),
    response_time_ms INTEGER,
    page_load_time_ms INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create compliance_records table
CREATE TABLE IF NOT EXISTS compliance_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    regulatory_framework VARCHAR(100) NOT NULL,
    compliance_requirement VARCHAR(255) NOT NULL,
    compliance_category VARCHAR(100),
    record_type VARCHAR(100) NOT NULL,
    record_id UUID NOT NULL,
    record_summary TEXT,
    compliance_status VARCHAR(50) NOT NULL DEFAULT 'pending',
    compliance_score NUMERIC(5, 4),
    compliance_notes TEXT,
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMP,
    review_notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_audit_trail_action_type ON audit_trail(action_type);
CREATE INDEX IF NOT EXISTS idx_audit_trail_created_at ON audit_trail(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_trail_user_id ON audit_trail(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_trail_session_id ON audit_trail(session_id);
CREATE INDEX IF NOT EXISTS idx_audit_trail_entity_type ON audit_trail(entity_type);

CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(log_level);
CREATE INDEX IF NOT EXISTS idx_system_logs_created_at ON system_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_system_logs_component ON system_logs(component);

CREATE INDEX IF NOT EXISTS idx_user_activity_user_id ON user_activity(user_id);
CREATE INDEX IF NOT EXISTS idx_user_activity_session_id ON user_activity(session_id);
CREATE INDEX IF NOT EXISTS idx_user_activity_created_at ON user_activity(created_at);

-- Grant permissions to fs_user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO fs_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO fs_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO fs_user;

-- Create a function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_data_lineage_updated_at 
    BEFORE UPDATE ON data_lineage 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_compliance_records_updated_at 
    BEFORE UPDATE ON compliance_records 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
