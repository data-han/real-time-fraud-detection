# Real-Time Fraud Detection System

A scalable, distributed real-time fraud detection system built with Apache Kafka, Apache Flink, PostgreSQL, and Streamlit. The system processes transaction streams from multiple banks, applies fraud detection rules, and provides real-time monitoring through an interactive dashboard.

---

## 📊 Architecture Overview

+-------------------+      +-------------------+      +-------------------+      +-------------------+
|   Producers       | ---> |   Kafka Cluster   | ---> |      Flink        | ---> |   PostgreSQL      |
| (Bank A, Bank B)  |      | (3 Brokers, KRaft)|      | (Stream/Archive)  |      | (transactions)    |
+-------------------+      +-------------------+      +-------------------+      +-------------------+
                                                           |
                                                           v
                                                +-------------------+
                                                |   Kafka Topic     |
                                                |  (fraud-alerts)   |
                                                +-------------------+
                                                           |
                                                           v
                                                +-------------------+
                                                |    Streamlit      |
                                                |    Dashboard      |
                                                +-------------------+

**Data Flow:**
1. Producers (Bank A, Bank B) generate transactions and send them to the Kafka cluster.
2. Kafka brokers store and replicate transaction streams.
3. Flink consumes transactions from Kafka:
   - Archives all transactions to PostgreSQL.
   - Detects fraud and publishes alerts to the `fraud-alerts` Kafka topic.
4. Streamlit dashboard consumes fraud alerts from Kafka and displays real-time analytics.

## 🏗️ System Components

### 1. **Kafka Cluster (KRaft Mode)**
**Purpose**: Distributed message broker for high-throughput transaction streaming

**Architecture**:
- **3 Kafka Brokers** (`kafka-1`, `kafka-2`, `kafka-3`)
  - Store and serve transaction data
  - Provide fault tolerance through replication
  - Each exposed on ports: 9092, 9093, 9094
  - Each listens on port 9092 inside its own isolated container
  - KAFKA_PROCESS_ROLES: broker — they only broker messages
  - Each has its own persistent volume (kafka_1_data, kafka_2_data, kafka_3_data)
  
- **1 Kafka Controller** 
  - Manages cluster metadata and leader elections
  - Replaces ZooKeeper in KRaft mode
  - Listens on ports 9093, 9094, 9095 inside its container (for broker communication)
  - Exposed on port 19093, 19094, 19095
  - KAFKA_PROCESS_ROLES: controller — only manages, doesn't broker
  - Has its own volume (kafka_controller_data)

**Topics**:
- `transactions` (3 partitions, replication factor: 3) - Raw transaction stream
- `fraud-alerts` (3 partitions, replication factor: 3) - Detected fraud events

**Rationale**: 
- KRaft mode eliminates ZooKeeper dependency, simplifying operations
- 3-broker setup provides high availability and fault tolerance
- Partitioning enables horizontal scaling for high-volume transaction processing

### 2. **Transaction Producers**
**Purpose**: Simulate real-world transaction generation from multiple banks

**Components**:
- **Bank A Producer**: Generates 50 transactions/second (users 1000-4999)
- **Bank B Producer**: Generates 30 transactions/second (users 5000-9999)

**Transaction Data Example**:
```json
{
  "transaction_id": "uuid",
  "bank_id": "BANK_A|BANK_B",
  "payment_system": "VISA|MasterCard|AMEX",
  "card_number": "4###############",
  "user_id": 1000-9999,
  "amount": 1.0-10000.0,
  "currency": "USD",
  "merchant": "Company Name",
  "country": "ISO Country Code",
  "timestamp": "2025-12-16T10:30:45+00:00"
}
```

**Rationale**:
- Realistic transaction patterns for testing fraud detection rules
- Configurable TPS allows load testing
- Easily scalable to add more banks/payment channels

---

### 3. **Flink + PostgreSQL**
- Flink jobs consume transactions from Kafka, archive to PostgreSQL, and detect fraud.
- Fraud alerts are published to the `fraud-alerts` topic.

---

### 4. **Streamlit Dashboard**
- Consumes fraud alerts from Kafka and displays real-time analytics and transaction metrics.

---

## 🚀 Quickstart

1. **Start Docker Compose**
   ```sh
   docker compose down -v && docker compose up -d
   ```

2. **Create Topics (if needed)**
   ```sh
   docker exec -it kafka-1 /opt/kafka/bin/kafka-topics.sh --create --topic transactions --bootstrap-server localhost:9092 --partitions 3 --replication-factor 3
   docker exec -it kafka-1 /opt/kafka/bin/kafka-topics.sh --create --topic fraud-alerts --bootstrap-server localhost:9092 --partitions 3 --replication-factor 3
   ```

3. **Start Producers**
   ```sh
   docker compose up -d --build app-producer-bank-a app-producer-bank-b
   ```

4. **Start Flink and PostgreSQL**
   ```sh
   docker compose up -d --build flink-jobmanager flink-taskmanager postgres
   ```

5. **Run Streamlit Dashboard**
   ```sh
   streamlit run dashboard/streamlit_app.py
   ```

---

## 📝 Next Steps

- For higher TPS, consider time-series DBs like InfluxDB.
- For advanced analytics, explore ClickHouse or DruidDB.

