-- ============================================================================
-- Source: Kafka transactions topic
-- ============================================================================
CREATE TABLE transactions (
    transaction_id STRING,
    bank_id STRING,
    payment_system STRING,
    card_number STRING,
    user_id INT,
    amount DECIMAL(10, 2),
    currency STRING,
    merchant STRING,
    country STRING,
    `timestamp` STRING,
    ts AS CAST(REPLACE(REPLACE(`timestamp`, '+00:00', ''), 'T', ' ') AS TIMESTAMP(3)),  -- Remove timezone then cast
    WATERMARK FOR ts AS ts - INTERVAL '5' SECOND  -- Use ts for watermark
) WITH (
    'connector' = 'kafka',
    'topic' = 'transactions',
    'properties.bootstrap.servers' = 'kafka-1:9092,kafka-2:9092,kafka-3:9092',
    'properties.group.id' = 'flink-consumer',
    'scan.startup.mode' = 'latest-offset',
    'format' = 'json',
    'json.timestamp-format.standard' = 'ISO-8601'
);

-- ============================================================================
-- Sink 1: PostgreSQL - Archive ALL transactions
-- ============================================================================
CREATE TABLE transactions_archive (
    transaction_id STRING,
    bank_id STRING,
    payment_system STRING,
    card_number STRING,
    user_id INT,
    amount DECIMAL(10, 2),
    currency STRING,
    merchant STRING,
    country STRING,
    `timestamp` TIMESTAMP,
    PRIMARY KEY (transaction_id) NOT ENFORCED
) WITH (
    'connector' = 'jdbc',
    'url' = 'jdbc:postgresql://postgres:5432/transactions_db',
    'table-name' = 'transactions',
    'username' = 'transactions_user',
    'password' = 'transactions123',
    'driver' = 'org.postgresql.Driver'
);

-- ============================================================================
-- Sink 2: Kafka - Fraud alerts
-- ============================================================================
CREATE TABLE fraud_alerts (
    transaction_id STRING,
    bank_id STRING,
    payment_system STRING,
    card_number STRING,
    user_id INT,
    amount DECIMAL(10, 2),
    currency STRING,
    merchant STRING,
    country STRING,
    reason STRING,
    `timestamp` TIMESTAMP(3)
) WITH (
    'connector' = 'kafka',
    'topic' = 'fraud-alerts',
    'properties.bootstrap.servers' = 'kafka-1:9092,kafka-2:9092,kafka-3:9092',
    'properties.group.id' = 'fraud-alerts-reader',
    'scan.startup.mode' = 'earliest-offset',
    'format' = 'json'
);

-- ============================================================================
-- Job 1: Archive ALL transactions to PostgreSQL
-- ============================================================================
INSERT INTO transactions_archive
SELECT 
    transaction_id,
    bank_id,
    payment_system,
    card_number,
    user_id,
    amount,
    currency,
    merchant,
    country,
    ts
FROM transactions;

-- ============================================================================
-- Job 2: Fraud Detection - Rule 1: High-value transactions (amount > $1000)
-- ============================================================================
INSERT INTO fraud_alerts
SELECT 
    transaction_id,
    bank_id,
    payment_system,
    card_number,
    user_id,
    amount,
    currency,
    merchant,
    country,
    'High-value transaction (amount > $5000)' as reason,
    ts as `timestamp`
FROM transactions
WHERE amount > 5000;

-- ============================================================================
-- Job 3: Fraud Detection - Rule 2: Velocity check (>5 txns in 2 minutes)
-- ============================================================================
INSERT INTO fraud_alerts
SELECT 
    MAX(transaction_id) as transaction_id,
    MAX(bank_id) as bank_id,
    MAX(payment_system) as payment_system,
    MAX(card_number) as card_number,
    user_id,
    SUM(amount) as amount,
    MAX(currency) as currency,
    MAX(merchant) as merchant,
    MAX(country) as country,
    CONCAT('Velocity check: ', CAST(COUNT(*) AS STRING), ' transactions in 2 minutes') as reason,
    MAX(`ts`) as `timestamp`
FROM transactions
GROUP BY 
    user_id,
    TUMBLE(`ts`, INTERVAL '2' MINUTE)
HAVING COUNT(*) > 5;

-- -- ============================================================================
-- -- Job 4: Fraud Detection - Rule 3: Geographic anomaly (multiple countries in 1 hour)
-- -- ============================================================================
INSERT INTO fraud_alerts
SELECT 
    MAX(transaction_id) as transaction_id,
    MAX(bank_id) as bank_id,
    MAX(payment_system) as payment_system,
    MAX(card_number) as card_number,
    user_id,
    SUM(amount) as amount,
    MAX(currency) as currency,
    MAX(merchant) as merchant,
    CAST(COUNT(DISTINCT country) AS STRING) as country,  -- Changed: just show count instead of list
    CONCAT('Geographic anomaly: ', CAST(COUNT(DISTINCT country) AS STRING), ' countries in 1 hour') as reason,
    MAX(`ts`) as `timestamp`
FROM transactions
GROUP BY 
    user_id,
    TUMBLE(`ts`, INTERVAL '1' HOUR)
HAVING COUNT(DISTINCT country) > 2;