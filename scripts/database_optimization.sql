-- FS Reconciliation Agents - Database Optimization Script
-- This script creates performance indexes, partitioning, and optimizations

-- ============================================================================
-- PERFORMANCE INDEXES
-- ============================================================================

-- Composite indexes for common query patterns
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_composite_security 
ON transactions(security_id, trade_date, amount) 
WHERE security_id IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_composite_source 
ON transactions(data_source, created_at, status) 
WHERE data_source IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_composite_dates 
ON transactions(trade_date, settlement_date, value_date) 
WHERE trade_date IS NOT NULL;

-- Exception indexes for filtering and reporting
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_exceptions_composite_status 
ON reconciliation_exceptions(break_type, severity, status, created_at);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_exceptions_composite_assignment 
ON reconciliation_exceptions(assigned_to, status, priority, created_at) 
WHERE assigned_to IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_exceptions_composite_financial 
ON reconciliation_exceptions(break_amount, break_currency, created_at) 
WHERE break_amount IS NOT NULL;

-- Audit trail indexes for compliance and reporting
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_trails_user_action 
ON audit_trails(user_id, action, created_at) 
WHERE user_id IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_trails_resource 
ON audit_trails(resource_type, resource_id, created_at) 
WHERE resource_type IS NOT NULL;

-- Transaction match indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_composite 
ON transaction_matches(transaction_id, matched_transaction_id, match_type, confidence_score);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_status 
ON transaction_matches(status, reviewed_by, created_at);

-- ============================================================================
-- PARTITIONING FOR LARGE TABLES
-- ============================================================================

-- Create partitioned table for reconciliation_exceptions (if table is large)
-- This helps with query performance and maintenance

-- Create partition function for monthly partitioning
CREATE OR REPLACE FUNCTION create_monthly_partition_function()
RETURNS TRIGGER AS $$
DECLARE
    partition_date DATE;
    partition_name TEXT;
    start_date DATE;
    end_date DATE;
BEGIN
    partition_date := DATE_TRUNC('month', NEW.created_at);
    partition_name := 'reconciliation_exceptions_' || TO_CHAR(partition_date, 'YYYY_MM');
    
    -- Check if partition exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = partition_name
    ) THEN
        -- Create partition
        start_date := partition_date;
        end_date := partition_date + INTERVAL '1 month';
        
        EXECUTE format(
            'CREATE TABLE %I PARTITION OF reconciliation_exceptions 
             FOR VALUES FROM (%L) TO (%L)',
            partition_name, start_date, end_date
        );
        
        -- Create indexes on partition
        EXECUTE format(
            'CREATE INDEX %I ON %I (break_type, severity, status)',
            partition_name || '_idx_break_type', partition_name
        );
        
        EXECUTE format(
            'CREATE INDEX %I ON %I (created_at)',
            partition_name || '_idx_created_at', partition_name
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for automatic partition creation
DROP TRIGGER IF EXISTS create_partition_trigger ON reconciliation_exceptions;
CREATE TRIGGER create_partition_trigger
    BEFORE INSERT ON reconciliation_exceptions
    FOR EACH ROW
    EXECUTE FUNCTION create_monthly_partition_function();

-- ============================================================================
-- QUERY OPTIMIZATION
-- ============================================================================

-- Create materialized views for common aggregations
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_exception_summary AS
SELECT 
    break_type,
    severity,
    status,
    COUNT(*) as count,
    SUM(break_amount) as total_amount,
    AVG(break_amount) as avg_amount,
    MIN(created_at) as first_occurrence,
    MAX(created_at) as last_occurrence
FROM reconciliation_exceptions
GROUP BY break_type, severity, status;

-- Create index on materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_exception_summary 
ON mv_exception_summary(break_type, severity, status);

-- Materialized view for transaction statistics
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_transaction_summary AS
SELECT 
    data_source,
    transaction_type,
    status,
    COUNT(*) as count,
    SUM(amount) as total_amount,
    AVG(amount) as avg_amount,
    MIN(created_at) as first_transaction,
    MAX(created_at) as last_transaction
FROM transactions
GROUP BY data_source, transaction_type, status;

-- Create index on materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_transaction_summary 
ON mv_transaction_summary(data_source, transaction_type, status);

-- ============================================================================
-- STATISTICS AND ANALYTICS
-- ============================================================================

-- Create function to refresh materialized views
CREATE OR REPLACE FUNCTION refresh_analytics_views()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_exception_summary;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_transaction_summary;
END;
$$ LANGUAGE plpgsql;

-- Create function for exception trend analysis
CREATE OR REPLACE FUNCTION get_exception_trends(
    days_back INTEGER DEFAULT 30
)
RETURNS TABLE (
    date DATE,
    break_type TEXT,
    count BIGINT,
    total_amount NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        DATE(created_at) as date,
        break_type,
        COUNT(*) as count,
        SUM(break_amount) as total_amount
    FROM reconciliation_exceptions
    WHERE created_at >= CURRENT_DATE - INTERVAL '1 day' * days_back
    GROUP BY DATE(created_at), break_type
    ORDER BY date DESC, break_type;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- PERFORMANCE MONITORING
-- ============================================================================

-- Create table for query performance monitoring
CREATE TABLE IF NOT EXISTS query_performance_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_hash TEXT NOT NULL,
    query_text TEXT NOT NULL,
    execution_time_ms INTEGER NOT NULL,
    rows_returned INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on performance log
CREATE INDEX IF NOT EXISTS idx_query_performance_log 
ON query_performance_log(query_hash, execution_time_ms, created_at);

-- Function to log slow queries
CREATE OR REPLACE FUNCTION log_slow_query(
    p_query_hash TEXT,
    p_query_text TEXT,
    p_execution_time_ms INTEGER,
    p_rows_returned INTEGER DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO query_performance_log (
        query_hash, 
        query_text, 
        execution_time_ms, 
        rows_returned
    ) VALUES (
        p_query_hash,
        p_query_text,
        p_execution_time_ms,
        p_rows_returned
    );
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- MAINTENANCE PROCEDURES
-- ============================================================================

-- Create function for database maintenance
CREATE OR REPLACE FUNCTION perform_database_maintenance()
RETURNS VOID AS $$
BEGIN
    -- Update table statistics
    ANALYZE transactions;
    ANALYZE reconciliation_exceptions;
    ANALYZE transaction_matches;
    ANALYZE audit_trails;
    
    -- Refresh materialized views
    PERFORM refresh_analytics_views();
    
    -- Clean up old performance logs (keep last 30 days)
    DELETE FROM query_performance_log 
    WHERE created_at < CURRENT_DATE - INTERVAL '30 days';
    
    -- Vacuum tables
    VACUUM ANALYZE transactions;
    VACUUM ANALYZE reconciliation_exceptions;
    VACUUM ANALYZE transaction_matches;
    VACUUM ANALYZE audit_trails;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- CONFIGURATION OPTIMIZATIONS
-- ============================================================================

-- Set optimal PostgreSQL configuration for reconciliation workloads
-- Note: These should be set in postgresql.conf, but we'll document them here

/*
# Memory Configuration
shared_buffers = 256MB                    # 25% of available RAM
effective_cache_size = 1GB                # 75% of available RAM
work_mem = 4MB                            # For complex queries
maintenance_work_mem = 64MB               # For maintenance operations

# WAL Configuration
wal_buffers = 16MB                        # WAL buffer size
checkpoint_completion_target = 0.9        # Spread checkpoint writes
wal_writer_delay = 200ms                  # WAL writer frequency

# Query Planner
random_page_cost = 1.1                    # SSD optimization
effective_io_concurrency = 200            # Parallel I/O
default_statistics_target = 100           # Better query planning

# Connection Settings
max_connections = 100                     # Adjust based on load
shared_preload_libraries = 'pg_stat_statements'  # Query monitoring
*/

-- ============================================================================
-- MONITORING QUERIES
-- ============================================================================

-- Query to monitor index usage
-- SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
-- FROM pg_stat_user_indexes
-- ORDER BY idx_scan DESC;

-- Query to monitor slow queries
-- SELECT query_hash, AVG(execution_time_ms) as avg_time, COUNT(*) as executions
-- FROM query_performance_log
-- WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
-- GROUP BY query_hash
-- HAVING AVG(execution_time_ms) > 1000
-- ORDER BY avg_time DESC;

-- Query to monitor table sizes
-- SELECT 
--     schemaname,
--     tablename,
--     pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
-- FROM pg_tables
-- WHERE schemaname = 'public'
-- ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

COMMIT;
