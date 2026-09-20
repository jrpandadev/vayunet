"""
Controlled Random Forest Baseline Training Script for VayuNet PM2.5 Forecasting.

Trains one RandomForestRegressor per forecasting horizon (6h, 24h, 72h) against
the locked tuned XGBoost champion models using the exact same canonical feature sets
and chronological train/validation/test split protocol.

Rules & Constraints:
- Does NOT modify feature_builder.py, forecast_service.py, canonical dataset, or champion models.
- Uses exact canonical horizon feature sets:
    6h: 47 features
    24h: 44 features
    72h: 42 features
- Chronological protocol:
    Train+Valid: Timestamp < 2025-08-30 15:00:00 (N ~ 306,638)
    Test: 2025-08-30 15:00:00 to 2026-08-31 23:00:00 (N = 76,665)
- No target imputation. Rows with missing target values are dropped.
- Uses sklearn.ensemble.RandomForestRegressor with default n_estimators=100, random_state=42, n_jobs=-1.
- Validates pre-training alignment against XGBoost champion test setup.
- Saves baseline models to backend/models/rf_pm25_{h}_baseline.joblib.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, median_absolute_error

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths & Configuration
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

DATA_FILE = BASE_DIR / "data" / "processed" / "delhi_forecasting_weather.csv"
HORIZON_METADATA_FILE = BASE_DIR / "models" / "horizon_features.json"
MODELS_DIR = BASE_DIR / "models"
RESULTS_DIR = BASE_DIR / "ml" / "results"

HORIZONS = ["6h", "24h", "72h"]
HORIZON_HOURS = {"6h": 6, "24h": 24, "72h": 72}
TARGET_COLS = {
    "6h": "target_pm25_6h",
    "24h": "target_pm25_24h",
    "72h": "target_pm25_72h",
}

CHAMPION_MODEL_FILES = {
    "6h": MODELS_DIR / "xgb_weather_pm25_6h_tuned.joblib",
    "24h": MODELS_DIR / "xgb_weather_pm25_24h_tuned.joblib",
    "72h": MODELS_DIR / "xgb_weather_pm25_72h_tuned.joblib",
}

RF_MODEL_FILES = {
    "6h": MODELS_DIR / "rf_pm25_6h_baseline.joblib",
    "24h": MODELS_DIR / "rf_pm25_24h_baseline.joblib",
    "72h": MODELS_DIR / "rf_pm25_72h_baseline.joblib",
}

EXPECTED_STATIONS = sorted([
    "anand vihar", "aya nagar", "bawana", "ito", "jahangirpuri",
    "narela", "punjabi bagh", "r k puram", "vivek vihar", "wazirpur",
])

VAL_END = pd.Timestamp("2025-08-30 15:00:00")
TEST_END = pd.Timestamp("2026-08-31 23:00:00")


def load_dataset() -> Tuple[pd.DataFrame, Dict[str, List[str]]]:
    """Load canonical dataset and canonical horizon feature definitions."""
    logger.info(f"Loading canonical dataset from {DATA_FILE.name}...")
    df = pd.read_csv(DATA_FILE, parse_dates=["timestamp"])
    if "timestamp" in df.columns:
        df.rename(columns={"timestamp": "Timestamp"}, inplace=True)
    df = df.sort_values(by=["Timestamp", "station_id"]).reset_index(drop=True)
    logger.info(f"Loaded {len(df):,} rows from {df['Timestamp'].min()} to {df['Timestamp'].max()}")

    # One-hot encode stations matching canonical features
    for stn in EXPECTED_STATIONS:
        df[f"station_id_{stn}"] = (df["station_id"] == stn).astype(int)

    with open(HORIZON_METADATA_FILE, "r") as f:
        meta = json.load(f)
    horizon_features = meta["horizon_features"]

    # Verify feature counts
    expected_counts = {"6h": 47, "24h": 44, "72h": 42}
    for h in HORIZONS:
        actual_count = len(horizon_features[h])
        expected_count = expected_counts[h]
        if actual_count != expected_count:
            raise ValueError(f"Feature count mismatch for {h}: expected {expected_count}, got {actual_count}")
        logger.info(f"Feature count verified: {h} has {actual_count} canonical features")

    return df, horizon_features


def verify_alignment_pre_training(df: pd.DataFrame, horizon_features: Dict[str, List[str]]) -> None:
    """Strictly verify that RF and XGBoost champion use identical origins, targets, and test rows."""
    logger.info("=" * 78)
    logger.info("MANDATORY PRE-TRAINING ALIGNMENT & INTEGRITY VERIFICATION")
    logger.info("=" * 78)

    test_df = df[(df["Timestamp"] >= VAL_END) & (df["Timestamp"] <= TEST_END)].copy().reset_index(drop=True)
    logger.info(f"Test slice: {len(test_df):,} rows from {test_df['Timestamp'].min()} to {test_df['Timestamp'].max()}")

    # 1. Station verification
    actual_stations = sorted(test_df["station_id"].unique().tolist())
    if actual_stations != EXPECTED_STATIONS:
        raise AssertionError(f"Station list mismatch: expected {EXPECTED_STATIONS}, got {actual_stations}")
    logger.info("  [PASS] Station IDs match exactly across all 10 canonical stations.")

    # 2. Duplicate forecast origins check
    dups = test_df.duplicated(subset=["Timestamp", "station_id"]).sum()
    if dups > 0:
        raise AssertionError(f"Found {dups} duplicate (Timestamp, station_id) test rows!")
    logger.info("  [PASS] Zero duplicate forecast origins in test slice.")

    # 3. Horizon-by-horizon alignment against locked champion models
    for h in HORIZONS:
        target_col = TARGET_COLS[h]
        h_hours = HORIZON_HOURS[h]
        c_path = CHAMPION_MODEL_FILES[h]
        if not c_path.exists():
            raise FileNotFoundError(f"Locked champion model not found: {c_path}")

        mask = test_df[target_col].notna()
        sub_df = test_df[mask].copy().reset_index(drop=True)
        y_test = sub_df[target_col].values
        origins = sub_df["Timestamp"]
        target_timestamps = origins + pd.Timedelta(hours=h_hours)

        # Check random spot samples to verify target matches PM2.5 at origin + horizon
        rng = np.random.RandomState(42)
        sample_indices = rng.choice(len(sub_df), size=min(10, len(sub_df)), replace=False)
        for idx in sample_indices:
            row = sub_df.iloc[idx]
            o_ts = row["Timestamp"]
            e_ts = o_ts + pd.Timedelta(hours=h_hours)
            t_val = row[target_col]
            match = df[(df["Timestamp"] == e_ts) & (df["station_id"] == row["station_id"])]
            if not match.empty:
                actual_val = match.iloc[0]["PM2.5"]
                if not np.isclose(t_val, actual_val, equal_nan=True):
                    raise AssertionError(f"Target timestamp misalignment for {h} at {o_ts}: {t_val} != {actual_val}")

        # Evaluate XGBoost champion on this exact slice to confirm reproduction
        feats = horizon_features[h]
        X_test = sub_df[feats].values
        champ_model = joblib.load(c_path)
        y_pred_champ = champ_model.predict(X_test)
        mae_champ = float(mean_absolute_error(y_test, y_pred_champ))

        # Expected baseline MAEs from locked evaluation
        expected_maes = {"6h": 33.5042, "24h": 39.2937, "72h": 44.8938}
        if not np.isclose(mae_champ, expected_maes[h], atol=1e-3):
            raise AssertionError(f"Champion MAE reproduction failed for {h}: expected {expected_maes[h]}, got {mae_champ:.4f}")

        logger.info(
            f"  [PASS] Horizon {h}: {len(sub_df):,} test rows, forecast origins & target timestamps strictly verified. "
            f"Champion MAE reproduced: {mae_champ:.4f}"
        )

    logger.info("=" * 78)
    logger.info("ALL INTEGRITY AND ALIGNMENT CHECKS PASSED PERFECTLY")
    logger.info("=" * 78 + "\n")


def train_rf_models(df: pd.DataFrame, horizon_features: Dict[str, List[str]]) -> None:
    """Train one RandomForestRegressor per horizon using default baseline parameters."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    train_val_df = df[df["Timestamp"] < VAL_END].copy()
    test_df = df[(df["Timestamp"] >= VAL_END) & (df["Timestamp"] <= TEST_END)].copy()

    logger.info(f"Dataset split: Train+Valid rows={len(train_val_df):,}, Test rows={len(test_df):,}")

    training_summary = []

    for h in HORIZONS:
        logger.info(f"\n{'=' * 60}\nTRAINING RANDOM FOREST BASELINE: {h}\n{'=' * 60}")
        feats = horizon_features[h]
        target = TARGET_COLS[h]

        train_mask = train_val_df[target].notna()
        test_mask = test_df[target].notna()

        X_train = train_val_df.loc[train_mask, feats].values
        y_train = train_val_df.loc[train_mask, target].values

        X_test = test_df.loc[test_mask, feats].values
        y_test = test_df.loc[test_mask, target].values

        nan_feature_count = int(np.isnan(X_train).sum())
        logger.info(
            f"  Horizon {h}: Training samples = {len(X_train):,}, Features = {len(feats)}, "
            f"NaN feature entries in train = {nan_feature_count:,}"
        )

        rf = RandomForestRegressor(
            n_estimators=100,
            criterion="squared_error",
            max_depth=None,
            min_samples_split=2,
            min_samples_leaf=1,
            random_state=42,
            n_jobs=-1,
            verbose=0,
        )

        logger.info(f"  Fitting RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)...")
        start_time = time.time()
        rf.fit(X_train, y_train)
        duration = time.time() - start_time
        logger.info(f"  Fitting completed in {duration:.1f} s ({duration / 60.0:.2f} min)")

        # Save model
        save_path = RF_MODEL_FILES[h]
        joblib.dump(rf, save_path)
        logger.info(f"  Saved trained baseline model to: {save_path.name}")

        # Quick test verification
        y_pred = rf.predict(X_test)
        mae = float(mean_absolute_error(y_test, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        r2 = float(r2_score(y_test, y_pred))
        logger.info(f"  Test metrics for RF {h}: MAE={mae:.4f}, RMSE={rmse:.4f}, R²={r2:.4f}")

        training_summary.append({
            "horizon": h,
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "n_features": len(feats),
            "fit_duration_seconds": round(duration, 1),
            "test_mae": round(mae, 4),
            "test_rmse": round(rmse, 4),
            "test_r2": round(r2, 4),
        })

    summary_file = RESULTS_DIR / "rf_training_summary.json"
    with open(summary_file, "w") as f:
        json.dump(training_summary, f, indent=2)
    logger.info(f"\nTraining summary saved to {summary_file}")


def main():
    df, horizon_features = load_dataset()
    verify_alignment_pre_training(df, horizon_features)
    train_rf_models(df, horizon_features)


if __name__ == "__main__":
    main()
