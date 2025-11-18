"""
Train a calibrated Logistic Regression model to predict 30-day payment recovery.

Steps:
1. Load features from Postgres view v_feature_view
2. Temporal train/test split by invoice_date
3. Build preprocessing + LogisticRegression pipeline
4. Train, evaluate (PR AUC, Brier)
5. Calibrate with CalibratedClassifierCV
6. Save calibrated model to models/model_calibrated.joblib
"""

import os
import pandas as pd
import joblib
import psycopg2

from dotenv import load_dotenv

from sklearn.linear_model import LogisticRegression
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import average_precision_score, brier_score_loss

def main():
    # -------- 1. Load config / env vars -------- #
    load_dotenv()  # reads .env in project root
    
    DB_HOST = os.getenv("PAYREC_DB_HOST", "localhost")
    DB_PORT = int(os.getenv("PAYREC_DB_PORT", "5432"))
    DB_NAME = os.getenv("PAYREC_DB_NAME", "payrec")
    DB_USER = os.getenv("PAYREC_DB_USER", "postgres")
    DB_PASS = os.getenv("PAYREC_DB_PASS")
    
    if DB_PASS is None:
        raise RuntimeError("PAYREC_DB_PASS is not set. Please create a .env file or export the variable.")

    
    MODEL_PATH = "models/model_calibrated.joblib"
    
    
    # -------- 2. Load data from Postgres -------- #
    query = "SELECT * FROM v_feature_view;"
    
    with psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port=DB_PORT,
    ) as conn:
        df = pd.read_sql(query, conn)
    
    # Ensure dates are datetime
    df["invoice_date"] = pd.to_datetime(df["invoice_date"], errors="coerce")
    df["payment_date"] = pd.to_datetime(df["payment_date"], errors="coerce")
    
    print("Loaded data:", df.shape)
    
    
    # -------- 3. Temporal train/test split -------- #
    cutoff = pd.Timestamp("2025-01-01")
    train = df[df["invoice_date"] < cutoff].copy()
    test  = df[df["invoice_date"] >= cutoff].copy()
    
    print("Train shape:", train.shape)
    print("Test shape: ", test.shape)
    
    y_col = "label_recovered_30d"
    
    
    # -------- 4. Define feature columns -------- #
    # Numeric: all numeric except label
    num_cols = [
        c for c in df.select_dtypes(include="number").columns
        if c != y_col
    ]
    
    # Categorical: object/category minus IDs/free text
    cat_cols = [
        c for c in df.select_dtypes(include=["object", "category"]).columns
        if c not in ["order_id", "customer_id", "reason_code"]
    ]
    
    feature_cols = num_cols + cat_cols
    
    print("Numeric features:", num_cols)
    print("Categorical features:", cat_cols)
    
    
    # -------- 5. Preprocessing + base model -------- #
    preprocess = ColumnTransformer([
        ("num", Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]), num_cols),
        ("cat", Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore")),
        ]), cat_cols),
    ])
    
    base_model = LogisticRegression(
        max_iter=2000,
        class_weight="balanced"
    )
    
    pipe = Pipeline([
        ("preprocess", preprocess),
        ("model", base_model),
    ])
    
    X_train = train[num_cols + cat_cols]
    X_test  = test[num_cols + cat_cols]
    y_train = train[y_col]
    y_test  = test[y_col]
    
    pipe.fit(X_train, y_train)
    
    proba = pipe.predict_proba(X_test)[:, 1]
    ap = average_precision_score(y_test, proba)
    brier = brier_score_loss(y_test, proba)
    
    print(f"Before calibration → PR AUC: {ap:.3f}, Brier: {brier:.3f}")
    
    
    # -------- 6. Calibrate model -------- #
    calibrated_model = CalibratedClassifierCV(pipe, method="sigmoid", cv=3)
    calibrated_model.fit(X_train, y_train)
    
    proba_cal = calibrated_model.predict_proba(X_test)[:, 1]
    ap_cal = average_precision_score(y_test, proba_cal)
    brier_cal = brier_score_loss(y_test, proba_cal)
    
    print(f"After calibration  → PR AUC: {ap_cal:.3f}, Brier: {brier_cal:.3f}")
    
    
    # -------- 7. Save calibrated model -------- #
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    artifact = {
    "model": calibrated_model,
    "feature_cols": feature_cols,
    }

    joblib.dump(artifact, MODEL_PATH)

    print(f"✅ Saved calibrated model to {MODEL_PATH}")

if __name__ == "__main__":
    main()