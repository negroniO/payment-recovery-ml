import os
from io import StringIO

import streamlit as st
import pandas as pd
import numpy as np
import joblib

try:
    import psycopg2
    HAS_PG = True
except ImportError:
    HAS_PG = False


# ------------- CONFIG ------------- #
MODEL_PATH = "models/model_calibrated.joblib"

# Default DB settings (override with env vars if you like)
DB_HOST = os.getenv("PAYREC_DB_HOST", "localhost")
DB_PORT = int(os.getenv("PAYREC_DB_PORT", "5432"))
DB_NAME = os.getenv("PAYREC_DB_NAME", "payrec")
DB_USER = os.getenv("PAYREC_DB_USER", "postgres")


# ------------- HELPERS ------------- #
@st.cache_resource
def load_model(path: str = MODEL_PATH):
    """Load calibrated model + feature columns artifact."""
    artifact = joblib.load(path)
    return artifact["model"], artifact["feature_cols"]


def load_from_postgres(password: str, query: str = "SELECT * FROM v_feature_view;") -> pd.DataFrame:
    if not HAS_PG:
        st.error("psycopg2 is not installed in this environment.")
        return pd.DataFrame()

    import psycopg2
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=password,
        port=DB_PORT
    )
    try:
        df = pd.read_sql(query, conn)
    finally:
        conn.close()

    # Ensure dates are proper datetimes
    for c in ("invoice_date", "payment_date"):
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")

    return df


def score_dataframe(df: pd.DataFrame, pipe, feature_cols, capacity: int) -> pd.DataFrame:
    """Add prediction, expected value, and priority flag columns to a copy of df."""
    df = df.copy()

    # Make sure date columns are datetime
    for c in ("invoice_date", "payment_date"):
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")

    # Optionally filter to unpaid rows
    if "payment_date" in df.columns:
        to_score = df[df["payment_date"].isna()].copy()
        if to_score.empty:
            to_score = df.copy()
    else:
        to_score = df.copy()

    # Check features
    missing = [c for c in feature_cols if c not in to_score.columns]
    if missing:
        raise ValueError(f"Missing expected feature columns: {missing}")

    # Predict probabilities
    proba = pipe.predict_proba(to_score[feature_cols])[:, 1]
    to_score["p_recover_30d"] = proba

    # Ensure amount is numeric
    to_score["amount"] = pd.to_numeric(to_score["amount"], errors="coerce").fillna(0.0)

    # Expected recovered value
    to_score["ev_recovered"] = to_score["amount"] * to_score["p_recover_30d"]

    # Prioritize by expected value
    n = len(to_score)
    K = min(capacity, n)

    to_score = to_score.sort_values("ev_recovered", ascending=False, kind="mergesort")
    cutoff_ev = to_score["ev_recovered"].iloc[K - 1] if K > 0 else to_score["ev_recovered"].min()

    to_score = to_score.reset_index(drop=False)
    to_score["priority_flag"] = (
        (to_score["ev_recovered"] > cutoff_ev)
        | ((to_score["ev_recovered"] == cutoff_ev) & (to_score.index < K))
    ).astype(int)

    # Round for display
    to_score["p_recover_30d"] = to_score["p_recover_30d"].round(4)
    to_score["ev_recovered"] = to_score["ev_recovered"].round(2)

    return to_score


# ------------- UI ------------- #
st.set_page_config(page_title="Payment Recovery Predictor", layout="wide")
st.title("Payment Recovery Predictor")

st.markdown(
    """
This app uses a calibrated Logistic Regression model to estimate the probability that an invoice
will be **recovered within 30 days**, and helps you **prioritize outreach**.
Prioritization is based on **expected recovered value** (amount × probability).
"""
)

pipe, feature_cols = load_model()

# Sidebar: data source + capacity
st.sidebar.header("Configuration")

source = st.sidebar.radio(
    "Choose data source",
    ["Upload CSV", "Load from Postgres"],
)

capacity = st.sidebar.slider(
    "Outreach capacity (number of invoices to prioritize)",
    min_value=50,
    max_value=2000,
    value=500,
    step=50,
)

df_input = pd.DataFrame()

if source == "Upload CSV":
    uploaded_file = st.sidebar.file_uploader(
        "Upload a CSV exported from v_feature_view or similar",
        type=["csv"]
    )
    if uploaded_file is not None:
        df_input = pd.read_csv(uploaded_file)
        
# Optional: Load sample feature file directly from repo
if st.sidebar.button("Load Sample Data"):
    try:
        df_input = pd.read_csv("data/sample_feature_view.csv")
        st.sidebar.success(f"Loaded {len(df_input)} rows from sample_feature_view.csv")
    except Exception as e:
        st.sidebar.error(f"Could not load sample data: {e}")

elif source == "Load from Postgres":
    st.sidebar.markdown(f"**Host:** `{DB_HOST}`  \n**DB:** `{DB_NAME}`  \n**User:** `{DB_USER}`")
    db_password = st.sidebar.text_input("Postgres password", type="password")
    if st.sidebar.button("Load from DB"):
        if not db_password:
            st.sidebar.error("Please enter the Postgres password.")
        else:
            with st.spinner("Loading data from Postgres..."):
                df_input = load_from_postgres(db_password)
                st.sidebar.success(f"Loaded {len(df_input):,} rows from v_feature_view")


if df_input.empty:
    st.info("Upload a CSV or load data from Postgres to start scoring.")
    st.stop()

st.subheader("Raw Input Data")
st.write(f"Rows: {len(df_input):,}")
st.dataframe(df_input.head(10))

# Score
with st.spinner("Scoring invoices..."):
    scored = score_dataframe(df_input, pipe, feature_cols, capacity)

# Determine subset that was actually scored (e.g., unpaid invoices)
if "p_recover_30d" not in scored.columns:
    st.error("Scoring did not produce probabilities. Please check your data.")
    st.stop()

scored_full = scored.copy()
scored_priority = scored_full[scored_full["priority_flag"] == 1]

# KPIs
st.subheader("Model-Based KPIs")

col1, col2, col3 = st.columns(3)
col1.metric("Mean predicted recovery probability", f"{scored_full['p_recover_30d'].mean():.2%}")
col2.metric("Capacity (K)", len(scored_priority))

total_ev_top = scored_priority["ev_recovered"].sum() if len(scored_priority) > 0 else 0.0
col3.metric("Expected recovered £ (Top-K)", f"£{total_ev_top:,.0f}")

# Optional: if labels exist, show lift in a second row
if "label_recovered_30d" in scored_full.columns:
    base = scored_full["label_recovered_30d"].mean()
    top = scored_priority["label_recovered_30d"].mean() if len(scored_priority) > 0 else 0.0
    lift = (top / base) if base else np.nan
    st.write(f"Lift (Top-K vs overall): **{lift:.2f}×** (if labels in input)")

# Top-K table
st.subheader("Prioritized Invoices")

display_cols = [
    c for c in [
        "order_id", "customer_id", "provider", "payment_method", "currency",
        "country", "device", "amount", "retries",
        "p_recover_30d", "ev_recovered", "priority_flag"
    ] if c in scored_priority.columns
]

st.write(f"Showing top {len(scored_priority):,} prioritized invoices.")
st.dataframe(
    scored_priority
    .sort_values("ev_recovered", ascending=False)[display_cols]
    .head(capacity)
)

# Download scored CSV
csv_buf = StringIO()
scored_full.to_csv(csv_buf, index=False)
st.download_button(
    label="📥 Download full scored dataset as CSV",
    data=csv_buf.getvalue(),
    file_name="scored_invoices_streamlit.csv",
    mime="text/csv"
)
