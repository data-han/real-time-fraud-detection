import os
import json
import time
import random
from datetime import datetime, timezone
from faker import Faker
from kafka import KafkaProducer

fake = Faker()

# Kafka Configuration
BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
TOPIC = os.getenv("TOPIC", "transactions")

producer = KafkaProducer(
    bootstrap_servers=BROKER,
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    acks="all"
)

# Environment Variables
BANK_ID = os.getenv("BANK_ID", "UNKNOWN")
USER_ID_MIN = int(os.getenv("USER_ID_MIN", "1000"))
USER_ID_MAX = int(os.getenv("USER_ID_MAX", "9999"))
TPS = int(os.getenv("TPS", "50")) # Transactions Per Second
SLEEP_TIME = 1.0 / TPS

def generate_fake_transactions():
    """
    Generate a fake transaction record
    """
    return {
        "transaction_id": fake.uuid4(),
        "bank_id": BANK_ID,
        "payment_system": fake.random_element(elements=("VISA", "MasterCard", "AMEX")),
        "card_number": fake.numerify(text="4###############"),
        "user_id": fake.random_int(USER_ID_MIN, USER_ID_MAX),
        "amount": round(random.uniform(1.0, 1500.0), 2),
        "currency": "USD",
        "merchant": fake.company(),
        "country": fake.country_code(),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    }

if __name__ == "__main__":
    print(f"Starting producer... broker={BROKER}, topic={TOPIC}")
    try:
        while True:
            producer.send(TOPIC, value=generate_fake_transactions())
            time.sleep(SLEEP_TIME)
    except KeyboardInterrupt:
        print("Shutting down...")
        producer.flush(timeout=10)
        producer.close()

