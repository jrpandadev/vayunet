from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    median_absolute_error,
)

from physics_features import (
    add_physics_features,
    get_physics_feature_names,
)


# ============================================================
# Paths
# ============================================================

BACKEND_DIR = Path(__file__).resolve().parents[1]

DATA_PATH = (
    BACKEND_DIR
    / "data"
    / "processed"
    / "delhi_forecasting_weather.csv"
)

MODEL_DIR = BACKEND_DIR / "models"
REPORT_DIR = BACKEND_DIR / "reports"

MODEL_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# Configuration
# ============================================================

HORIZONS = [6, 24, 72]

TARGET_COLUMNS = {
    6: "target_pm25_6h",
    24: "target_pm25_24h",
    72: "target_pm25_72h",
}

# Same strict chronological split used in the final evaluation.
TRAIN_END = pd.Timestamp("2024-10-01 13:00:00")
VALID_END = pd.Timestamp("2025-08-30 15:00:00")
TEST_END = pd.Timestamp("2026-08-31 23:00:00")


# ============================================================
# Locked baseline features
# ============================================================

BASELINE_FEATURES = [
    "PM2.5",
    "PM2.5_lag_1h",
    "PM2.5_lag_3h",
    "PM2.5_lag_6h",
    "PM2.5_lag_12h",
    "PM2.5_lag_24h",
    "PM2.5_lag_48h",
    "PM2.5_lag_72h",
    "PM2.5_roll_mean_6h",
    "PM2.5_roll_mean_24h",
    "PM2.5_roll_std_24h",
    "hour",
    "day_of_week",
    "day_of_year",
    "month",
    "is_weekend",
    "WD_sin",
    "WD_cos",
    "PM10",
    "NO",
    "NO2",
    "NOx",
    "NH3",
    "SO2",
    "CO",
    "Ozone",
    "AT",
    "RH",
    "WS",
    "WD",
    "SR",
    "BP",
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
]


# ============================================================
# Physics features
# ============================================================

PHYSICS_FEATURES = get_physics_feature_names()

FEATURES = BASELINE_FEATURES + PHYSICS_FEATURES


# ============================================================
# Metrics
# ============================================================

def calculate_metrics(
    y_true: pd.Series,
    y_pred: np.ndarray,
) -> dict:

    error = y_pred - y_true.to_numpy()

    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(
            np.sqrt(mean_squared_error(y_true, y_pred))
        ),
        "R2": float(r2_score(y_true, y_pred)),
        "Bias": float(np.mean(error)),
        "MedAE": float(
            median_absolute_error(y_true, y_pred)
        ),
    }


# ============================================================
# Regime metrics
# ============================================================

def calculate_regime_metrics(
    y_true: pd.Series,
    y_pred: np.ndarray,
) -> dict:

    y = y_true.to_numpy()
    p = np.asarray(y_pred)

    regimes = {
        "below_60": y < 60,
        "60_to_150": (y >= 60) & (y < 150),
        "150_to_250": (y >= 150) & (y < 250),
        "above_250": y >= 250,
    }

    output = {}

    for name, mask in regimes.items():

        count = int(mask.sum())

        if count == 0:
            output[name] = {
                "count": 0,
                "MAE": None,
                "RMSE": None,
                "Bias": None,
            }
            continue

        errors = p[mask] - y[mask]

        output[name] = {
            "count": count,
            "MAE": float(
                np.mean(np.abs(errors))
            ),
            "RMSE": float(
                np.sqrt(np.mean(errors ** 2))
            ),
            "Bias": float(
                np.mean(errors)
            ),
        }

    return output


# ============================================================
# Train one horizon
# ============================================================

def train_horizon(
    df: pd.DataFrame,
    horizon: int,
):

    target = TARGET_COLUMNS[horizon]

    print()
    print("=" * 80)
    print(f"PHYSICS XGBOOST - {horizon}H FORECAST")
    print("=" * 80)

    # --------------------------------------------------------
    # Check columns
    # --------------------------------------------------------

    missing_features = [
        col
        for col in FEATURES
        if col not in df.columns
    ]

    if missing_features:
        raise ValueError(
            f"Missing feature columns: {missing_features}"
        )

    if target not in df.columns:
        raise ValueError(
            f"Missing target column: {target}"
        )

    # --------------------------------------------------------
    # Remove rows without target
    # --------------------------------------------------------

    data = df[
        df[target].notna()
    ].copy()

    # --------------------------------------------------------
    # Temporal split
    # --------------------------------------------------------

    train = data[
        data["timestamp"] < TRAIN_END
    ]

    valid = data[
        (data["timestamp"] >= TRAIN_END)
        & (data["timestamp"] < VALID_END)
    ]

    test = data[
        (data["timestamp"] >= VALID_END)
        & (data["timestamp"] <= TEST_END)
    ]

    print("\nSplit:")
    print(
        f"Train: {len(train):,} "
        f"{train['timestamp'].min()} -> "
        f"{train['timestamp'].max()}"
    )

    print(
        f"Valid: {len(valid):,} "
        f"{valid['timestamp'].min()} -> "
        f"{valid['timestamp'].max()}"
    )

    print(
        f"Test : {len(test):,} "
        f"{test['timestamp'].min()} -> "
        f"{test['timestamp'].max()}"
    )

    # --------------------------------------------------------
    # Features / target
    # --------------------------------------------------------

    X_train = train[FEATURES]
    y_train = train[target]

    X_valid = valid[FEATURES]
    y_valid = valid[target]

    X_test = test[FEATURES]
    y_test = test[target]

    # --------------------------------------------------------
    # XGBoost
    #
    # These are deliberately conservative first-pass
    # parameters. This is an experiment, not a tuned champion.
    # --------------------------------------------------------

    model = xgb.XGBRegressor(
        n_estimators=1000,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="reg:squarederror",
        eval_metric="mae",
        tree_method="hist",
        random_state=42,
        n_jobs=-1,
    )

    print("\nTraining...")

    model.fit(
        X_train,
        y_train,
        eval_set=[
            (X_valid, y_valid),
        ],
        verbose=100,
    )

    # --------------------------------------------------------
    # Predictions
    # --------------------------------------------------------

    valid_pred = model.predict(X_valid)
    test_pred = model.predict(X_test)

    # --------------------------------------------------------
    # Metrics
    # --------------------------------------------------------

    valid_metrics = calculate_metrics(
        y_valid,
        valid_pred,
    )

    test_metrics = calculate_metrics(
        y_test,
        test_pred,
    )

    valid_regimes = calculate_regime_metrics(
        y_valid,
        valid_pred,
    )

    test_regimes = calculate_regime_metrics(
        y_test,
        test_pred,
    )

    # --------------------------------------------------------
    # Print
    # --------------------------------------------------------

    print("\nValidation:")
    for key, value in valid_metrics.items():
        print(f"  {key:<8}: {value:.4f}")

    print("\nUntouched Test:")
    for key, value in test_metrics.items():
        print(f"  {key:<8}: {value:.4f}")

    print("\nTest pollution regimes:")

    for regime, values in test_regimes.items():

        print(
            f"  {regime:<12} "
            f"N={values['count']:>7,} "
            f"MAE={values['MAE']:.2f} "
            f"RMSE={values['RMSE']:.2f} "
            f"Bias={values['Bias']:.2f}"
        )

    # --------------------------------------------------------
    # Save model
    # --------------------------------------------------------

    model_path = (
        MODEL_DIR
        / f"xgb_pm25_{horizon}h_physics_experimental.joblib"
    )

    joblib.dump(
        model,
        model_path,
    )

    # --------------------------------------------------------
    # Save report
    # --------------------------------------------------------

    report = {
        "experiment": "physics_informed_xgboost",
        "horizon_hours": horizon,
        "target": target,
        "features": FEATURES,
        "baseline_feature_count": len(BASELINE_FEATURES),
        "physics_feature_count": len(PHYSICS_FEATURES),
        "split": {
            "train_end": str(TRAIN_END),
            "validation_end": str(VALID_END),
            "test_end": str(TEST_END),
        },
        "validation_metrics": valid_metrics,
        "test_metrics": test_metrics,
        "validation_regimes": valid_regimes,
        "test_regimes": test_regimes,
        "model_path": str(model_path),
    }

    report_path = (
        REPORT_DIR
        / f"physics_xgb_{horizon}h_report.json"
    )

    with open(
        report_path,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            report,
            f,
            indent=2,
        )

    print(f"\nModel saved:")
    print(f"  {model_path}")

    print(f"\nReport saved:")
    print(f"  {report_path}")

    return {
        "horizon": horizon,
        "validation": valid_metrics,
        "test": test_metrics,
        "test_regimes": test_regimes,
    }


# ============================================================
# Main
# ============================================================

def main():

    print("=" * 80)
    print("VayuNet - Physics-Informed XGBoost Experiment")
    print("=" * 80)

    print(f"\nLoading dataset:")
    print(DATA_PATH)

    df = pd.read_csv(
        DATA_PATH,
        parse_dates=["timestamp"],
    )

    print(
        f"Loaded {len(df):,} rows "
        f"x {len(df.columns)} columns"
    )

    # --------------------------------------------------------
    # Create physics features
    # --------------------------------------------------------

    print("\nGenerating physics features...")

    df = add_physics_features(
        df,
        copy=False,
    )

    print(
        f"Physics feature generation complete."
    )

    print(
        f"Total features: {len(FEATURES)} "
        f"({len(BASELINE_FEATURES)} baseline + "
        f"{len(PHYSICS_FEATURES)} physics)"
    )

    # --------------------------------------------------------
    # Train all horizons
    # --------------------------------------------------------

    results = []

    for horizon in HORIZONS:

        result = train_horizon(
            df,
            horizon,
        )

        results.append(result)

    # --------------------------------------------------------
    # Final summary
    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("PHYSICS XGBOOST SUMMARY")
    print("=" * 80)

    print(
        f"{'Horizon':<10}"
        f"{'Val MAE':>12}"
        f"{'Test MAE':>12}"
        f"{'Test RMSE':>12}"
        f"{'Test R2':>12}"
        f"{'Test Bias':>12}"
    )

    print("-" * 80)

    for result in results:

        horizon = result["horizon"]
        validation = result["validation"]
        test = result["test"]

        print(
            f"{horizon}h"
            f"{validation['MAE']:>12.2f}"
            f"{test['MAE']:>12.2f}"
            f"{test['RMSE']:>12.2f}"
            f"{test['R2']:>12.4f}"
            f"{test['Bias']:>12.2f}"
        )

    print()
    print("Experiment complete.")
    print(
        "Existing champion models were NOT overwritten."
    )


if __name__ == "__main__":
    main()
