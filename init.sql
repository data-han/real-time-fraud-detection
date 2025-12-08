-- Database creation
-- SELECT 'CREATE DATABASE transactions_db'
-- WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'transactions_db')\gexec

-- Table for ALL transactions
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id VARCHAR(255) PRIMARY KEY,
    user_id INT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    bank_id VARCHAR(50),
    payment_system VARCHAR(50),
    card_number VARCHAR(20),
    merchant VARCHAR(255),
    country VARCHAR(10),
    currency VARCHAR(10),
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for fraud detection queries
CREATE INDEX IF NOT EXISTS idx_user_id ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_timestamp ON transactions(timestamp);
CREATE INDEX IF NOT EXISTS idx_amount ON transactions(amount);
CREATE INDEX IF NOT EXISTS idx_bank_id ON transactions(bank_id);
CREATE INDEX IF NOT EXISTS idx_user_timestamp ON transactions(user_id, timestamp DESC);