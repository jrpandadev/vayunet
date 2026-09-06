import argparse
from pathlib import Path
import json

import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DATA_FILE = BASE_DIR / "data" / "processed" / "delhi_forecasting.csv"
MODELS_DIR = BASE_DIR / "models"

TARGETS = {
    "6h": "target_pm25_6h",
    "24h": "target_pm25_24h",
    "72h": "target_pm25_72h",
}

def load_data():
    df = pd.read_csv(PROCESSED_DATA_FILE, parse_dates=["Timestamp"])
    df = df.sort_values(by="Timestamp").reset_index(drop=True)
    return df

def chronological_test_split(df, train_frac=0.70, val_frac=0.15):
    n = len(df)
    train_end = int(n * train_frac)
    val_end = train_end + int(n * val_frac)
    
    test_df = df.iloc[val_end:].copy()
    return test_df

def evaluate(y_true, y_pred):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    return mae, rmse, r2

def main():
    if not PROCESSED_DATA_FILE.exists():
        raise FileNotFoundError(f"Data file not found: {PROCESSED_DATA_FILE}")
        
    df = load_data()
    
    # Needs the exact same encoding to run xgb models
    drop_cols = ["Timestamp", "segment_id"] + list(TARGETS.values())
    df_encoded = pd.get_dummies(df, columns=["station_id"], dtype=int)
    
    # Load features.json to ensure exact order
    features_path = MODELS_DIR / "features.json"
    with open(features_path, "r") as f:
        feature_cols = json.load(f)
        
    test_df = chronological_test_split(df_encoded)
    
    results = {}
    
    for horizon, target_col in TARGETS.items():
        # Load XGBoost model
        model_path = MODELS_DIR / f"xgb_pm25_{horizon}.joblib"
        xgb_model = joblib.load(model_path)
        
        y_true_full = test_df[target_col]
        # Persistence prediction is current PM2.5
        y_pred_pers_full = test_df["PM2.5"]
        X_test_full = test_df[feature_cols]
        
        # We can only evaluate where target is not NaN
        mask = y_true_full.notna()
        
        y_true = y_true_full[mask]
        y_pred_pers = y_pred_pers_full[mask]
        X_test = X_test_full[mask]
        
        # Make XGBoost predictions on the same set
        y_pred_xgb = xgb_model.predict(X_test)
        
        # Evaluate Persistence
        pers_mae, pers_rmse, pers_r2 = evaluate(y_true, y_pred_pers)
        
        # Evaluate XGBoost
        xgb_mae, xgb_rmse, xgb_r2 = evaluate(y_true, y_pred_xgb)
        
        results[horizon] = {
            "samples": len(y_true),
            "pers_mae": pers_mae, "xgb_mae": xgb_mae,
            "pers_rmse": pers_rmse, "xgb_rmse": xgb_rmse,
            "pers_r2": pers_r2, "xgb_r2": xgb_r2
        }

    # Print results
    print("=========================================================================================")
    print(f"{'Horizon':<8} | {'Persistence MAE':<15} | {'XGBoost MAE':<11} | {'Improvement %':<13}")
    print("-----------------------------------------------------------------------------------------")
    for h in TARGETS.keys():
        r = results[h]
        imp = (r['pers_mae'] - r['xgb_mae']) / r['pers_mae'] * 100
        print(f"{h:<8} | {r['pers_mae']:<15.2f} | {r['xgb_mae']:<11.2f} | {imp:>12.2f}%")
        
    print("\n=========================================================================================")
    print(f"{'Horizon':<8} | {'Persistence RMSE':<16} | {'XGBoost RMSE':<12} | {'Improvement %':<13}")
    print("-----------------------------------------------------------------------------------------")
    for h in TARGETS.keys():
        r = results[h]
        imp = (r['pers_rmse'] - r['xgb_rmse']) / r['pers_rmse'] * 100
        print(f"{h:<8} | {r['pers_rmse']:<16.2f} | {r['xgb_rmse']:<12.2f} | {imp:>12.2f}%")

    print("\n=========================================================================================")
    print(f"{'Horizon':<8} | {'Persistence R²':<14} | {'XGBoost R²':<10} | {'Difference':<10}")
    print("-----------------------------------------------------------------------------------------")
    for h in TARGETS.keys():
        r = results[h]
        diff = r['xgb_r2'] - r['pers_r2']
        print(f"{h:<8} | {r['pers_r2']:<14.3f} | {r['xgb_r2']:<10.3f} | {diff:>+10.3f}")
    print("=========================================================================================")

if __name__ == "__main__":
    main()
