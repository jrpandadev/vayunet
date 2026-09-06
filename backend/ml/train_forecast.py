import argparse
from pathlib import Path
import json

import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb
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
    print("Loading data...")
    df = pd.read_csv(PROCESSED_DATA_FILE, parse_dates=["Timestamp"])
    # Strictly sort by timestamp for chronological split
    df = df.sort_values(by="Timestamp").reset_index(drop=True)
    return df

def prepare_features(df):
    # Features to drop
    drop_cols = ["Timestamp", "segment_id"] + list(TARGETS.values())
    
    # One-hot encode station_id
    df_encoded = pd.get_dummies(df, columns=["station_id"], dtype=int)
    
    # Get final feature list
    feature_cols = [c for c in df_encoded.columns if c not in drop_cols]
    
    return df_encoded, feature_cols

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
    
    return mae, rmse, r2

def main():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    
    if not PROCESSED_DATA_FILE.exists():
        raise FileNotFoundError(f"Data file not found: {PROCESSED_DATA_FILE}")
        
    df = load_data()
    
    # Verify targets exist
    for _, t_col in TARGETS.items():
        if t_col not in df.columns:
            raise ValueError(f"Expected target column {t_col} missing from dataset.")
            
    df_encoded, feature_cols = prepare_features(df)
    
    # Split
    train_df, val_df, test_df = chronological_split(df_encoded)
    
    # Print split info
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
    
    # Save feature list
    features_path = MODELS_DIR / "features.json"
    with open(features_path, "w") as f:
        json.dump(feature_cols, f, indent=2)
    print(f"Saved {len(feature_cols)} feature names to {features_path}\n")
    
    X_train = train_df[feature_cols]
    X_val = val_df[feature_cols]
    X_test = test_df[feature_cols]
    
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
    
    print("======================================================================")
    print("MODEL TRAINING & EVALUATION")
    print("======================================================================")
    
    for horizon, target_col in TARGETS.items():
        print(f"\nTraining {horizon} model ({target_col})...")
        
        y_train = train_df[target_col]
        y_val = val_df[target_col]
        y_test = test_df[target_col]
        
        # Drop NaNs in y for training
        train_mask = y_train.notna()
        X_train_valid = X_train[train_mask]
        y_train_valid = y_train[train_mask]
        
        # Also drop NaNs in validation for eval_set
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
        
        train_mae, train_rmse, train_r2 = evaluate(model, X_train, y_train)
        val_mae, val_rmse, val_r2 = evaluate(model, X_val, y_val)
        test_mae, test_rmse, test_r2 = evaluate(model, X_test, y_test)
        
        print(f"{horizon}:")
        print(f"Train MAE/RMSE/R²      : {train_mae:.2f} / {train_rmse:.2f} / {train_r2:.3f}")
        print(f"Validation MAE/RMSE/R² : {val_mae:.2f} / {val_rmse:.2f} / {val_r2:.3f}")
        print(f"Test MAE/RMSE/R²       : {test_mae:.2f} / {test_rmse:.2f} / {test_r2:.3f}")
        
        model_path = MODELS_DIR / f"xgb_pm25_{horizon}.joblib"
        joblib.dump(model, model_path)
        print(f"Saved to {model_path}")

if __name__ == "__main__":
    main()
