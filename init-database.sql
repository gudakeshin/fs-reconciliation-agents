-- FS Reconciliation Agents Database Initialization Script

-- Create tables for transactions
CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(255) UNIQUE NOT NULL,
    amount DECIMAL(20, 8) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    trade_date DATE,
    settlement_date DATE,
    security_id VARCHAR(50),
    transaction_type VARCHAR(50),
    status VARCHAR(50) DEFAULT 'pending',
    data_source VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transaction_matches (
    id SERIAL PRIMARY KEY,
    transaction_id INTEGER REFERENCES transactions(id),
    matched_transaction_id INTEGER REFERENCES transactions(id),
    match_confidence DECIMAL(5, 4),
    match_criteria JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create tables for reconciliation breaks
CREATE TABLE IF NOT EXISTS reconciliation_exceptions (
    id SERIAL PRIMARY KEY,
    break_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) DEFAULT 'medium',
    status VARCHAR(20) DEFAULT 'open',
    description TEXT,
    affected_transactions JSONB,
    resolution_actions JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    resolved_by VARCHAR(100)
);

-- Create audit trail tables
CREATE TABLE IF NOT EXISTS audit_trail (
    id SERIAL PRIMARY KEY,
    action_type VARCHAR(50) NOT NULL,
    user_id VARCHAR(100),
    entity_type VARCHAR(50),
    entity_id INTEGER,
    changes JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_transactions_external_id ON transactions(external_id);
CREATE INDEX IF NOT EXISTS idx_transactions_security_id ON transactions(security_id);
CREATE INDEX IF NOT EXISTS idx_transactions_trade_date ON transactions(trade_date);
CREATE INDEX IF NOT EXISTS idx_reconciliation_exceptions_break_type ON reconciliation_exceptions(break_type);
CREATE INDEX IF NOT EXISTS idx_reconciliation_exceptions_status ON reconciliation_exceptions(status);
CREATE INDEX IF NOT EXISTS idx_audit_trail_timestamp ON audit_trail(timestamp);

-- Insert some sample data
INSERT INTO transactions (external_id, amount, currency, trade_date, settlement_date, security_id, transaction_type, status, data_source) VALUES
('TXN001', 1000000.00, 'USD', '2024-01-15', '2024-01-17', 'US912810TM08', 'BUY', 'matched', 'internal'),
('TXN002', 500000.00, 'EUR', '2024-01-16', '2024-01-18', 'DE000BA001001', 'SELL', 'pending', 'external'),
('TXN003', 750000.00, 'GBP', '2024-01-17', '2024-01-19', 'GB0002875804', 'BUY', 'matched', 'internal');

INSERT INTO reconciliation_exceptions (break_type, severity, status, description, affected_transactions) VALUES
('security_id', 'high', 'open', 'Security ID mismatch for transaction TXN002', '[{"transaction_id": "TXN002", "expected": "DE000BA001001", "actual": "DE000BA001002"}]'),
('market_price', 'medium', 'open', 'Price difference exceeds threshold', '[{"transaction_id": "TXN003", "expected_price": 750000.00, "actual_price": 755000.00}]');

-- Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers to automatically update the updated_at column
CREATE TRIGGER update_transactions_updated_at BEFORE UPDATE ON transactions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); 