"""
Ablation experiment for S6 Episode Dynamics Features vs S5 (S4 + NWP).
Uses GPU (tree_method='hist', device='cuda') on NVIDIA RTX 3050 with exact row-matched control vs treatment.
"""

from pathlib import Path
import json
import numpy as np
import pandas as pd
from xgboost import XGBRegressor

BASE_DIR = Path(__file__).resolve().parent.parent

S5_DATA_FILE = BASE_DIR / "data/processed/fusion/delhi_forecasting_s5_nwp.csv"
EPISODE_DATA_FILE = BASE_DIR / "data/processed/fusion/delhi_forecasting_episode.csv"
HORIZON_METADATA_FILE = BASE_DIR / "models/horizon_features.json"
BEST_PARAMS_FILE = BASE_DIR / "ml/results/satellite/s4_best_params.json"

REPORT_DIR = BASE_DIR / "reports/episode"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

HORIZONS = {"6h": 6, "24h": 24, "72h": 72}

TRAIN_END = pd.Timestamp("2024-10-01 13:00:00")
VALID_END = pd.Timestamp("2025-08-30 15:00:00")
TEST_END = pd.Timestamp("2026-08-31 23:00:00")

SATELLITE_FEATURES = ["satellite_no2_latest", "satellite_no2_age_hours"]
PM10_FEATURES = [
    "PM10_lag_1h", "PM10_lag_3h", "PM10_lag_6h", "PM10_lag_12h",
    "PM10_lag_24h", "PM10_lag_48h", "PM10_lag_72h", "PM10_roll_mean_6h",
    "PM10_roll_mean_24h", "PM10_roll_std_24h",
]
NWP_BASE_VARS = [
    "temperature_2m", "relative_humidity_2m", "precipitation",
    "surface_pressure", "wind_speed_10m", "wind_direction_10m",
    "boundary_layer_height"
]
EPISODE_FEATURES = [
    "pm25_delta_1h", "pm25_delta_3h", "pm25_delta_6h", "pm25_delta_12h", "pm25_delta_24h",
    "pm25_acceleration_1h", "pm25_acceleration_3h", "pm25_acceleration_6h",
    "pm25_mean_6h", "pm25_mean_12h", "pm25_mean_24h",
    "pm25_std_6h", "pm25_std_24h",
    "pm25_max_6h", "pm25_max_24h",
    "hours_since_150_onset", "hours_since_250_onset",
    "hours_above_150_24h", "hours_above_250_24h",
    "fraction_above_150_24h", "fraction_above_250_24h",
]

def main():
    print("=" * 70)
    print("S6 EPISODE DYNAMICS ABLATION EXPERIMENT (GPU ACCELERATED)")
    print("=" * 70)

    print("\nLoading datasets...")
    s5_df = pd.read_csv(S5_DATA_FILE, parse_dates=["timestamp"])
    ep_df = pd.read_csv(EPISODE_DATA_FILE, usecols=EPISODE_FEATURES)

    df = pd.concat([s5_df, ep_df], axis=1)
    df = df.rename(columns={"timestamp": "Timestamp"})
    df = df.sort_values("Timestamp").reset_index(drop=True)

    if "station_id" in df.columns:
        df = pd.get_dummies(df, columns=["station_id"], dtype=int)

    df = df.loc[:, ~df.columns.duplicated()].copy()

    with open(HORIZON_METADATA_FILE, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    with open(BEST_PARAMS_FILE, "r", encoding="utf-8") as f:
        best_params = json.load(f)

    def get_metrics(y_true, y_pred):
        errors = y_pred - y_true
        mae = float(np.mean(np.abs(errors)))
        rmse = float(np.sqrt(np.mean(errors ** 2)))
        ss_res = float(np.sum(errors ** 2))
        ss_tot = float(np.sum((y_true - y_true.mean()) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
        return mae, rmse, r2

    results = []

    for horizon_key, horizon_hrs in HORIZONS.items():
        print("\n" + "=" * 70)
        print(f"ABLATION — {horizon_key}")
        print("=" * 70)

        target = f"target_pm25_{horizon_key}"
        if target not in df.columns:
            target = f"PM2.5_{horizon_key}"

        canonical_features = metadata["horizon_features"][horizon_key]
        s4_features = canonical_features + SATELLITE_FEATURES + PM10_FEATURES
        nwp_features = [f"nwp_{v}_{horizon_hrs}h" for v in NWP_BASE_VARS]
        s5_features = s4_features + nwp_features
        s6_features = s5_features + EPISODE_FEATURES

        # Mask: ensure matched rows (valid target AND available NWP features)
        valid_rows_mask = df[target].notna()
        for feat in nwp_features:
            if feat in df.columns:
                valid_rows_mask &= df[feat].notna()

        df_ablation = df[valid_rows_mask].copy()

        train = df_ablation[df_ablation["Timestamp"] < TRAIN_END]
        valid = df_ablation[(df_ablation["Timestamp"] >= TRAIN_END) & (df_ablation["Timestamp"] < VALID_END)]
        test = df_ablation[(df_ablation["Timestamp"] >= VALID_END) & (df_ablation["Timestamp"] <= TEST_END)]

        print(f"\nRows (Control vs Treatment matched):")
        print(f"  Train: {len(train):,}")
        print(f"  Valid: {len(valid):,}")
        print(f"  Test:  {len(test):,}")

        train_valid = pd.concat([train, valid], axis=0)

        params_entry = best_params[horizon_key]
        params = params_entry.get("params") or params_entry.get("best_params")
        best_iteration = int(params_entry["best_iteration"])

        def train_and_eval(features, name):
            X_tv = train_valid[features]
            y_tv = train_valid[target]
            X_ts = test[features]
            y_ts = test[target].to_numpy()

            model = XGBRegressor(
                n_estimators=best_iteration,
                max_depth=params["max_depth"],
                min_child_weight=params["min_child_weight"],
                learning_rate=params["learning_rate"],
                subsample=params["subsample"],
                colsample_bytree=params["colsample_bytree"],
                tree_method="hist",
                device="cuda",
                random_state=42,
            )
            model.fit(X_tv, y_tv)
            preds = model.predict(X_ts)
            mae, rmse, r2 = get_metrics(y_ts, preds)

            print(f"  [{name}] MAE: {mae:.4f} | RMSE: {rmse:.4f} | R²: {r2:.4f}")
            return mae, rmse, r2

        print("\nTraining Control (S5: S4 + NWP)...")
        mae_c, rmse_c, r2_c = train_and_eval(s5_features, "Control (S5 NWP)")

        print("\nTraining Treatment (S6: S5 + Episode Dynamics)...")
        mae_t, rmse_t, r2_t = train_and_eval(s6_features, "Treatment (S6 Episode)")

        results.append({
            "horizon": horizon_key,
            "test_rows": len(test),
            "s5_mae": mae_c,
            "s5_rmse": rmse_c,
            "s5_r2": r2_c,
            "s6_mae": mae_t,
            "s6_rmse": rmse_t,
            "s6_r2": r2_t,
            "mae_improvement": mae_c - mae_t,
            "rmse_improvement": rmse_c - rmse_t,
        })

    results_df = pd.DataFrame(results)
    summary_path = REPORT_DIR / "s6_episode_ablation_report.json"
    results_df.to_json(summary_path, orient="records", indent=2)

    csv_path = REPORT_DIR / "s6_episode_ablation_report.csv"
    results_df.to_csv(csv_path, index=False)

    print("\n" + "=" * 70)
    print("S6 EPISODE DYNAMICS ABLATION COMPLETE")
    print("=" * 70)
    print(results_df.to_string(index=False))
    print(f"\nSaved summary: {summary_path}")

if __name__ == "__main__":
    main()
