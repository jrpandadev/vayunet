from pathlib import Path
import json
import joblib
import numpy as np
import pandas as pd

from xgboost import XGBRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    median_absolute_error,
)


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

DATA_PATH = (
    ROOT
    / "backend/data/processed/fusion/delhi_forecasting_satellite.csv"
)

FEATURE_META_PATH = (
    ROOT
    / "backend/models/horizon_features.json"
)

RESULT_DIR = ROOT / "backend/ml/results/satellite"
REPORT_DIR = ROOT / "backend/reports/satellite"
MODEL_DIR = ROOT / "backend/models"

RESULT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# SPLIT BOUNDARIES
# ============================================================

TRAIN_END = pd.Timestamp("2025-03-15 12:00:00")
VALID_END = pd.Timestamp("2025-11-21 22:00:00")


# ============================================================
# HORIZONS
# ============================================================

HORIZONS = {
    6: "target_pm25_6h",
    24: "target_pm25_24h",
    72: "target_pm25_72h",
}


# ============================================================
# SATELLITE FEATURES
# ============================================================

SATELLITE_FEATURES = [
    "satellite_no2_latest",
    "satellite_no2_age_hours",
]


# ============================================================
# FROZEN CHAMPION MODELS
# ============================================================

S0_MODELS = {
    6: MODEL_DIR / "xgb_weather_pm25_6h_tuned.joblib",
    24: MODEL_DIR / "xgb_weather_pm25_24h_tuned.joblib",
    72: MODEL_DIR / "xgb_weather_pm25_72h_tuned.joblib",
}


# ============================================================
# LOAD CANONICAL FEATURE METADATA
# ============================================================

with open(FEATURE_META_PATH, "r", encoding="utf-8") as f:
    feature_meta = json.load(f)

HORIZON_FEATURES = feature_meta["horizon_features"]


# ============================================================
# LOAD DATA
# ============================================================

print("=" * 72)
print("S3 SATELLITE FORECASTING EXPERIMENT")
print("=" * 72)

print("\nDataset:")
print(DATA_PATH)

df = pd.read_csv(DATA_PATH)

df["timestamp"] = pd.to_datetime(df["timestamp"])

print(f"Rows: {len(df):,}")
print(f"Columns: {len(df.columns)}")


# ============================================================
# DATA INTEGRITY
# ============================================================

duplicate_count = df.duplicated(
    subset=["station_id", "timestamp"]
).sum()

if duplicate_count != 0:
    raise RuntimeError(
        f"Duplicate station/timestamp rows detected: "
        f"{duplicate_count}"
    )

for feature in SATELLITE_FEATURES:
    if feature not in df.columns:
        raise RuntimeError(
            f"Missing satellite feature: {feature}"
        )


# ============================================================
# SPLITS
# ============================================================

train_mask = df["timestamp"] < TRAIN_END

valid_mask = (
    (df["timestamp"] >= TRAIN_END)
    & (df["timestamp"] < VALID_END)
)

test_mask = df["timestamp"] >= VALID_END


print("\nSplit sizes:")
print(f"Train:      {train_mask.sum():,}")
print(f"Validation: {valid_mask.sum():,}")
print(f"Test:       {test_mask.sum():,}")


# ============================================================
# XGBOOST PARAMETERS
# ============================================================

# Controlled training configuration.
#
# IMPORTANT:
# The S0 models remain frozen.
# These parameters are used only for the new S3 models.

XGB_PARAMS = {
    "n_estimators": 200,
    "max_depth": 5,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "objective": "reg:squarederror",
    "random_state": 42,
    "n_jobs": -1,
}


# ============================================================
# METRICS
# ============================================================

def calculate_metrics(y_true, predictions):

    return {
        "MAE": float(
            mean_absolute_error(y_true, predictions)
        ),

        "RMSE": float(
            np.sqrt(
                mean_squared_error(
                    y_true,
                    predictions,
                )
            )
        ),

        "R2": float(
            r2_score(
                y_true,
                predictions,
            )
        ),

        "Bias": float(
            np.mean(
                predictions - y_true
            )
        ),

        "MedAE": float(
            median_absolute_error(
                y_true,
                predictions,
            )
        ),
    }


# ============================================================
# RESULTS
# ============================================================

summary_results = []


# ============================================================
# HORIZON LOOP
# ============================================================

for horizon, target_col in HORIZONS.items():

    print("\n" + "=" * 72)
    print(f"HORIZON: {horizon} HOURS")
    print("=" * 72)

    canonical_features = list(
        HORIZON_FEATURES.get(f"{horizon}h", HORIZON_FEATURES.get(str(horizon)))
    )

    expected_count = {
        6: 47,
        24: 44,
        72: 42,
    }[horizon]

    if len(canonical_features) != expected_count:
        raise RuntimeError(
            f"Unexpected canonical feature count for "
            f"{horizon}h: {len(canonical_features)} "
            f"(expected {expected_count})"
        )

    # --------------------------------------------------------
    # VERIFY CANONICAL FEATURES
    # --------------------------------------------------------

    missing_canonical = [
        feature
        for feature in canonical_features
        if feature not in df.columns
    ]

    if missing_canonical:
        raise RuntimeError(
            f"Missing canonical features for {horizon}h: "
            f"{missing_canonical}"
        )

    # --------------------------------------------------------
    # S3 FEATURE SET
    # --------------------------------------------------------

    s3_features = (
        canonical_features
        + SATELLITE_FEATURES
    )

    print(f"Canonical S0 features: {len(canonical_features)}")
    print(f"Satellite additions:   {len(SATELLITE_FEATURES)}")
    print(f"S3 total features:     {len(s3_features)}")

    # --------------------------------------------------------
    # TARGET VALIDITY
    # --------------------------------------------------------

    target_valid = df[target_col].notna()

    train_idx = train_mask & target_valid
    valid_idx = valid_mask & target_valid
    test_idx = test_mask & target_valid

    y_train = df.loc[
        train_idx,
        target_col
    ]

    y_valid = df.loc[
        valid_idx,
        target_col
    ]

    y_test = df.loc[
        test_idx,
        target_col
    ]

    print(f"\nTarget-valid rows:")
    print(f"  Train:      {len(y_train):,}")
    print(f"  Validation: {len(y_valid):,}")
    print(f"  Test:       {len(y_test):,}")

    # ========================================================
    # S0 — FROZEN CHAMPION
    # ========================================================

    s0_model_path = S0_MODELS[horizon]

    if not s0_model_path.exists():
        raise FileNotFoundError(
            f"Frozen S0 model not found:\n{s0_model_path}"
        )

    print("\nLoading frozen S0 champion:")
    print(s0_model_path)

    s0_model = joblib.load(
        s0_model_path
    )

    s0_feature_count = getattr(
        s0_model,
        "n_features_in_",
        None,
    )

    if s0_feature_count != len(
        canonical_features
    ):
        raise RuntimeError(
            f"S0 model feature mismatch for "
            f"{horizon}h: model expects "
            f"{s0_feature_count}, canonical metadata has "
            f"{len(canonical_features)}"
        )

    X_test_s0 = df.loc[
        test_idx,
        canonical_features
    ]

    pred_s0 = s0_model.predict(
        X_test_s0
    )

    s0_metrics = calculate_metrics(
        y_test,
        pred_s0,
    )

    # ========================================================
    # S3 — SATELLITE MODEL
    # ========================================================

    print("\nTraining S3 model...")

    X_train_s3 = df.loc[
        train_idx,
        s3_features
    ]

    X_valid_s3 = df.loc[
        valid_idx,
        s3_features
    ]

    X_test_s3 = df.loc[
        test_idx,
        s3_features
    ]

    s3_model = XGBRegressor(
        **XGB_PARAMS
    )

    s3_model.fit(
        X_train_s3,
        y_train,
        eval_set=[
            (
                X_valid_s3,
                y_valid,
            )
        ],
        verbose=False,
    )

    pred_s3 = s3_model.predict(
        X_test_s3
    )

    s3_metrics = calculate_metrics(
        y_test,
        pred_s3,
    )

    # ========================================================
    # COMPARISON
    # ========================================================

    mae_improvement = (
        (
            s0_metrics["MAE"]
            - s3_metrics["MAE"]
        )
        / s0_metrics["MAE"]
        * 100
    )

    rmse_improvement = (
        (
            s0_metrics["RMSE"]
            - s3_metrics["RMSE"]
        )
        / s0_metrics["RMSE"]
        * 100
    )

    r2_change = (
        s3_metrics["R2"]
        - s0_metrics["R2"]
    )

    print("\nS0 — Frozen Champion")

    for name, value in s0_metrics.items():
        print(f"  {name}: {value:.4f}")

    print("\nS3 — Satellite")

    for name, value in s3_metrics.items():
        print(f"  {name}: {value:.4f}")

    print("\nS3 vs S0")

    print(
        f"  MAE improvement:  "
        f"{mae_improvement:+.2f}%"
    )

    print(
        f"  RMSE improvement: "
        f"{rmse_improvement:+.2f}%"
    )

    print(
        f"  R² change: "
        f"{r2_change:+.4f}"
    )

    # ========================================================
    # SATELLITE COVERAGE ON TEST
    # ========================================================

    satellite_available_test = (
        df.loc[
            test_idx,
            "satellite_no2_latest"
        ]
        .notna()
    )

    availability_pct = (
        satellite_available_test.mean()
        * 100
    )

    print(
        f"\nSatellite available in test: "
        f"{availability_pct:.2f}%"
    )

    # ========================================================
    # SAVE MODEL
    # ========================================================

    model_path = (
        MODEL_DIR
        / f"xgb_satellite_pm25_{horizon}h.joblib"
    )

    joblib.dump(
        s3_model,
        model_path,
    )

    print(
        f"\nSaved S3 model:\n{model_path}"
    )

    # ========================================================
    # SAVE PREDICTIONS
    # ========================================================

    prediction_df = df.loc[
        test_idx,
        [
            "station_id",
            "timestamp",
            target_col,
            "satellite_no2_latest",
            "satellite_no2_age_hours",
        ]
    ].copy()

    prediction_df["prediction_s0"] = pred_s0
    prediction_df["prediction_s3"] = pred_s3

    prediction_path = (
        REPORT_DIR
        / f"s3_predictions_{horizon}h.csv"
    )

    prediction_df.to_csv(
        prediction_path,
        index=False,
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    summary_results.append({

        "horizon": horizon,

        "s0_feature_count":
            len(canonical_features),

        "s3_feature_count":
            len(s3_features),

        "test_rows":
            len(y_test),

        "test_satellite_available_pct":
            availability_pct,

        "s0_mae":
            s0_metrics["MAE"],

        "s3_mae":
            s3_metrics["MAE"],

        "mae_improvement_pct":
            mae_improvement,

        "s0_rmse":
            s0_metrics["RMSE"],

        "s3_rmse":
            s3_metrics["RMSE"],

        "rmse_improvement_pct":
            rmse_improvement,

        "s0_r2":
            s0_metrics["R2"],

        "s3_r2":
            s3_metrics["R2"],

        "r2_change":
            r2_change,

        "s0_bias":
            s0_metrics["Bias"],

        "s3_bias":
            s3_metrics["Bias"],

        "s0_medae":
            s0_metrics["MedAE"],

        "s3_medae":
            s3_metrics["MedAE"],
    })


# ============================================================
# SAVE FINAL SUMMARY
# ============================================================

summary_df = pd.DataFrame(
    summary_results
)

summary_csv = (
    REPORT_DIR
    / "s3_vs_s0_summary.csv"
)

summary_json = (
    RESULT_DIR
    / "s3_vs_s0_summary.json"
)

summary_df.to_csv(
    summary_csv,
    index=False,
)

with open(
    summary_json,
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        summary_results,
        f,
        indent=2,
    )


# ============================================================
# FINAL OUTPUT
# ============================================================

print("\n" + "=" * 72)
print("S3 EXPERIMENT COMPLETE")
print("=" * 72)

print("\nFinal comparison:")
print(
    summary_df.to_string(
        index=False
    )
)

print(f"\nSummary CSV:")
print(summary_csv)

print(f"\nSummary JSON:")
print(summary_json)

print("\nNo test-set tuning was performed.")
print("S0 remained frozen.")
