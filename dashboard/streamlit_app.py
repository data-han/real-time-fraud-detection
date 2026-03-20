import streamlit as st
import pandas as pd
import psycopg2
from kafka import KafkaConsumer
import json
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import time
import os

# Page config
st.set_page_config(page_title="Fraud Detection Dashboard", layout="wide", page_icon="🚨")

# Database connection (no caching)
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "transactions_db"),
        user=os.getenv("POSTGRES_USER", "transactions_user"),
        password=os.getenv("POSTGRES_PASSWORD", "transactions123")
    )

# Query functions
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

# Fraud alerts from Kafka
def fetch_fraud_alerts(max_alerts=50):
    try:
        consumer = KafkaConsumer(
            'fraud-alerts',
            bootstrap_servers=os.getenv("KAFKA_BROKER", "localhost:19092,localhost:29092,localhost:39092"),
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=False,
            group_id=None,  # No group = no offset tracking, always reads from earliest
            consumer_timeout_ms=10000  # 10s timeout for consumer to connect and fetch
        )
        alerts = []
        for msg in consumer:
            alert = msg.value
            if isinstance(alert, dict):
                alerts.append(alert)
            if len(alerts) >= max_alerts:
                break
        consumer.close()
        return alerts
    except Exception as e:
        st.error(f"Kafka error: {e}")
        return []

# Main dashboard
st.title("🚨 Real-Time Fraud Detection Dashboard")

# Create tabs
tab1, tab2, tab3 = st.tabs(["📊 Overview", "🔍 Fraud Alerts", "📈 Analytics"])

# Tab 1: Overview
with tab1:
    st.header("Transaction Overview (Last Hour)")
    stats = get_transaction_stats()
    if not stats.empty:
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Total Transactions", f"{stats['total_transactions'][0] or 0:,}")
        with col2:
            total_amount = stats['total_amount'][0] or 0
            st.metric(
                label="Total Amount",
                value=f"${total_amount/1000:.1f}K",
                help=f"Exact: ${total_amount:,.2f}"
            )
        with col3:
            avg_amount = stats['avg_amount'][0] or 0
            st.metric("Avg Transaction", f"${avg_amount:,.2f}")
        with col4:
            st.metric("Unique Users", f"{stats['unique_users'][0] or 0:,}")
        with col5:
            st.metric("Countries", f"{stats['unique_countries'][0] or 0:,}")
    st.subheader("Transactions Per Minute")
    time_data = get_transactions_over_time()
    if not time_data.empty:
        fig = px.line(time_data, x='minute', y='count', 
                     title='Transaction Volume Over Time',
                     labels={'count': 'Transaction Count', 'minute': 'Time'})
        st.plotly_chart(fig, use_container_width=True)
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
    if st.button("🔄 Refresh Alerts", key="refresh_fraud"):
        with st.spinner("Fetching fraud alerts from Kafka..."):
            alerts = fetch_fraud_alerts()
            if alerts:
                st.success(f"Found {len(alerts)} fraud alerts.")
                for alert in reversed(alerts[-10:]):
                    st.markdown("---")
                    cols = st.columns(2)
                    with cols[0]:
                        st.markdown(f"**Transaction ID:** {alert.get('transaction_id', '-')}")
                        st.markdown(f"**User ID:** {alert.get('user_id', '-')}")
                        st.markdown(f"**Amount:** ${alert.get('amount', '-')} {alert.get('currency', '')}")
                        st.markdown(f"**Bank:** {alert.get('bank_id', '-')}")
                        st.markdown(f"**Payment System:** {alert.get('payment_system', '-')}")
                    with cols[1]:
                        st.markdown(f"**Card:** {alert.get('card_number', '-')}")
                        st.markdown(f"**Merchant:** {alert.get('merchant', '-')}")
                        st.markdown(f"**Country:** {alert.get('country', '-')}")
                        st.markdown(f"**Timestamp:** {alert.get('timestamp', '-')}")
                        st.markdown(f"**Reason:** {alert.get('reason', '-')}")
            else:
                st.info("No fraud alerts found. Ensure Flink jobs are running and producing alerts.")
    else:
        st.info("💡 Click 'Refresh Alerts' to load the latest fraud alerts from Kafka.")

# Tab 3: Analytics
with tab3:
    st.header("📈 Transaction Analytics")
    st.subheader("Recent Transactions")
    recent = get_recent_transactions(limit=50)
    if not recent.empty:
        st.dataframe(recent, use_container_width=True)
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