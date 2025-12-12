import streamlit as st
import pandas as pd
import psycopg2
from kafka import KafkaConsumer
import json
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from threading import Thread
import time

# Page config
st.set_page_config(page_title="Fraud Detection Dashboard", layout="wide", page_icon="🚨")

# Postgres Database connection - Don't cache, create fresh each time
def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="transactions_db",
        user="transactions_user",
        password="transactions123"
    )

# Kafka consumer for fraud alerts - stays cached during session
@st.cache_resource
def get_fraud_consumer():
    return KafkaConsumer(
        'fraud-alerts',
        bootstrap_servers='localhost:9092',
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset='latest',
        enable_auto_commit=True,
        group_id='streamlit-dashboard',
        consumer_timeout_ms=1000  # Don't block forever
    )

# Query functions - Create and close connection each time
def query_db(query):
    conn = get_db_connection()
    try:
        df = pd.read_sql(query, conn)
        return df
    finally:
        conn.close()

def get_recent_transactions(limit=100):
    query = f"""
        SELECT * FROM transactions 
        ORDER BY timestamp DESC 
        LIMIT {limit}
    """
    return query_db(query)

def get_transaction_stats():
    query = """
        SELECT 
            COUNT(*) as total_transactions,
            SUM(amount) as total_amount,
            AVG(amount) as avg_amount,
            COUNT(DISTINCT user_id) as unique_users,
            COUNT(DISTINCT country) as unique_countries
        FROM transactions
        WHERE timestamp > NOW() - INTERVAL '1 hour'
    """
    return query_db(query)

def get_transactions_by_bank():
    query = """
        SELECT 
            bank_id,
            COUNT(*) as transaction_count,
            SUM(amount) as total_amount
        FROM transactions
        WHERE timestamp > NOW() - INTERVAL '1 hour'
        GROUP BY bank_id
    """
    return query_db(query)

def get_top_merchants():
    query = """
        SELECT 
            merchant,
            COUNT(*) as transaction_count,
            SUM(amount) as total_amount
        FROM transactions
        WHERE timestamp > NOW() - INTERVAL '1 hour'
        GROUP BY merchant
        ORDER BY transaction_count DESC
        LIMIT 10
    """
    return query_db(query)

def get_transactions_over_time():
    query = """
        SELECT 
            DATE_TRUNC('minute', timestamp) as minute,
            COUNT(*) as count,
            AVG(amount) as avg_amount
        FROM transactions
        WHERE timestamp > NOW() - INTERVAL '1 hour'
        GROUP BY minute
        ORDER BY minute
    """
    return query_db(query)

# Main dashboard
st.title("🚨 Real-Time Fraud Detection Dashboard")

# Create tabs
tab1, tab2, tab3 = st.tabs(["📊 Overview", "🔍 Fraud Alerts", "📈 Analytics"])

# Tab 1: Overview
# Tab 1: Overview
with tab1:
    st.header("Transaction Overview (Last Hour)")
    
    # Metrics
    stats = get_transaction_stats()
    if not stats.empty:
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Total Transactions", f"{stats['total_transactions'][0] or 0:,}")
        with col2:
            # Use smaller font in the label, larger number
            total_amount = stats['total_amount'][0] or 0
            st.metric(
                label="Total Amount",
                value=f"${total_amount/1000:.1f}K",  # Show in thousands
                help=f"Exact: ${total_amount:,.2f}"  # Hover for exact value
            )
        with col3:
            avg_amount = stats['avg_amount'][0] or 0
            st.metric("Avg Transaction", f"${avg_amount:,.2f}")
        with col4:
            st.metric("Unique Users", f"{stats['unique_users'][0] or 0:,}")
        with col5:
            st.metric("Countries", f"{stats['unique_countries'][0] or 0:,}")
    
    # Transactions over time
    st.subheader("Transactions Per Minute")
    time_data = get_transactions_over_time()
    if not time_data.empty:
        fig = px.line(time_data, x='minute', y='count', 
                     title='Transaction Volume Over Time',
                     labels={'count': 'Transaction Count', 'minute': 'Time'})
        st.plotly_chart(fig, use_container_width=True)
    
    # Bank comparison
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Transactions by Bank")
        bank_data = get_transactions_by_bank()
        if not bank_data.empty:
            fig = px.pie(bank_data, values='transaction_count', names='bank_id',
                        title='Transaction Distribution')
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Top 10 Merchants")
        merchant_data = get_top_merchants()
        if not merchant_data.empty:
            fig = px.bar(merchant_data, x='merchant', y='transaction_count',
                        title='Most Active Merchants')
            st.plotly_chart(fig, use_container_width=True)

# Tab 2: Fraud Alerts
with tab2:
    st.header("🚨 Live Fraud Alerts")
    
    # Button to refresh alerts
    if st.button("🔄 Refresh Alerts", key="refresh_fraud"):
        with st.spinner("Connecting to Kafka and fetching alerts..."):
            try:
                # Create a fresh consumer that reads from beginning
                consumer = KafkaConsumer(
                    'fraud-alerts',
                    bootstrap_servers='kafka-1:9092,kafka-2:9092,kafka-3:9092',
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                    auto_offset_reset='earliest',  # Read all messages from beginning
                    enable_auto_commit=False,
                    group_id=f'streamlit-{int(time.time())}',  # Unique group each time
                    consumer_timeout_ms=5000
                )
                
                alerts = []
                
                # Collect messages (with timeout)
                for message in consumer:
                    alerts.append(message.value)
                    if len(alerts) >= 50:  # Limit to last 50
                        break
                
                consumer.close()
                
                if alerts:
                    st.success(f"📊 Found {len(alerts)} fraud alerts!")
                    # Display alerts in reverse chronological order
                    for alert in reversed(alerts[-10:]):  # Show last 10
                        with st.expander(f"⚠️ {alert['reason']} - User {alert['user_id']}", expanded=True):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.write(f"**Transaction ID:** {alert['transaction_id']}")
                                st.write(f"**User ID:** {alert['user_id']}")
                                st.write(f"**Amount:** ${alert['amount']} {alert['currency']}")
                                st.write(f"**Bank:** {alert['bank_id']}")
                                st.write(f"**Payment System:** {alert['payment_system']}")
                            
                            with col2:
                                st.write(f"**Card:** {alert['card_number']}")
                                st.write(f"**Merchant:** {alert['merchant']}")
                                st.write(f"**Country:** {alert['country']}")
                                st.write(f"**Timestamp:** {alert['timestamp']}")
                                st.write(f"**Reason:** {alert['reason']}")
                else:
                    st.warning("No fraud alerts found in Kafka topic. Make sure Flink fraud detection jobs are running.")
                    st.info("Check: `docker exec -it kafka-1 /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server kafka-1:9092 --topic fraud-alerts --from-beginning`")
                    
            except Exception as e:
                st.error(f"❌ Error connecting to Kafka: {str(e)}")
                st.info("Make sure Kafka is running: `docker ps | grep kafka`")
    else:
        st.info("💡 Click 'Refresh Alerts' button above to load fraud detections from Kafka")

# Tab 3: Analytics
with tab3:
    st.header("📈 Transaction Analytics")
    
    # Recent transactions table
    st.subheader("Recent Transactions")
    recent = get_recent_transactions(limit=50)
    if not recent.empty:
        st.dataframe(recent, use_container_width=True)
    
    # Amount distribution
    st.subheader("Transaction Amount Distribution")
    if not recent.empty:
        fig = px.histogram(recent, x='amount', nbins=50,
                          title='Distribution of Transaction Amounts',
                          labels={'amount': 'Transaction Amount ($)'})
        st.plotly_chart(fig, use_container_width=True)

# Auto-refresh option
st.sidebar.header("Settings")
auto_refresh = st.sidebar.checkbox("Auto-refresh (every 10s)")

if auto_refresh:
    st.sidebar.info("Dashboard will auto-refresh every 10 seconds")
    time.sleep(10)
    st.rerun()