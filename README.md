# Real-Time Fraud Detection System

A scalable, distributed real-time fraud detection system built with Apache Kafka, Apache Flink, PostgreSQL, and Streamlit. The system processes transaction streams from multiple banks, applies fraud detection rules, and provides real-time monitoring through an interactive dashboard.

---

## 📊 Architecture Overview

Producers (Bank A, Bank B) 
   ↓
Apache Kafka Cluster
   ↓
Apache Flink (consumer + processor)
   ├── Archive: ALL transactions 
   |-- --> PostgreSQL: transactions table (all historical data)
   └── Stream: Fraud detected → Kafka (fraud-alerts topic)
   ↓
Streamlit dashboard 



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


c. Data flow
You (Mac) → localhost:9092 → kafka-1:9092 (inside Docker)
↓
kafka-1 replicates to kafka-2:9092 and kafka-3:9092
↓
All 3 brokers report to kafka-controller:9093/9094/9095 for coordination

z. Run Kafka
--> Start Docker
`docker compose down -v && docker compose up -d`
--> Get into the container
`docker exec -it kafka bash` 
--> Create topic - transactions
single: `docker exec -it kafka opt/kafka/bin/kafka-topics.sh --create --topic transactions --bootstrap-server kafka:9092 --partitions 1 --replication-factor 1`

replication: `docker exec -it kafka-1 opt/kafka/bin/kafka-topics.sh --create --topic transactions --bootstrap-server kafka-1:9092 --partitions 3 --replication-factor 3`

--> List topic
replication: `docker exec -it kafka-1 opt/kafka/bin/kafka-topics.sh --list --bootstrap-server kafka-1:9092`

---

### 2. **Transaction Producers**
**Purpose**: Simulate real-world transaction generation from multiple banks

**Components**:
- **Bank A Producer**: Generates 50 transactions/second (users 1000-4999)
- **Bank B Producer**: Generates 30 transactions/second (users 5000-9999)

**Transaction Data**:
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


**Rationale**:
- Realistic transaction patterns for testing fraud detection rules
- Configurable TPS allows load testing
- Easily scalable to add more banks/payment channels





--> Consume message
single: `docker exec -it kafka opt/kafka/bin/kafka-console-consumer.sh --topic transactions --bootstrap-server kafka:9092 --from-beginning`

replication: `docker exec -it kafka-1 opt/kafka/bin/kafka-console-consumer.sh --topic transactions --bootstrap-server kafka-1:9092 --from-beginning`

2. Producer
--> dockerfile
    `docker compose up -d --build app-producer-bank-a app-producer-bank-b`
    `docker build -t rtfd-producer:local -f producers/Dockerfile .`
--> docker compose

--> can scale to add more producer - different banks, mobile payments etc. to make it more realistic

3. Flink + Postgres
--> Dockerfile
`docker compose up -d --build flink-jobmanager flink-taskmanager`


4. Grafana/ streamlit



next steps
for higher tps , can consider time-series db like influxdb, realtime analytics using clickhouse/ druiddb