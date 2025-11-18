#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Score invoices with calibrated model, flag top-K, and export a scored file.
"""

import os
import pandas as pd
import numpy as np
import psycopg2
import joblib
from datetime import datetime
from dotenv import load_dotenv


def main():
    # -------- Config --------
    MODEL_PATH = "models/model_calibrated.joblib"
    OUT_DIR    = "data"
    CAPACITY_K = 500

    load_dotenv()

    DB_HOST = os.getenv("PAYREC_DB_HOST", "localhost")
    DB_PORT = int(os.getenv("PAYREC_DB_PORT", "5432"))
    DB_NAME = os.getenv("PAYREC_DB_NAME", "payrec")
    DB_USER = os.getenv("PAYREC_DB_USER", "postgres")
    DB_PASS = os.getenv("PAYREC_DB_PASS")

    if DB_PASS is None:
        raise RuntimeError("PAYREC_DB_PASS is not set. Please create a .env file or export the variable.")

    # -------- Load model + feature_cols artifact --------
    artifact = joblib.load(MODEL_PATH)
    pipe = artifact["model"]
    feature_cols = artifact["feature_cols"]

    # -------- Load data from Postgres --------
    query = "SELECT * FROM v_feature_view;"
    with psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port=DB_PORT,
    ) as conn:
        df = pd.read_sql(query, conn)

    # Ensure datetimes
    for c in ("invoice_date", "payment_date"):
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")

    # -------- Filter rows to score (e.g. only unpaid) --------
    to_score = df[df["payment_date"].isna()].copy()
    if to_score.empty:
        print("No rows to score (payment_date is present on all rows). Falling back to full dataset.")
        to_score = df.copy()

    # -------- Build feature matrix using same columns as training --------
    missing = [c for c in feature_cols if c not in to_score.columns]
    if missing:
        raise ValueError(f"Missing expected feature columns: {missing}")

    # Predict calibrated probabilities
    to_score["p_recover_30d"] = pipe.predict_proba(to_score[feature_cols])[:, 1]

    # Ensure amount is numeric
    to_score["amount"] = pd.to_numeric(to_score["amount"], errors="coerce").fillna(0.0)

    # Expected recovered value (amount * probability)
    to_score["ev_recovered"] = to_score["amount"] * to_score["p_recover_30d"]

    # -------- Prioritize top-K by expected value --------
    n = len(to_score)
    K = min(CAPACITY_K, n)

    # Sort by expected value desc (stable)
    to_score = to_score.sort_values(["ev_recovered"], ascending=False, kind="mergesort")
    cutoff_ev = to_score["ev_recovered"].iloc[K - 1] if K > 0 else to_score["ev_recovered"].min()

    to_score = to_score.reset_index(drop=False)
    to_score["priority_flag"] = (
        (to_score["ev_recovered"] > cutoff_ev)
        | ((to_score["ev_recovered"] == cutoff_ev) & (to_score.index < K))
    ).astype(int)

    # Round for readability
    to_score["p_recover_30d"] = to_score["p_recover_30d"].round(4)
    to_score["ev_recovered"] = to_score["ev_recovered"].round(2)

    # -------- Ops KPIs (if label exists) --------
    if "label_recovered_30d" in to_score.columns:
        base = to_score["label_recovered_30d"].mean()
        top = to_score.loc[to_score["priority_flag"] == 1, "label_recovered_30d"].mean()
        lift = (top / base) if base and not np.isnan(base) else np.nan

        total_amount_top = to_score.loc[to_score["priority_flag"] == 1, "amount"].sum()
        total_ev_top = to_score.loc[to_score["priority_flag"] == 1, "ev_recovered"].sum()

        print(f"Base recover rate: {base:.2%} | Top-{K} recover rate: {top:.2%} | Lift: {lift:.2f}x")
        print(f"Total amount in Top-{K}: £{total_amount_top:,.0f}")
        print(f"Expected recovered amount in Top-{K}: £{total_ev_top:,.0f}")

    print("High-priority invoices:", int(to_score["priority_flag"].sum()), f"out of {n}")

    # -------- Export --------
    os.makedirs(OUT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    cols_out = [
        "order_id", "customer_id", "provider", "payment_method", "currency",
        "country", "device", "amount", "retries",
        "p_recover_30d", "ev_recovered", "priority_flag",
    ]
    out_path = os.path.join(OUT_DIR, f"scored_invoices_{ts}.csv")
    to_score[cols_out].sort_values(
        ["priority_flag", "ev_recovered"],
        ascending=[False, False],
    ).to_csv(out_path, index=False)

    print(f"✅ Saved {out_path}")


if __name__ == "__main__":
    main()
