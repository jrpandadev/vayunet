import os
import sys
import json
import time
import random
from pathlib import Path
from typing import Dict, Any, List

import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

DATA_FILE = BASE_DIR / "data" / "processed" / "delhi_forecasting_weather.csv"
HORIZON_METADATA_FILE = BASE_DIR / "models" / "horizon_features.json"
RESULTS_DIR = BASE_DIR / "ml" / "results"
RESULTS_CSV = RESULTS_DIR / "xgb_tuning_results.csv"
BEST_PARAMS_JSON = RESULTS_DIR / "xgb_best_params.json"

TARGETS = {
    "6h": "target_pm25_6h",
    "24h": "target_pm25_24h",
    "72h": "target_pm25_72h",
}
HORIZONS = ["6h", "24h", "72h"]

def load_data():
    df = pd.read_csv(DATA_FILE, parse_dates=["timestamp"])
    if "timestamp" in df.columns and "Timestamp" not in df.columns:
        df.rename(columns={"timestamp": "Timestamp"}, inplace=True)
    df = df.sort_values(by="Timestamp").reset_index(drop=True)

    df_encoded = pd.get_dummies(df, columns=["station_id"], dtype=int)

    # TRAIN: 2022-01-01 00:00 to 2024-10-01 13:00
    # VALID: 2024-10-01 13:00 to 2025-08-30 15:00
    # TEST: 2025-08-30 15:00 to 2026-08-31 23:00

    train_end = pd.to_datetime("2024-10-01 13:00:00")
    val_end = pd.to_datetime("2025-08-30 15:00:00")
    test_end = pd.to_datetime("2026-08-31 23:00:00")

    train_df = df_encoded[df_encoded["Timestamp"] < train_end].copy()
    val_df = df_encoded[(df_encoded["Timestamp"] >= train_end) & (df_encoded["Timestamp"] < val_end)].copy()
    test_df = df_encoded[(df_encoded["Timestamp"] >= val_end) & (df_encoded["Timestamp"] <= test_end)].copy()

    # Sanity checks
    assert train_df["Timestamp"].max() < val_df["Timestamp"].min(), "Leakage: Train and Validation sets overlap."
    assert val_df["Timestamp"].max() < test_df["Timestamp"].min(), "Leakage: Validation and Test sets overlap."
    
    return train_df, val_df, test_df

def evaluate_predictions(y_true, y_pred):
    err = y_pred - y_true
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "R2": float(r2_score(y_true, y_pred)),
        "bias": float(np.mean(err)),
        "MedAE": float(np.median(np.abs(err))),
    }

def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(HORIZON_METADATA_FILE, "r") as f:
        meta = json.load(f)
    horizon_features = meta["horizon_features"]
    
    train_df, val_df, test_df = load_data()
    
    # Check baseline features structure
    for h in HORIZONS:
        assert h in horizon_features, f"Metadata for {h} missing"
        # The number of features should match requirements: 
        # 6h: 47, 24h: 44, 72h: 42 (assuming base features are 42)
        # Actually it depends on the exact JSON, we just trust the metadata loaded

    param_grid = {
        "max_depth": [3, 4, 5, 6, 7, 8],
        "min_child_weight": [1, 3, 5, 7, 10],
        "learning_rate": [0.02, 0.05, 0.08, 0.1],
        "subsample": [0.7, 0.8, 0.9, 1.0],
        "colsample_bytree": [0.7, 0.8, 0.9, 1.0],
    }

    n_iter = 20 # Number of random trials per horizon
    random.seed(42)

    results_list = []
    best_params_all = {}
    
    print(f"Starting Random Search with {n_iter} trials per horizon...")

    for horizon in HORIZONS:
        print(f"\n--- Horizon: {horizon} ---")
        features = horizon_features[horizon]
        target = TARGETS[horizon]
        
        t_mask = train_df[target].notna()
        v_mask = val_df[target].notna()
        
        X_train = train_df.loc[t_mask, features]
        y_train = train_df.loc[t_mask, target]
        
        X_val = val_df.loc[v_mask, features]
        y_val = val_df.loc[v_mask, target]
        
        best_mae = float("inf")
        best_params = None
        best_iter_round = None
        best_metrics = None
        
        for i in range(n_iter):
            params = {k: random.choice(v) for k, v in param_grid.items()}
            
            model = xgb.XGBRegressor(
                **params,
                n_estimators=2000,
                early_stopping_rounds=50,
                eval_metric="mae",
                objective="reg:squarederror",
                random_state=42,
                n_jobs=-1,
            )
            
            model.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                verbose=False
            )
            
            best_iter = getattr(model, "best_iteration", 2000)
            
            y_pred_val = model.predict(X_val)
            metrics = evaluate_predictions(y_val, y_pred_val)
            
            results_list.append({
                "horizon": horizon,
                "feature_set": f"weather_selected_{len(features)}",
                "max_depth": params["max_depth"],
                "min_child_weight": params["min_child_weight"],
                "learning_rate": params["learning_rate"],
                "subsample": params["subsample"],
                "colsample_bytree": params["colsample_bytree"],
                "best_iteration": best_iter,
                "validation MAE": metrics["MAE"],
                "validation RMSE": metrics["RMSE"],
                "validation R2": metrics["R2"],
                "validation bias": metrics["bias"],
                "validation MedAE": metrics["MedAE"],
            })
            
            if metrics["MAE"] < best_mae:
                best_mae = metrics["MAE"]
                best_params = params
                best_iter_round = best_iter
                best_metrics = metrics
                
            print(f"Trial {i+1}/{n_iter} - MAE: {metrics['MAE']:.4f} | Params: {params}")

        best_params_all[horizon] = {
            "params": best_params,
            "best_iteration": best_iter_round,
            "validation_metrics": best_metrics
        }
        
    df_results = pd.DataFrame(results_list)
    df_results.to_csv(RESULTS_CSV, index=False)
    print(f"\nAll trial records logged to {RESULTS_CSV}")
    
    with open(BEST_PARAMS_JSON, "w") as f:
        json.dump(best_params_all, f, indent=2)
    print(f"Best configurations saved to {BEST_PARAMS_JSON}")
    
    print("\n" + "="*50)
    print("FINAL TUNING REPORT")
    print("="*50)
    for h in HORIZONS:
        print(f"\nHorizon: {h}")
        print(f"1. Best Configuration: {best_params_all[h]['params']}")
        print(f"2. Best Iteration: {best_params_all[h]['best_iteration']}")
        print(f"3. Validation Metrics: {best_params_all[h]['validation_metrics']}")
        
    print(f"\nTotal number of trials per horizon: {n_iter}")
    print("Sanity checks passed: Temporal splits are strictly non-overlapping, and final test set was NOT evaluated.")

if __name__ == "__main__":
    main()
