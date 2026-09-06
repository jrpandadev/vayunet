import os
import json
from pathlib import Path

import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb
import joblib

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DATA_FILE = BASE_DIR / "data" / "processed" / "delhi_forecasting_weather.csv"
MODELS_DIR = BASE_DIR / "models"
REPORTS_DIR = BASE_DIR / "reports" / "final_weather_evaluation"

TARGETS = {
    "6h": "target_pm25_6h",
    "24h": "target_pm25_24h",
    "72h": "target_pm25_72h",
}
HORIZONS = ["6h", "24h", "72h"]

SELECTED_WEATHER = {
    "6h": ["shortwave_radiation", "dew_point_2m", "wind_gusts_10m", "relative_humidity_2m", "boundary_layer_height"],
    "24h": ["temperature_2m", "dew_point_2m"],
    "72h": []
}

def load_data():
    df = pd.read_csv(PROCESSED_DATA_FILE, parse_dates=["timestamp"])
    if 'timestamp' in df.columns:
        df.rename(columns={'timestamp': 'Timestamp'}, inplace=True)
    df = df.sort_values(by="Timestamp").reset_index(drop=True)
    return df

def chronological_split(df, train_frac=0.60, val_frac=0.20):
    n = len(df)
    train_end = int(n * train_frac)
    val_end = train_end + int(n * val_frac)
    
    train_df = df.iloc[:train_end].copy()
    val_df = df.iloc[train_end:val_end].copy()
    test_df = df.iloc[val_end:].copy()
    
    return train_df, val_df, test_df

def evaluate(model, X, y):
    mask = y.notna()
    if mask.sum() == 0:
        return np.nan, np.nan, np.nan, np.nan, np.nan
        
    y_true = y[mask]
    X_valid = X[mask]
    
    y_pred = model.predict(X_valid)
    
    err = y_pred - y_true
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    bias = np.mean(err)
    medae = np.median(np.abs(err))
    
    return mae, rmse, r2, bias, medae

def prepare_features(df, baseline_features):
    return pd.get_dummies(df, columns=["station_id"], dtype=int)

def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    if not PROCESSED_DATA_FILE.exists():
        raise FileNotFoundError(f"Data file not found: {PROCESSED_DATA_FILE}")
        
    baseline_features_path = MODELS_DIR / "features.json"
    with open(baseline_features_path, "r") as f:
        baseline_features = json.load(f)
        
    print("Loading data...")
    df = load_data()
    df_encoded = prepare_features(df, baseline_features)
    
    train_df, val_df, test_df = chronological_split(df_encoded, train_frac=0.60, val_frac=0.20)
    
    summary_lines = []
    def log(msg, also_print=True):
        if also_print:
            print(msg)
        summary_lines.append(msg)
        
    log("======================================================================")
    log("FINAL WEATHER EVALUATION SPLIT (60/20/20)")
    log("======================================================================")
    log(f"Train : {train_df['Timestamp'].min()} to {train_df['Timestamp'].max()} (N={len(train_df)})")
    log(f"Valid : {val_df['Timestamp'].min()} to {val_df['Timestamp'].max()} (N={len(val_df)})")
    log(f"Test  : {test_df['Timestamp'].min()} to {test_df['Timestamp'].max()} (N={len(test_df)})")
    
    params = {
        "n_estimators": 200,
        "max_depth": 5,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "objective": "reg:squarederror",
        "random_state": 42,
        "n_jobs": -1
    }
    
    results = []
    
    for horizon, target_col in TARGETS.items():
        log(f"\n======================================================================")
        log(f"HORIZON: {horizon}")
        log(f"======================================================================")
        
        y_train = train_df[target_col]
        y_val = val_df[target_col]
        y_test = test_df[target_col]
        
        t_mask = y_train.notna()
        v_mask = y_val.notna()
        
        # --- BASELINE ---
        log(f"  Training BASELINE (42 features)...")
        X_train_b = train_df[baseline_features]
        X_val_b = val_df[baseline_features]
        X_test_b = test_df[baseline_features]
        
        baseline_model = xgb.XGBRegressor(**params)
        baseline_model.fit(
            X_train_b[t_mask], y_train[t_mask],
            eval_set=[(X_val_b[v_mask], y_val[v_mask])], verbose=False
        )
        b_mae, b_rmse, b_r2, b_bias, b_medae = evaluate(baseline_model, X_test_b, y_test)
        
        # --- WEATHER ---
        weather_feats = SELECTED_WEATHER[horizon]
        exp_features = baseline_features + weather_feats
        log(f"  Training WEATHER ({len(exp_features)} features)...")
        
        X_train_w = train_df[exp_features]
        X_val_w = val_df[exp_features]
        X_test_w = test_df[exp_features]
        
        weather_model = xgb.XGBRegressor(**params)
        weather_model.fit(
            X_train_w[t_mask], y_train[t_mask],
            eval_set=[(X_val_w[v_mask], y_val[v_mask])], verbose=False
        )
        w_mae, w_rmse, w_r2, w_bias, w_medae = evaluate(weather_model, X_test_w, y_test)
        
        mae_diff = b_mae - w_mae
        mae_imp = (mae_diff / b_mae) * 100 if b_mae > 0 else 0
        rmse_diff = b_rmse - w_rmse
        rmse_imp = (rmse_diff / b_rmse) * 100 if b_rmse > 0 else 0
        r2_diff = w_r2 - b_r2
        
        results.append({
            "Horizon": horizon,
            
            "Baseline MAE": b_mae,
            "Weather MAE": w_mae,
            "Abs MAE Diff": mae_diff,
            "MAE Imp %": mae_imp,
            
            "Baseline RMSE": b_rmse,
            "Weather RMSE": w_rmse,
            "Abs RMSE Diff": rmse_diff,
            "RMSE Imp %": rmse_imp,
            
            "Baseline R2": b_r2,
            "Weather R2": w_r2,
            "R2 Diff": r2_diff,
            
            "Baseline Bias": b_bias,
            "Weather Bias": w_bias,
            
            "Baseline MedAE": b_medae,
            "Weather MedAE": w_medae
        })
        
    df_res = pd.DataFrame(results)
    df_res.to_csv(REPORTS_DIR / "final_weather_results.csv", index=False)
    
    log("\n=========================================================================================")
    log("FINAL WEATHER EVALUATION SUMMARY (OUT-OF-SAMPLE TEST)")
    log("=========================================================================================")
    
    header = f"{'Horiz':<5} | {'BaseMAE':<7} | {'WeatMAE':<7} | {'MAE Imp%':<9} | {'Abs MAE':<7} | {'BaseRMSE':<8} | {'WeatRMSE':<8} | {'RMSE Imp%':<9} | {'Abs RMSE':<8} | {'R² Diff':<8} | {'BaseBias':<8} | {'WeatBias':<8} | {'BaseMedAE':<9} | {'WeatMedAE':<9}"
    log(header)
    log("-" * len(header))
    
    for r in results:
        line = f"{r['Horizon']:<5} | {r['Baseline MAE']:7.2f} | {r['Weather MAE']:7.2f} | {r['MAE Imp %']:8.2f}% | {r['Abs MAE Diff']:7.2f} | {r['Baseline RMSE']:8.2f} | {r['Weather RMSE']:8.2f} | {r['RMSE Imp %']:8.2f}% | {r['Abs RMSE Diff']:8.2f} | {r['R2 Diff']:+8.3f} | {r['Baseline Bias']:8.2f} | {r['Weather Bias']:8.2f} | {r['Baseline MedAE']:9.2f} | {r['Weather MedAE']:9.2f}"
        log(line)
        
    with open(REPORTS_DIR / "final_weather_summary.txt", "w") as f:
        f.write("\n".join(summary_lines))
        
    print(f"\nSaved final weather evaluation results to {REPORTS_DIR}")

if __name__ == "__main__":
    main()
