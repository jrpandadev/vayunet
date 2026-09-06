import os
import sys
import json
import time
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb
import joblib

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

DATA_FILE = BASE_DIR / "data" / "processed" / "delhi_forecasting_weather.csv"
HORIZON_METADATA_FILE = BASE_DIR / "models" / "horizon_features.json"
RESULTS_DIR = BASE_DIR / "ml" / "results"
BEST_PARAMS_JSON = RESULTS_DIR / "xgb_best_params.json"
MODELS_DIR = BASE_DIR / "models"
FINAL_REPORTS_DIR = BASE_DIR / "reports" / "final_weather_evaluation"

TARGETS = {
    "6h": "target_pm25_6h",
    "24h": "target_pm25_24h",
    "72h": "target_pm25_72h",
}
HORIZONS = ["6h", "24h", "72h"]

def load_data():
    print(f"Loading data from {DATA_FILE}...")
    df = pd.read_csv(DATA_FILE, parse_dates=["timestamp"])
    if "timestamp" in df.columns and "Timestamp" not in df.columns:
        df.rename(columns={"timestamp": "Timestamp"}, inplace=True)
    df = df.sort_values(by="Timestamp").reset_index(drop=True)

    df_encoded = pd.get_dummies(df, columns=["station_id"], dtype=int)

    train_end = pd.to_datetime("2024-10-01 13:00:00")
    val_end = pd.to_datetime("2025-08-30 15:00:00")
    test_end = pd.to_datetime("2026-08-31 23:00:00")

    # Combine TRAIN + VALID
    train_val_df = df_encoded[df_encoded["Timestamp"] < val_end].copy()
    test_df = df_encoded[(df_encoded["Timestamp"] >= val_end) & (df_encoded["Timestamp"] <= test_end)].copy()

    return train_val_df, test_df

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
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    FINAL_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(HORIZON_METADATA_FILE, "r") as f:
        horizon_features = json.load(f)["horizon_features"]
        
    with open(BEST_PARAMS_JSON, "r") as f:
        best_params_all = json.load(f)
        
    train_val_df, test_df = load_data()
    
    print("\nStarting final model training on TRAIN+VALID set...\n")
    
    results = []
    
    for horizon in HORIZONS:
        print(f"--- Horizon: {horizon} ---")
        features = horizon_features[horizon]
        target = TARGETS[horizon]
        
        best_conf = best_params_all[horizon]
        params = best_conf["params"]
        best_iter = best_conf["best_iteration"]
        
        t_mask = train_val_df[target].notna()
        test_mask = test_df[target].notna()
        
        X_train_val = train_val_df.loc[t_mask, features]
        y_train_val = train_val_df.loc[t_mask, target]
        
        X_test = test_df.loc[test_mask, features]
        y_test = test_df.loc[test_mask, target]
        
        print(f"  Training on {len(X_train_val)} samples with {len(features)} features")
        print(f"  Using params: {params}")
        print(f"  Setting n_estimators = {best_iter}")
        
        model = xgb.XGBRegressor(
            **params,
            n_estimators=best_iter,
            objective="reg:squarederror",
            random_state=42,
            n_jobs=-1,
        )
        
        start_t = time.time()
        model.fit(X_train_val, y_train_val, verbose=False)
        duration = time.time() - start_t
        print(f"  Training finished in {duration:.1f} seconds")
        
        # Evaluate on TEST
        y_pred = model.predict(X_test)
        metrics = evaluate_predictions(y_test, y_pred)
        print(f"  Final Test Metrics: {metrics}")
        
        # Save model
        model_path = MODELS_DIR / f"xgb_weather_pm25_{horizon}_tuned.joblib"
        joblib.dump(model, model_path)
        print(f"  Saved model to {model_path}\n")
        
        results.append({
            "Horizon": horizon,
            "Final Test MAE": metrics["MAE"],
            "Final Test RMSE": metrics["RMSE"],
            "Final Test R2": metrics["R2"],
            "Final Test Bias": metrics["bias"],
            "Final Test MedAE": metrics["MedAE"],
        })
        
    # Save final results summary
    df_results = pd.DataFrame(results)
    csv_path = FINAL_REPORTS_DIR / "tuned_models_final_test_results.csv"
    df_results.to_csv(csv_path, index=False)
    print(f"Final test evaluation results saved to {csv_path}")
    print("All tasks completed.")

if __name__ == "__main__":
    main()
