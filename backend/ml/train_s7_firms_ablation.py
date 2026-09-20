"""
S7 FIRMS Biomass-Burning Ablation

Evaluates the addition of causal S7 FIRMS active fire features against the frozen S5/S6 production baseline.
6h  -> S6 + S7
24h -> S5 + S7
72h -> S6 + S7
"""

from pathlib import Path
import json
import time

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

S5_DATA_FILE = BASE_DIR / "data/processed/fusion/delhi_forecasting_s5_nwp.csv"
EPISODE_DATA_FILE = BASE_DIR / "data/processed/fusion/delhi_forecasting_episode.csv"
S7_DATA_FILE = BASE_DIR / "data/processed/fusion/delhi_forecasting_s7_firms.csv"

HORIZON_METADATA_FILE = BASE_DIR / "models/horizon_features.json"
BEST_PARAMS_FILE = BASE_DIR / "ml/results/satellite/s4_best_params.json"

REPORT_DIR = BASE_DIR / "reports/experiments"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# HORIZONS & SPLITS
# ============================================================

HORIZONS = {"6h": 6, "24h": 24, "72h": 72}
TARGETS = {"6h": "target_pm25_6h", "24h": "target_pm25_24h", "72h": "target_pm25_72h"}

TRAIN_END = pd.Timestamp("2024-10-01 13:00:00")
VALID_END = pd.Timestamp("2025-08-30 15:00:00")
TEST_END = pd.Timestamp("2026-08-31 23:00:00")

SATELLITE_FEATURES = ["satellite_no2_latest", "satellite_no2_age_hours"]
PM10_FEATURES = [
    "PM10_lag_1h", "PM10_lag_3h", "PM10_lag_6h", "PM10_lag_12h",
    "PM10_lag_24h", "PM10_lag_48h", "PM10_lag_72h",
    "PM10_roll_mean_6h", "PM10_roll_mean_24h", "PM10_roll_std_24h"
]
NWP_BASE_VARS = [
    "temperature_2m", "relative_humidity_2m", "precipitation",
    "surface_pressure", "wind_speed_10m", "wind_direction_10m", "boundary_layer_height"
]
EPISODE_FEATURES = [
    "pm25_delta_1h", "pm25_delta_3h", "pm25_delta_6h", "pm25_delta_12h", "pm25_delta_24h",
    "pm25_acceleration_1h", "pm25_acceleration_3h", "pm25_acceleration_6h",
    "pm25_mean_6h", "pm25_mean_12h", "pm25_mean_24h", "pm25_std_6h", "pm25_std_24h",
    "pm25_max_6h", "pm25_max_24h", "hours_since_150_onset", "hours_since_250_onset",
    "hours_above_150_24h", "hours_above_250_24h", "fraction_above_150_24h", "fraction_above_250_24h"
]

USE_EPISODE = {"6h": True, "24h": False, "72h": True}

# FROZEN BASELINE METRICS (S5/S6)
BASELINE_RMSE = {"6h": 53.74, "24h": 61.08, "72h": 69.12}

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
    s5_df = pd.read_csv(S5_DATA_FILE, parse_dates=["timestamp"])
    ep_df = pd.read_csv(EPISODE_DATA_FILE, usecols=EPISODE_FEATURES)
    s7_df = pd.read_csv(S7_DATA_FILE)

    if len(s5_df) != len(ep_df) or len(s5_df) != len(s7_df):
        raise RuntimeError("Row counts differ.")

    # Drop timestamp from s7 so we can concat cleanly
    s7_df = s7_df.drop(columns=["timestamp"])

    df = pd.concat([s5_df, ep_df, s7_df], axis=1)
    df = df.rename(columns={"timestamp": "Timestamp"})
    df = df.sort_values("Timestamp").reset_index(drop=True)

    if "station_id" in df.columns:
        df = pd.get_dummies(df, columns=["station_id"], dtype=int)

    df = df.loc[:, ~df.columns.duplicated()].copy()
    return df, list(s7_df.columns)


def main():
    print("=" * 80)
    print("S7 FIRMS ABLATION EXPERIMENT")
    print("=" * 80)

    with open(HORIZON_METADATA_FILE, "r") as f:
        metadata = json.load(f)

    with open(BEST_PARAMS_FILE, "r") as f:
        best_params = json.load(f)

    df, all_s7_features = load_data()
    print(f"Combined rows: {len(df):,}")
    print(f"Total S7 features available: {len(all_s7_features)}")

    results = []

    for horizon, horizon_hours in HORIZONS.items():
        print("\n" + "=" * 80)
        print(f"EVALUATING HORIZON — {horizon}")
        print("=" * 80)

        target = TARGETS[horizon]
        use_episode = USE_EPISODE[horizon]

        canonical_features = metadata["horizon_features"][horizon]
        nwp_features = [f"nwp_{variable}_{horizon_hours}h" for variable in NWP_BASE_VARS]

        baseline_features = canonical_features + SATELLITE_FEATURES + PM10_FEATURES + nwp_features
        if use_episode:
            baseline_features += EPISODE_FEATURES

        # Select S7 features: general + those specific to this horizon
        s7_features_for_horizon = [
            c for c in all_s7_features
            if not c.endswith("_horizon") or c.endswith(f"_{horizon}_horizon")
        ]

        final_features = list(dict.fromkeys(baseline_features + s7_features_for_horizon))

        print(f"Baseline feature count: {len(baseline_features)}")
        print(f"S7 features added: {len(s7_features_for_horizon)}")
        print(f"Total features: {len(final_features)}")

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
        print(f"GPU Training completed in {training_seconds:.1f}s")

        predictions = model.predict(X_test)
        metrics = evaluate_predictions(y_test, predictions)

        baseline_rmse = BASELINE_RMSE[horizon]
        s7_rmse = metrics["RMSE"]
        improvement = baseline_rmse - s7_rmse
        pct_imp = (improvement / baseline_rmse) * 100

        print(f"\nFINAL TEST METRICS ({horizon})")
        print(f"  MAE : {metrics['MAE']:.6f}")
        print(f"  RMSE: {s7_rmse:.6f}  (Baseline: {baseline_rmse:.2f})")
        print(f"  IMP : {improvement:+.4f} ({pct_imp:+.2f}%)")

        results.append({
            "horizon": horizon,
            "baseline_rmse": baseline_rmse,
            "s7_rmse": s7_rmse,
            "pct_improvement": pct_imp
        })

    print("\n" + "=" * 80)
    print("S7 FIRMS EXPERIMENT SUMMARY")
    print("=" * 80)
    for r in results:
        print(f"{r['horizon']:<5} | Base RMSE: {r['baseline_rmse']:>6.2f} | S7 RMSE: {r['s7_rmse']:>8.4f} | Imp: {r['pct_improvement']:>+6.2f}%")

if __name__ == "__main__":
    main()
