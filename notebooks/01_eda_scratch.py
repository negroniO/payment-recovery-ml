#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov  5 15:51:56 2025

@author: negroni
"""

import pandas as pd
import numpy as np
import psycopg2

# Connection details
conn = psycopg2.connect(
    host="localhost",
    database="payrec",
    user="postgres",
    password="Nicosia2025!",
    port=5432
    )

# Load fro SQL view
query = "SELECT * from v_feature_view;"
df = pd.read_sql(query,conn)

conn.close()

print(df.shape)
print(df.head())
print(df.dtypes)
print(df.isna().mean().sort_values(ascending=False).head(10))

# Convert 'invoice_date' and 'payment_date' to datetime

df['invoice_date'] = pd.to_datetime(df['invoice_date'])

df['payment_date'] = pd.to_datetime(df['payment_date'])

print(df['invoice_date'].dtype, df['payment_date'].dtype)

# Train/Test temporal split

cutoff = pd.Timestamp("2025-01-01")

train = df[df['invoice_date'] < cutoff].copy()

test = df[df['invoice_date'] >= cutoff].copy()

print(len(train), len(test))

train_rate = train['label_recovered_30d'].mean()
test_rate = test['label_recovered_30d'].mean()

print(f"Train positive label_recovered: {train_rate:.2%}")
print(f"Test positive label_recovered: {test_rate:.2%}")

print(train["amount"].describe())
print(train["amount_bucket"].value_counts())
print(train["provider"].value_counts().head(10))

# Correlation

# Select numberic columns
num_cols = df.select_dtypes(include=["number"]).columns.tolist()

# Drop targer column
num_cols = [c for c in num_cols if c != "label_recovered_30d"]

print(train[num_cols + ["label_recovered_30d"]].corr(numeric_only=True)["label_recovered_30d"].sort_values())
















