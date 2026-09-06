import os
import json
import argparse
from pathlib import Path

import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb
import joblib

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DATA_FILE = BASE_DIR / "data" / "processed" / "delhi_forecasting_weather.csv"
MODELS_DIR = BASE_DIR / "models"
REPORTS_DIR = BASE_DIR / "reports"

TARGETS = {
    "6h": "target_pm25_6h",
    "24h": "target_pm25_24h",
    "72h": "target_pm25_72h",
}

WEATHER_FEATURES = [
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

def load_data():
    print("Loading data...")
    df = pd.read_csv(PROCESSED_DATA_FILE, parse_dates=["timestamp"])
    # Standardize column name if necessary to match the train_forecast logic which expects Timestamp (capital T) for split logging, though here it's lowercase 'timestamp' from merge
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
        return np.nan, np.nan, np.nan
        
    y_true = y[mask]
    X_valid = X[mask]
    
    y_pred = model.predict(X_valid)
    
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    
    bias = np.mean(y_pred - y_true)
    
    return mae, rmse, r2, bias

def prepare_features(df, baseline_features):
    # Features to drop for baseline were: ["Timestamp", "segment_id"] + TARGETS
    # The one-hot encoding was done on station_id. Let's do exactly that.
    df_encoded = pd.get_dummies(df, columns=["station_id"], dtype=int)
    
    # Weather features are already in the dataframe and unchanged.
    weather_feature_cols = baseline_features + WEATHER_FEATURES
    
    # Check if all weather features are present
    for wf in WEATHER_FEATURES:
        if wf not in df_encoded.columns:
            raise ValueError(f"Weather feature {wf} missing from encoded dataset.")
            
    return df_encoded, weather_feature_cols

def main():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    if not PROCESSED_DATA_FILE.exists():
        raise FileNotFoundError(f"Data file not found: {PROCESSED_DATA_FILE}")
        
    # Load baseline feature list
    baseline_features_path = MODELS_DIR / "features.json"
    with open(baseline_features_path, "r") as f:
        baseline_features = json.load(f)
        
    df = load_data()
    
    # Validations
    print("Running pre-training validations...")
    assert len(df) == 383303, f"Row count {len(df)} != 383303"
    assert df['station_id'].nunique() == 10, "Station count != 10"
    assert df.duplicated(subset=['station_id', 'Timestamp']).sum() == 0, "Duplicate timestamps found"
    
    # Check existing features
    df_encoded, feature_cols = prepare_features(df, baseline_features)
    for bf in baseline_features:
        assert bf in df_encoded.columns, f"Baseline feature {bf} missing"
    
    for wf in WEATHER_FEATURES:
        assert wf in df_encoded.columns, f"Weather feature {wf} missing"
        
    for _, t_col in TARGETS.items():
        assert t_col in df_encoded.columns, f"Target column {t_col} missing"
        
    print("\nWeather Features Missing Values:")
    for wf in WEATHER_FEATURES:
        missing = df_encoded[wf].isna().sum()
        print(f"  {wf}: {missing} ({(missing/len(df_encoded))*100:.2f}%)")
        
    print("\nValidations passed.")
    
    # Split
    train_df, val_df, test_df = chronological_split(df_encoded)
    
    print("\n======================================================================")
    print("DATA SPLIT (CHRONOLOGICAL)")
    print("======================================================================")
    def print_split_info(name, split_df):
        start = split_df["Timestamp"].min()
        end = split_df["Timestamp"].max()
        count = len(split_df)
        print(f"{name:12s}: {count:,} samples | {start} to {end}")
        
    print_split_info("Train", train_df)
    print_split_info("Validation", val_df)
    print_split_info("Test", test_df)
    print()
    
    # Save new feature list
    features_path = MODELS_DIR / "xgb_weather_feature_metadata.json"
    with open(features_path, "w") as f:
        json.dump(feature_cols, f, indent=2)
    print(f"Saved {len(feature_cols)} weather feature names to {features_path}\n")
    
    X_train = train_df[feature_cols]
    X_val = val_df[feature_cols]
    X_test = test_df[feature_cols]
    
    # For baseline evaluation
    X_test_baseline = test_df[baseline_features]
    
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
    
    report_lines = []
    report_lines.append("WEATHER MODEL TRAINING & COMPARISON REPORT")
    report_lines.append("========================================\n")
    
    results = []
    
    for horizon, target_col in TARGETS.items():
        print(f"\nTraining Weather Model for {horizon} horizon ({target_col})...")
        
        y_train = train_df[target_col]
        y_val = val_df[target_col]
        y_test = test_df[target_col]
        
        train_mask = y_train.notna()
        X_train_valid = X_train[train_mask]
        y_train_valid = y_train[train_mask]
        
        val_mask = y_val.notna()
        X_val_valid = X_val[val_mask]
        y_val_valid = y_val[val_mask]
        
        model = xgb.XGBRegressor(**params)
        model.fit(
            X_train_valid, 
            y_train_valid,
            eval_set=[(X_val_valid, y_val_valid)],
            verbose=False
        )
        
        train_mae, train_rmse, train_r2, _ = evaluate(model, X_train, y_train)
        val_mae, val_rmse, val_r2, _ = evaluate(model, X_val, y_val)
        test_mae, test_rmse, test_r2, test_bias = evaluate(model, X_test, y_test)
        
        print(f"Weather Model {horizon}:")
        print(f"Train MAE/RMSE/R²      : {train_mae:.2f} / {train_rmse:.2f} / {train_r2:.3f}")
        print(f"Validation MAE/RMSE/R² : {val_mae:.2f} / {val_rmse:.2f} / {val_r2:.3f}")
        print(f"Test MAE/RMSE/R²       : {test_mae:.2f} / {test_rmse:.2f} / {test_r2:.3f}")
        
        model_path = MODELS_DIR / f"xgb_weather_pm25_{horizon}.joblib"
        joblib.dump(model, model_path)
        print(f"Saved weather model to {model_path}")
        
        # Load Baseline model and evaluate
        baseline_model_path = MODELS_DIR / f"xgb_pm25_{horizon}.joblib"
        baseline_model = joblib.load(baseline_model_path)
        b_test_mae, b_test_rmse, b_test_r2, b_test_bias = evaluate(baseline_model, X_test_baseline, y_test)
        
        # Improvement relative to baseline
        # improvement = (baseline - weather_model) / baseline * 100
        mae_imp = ((b_test_mae - test_mae) / b_test_mae) * 100
        rmse_imp = ((b_test_rmse - test_rmse) / b_test_rmse) * 100
        r2_diff = test_r2 - b_test_r2
        
        print(f"Baseline {horizon} Test:")
        print(f"Test MAE/RMSE/R²       : {b_test_mae:.2f} / {b_test_rmse:.2f} / {b_test_r2:.3f}")
        
        res_dict = {
            "Horizon": horizon,
            "Baseline MAE": b_test_mae,
            "Weather MAE": test_mae,
            "MAE improvement": mae_imp,
            "Baseline RMSE": b_test_rmse,
            "Weather RMSE": test_rmse,
            "RMSE improvement": rmse_imp,
            "Baseline R2": b_test_r2,
            "Weather R2": test_r2,
            "R2 change": r2_diff,
            "Baseline Bias": b_test_bias,
            "Weather Bias": test_bias
        }
        results.append(res_dict)
        
        report_lines.append(f"HORIZON: {horizon}")
        report_lines.append(f"Weather Model Train MAE: {train_mae:.2f}, RMSE: {train_rmse:.2f}, R2: {train_r2:.3f}")
        report_lines.append(f"Weather Model Val MAE:   {val_mae:.2f}, RMSE: {val_rmse:.2f}, R2: {val_r2:.3f}")
        report_lines.append(f"Weather Model Test MAE:  {test_mae:.2f}, RMSE: {test_rmse:.2f}, R2: {test_r2:.3f}, Bias: {test_bias:.2f}")
        report_lines.append(f"Baseline Model Test MAE: {b_test_mae:.2f}, RMSE: {b_test_rmse:.2f}, R2: {b_test_r2:.3f}, Bias: {b_test_bias:.2f}")
        report_lines.append(f"Improvements -> MAE: {mae_imp:+.2f}%, RMSE: {rmse_imp:+.2f}%, R2 diff: {r2_diff:+.3f}\n")
        
    print("\n======================================================================")
    print("FINAL COMPARISON")
    print("======================================================================")
    header = f"{'Horizon':<8} | {'Baseline MAE':<12} | {'Weather MAE':<11} | {'MAE imp %':<10} | {'Baseline RMSE':<13} | {'Weather RMSE':<12} | {'RMSE imp %':<10} | {'Baseline R²':<11} | {'Weather R²':<10} | {'R² change'}"
    print(header)
    print("-" * len(header))
    for r in results:
        line = f"{r['Horizon']:<8} | {r['Baseline MAE']:<12.2f} | {r['Weather MAE']:<11.2f} | {r['MAE improvement']:<10.2f} | {r['Baseline RMSE']:<13.2f} | {r['Weather RMSE']:<12.2f} | {r['RMSE improvement']:<10.2f} | {r['Baseline R2']:<11.3f} | {r['Weather R2']:<10.3f} | {r['R2 change']:.3f}"
        print(line)
        report_lines.append(line)
        
    # Save CSV
    df_results = pd.DataFrame(results)
    csv_path = REPORTS_DIR / "weather_model_comparison.csv"
    df_results.to_csv(csv_path, index=False)
    print(f"\nSaved comparison to {csv_path}")
    
    # Save txt report
    txt_path = REPORTS_DIR / "weather_model_training_report.txt"
    with open(txt_path, "w") as f:
        f.write("\n".join(report_lines))
    print(f"Saved text report to {txt_path}")

if __name__ == "__main__":
    main()
