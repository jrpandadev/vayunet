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
REPORTS_DIR = BASE_DIR / "reports" / "weather_ablation"

TARGETS = {
    "6h": "target_pm25_6h",
    "24h": "target_pm25_24h",
    "72h": "target_pm25_72h",
}

HORIZONS = ["6h", "24h", "72h"]

ALL_WEATHER_FEATURES = [
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "precipitation",
    "surface_pressure",
    "cloud_cover",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    "shortwave_radiation",
    "boundary_layer_height"
]

EXPERIMENTS = {
    "A_BASELINE": [],
    "B_ALL_WEATHER": ALL_WEATHER_FEATURES,
    "C_ATMOSPHERIC": ["temperature_2m", "relative_humidity_2m", "dew_point_2m", "surface_pressure"],
    "D_WIND": ["wind_speed_10m", "wind_direction_10m", "wind_gusts_10m"],
    "E_RADIATION_CLOUD": ["shortwave_radiation", "cloud_cover"],
    "F_PRECIPITATION": ["precipitation"],
    "G_PBL": ["boundary_layer_height"]
}

def load_data():
    print("Loading data...")
    df = pd.read_csv(PROCESSED_DATA_FILE, parse_dates=["timestamp"])
    if 'timestamp' in df.columns:
        df.rename(columns={'timestamp': 'Timestamp'}, inplace=True)
    df = df.sort_values(by="Timestamp").reset_index(drop=True)
    return df

def chronological_split(df, train_frac=0.70, val_frac=0.15):
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
        return np.nan, np.nan, np.nan, np.nan
        
    y_true = y[mask]
    X_valid = X[mask]
    
    y_pred = model.predict(X_valid)
    
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    bias = np.mean(y_pred - y_true)
    
    return mae, rmse, r2, bias

def prepare_features(df, baseline_features):
    df_encoded = pd.get_dummies(df, columns=["station_id"], dtype=int)
    return df_encoded

def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    if not PROCESSED_DATA_FILE.exists():
        raise FileNotFoundError(f"Data file not found: {PROCESSED_DATA_FILE}")
        
    baseline_features_path = MODELS_DIR / "features.json"
    with open(baseline_features_path, "r") as f:
        baseline_features = json.load(f)
        
    df = load_data()
    df_encoded = prepare_features(df, baseline_features)
    train_df, val_df, test_df = chronological_split(df_encoded)
    
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
    baseline_metrics = {} # {horizon: {mae, rmse, r2}}
    
    print("\nStarting Weather Ablation Experiment")
    print("="*70)
    
    for exp_name, weather_feats in EXPERIMENTS.items():
        print(f"\n--- Experiment: {exp_name} ---")
        exp_features = baseline_features + weather_feats
        
        X_train = train_df[exp_features]
        X_val = val_df[exp_features]
        X_test = test_df[exp_features]
        
        for horizon, target_col in TARGETS.items():
            print(f"  Training {horizon} model...")
            
            y_train = train_df[target_col]
            y_val = val_df[target_col]
            y_test = test_df[target_col]
            
            train_mask = y_train.notna()
            val_mask = y_val.notna()
            
            model = xgb.XGBRegressor(**params)
            model.fit(
                X_train[train_mask], 
                y_train[train_mask],
                eval_set=[(X_val[val_mask], y_val[val_mask])],
                verbose=False
            )
            
            test_mae, test_rmse, test_r2, test_bias = evaluate(model, X_test, y_test)
            
            if exp_name == "A_BASELINE":
                baseline_metrics[horizon] = {
                    "mae": test_mae,
                    "rmse": test_rmse,
                    "r2": test_r2
                }
                mae_imp = 0.0
                rmse_imp = 0.0
                r2_change = 0.0
            else:
                b_mae = baseline_metrics[horizon]["mae"]
                b_rmse = baseline_metrics[horizon]["rmse"]
                b_r2 = baseline_metrics[horizon]["r2"]
                
                mae_imp = ((b_mae - test_mae) / b_mae) * 100
                rmse_imp = ((b_rmse - test_rmse) / b_rmse) * 100
                r2_change = test_r2 - b_r2
                
            results.append({
                "Experiment": exp_name,
                "Horizon": horizon,
                "MAE": test_mae,
                "RMSE": test_rmse,
                "R2": test_r2,
                "Bias": test_bias,
                "MAE improvement": mae_imp,
                "RMSE improvement": rmse_imp,
                "R2 change": r2_change
            })
            
    df_results = pd.DataFrame(results)
    
    print("\n" + "="*90)
    print("ALL ABLATION RESULTS")
    print("="*90)
    header = f"{'Experiment':<20} | {'Horiz':<5} | {'MAE':<7} | {'RMSE':<7} | {'R²':<7} | {'Bias':<7} | {'MAE Imp%':<9} | {'RMSE Imp%':<9} | {'R² diff'}"
    print(header)
    print("-" * len(header))
    summary_lines = [header, "-" * len(header)]
    
    for r in results:
        line = f"{r['Experiment']:<20} | {r['Horizon']:<5} | {r['MAE']:7.2f} | {r['RMSE']:7.2f} | {r['R2']:7.3f} | {r['Bias']:7.2f} | {r['MAE improvement']:8.2f}% | {r['RMSE improvement']:8.2f}% | {r['R2 change']:+7.3f}"
        print(line)
        summary_lines.append(line)
        
    print("\n" + "="*90)
    print("BEST EXPERIMENT FOR EACH HORIZON (By MAE)")
    print("="*90)
    summary_lines.extend(["\n" + "="*90, "BEST EXPERIMENT FOR EACH HORIZON (By MAE)", "="*90, header, "-" * len(header)])
    
    best_results = []
    for horizon in HORIZONS:
        df_h = df_results[df_results["Horizon"] == horizon]
        best_row = df_h.loc[df_h["MAE"].idxmin()]
        best_results.append(best_row)
        r = best_row
        line = f"{r['Experiment']:<20} | {r['Horizon']:<5} | {r['MAE']:7.2f} | {r['RMSE']:7.2f} | {r['R2']:7.3f} | {r['Bias']:7.2f} | {r['MAE improvement']:8.2f}% | {r['RMSE improvement']:8.2f}% | {r['R2 change']:+7.3f}"
        print(line)
        summary_lines.append(line)
        
    # Save CSV and text report
    df_results.to_csv(REPORTS_DIR / "ablation_results.csv", index=False)
    with open(REPORTS_DIR / "ablation_summary.txt", "w") as f:
        f.write("\n".join(summary_lines))
        
    print(f"\nSaved ablation results to {REPORTS_DIR}")

if __name__ == "__main__":
    main()
