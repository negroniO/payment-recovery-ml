{\rtf1\ansi\ansicpg1252\cocoartf2865
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 CREATE TABLE IF NOT EXISTS raw_transactions (\
    order_id TEXT,\
    customer_id TEXT,\
    provider TEXT,\
    payment_method TEXT,\
    currency TEXT,\
    amount NUMERIC(14,2),\
    country TEXT,\
    device TEXT,\
    transaction_type TEXT,\
    result_status TEXT,\
    reason_code TEXT,\
    auth_ts TIMESTAMP,\
    capture_ts TIMESTAMP,\
    retries INT DEFAULT 0,\
    chargeback_flag BOOLEAN DEFAULT FALSE,\
    invoice_date DATE,\
    payment_date DATE,\
    label_recovered_30d BOOLEAN\
);\
\
CREATE INDEX IF NOT EXISTS idx_raw_tx_customer_date\
ON raw_transactions (customer_id, invoice_date);\
}