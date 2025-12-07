FROM flink:1.18-scala_2.12

# Kafka connector (to create Kafka tables)
RUN wget -P /opt/flink/lib/ \
    https://repo.maven.apache.org/maven2/org/apache/flink/flink-sql-connector-kafka/3.0.2-1.18/flink-sql-connector-kafka-3.0.2-1.18.jar

# JDBC connector (allows Flink to connect to relational databases)
RUN wget -P /opt/flink/lib/ \
    https://repo.maven.apache.org/maven2/org/apache/flink/flink-connector-jdbc/3.1.2-1.18/flink-connector-jdbc-3.1.2-1.18.jar

# PostgreSQL driver (allows Flink to connect to PostgreSQL databases)
RUN wget -P /opt/flink/lib/ \
    https://jdbc.postgresql.org/download/postgresql-42.7.1.jar

# Copy SQL job files
COPY flink/jobs/ /opt/flink/jobs/