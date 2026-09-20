import sys
from pathlib import Path
import json
import time
import traceback

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent

KAGGLE_DATA_FILE = BASE_DIR / "data" / "kaggle" / "vayunet_forecasting_kaggle.parquet"
HORIZON_METADATA_FILE = BASE_DIR / "models" / "horizon_features.json"
BEST_PARAMS_FILE = BASE_DIR / "ml" / "results" / "satellite" / "s4_best_params.json"
REPORT_DIR = BASE_DIR / "reports" / "reproduction"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

HORIZONS = {"6h": 6}
TARGETS = {"6h": "target_pm25_6h"}
USE_EPISODE = {"6h": True}

TRAIN_END = pd.Timestamp("2024-10-01 13:00:00")
VALID_END = pd.Timestamp("2025-08-30 15:00:00")
TEST_END = pd.Timestamp("2026-08-31 23:00:00")

SATELLITE_FEATURES = ["satellite_no2_latest", "satellite_no2_age_hours"]
PM10_FEATURES = [
    "PM10_lag_1h", "PM10_lag_3h", "PM10_lag_6h", "PM10_lag_12h", "PM10_lag_24h",
    "PM10_lag_48h", "PM10_lag_72h", "PM10_roll_mean_6h", "PM10_roll_mean_24h", "PM10_roll_std_24h"
]
NWP_BASE_VARS = [
    "temperature_2m", "relative_humidity_2m", "precipitation", "surface_pressure",
    "wind_speed_10m", "wind_direction_10m", "boundary_layer_height"
]
EPISODE_FEATURES = [
    "pm25_delta_1h", "pm25_delta_3h", "pm25_delta_6h", "pm25_delta_12h", "pm25_delta_24h",
    "pm25_acceleration_1h", "pm25_acceleration_3h", "pm25_acceleration_6h",
    "pm25_mean_6h", "pm25_mean_12h", "pm25_mean_24h", "pm25_std_6h", "pm25_std_24h",
    "pm25_max_6h", "pm25_max_24h", "hours_since_150_onset", "hours_since_250_onset",
    "hours_above_150_24h", "hours_above_250_24h", "fraction_above_150_24h", "fraction_above_250_24h"
]

CANONICAL_METRICS = {
    "MAE": 34.3264472742,
    "RMSE": 53.7418983638,
    "R2": 0.749532839,
    "bias": 1.5593710677,
    "MedAE": 21.3050231934
}

def evaluate_predictions(y_true, y_pred):
    errors = y_pred - y_true
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "R2": float(r2_score(y_true, y_pred)),
        "bias": float(np.mean(errors)),
        "MedAE": float(np.median(np.abs(errors))),
    }

def load_data():
    df = pd.read_parquet(KAGGLE_DATA_FILE)
    if "timestamp" in df.columns:
        df = df.rename(columns={"timestamp": "Timestamp"})
    df["Timestamp"] = pd.to_datetime(df["Timestamp"])
    df = df.sort_values("Timestamp").reset_index(drop=True)
    if "station_id" in df.columns:
        df = pd.get_dummies(df, columns=["station_id"], dtype=int)
    df = df.loc[:, ~df.columns.duplicated()].copy()
    return df

def build_features(metadata, horizon, use_episode):
    canonical_features = metadata["horizon_features"][horizon]
    horizon_hours = HORIZONS[horizon]
    nwp_features = [f"nwp_{variable}_{horizon_hours}h" for variable in NWP_BASE_VARS]
    s4_features = canonical_features + SATELLITE_FEATURES + PM10_FEATURES
    s5_features = s4_features + nwp_features
    if use_episode:
        final_features = s5_features + EPISODE_FEATURES
    else:
        final_features = s5_features
    final_features = list(dict.fromkeys(final_features))
    return s4_features, s5_features, final_features

def main():
    print("=" * 80)
    print("VAYUNET 6H REPRODUCTION TRAINING")
    print("=" * 80)

    try:
        with open(HORIZON_METADATA_FILE, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        with open(BEST_PARAMS_FILE, "r", encoding="utf-8") as f:
            best_params = json.load(f)

        df = load_data()
        results = []

        horizon = "6h"
        horizon_hours = HORIZONS[horizon]
        target = TARGETS[horizon]
        use_episode = USE_EPISODE[horizon]

        _, _, final_features = build_features(metadata, horizon, use_episode)
        nwp_features = [f"nwp_{variable}_{horizon_hours}h" for variable in NWP_BASE_VARS]

        matched_mask = df[target].notna()
        for feature in nwp_features:
            matched_mask &= df[feature].notna()

        matched_df = df[matched_mask].copy()

        train = matched_df[matched_df["Timestamp"] < TRAIN_END]
        valid = matched_df[(matched_df["Timestamp"] >= TRAIN_END) & (matched_df["Timestamp"] < VALID_END)]
        test = matched_df[(matched_df["Timestamp"] >= VALID_END) & (matched_df["Timestamp"] <= TEST_END)]

        train_valid = pd.concat([train, valid], axis=0)
        X_train = train_valid[final_features]
        y_train = train_valid[target]
        X_test = test[final_features]
        y_test = test[target].to_numpy()

        params_entry = best_params[horizon]
        params = params_entry["params"]
        best_iteration = int(params_entry["best_iteration"])

        model = xgb.XGBRegressor(
            **params,
            n_estimators=best_iteration,
            objective="reg:squarederror",
            random_state=42,
            tree_method="hist",
            device="cuda",
        )

        start_time = time.time()
        model.fit(X_train, y_train, verbose=False)
        training_seconds = time.time() - start_time

        predictions = model.predict(X_test)
        metrics = evaluate_predictions(y_test, predictions)

        metrics_diff = {}
        for k, v in metrics.items():
            diff = abs(v - CANONICAL_METRICS[k])
            metrics_diff[k] = diff

        max_diff = max(metrics_diff.values())
        if max_diff < 1e-4:
            verdict = "PASS"
        elif max_diff < 0.5:
            verdict = "PASS WITH NUMERICAL DIFFERENCES"
        else:
            verdict = "FAIL"

        results.append({
            "horizon": horizon,
            "model_family": "s6",
            "episode_enabled": use_episode,
            "feature_count": len(final_features),
            "train_rows": len(train),
            "valid_rows": len(valid),
            "test_rows": len(test),
            "best_iteration": best_iteration,
            "training_seconds": training_seconds,
            "MAE": metrics["MAE"],
            "RMSE": metrics["RMSE"],
            "R2": metrics["R2"],
            "bias": metrics["bias"],
            "MedAE": metrics["MedAE"],
        })

        results_df = pd.DataFrame(results)
        csv_path = REPORT_DIR / "local_6h_reproduction.csv"
        results_df.to_csv(csv_path, index=False)

        md_path = REPORT_DIR / "local_6h_reproduction.md"
        with open(md_path, "w") as f:
            f.write("# 6h Reproduction Metrics\n\n")
            f.write(f"**Verdict**: {verdict}\n\n")
            f.write("| Metric | Local Value | Canonical Value | Diff |\n")
            f.write("|---|---|---|---|\n")
            for k in metrics.keys():
                f.write(f"| {k} | {metrics[k]:.6f} | {CANONICAL_METRICS[k]:.6f} | {metrics_diff[k]:.6f} |\n")
            f.write("\n")
            f.write("### Data Rows\n")
            f.write(f"- **Train**: {len(train)}\n")
            f.write(f"- **Valid**: {len(valid)}\n")
            f.write(f"- **Test**: {len(test)}\n")

        print("Training successful!")
        print(f"Verdict: {verdict}")
        print(f"Max Diff: {max_diff:.6f}")
        print(f"Reports saved to {REPORT_DIR}")

    except Exception as e:
        print(f"Failed to reproduce 6h model: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
