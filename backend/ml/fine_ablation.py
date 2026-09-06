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

# Define the fine-grained experiments
EXPERIMENTS_6H = {
    "BASELINE": [],
    "ALL_WEATHER": [
        "temperature_2m", "relative_humidity_2m", "dew_point_2m", "precipitation",
        "surface_pressure", "cloud_cover", "wind_speed_10m", "wind_direction_10m",
        "wind_gusts_10m", "shortwave_radiation", "boundary_layer_height"
    ],
    "NO_PRECIP": [
        "temperature_2m", "relative_humidity_2m", "dew_point_2m",
        "surface_pressure", "cloud_cover", "wind_speed_10m", "wind_direction_10m",
        "wind_gusts_10m", "shortwave_radiation", "boundary_layer_height"
    ],
    "NO_WIND_DIR": [
        "temperature_2m", "relative_humidity_2m", "dew_point_2m", "precipitation",
        "surface_pressure", "cloud_cover", "wind_speed_10m",
        "wind_gusts_10m", "shortwave_radiation", "boundary_layer_height"
    ],
    "NO_PRECIP_WIND_DIR": [
        "temperature_2m", "relative_humidity_2m", "dew_point_2m",
        "surface_pressure", "cloud_cover", "wind_speed_10m",
        "wind_gusts_10m", "shortwave_radiation", "boundary_layer_height"
    ],
    "ONLY_STRONG": [
        "shortwave_radiation", "dew_point_2m", "wind_gusts_10m", 
        "relative_humidity_2m", "boundary_layer_height"
    ],
    "ONLY_TOP_3": [
        "shortwave_radiation", "dew_point_2m", "wind_gusts_10m"
    ]
}

EXPERIMENTS_24H = {
    "BASELINE": [],
    "ATMOSPHERIC": ["temperature_2m", "relative_humidity_2m", "dew_point_2m", "surface_pressure"],
    "T": ["temperature_2m"],
    "RH": ["relative_humidity_2m"],
    "DP": ["dew_point_2m"],
    "P": ["surface_pressure"],
    "T_RH": ["temperature_2m", "relative_humidity_2m"],
    "T_DP": ["temperature_2m", "dew_point_2m"],
    "T_P": ["temperature_2m", "surface_pressure"],
    "RH_DP": ["relative_humidity_2m", "dew_point_2m"],
    "RH_P": ["relative_humidity_2m", "surface_pressure"],
    "DP_P": ["dew_point_2m", "surface_pressure"],
    "T_RH_DP": ["temperature_2m", "relative_humidity_2m", "dew_point_2m"],
    "T_RH_P": ["temperature_2m", "relative_humidity_2m", "surface_pressure"],
    "T_DP_P": ["temperature_2m", "dew_point_2m", "surface_pressure"],
    "RH_DP_P": ["relative_humidity_2m", "dew_point_2m", "surface_pressure"],
}

# 72h will not be optimized heavily based on user instruction, so we skip it.

def load_data():
    df = pd.read_csv(PROCESSED_DATA_FILE, parse_dates=["timestamp"])
    if 'timestamp' in df.columns:
        df.rename(columns={'timestamp': 'Timestamp'}, inplace=True)
    df = df.sort_values(by="Timestamp").reset_index(drop=True)
    return df

def chronological_split(df, train_frac=0.70, val_frac=0.15):
    n = len(df)
    train_end = int(n * train_frac)
    val_end = train_end + int(n * val_frac)
    return df.iloc[:train_end].copy(), df.iloc[train_end:val_end].copy(), df.iloc[val_end:].copy()

def evaluate(model, X, y):
    mask = y.notna()
    if mask.sum() == 0:
        return np.nan, np.nan, np.nan, np.nan
    y_true = y[mask]
    y_pred = model.predict(X[mask])
    
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    bias = np.mean(y_pred - y_true)
    return mae, rmse, r2, bias

def prepare_features(df, baseline_features):
    return pd.get_dummies(df, columns=["station_id"], dtype=int)

def run_experiments_for_horizon(horizon, target_col, experiments, train_df, val_df, test_df, baseline_features, params):
    print(f"\n======================================================================")
    print(f"FINE ABLATION FOR {horizon} HORIZON")
    print(f"======================================================================")
    
    results = []
    
    # Run Baseline first
    print(f"  Training BASELINE...")
    X_train = train_df[baseline_features]
    X_val = val_df[baseline_features]
    X_test = test_df[baseline_features]
    
    y_train = train_df[target_col]
    y_val = val_df[target_col]
    y_test = test_df[target_col]
    
    t_mask = y_train.notna()
    v_mask = y_val.notna()
    
    baseline_model = xgb.XGBRegressor(**params)
    baseline_model.fit(
        X_train[t_mask], y_train[t_mask],
        eval_set=[(X_val[v_mask], y_val[v_mask])], verbose=False
    )
    b_mae, b_rmse, b_r2, b_bias = evaluate(baseline_model, X_test, y_test)
    
    results.append({
        "Experiment": "BASELINE",
        "MAE": b_mae, "RMSE": b_rmse, "R2": b_r2, "Bias": b_bias,
        "MAE Imp%": 0.0, "RMSE Imp%": 0.0, "R2 diff": 0.0
    })
    
    for exp_name, weather_feats in experiments.items():
        if exp_name == "BASELINE":
            continue
            
        print(f"  Training {exp_name}...")
        exp_features = baseline_features + weather_feats
        
        X_train_e = train_df[exp_features]
        X_val_e = val_df[exp_features]
        X_test_e = test_df[exp_features]
        
        model = xgb.XGBRegressor(**params)
        model.fit(
            X_train_e[t_mask], y_train[t_mask],
            eval_set=[(X_val_e[v_mask], y_val[v_mask])], verbose=False
        )
        t_mae, t_rmse, t_r2, t_bias = evaluate(model, X_test_e, y_test)
        
        mae_imp = ((b_mae - t_mae) / b_mae) * 100
        rmse_imp = ((b_rmse - t_rmse) / b_rmse) * 100
        r2_diff = t_r2 - b_r2
        
        results.append({
            "Experiment": exp_name,
            "MAE": t_mae, "RMSE": t_rmse, "R2": t_r2, "Bias": t_bias,
            "MAE Imp%": mae_imp, "RMSE Imp%": rmse_imp, "R2 diff": r2_diff
        })
        
    df_res = pd.DataFrame(results)
    
    print("\nRESULTS:")
    header = f"{'Experiment':<20} | {'MAE':<7} | {'RMSE':<7} | {'R²':<7} | {'Bias':<7} | {'MAE Imp%':<9} | {'RMSE Imp%':<9} | {'R² diff'}"
    print(header)
    print("-" * len(header))
    for r in results:
        print(f"{r['Experiment']:<20} | {r['MAE']:7.2f} | {r['RMSE']:7.2f} | {r['R2']:7.3f} | {r['Bias']:7.2f} | {r['MAE Imp%']:8.2f}% | {r['RMSE Imp%']:8.2f}% | {r['R2 diff']:+7.3f}")
        
    return df_res

def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(MODELS_DIR / "features.json", "r") as f:
        baseline_features = json.load(f)
        
    print("Loading data...")
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
    
    df_6h = run_experiments_for_horizon("6h", "target_pm25_6h", EXPERIMENTS_6H, train_df, val_df, test_df, baseline_features, params)
    df_24h = run_experiments_for_horizon("24h", "target_pm25_24h", EXPERIMENTS_24H, train_df, val_df, test_df, baseline_features, params)
    
    df_6h["Horizon"] = "6h"
    df_24h["Horizon"] = "24h"
    
    all_res = pd.concat([df_6h, df_24h])
    all_res.to_csv(REPORTS_DIR / "fine_ablation_results.csv", index=False)
    print(f"\nSaved fine ablation results to {REPORTS_DIR / 'fine_ablation_results.csv'}")

if __name__ == "__main__":
    main()
