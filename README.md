<p align="center">
  <img src="assets/banner.png" width="100%" />
</p>


# Payment Recovery Prediction (ML + SQL + Streamlit)

A complete end-to-end machine learning project that predicts which **failed customer payments** will be recovered within **30 days**, and prioritizes outreach based on **expected recovered revenue** (amount × probability).

This project includes:

- synthetic payment dataset  
- PostgreSQL data model + feature engineering  
- ML training pipeline with calibration  
- scoring pipeline with expected value optimization  
- Streamlit app for interactive scoring  
- Git version control & reproducible environment  

## Project Highlights

- **✔ ML model:** Calibrated Logistic Regression  
- **✔ Metrics:** PR AUC, Brier Score, Lift (Top-K vs overall)  
- **✔ Feature engineering:** customer history, device/country/provider, retries, event timing  
- **✔ Expected value ranking:** maximize revenue, not probability  
- **✔ SQL-first workflow:** raw → staging → feature view  
- **✔ Reproducible pipelines:** `train_from_scratch.py`, `score_from_scratch.py`  
- **✔ Interactive UI:** Streamlit dashboard to score invoices

## Project Structure

```
payment-recovery-ml/
├── app/
│   └── streamlit_app.py
├── data/
├── models/
│   └── model_calibrated.joblib
├── notebooks/
├── sql/
│   ├── 01_schema.sql
│   ├── 02_staging.sql
│   └── 03_feature_view.sql
├── train_from_scratch.py
├── score_from_scratch.py
└── README.md
```

## Data Model (PostgreSQL)

Includes raw transactions, staging, and a feature engineering layer using window functions.

## Machine Learning Pipeline

- Train/test temporal split  
- Preprocessing (scaling + one-hot encoding)  
- Logistic Regression with class balancing  
- Calibration (`CalibratedClassifierCV`)  
- PR AUC + Brier Score evaluation  
- Saves `model_calibrated.joblib`

## Scoring Pipeline

Computes:

- Probability of 30-day recovery  
- Expected recovered revenue (`amount × p_recover_30d`)  
- Top-K prioritization based on expected value  
- Outputs scored CSV  

## Streamlit App

- Upload CSV or load from Postgres  
- Score invoices  
- View KPIs  
- Download results  

## Running the Project

```
conda env create -f environment.yml
conda activate payrec-ml

python train_from_scratch.py
python score_from_scratch.py

streamlit run app/streamlit_app.py
```

## Future Enhancements

- Add XGBoost  
- SHAP explanations  
- Automated ETL  
- Writebacks to Postgres  
