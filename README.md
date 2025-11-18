<p align="center">
  <img src="assets/banner.png" width="100%" />
</p>

# 💳 Payment Recovery Prediction (ML + SQL + Streamlit)

An end-to-end machine learning project that predicts which **failed or unpaid transactions** will be recovered within **30 days**, and prioritizes outreach based on **expected recovered revenue** (amount × probability).  
Built fully from scratch using **Python**, **SQL**, **PostgreSQL**, **scikit-learn**, and **Streamlit**.

## 🚀 Live Demo (Streamlit)

👉 **https://payment-recovery-ml.streamlit.app**

Upload a CSV exported from your `v_feature_view` (or use the included sample file) to:

- score unpaid invoices  
- compute expected recovered revenue  
- see predicted 30-day recovery probability  
- and prioritize outreach based on business impact  

## 📌 Project Highlights

- **🔥 ML model:** Calibrated Logistic Regression  
- **📊 Metrics:** PR AUC, Brier Score, Lift (Top-K vs overall)  
- **🧠 Feature engineering:** customer history, retries, timestamps, device, provider, country  
- **💰 Expected value ranking:** maximize revenue, not raw probability  
- **🗄️ SQL pipeline:** raw → staging → feature view (PostgreSQL)  
- **📦 Reproducible:** Conda environment + modular Python scripts  
- **🖥️ Interactive UI:** Streamlit app for real-time scoring & prioritization  

## 🛠 Tech Stack

**Languages & Core**  
Python, SQL

**Data & ML**  
Pandas, NumPy, scikit-learn

**Database**  
PostgreSQL, psycopg2

**App**  
Streamlit

**Dev Tools**  
Git, Conda, Jupyter

## 📁 Project Structure

```
payment-recovery-ml/
├── app/
│   └── streamlit_app.py
├── data/
│   └── sample_feature_view.csv
├── models/
│   └── model_calibrated.joblib
├── notebooks/
├── sql/
│   ├── 01_schema.sql
│   ├── 02_staging.sql
│   └── 03_feature_view.sql
├── train_from_scratch.py
├── score_from_scratch.py
├── environment.yml
└── README.md
```

## 🗄️ Data Model (PostgreSQL)

The project uses a 3-layer SQL design:

### **1️⃣ Raw Layer**  
Stores synthetic transactions: provider, device, timestamps, retries, country, payment_date.

### **2️⃣ Staging Layer**  
Cleans data, fixes timestamps, and assigns the binary label:
```
label_recovered_30d = payment_date <= invoice_date + 30 days
```

### **3️⃣ Feature View**  
Window functions generate:  
customer history, amount bucket, days since invoice, days since last event, retries, provider, device, country, and more.

## 🤖 Machine Learning Pipeline

- Temporal split (train vs test)  
- Preprocessing (scaling + one-hot encoding)  
- Logistic Regression (balanced)  
- Probability calibration  
- PR AUC + Brier Score evaluation  
- Saves: `model_calibrated.joblib`

## 📈 Scoring Pipeline — Expected Value Approach

Instead of sorting only by probability:

```
ev_recovered = amount × p_recover_30d
```

This ranks invoices by **maximum revenue recovery** potential.

Exports:  
- recovery probability  
- expected recovered revenue  
- top-K prioritization  
- timestamped CSV  

## 🖥️ Streamlit App

Features:  
- Upload CSV or load from Postgres  
- Score invoices  
- View KPIs  
- Prioritize by expected value  
- Download results  

## ▶️ Run Locally

```
conda env create -f environment.yml
conda activate payrec-ml

python train_from_scratch.py
python score_from_scratch.py

streamlit run app/streamlit_app.py
```

## 🔮 Future Enhancements

- XGBoost model  
- SHAP explanations  
- Automated ETL & batch scoring  
- Writebacks to Postgres  
- Monitoring & alerting  
- CI/CD integration  
