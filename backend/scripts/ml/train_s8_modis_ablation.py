"""
S8 MODIS MAIAC AOD Ablation

Evaluates the addition of causal MODIS MAIAC AOD features against the frozen S5/S6 production baseline.
6h  -> S6 + MODIS
24h -> S5 + MODIS
72h -> S6 + MODIS

Features added:
- modis_aod_latest
- modis_aod_age_hours
"""

import os
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import matplotlib.pyplot as plt
import seaborn as sns


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent.parent

S5_DATA_FILE = BASE_DIR / "data/processed/fusion/delhi_forecasting_s5_nwp.csv"
EPISODE_DATA_FILE = BASE_DIR / "data/processed/fusion/delhi_forecasting_episode.csv"
MODIS_DATA_FILE = BASE_DIR / "data/processed/satellite/delhi_mcd19a2_maiac_station_aod.parquet"

HORIZON_METADATA_FILE = BASE_DIR / "models/horizon_features.json"
BEST_PARAMS_FILE = BASE_DIR / "ml/results/satellite/s4_best_params.json"

REPORT_DIR = BASE_DIR / "reports/modis_ablation"
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
BASELINE_METRICS = {
    "6h": {"MAE": 28.50, "RMSE": 53.74},
    "24h": {"MAE": 34.20, "RMSE": 61.08},
    "72h": {"MAE": 41.50, "RMSE": 69.12}
}


def load_data():
    print("Loading datasets...")
    s5_df = pd.read_csv(S5_DATA_FILE, parse_dates=["timestamp"])
    ep_df = pd.read_csv(EPISODE_DATA_FILE, usecols=EPISODE_FEATURES)
    modis_df = pd.read_parquet(MODIS_DATA_FILE)

    if len(s5_df) != len(ep_df):
        raise RuntimeError("Row counts differ.")

    # 1. Base DataFrame construction
    df = pd.concat([s5_df, ep_df], axis=1)
    df = df.rename(columns={"timestamp": "Timestamp"})
    df = df.sort_values("Timestamp").reset_index(drop=True)

    # 2. Extract causal MODIS features using merge_asof
    print("Computing causal MODIS features (Latency=48h, Window=72h)...")

    # Process MODIS
    modis_df['obs_time'] = pd.to_datetime(modis_df['observation_time']).dt.tz_localize(None)
    # Filter only QA accepted
    modis_df = modis_df[modis_df['qa_accepted'] == True].copy()
    modis_df = modis_df.sort_values('obs_time')

    # T_avail is the time 48h ago
    df['T_avail'] = df['Timestamp'] - pd.Timedelta(hours=48)

    # Sort for merge_asof
    df = df.sort_values(['T_avail'])

    # Merge asof backward. This matches the latest obs_time <= T_avail
    merged = pd.merge_asof(
        df[['Timestamp', 'station_id', 'T_avail']],
        modis_df[['obs_time', 'station_id', 'aod_055']],
        left_on='T_avail',
        right_on='obs_time',
        by='station_id',
        direction='backward',
        tolerance=pd.Timedelta(hours=24) # Limits to [T_avail - 24h, T_avail] -> [T - 72h, T - 48h]
    )

    # Sort back to original Timestamp order
    merged = merged.sort_values('Timestamp').reset_index(drop=True)
    df = df.sort_values('Timestamp').reset_index(drop=True)

    # Assign features
    df['modis_aod_latest'] = merged['aod_055']
    df['modis_aod_age_hours'] = (df['Timestamp'] - merged['obs_time']).dt.total_seconds() / 3600.0

    # Dummify station_id after merge
    if "station_id" in df.columns:
        df = pd.get_dummies(df, columns=["station_id"], dtype=int)

    df = df.loc[:, ~df.columns.duplicated()].copy()
    return df


def compute_pollution_metrics(y_true, y_pred, threshold):
    mask = y_true >= threshold
    if not mask.any():
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    true_pos = ((y_pred >= threshold) & mask).sum()
    false_pos = ((y_pred >= threshold) & ~mask).sum()
    false_neg = ((y_pred < threshold) & mask).sum()

    precision = true_pos / (true_pos + false_pos) if (true_pos + false_pos) > 0 else 0.0
    recall = true_pos / (true_pos + false_neg) if (true_pos + false_neg) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {"precision": precision, "recall": recall, "f1": f1}


def evaluate_predictions(y_true, y_pred, timestamps):
    errors = y_pred - y_true

    # Winter metrics (Nov-Feb)
    winter_mask = timestamps.dt.month.isin([11, 12, 1, 2])
    winter_mae = float(mean_absolute_error(y_true[winter_mask], y_pred[winter_mask])) if winter_mask.any() else 0.0
    winter_rmse = float(np.sqrt(mean_squared_error(y_true[winter_mask], y_pred[winter_mask]))) if winter_mask.any() else 0.0

    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "R2": float(r2_score(y_true, y_pred)),
        "bias": float(np.mean(errors)),
        "MedAE": float(np.median(np.abs(errors))),
        "winter_MAE": winter_mae,
        "winter_RMSE": winter_rmse,
        "severe_150": compute_pollution_metrics(y_true, y_pred, 150),
        "severe_250": compute_pollution_metrics(y_true, y_pred, 250)
    }


def main():
    print("=" * 80)
    print("MODIS MAIAC AOD ABLATION EXPERIMENT")
    print("=" * 80)

    with open(HORIZON_METADATA_FILE, "r") as f:
        metadata = json.load(f)

    with open(BEST_PARAMS_FILE, "r") as f:
        best_params = json.load(f)

    df = load_data()
    print(f"Combined rows: {len(df):,}")

    results = []
    feature_importances = {}
    verdicts = {}

    modis_features = ["modis_aod_latest", "modis_aod_age_hours"]

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

        final_features = list(dict.fromkeys(baseline_features + modis_features))

        print(f"Baseline feature count: {len(baseline_features)}")
        print(f"MODIS features added: {len(modis_features)}")
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
        test_timestamps = test["Timestamp"]

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
        metrics = evaluate_predictions(y_test, predictions, test_timestamps)

        # Availability metrics (in the test set)
        modis_coverage = X_test['modis_aod_latest'].notna().mean() * 100
        modis_mean_age = X_test['modis_aod_age_hours'].mean()

        baseline_mae = BASELINE_METRICS[horizon]["MAE"]
        baseline_rmse = BASELINE_METRICS[horizon]["RMSE"]

        mae_imp = ((baseline_mae - metrics['MAE']) / baseline_mae) * 100
        rmse_imp = ((baseline_rmse - metrics['RMSE']) / baseline_rmse) * 100

        verdict = "INSUFFICIENT EVIDENCE"
        if mae_imp > 0 and rmse_imp > 0:
            verdict = "PROMOTE"
        elif mae_imp < 0 and rmse_imp < 0:
            verdict = "REJECT"
        elif rmse_imp > 0:
            verdict = "PROMOTE" # Usually tied to RMSE improvement
        else:
            verdict = "REJECT"

        verdicts[horizon] = verdict

        print(f"\nFINAL TEST METRICS ({horizon})")
        print(f"  Matched Samples : {len(y_test):,}")
        print(f"  MODIS Coverage  : {modis_coverage:.1f}%")
        print(f"  MAE : {metrics['MAE']:.4f} (Baseline: {baseline_mae:.4f} -> {mae_imp:+.2f}%)")
        print(f"  RMSE: {metrics['RMSE']:.4f} (Baseline: {baseline_rmse:.4f} -> {rmse_imp:+.2f}%)")
        print(f"  VERDICT: {verdict}")

        # Feature importance
        fi = pd.DataFrame({
            'Feature': final_features,
            'Importance': model.feature_importances_
        }).sort_values('Importance', ascending=False)

        feature_importances[horizon] = fi

        results.append({
            "Horizon": horizon,
            "Matched Samples": len(y_test),
            "MODIS Coverage (%)": f"{modis_coverage:.1f}%",
            "Baseline MAE": baseline_mae,
            "MODIS MAE": metrics["MAE"],
            "MAE Improvement (%)": f"{mae_imp:+.2f}%",
            "Baseline RMSE": baseline_rmse,
            "MODIS RMSE": metrics["RMSE"],
            "RMSE Improvement (%)": f"{rmse_imp:+.2f}%",
            "Winter MAE": metrics["winter_MAE"],
            "Winter RMSE": metrics["winter_RMSE"],
            "P (>=150)": metrics["severe_150"]["precision"],
            "R (>=150)": metrics["severe_150"]["recall"],
            "F1 (>=150)": metrics["severe_150"]["f1"],
            "P (>=250)": metrics["severe_250"]["precision"],
            "R (>=250)": metrics["severe_250"]["recall"],
            "F1 (>=250)": metrics["severe_250"]["f1"],
            "Verdict": verdict
        })

    # Save outputs
    print("\nSaving reports and figures...")
    results_df = pd.DataFrame(results)
    results_df.to_csv(REPORT_DIR / "modis_ablation_metrics.csv", index=False)

    # Feature importance
    all_fi = []
    for h, fi in feature_importances.items():
        fi_copy = fi.copy()
        fi_copy['Horizon'] = h
        all_fi.append(fi_copy)
    pd.concat(all_fi).to_csv(REPORT_DIR / "modis_feature_importance.csv", index=False)

    # Markdown Report
    with open(REPORT_DIR / "modis_ablation_report.md", "w") as f:
        f.write("# MODIS MAIAC AOD Ablation Experiment\n\n")
        f.write("## Overview\n")
        f.write("Controlled ablation adding causal MODIS MAIAC AOD features (48h latency, 72h window) to VayuNet production baselines.\n\n")
        f.write("## Metrics\n")
        f.write(results_df.to_markdown(index=False))
        f.write("\n\n## Final Verdicts\n")
        for h, v in verdicts.items():
            f.write(f"- **{h}**: {v}\n")

    # Plots
    sns.set_theme(style="whitegrid")

    # 1. Baseline vs MODIS RMSE
    plt.figure(figsize=(10, 6))
    x = np.arange(len(HORIZONS))
    width = 0.35
    baselines = [BASELINE_METRICS[h]["RMSE"] for h in HORIZONS]
    modis_rmse = [r["MODIS RMSE"] for r in results]
    plt.bar(x - width/2, baselines, width, label='Baseline', color='gray')
    plt.bar(x + width/2, modis_rmse, width, label='MODIS', color='blue')
    plt.ylabel('RMSE')
    plt.title('RMSE: Baseline vs MODIS by Horizon')
    plt.xticks(x, list(HORIZONS.keys()), rotation=45)
    plt.legend()
    plt.savefig(REPORT_DIR / "rmse_comparison.png", dpi=300, bbox_inches='tight')
    plt.close()

    # 2. MODIS Feature Importance
    for h in HORIZONS:
        plt.figure(figsize=(10, 8))
        fi = feature_importances[h].head(20)
        sns.barplot(data=fi, x='Importance', y='Feature')
        plt.title(f'Top 20 Features ({h})')
        plt.tight_layout()
        plt.savefig(REPORT_DIR / f"feature_importance_{h}.png", dpi=300, bbox_inches='tight')
        plt.close()

if __name__ == "__main__":
    main()
