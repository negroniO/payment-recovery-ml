{\rtf1\ansi\ansicpg1252\cocoartf2865
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 DROP VIEW IF EXISTS v_feature_view;\
\
CREATE VIEW v_feature_view AS\
WITH tx AS (\
  SELECT * FROM v_staging\
),\
customer_history AS (\
  SELECT\
    customer_id,\
    invoice_date,\
    COUNT(*) FILTER (WHERE result_status = 'success') OVER (\
      PARTITION BY customer_id\
      ORDER BY invoice_date\
      ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING\
    )::FLOAT AS prev_success_cnt,\
    COUNT(*) OVER (\
      PARTITION BY customer_id\
      ORDER BY invoice_date\
      ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING\
    )::FLOAT AS prev_total_cnt\
  FROM tx\
),\
rolled AS (\
  SELECT\
    t.*,\
    GREATEST(\
      0,\
      EXTRACT(DAY FROM (COALESCE(t.auth_ts, t.invoice_date::timestamp) - t.invoice_date::timestamp))\
    )::INT AS days_since_invoice,\
    COALESCE(DATE_PART('day', NOW() - COALESCE(t.capture_ts, t.auth_ts)), 999)::INT AS days_since_last_event,\
    CASE\
      WHEN amount < 25 THEN 'low'\
      WHEN amount < 100 THEN 'mid'\
      WHEN amount < 500 THEN 'high'\
      ELSE 'very_high'\
    END AS amount_bucket\
  FROM tx t\
)\
SELECT\
  r.order_id, r.customer_id, r.provider, r.payment_method, r.currency,\
  r.amount, r.amount_bucket, r.country, r.device, r.transaction_type,\
  r.result_status, r.reason_code, r.invoice_date, r.payment_date,\
  r.chargeback_flag, r.retries, r.days_since_invoice, r.days_since_last_event,\
  ch.prev_success_cnt, ch.prev_total_cnt,\
  CASE WHEN ch.prev_total_cnt > 0\
       THEN ch.prev_success_cnt / ch.prev_total_cnt\
       ELSE NULL END AS customer_prior_success_rate,\
  CASE WHEN r.payment_date IS NOT NULL\
            AND r.payment_date <= r.invoice_date + INTERVAL '30 days'\
       THEN 1 ELSE 0 END AS label_recovered_30d\
FROM rolled r\
LEFT JOIN customer_history ch\
  ON ch.customer_id = r.customer_id\
 AND ch.invoice_date = r.invoice_date;\
}