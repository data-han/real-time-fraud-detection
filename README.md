# real-time-fraud-detection

# Architecture
Producers (Bank A, Bank B) 
   ↓
Kafka (transactions topic)
   ↓
Flink (consumer + processor)
   ├── Archive: ALL transactions 
   |-- --> PostgreSQL: transactions table (all historical data)
   └── Stream: Fraud detected → Kafka (fraud-alerts topic)
         ↓
   Alert Consumer (reads fraud-alerts)
   ↓
Real-time dashboard 



# Set-up

1. Kafka
KRaft architecture with 3 Kafka brokers and 1 controller
Service breakdown:

a. kafka-1, kafka-2, kafka-3 — Kafka brokers (store data, serve clients)
- Each listens on port 9092 inside its own isolated container
- Exposed to the host on ports 9092, 9093, 9094 respectively
- KAFKA_PROCESS_ROLES: broker — they only broker messages
- Each has its own persistent volume (kafka_1_data, kafka_2_data, kafka_3_data)

b. kafka-controller — Kafka controller (manages cluster, leader election)
- Listens on ports 9093, 9094, 9095 inside its container (for broker communication)
- Exposed to the host on ports 19093, 19094, 19095
- KAFKA_PROCESS_ROLES: controller — only manages, doesn't broker
- Has its own volume (kafka_controller_data)

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

--> Produce message
single: `docker exec -it kafka opt/kafka/bin/kafka-console-producer.sh --topic transactions --bootstrap-server kafka:9092`

replication: `docker exec -it kafka-1 opt/kafka/bin/kafka-console-producer.sh --topic transactions --bootstrap-server kafka-1:9092`

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