{\rtf1\ansi\ansicpg1252\cocoartf2865
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 DROP VIEW IF EXISTS v_staging;\
\
CREATE VIEW v_staging AS\
WITH base AS (\
  SELECT\
    rt.*,\
    CASE\
      WHEN payment_date IS NOT NULL\
           AND payment_date <= (invoice_date + INTERVAL '30 days')\
      THEN TRUE ELSE FALSE\
    END AS label_recovered_30d_calc\
  FROM raw_transactions rt\
)\
SELECT\
  order_id, customer_id, provider, payment_method, currency, amount,\
  country, device, transaction_type, result_status, reason_code,\
  auth_ts, capture_ts, retries, chargeback_flag, invoice_date, payment_date,\
  label_recovered_30d_calc AS label_recovered_30d\
FROM base;\
}