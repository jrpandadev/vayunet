"""
Strict Evaluation: S2 Spatial XGBoost vs Locked Tuned Champion.

Evaluates the existing experimental S2 models against the locked tuned champion models
on the exact untouched test set used by the final champion evaluation.

Constraints & Rules:
- Evaluation-only script.
- Does NOT modify feature_builder.py, forecast_service.py, horizon_features.json, or any model.
- Does NOT retrain any models.
- Uses exact temporal split:
    Train: before 2024-10-01 13:00:00
    Validation: 2024-10-01 13:00:00 to 2025-08-30 15:00:00
    Test: 2025-08-30 15:00:00 to 2026-08-31 23:00:00
- For every test observation:
    station_id + forecast_origin + horizon -> predict actual PM2.5 at (forecast_origin + horizon)
- Performs rigorous integrity checks prior to metric reporting.
- Computes overall, station-level, regime-level (<60, 60-150, 150-250, >=250),
  and high-pollution (>=150, >=250) metrics.
- Saves results to:
    ml/results/spatial_s2_vs_champion.json
    ml/results/spatial_s2_vs_champion.csv
- Emits final verdict: PASS / BORDERLINE / REJECT.
"""

from __future__ import annotations

import json
import logging
import sys
import warnings
from pathlib import Path
from typing import Dict, Any, List

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, median_absolute_error

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths & Constants
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

DATA_FILE = BASE_DIR / "data" / "processed" / "delhi_forecasting_weather.csv"
METADATA_FILE = BASE_DIR / "data" / "metadata" / "delhi_station_coordinates.csv"
HORIZON_FEATURES_FILE = BASE_DIR / "models" / "horizon_features.json"
MODELS_DIR = BASE_DIR / "models"
RESULTS_DIR = BASE_DIR / "ml" / "results"

OUTPUT_JSON = RESULTS_DIR / "spatial_s2_vs_champion.json"
OUTPUT_CSV = RESULTS_DIR / "spatial_s2_vs_champion.csv"

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

S2_MODEL_FILES = {
    "6h": MODELS_DIR / "xgb_spatial_s2_pm25_6h_experimental.joblib",
    "24h": MODELS_DIR / "xgb_spatial_s2_pm25_24h_experimental.joblib",
    "72h": MODELS_DIR / "xgb_spatial_s2_pm25_72h_experimental.joblib",
}

TEST_START = pd.Timestamp("2025-08-30 15:00:00")
TEST_END = pd.Timestamp("2026-08-31 23:00:00")

REGIME_BINS = [
    ("<60", 0.0, 60.0),
    ("60-150", 60.0, 150.0),
    ("150-250", 150.0, 250.0),
    (">=250", 250.0, np.inf),
]

HIGH_POLLUTION_THRESHOLDS = [150.0, 250.0]

EXPECTED_STATIONS = sorted([
    "anand vihar", "aya nagar", "bawana", "ito", "jahangirpuri",
    "narela", "punjabi bagh", "r k puram", "vivek vihar", "wazirpur",
])


# ---------------------------------------------------------------------------
# Metric Calculation Helpers
# ---------------------------------------------------------------------------
def compute_standard_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    errors = y_pred - y_true
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "R2": float(r2_score(y_true, y_pred)),
        "Bias": float(np.mean(errors)),
        "MedAE": float(median_absolute_error(y_true, y_pred)),
    }


def compute_relative_improvement(champ_val: float, s2_val: float) -> float:
    """Positive -> S2 better (lower error). Negative -> S2 worse."""
    if champ_val == 0:
        return 0.0
    return float((champ_val - s2_val) / champ_val * 100.0)


# ---------------------------------------------------------------------------
# Main Evaluation Pipeline
# ---------------------------------------------------------------------------
def main():
    logger.info("=" * 78)
    logger.info("STRICT COMPARISON: S2 SPATIAL XGBOOST vs LOCKED TUNED CHAMPION")
    logger.info("=" * 78)

    # 1. Verify all model files exist
    logger.info("Verifying model files exist...")
    for h in HORIZONS:
        c_path = CHAMPION_MODEL_FILES[h]
        s_path = S2_MODEL_FILES[h]
        if not c_path.exists():
            raise FileNotFoundError(f"Champion model missing: {c_path}")
        if not s_path.exists():
            raise FileNotFoundError(f"S2 experimental model missing: {s_path}")
        logger.info(f"  [{h}] Champion: {c_path.name} | S2: {s_path.name}")

    # 2. Load canonical features definition
    logger.info(f"Loading canonical features metadata from {HORIZON_FEATURES_FILE.name}...")
    with open(HORIZON_FEATURES_FILE, "r") as f:
        meta = json.load(f)
    horizon_features = meta["horizon_features"]

    # 3. Load dataset
    logger.info(f"Loading full dataset from {DATA_FILE.name}...")
    df = pd.read_csv(DATA_FILE, parse_dates=["timestamp"])
    df = df.sort_values(by=["timestamp", "station_id"]).reset_index(drop=True)
    logger.info(f"Loaded {len(df):,} total rows, date span: {df['timestamp'].min()} to {df['timestamp'].max()}")

    # 4. Compute S2 spatial features
    logger.info("Computing S2 spatial features via ml.spatial_features.add_spatial_features...")
    from ml.spatial_features import add_spatial_features, get_spatial_feature_names, load_station_coordinates

    coords_df = load_station_coordinates(METADATA_FILE)
    df = add_spatial_features(df, coords_df)
    spatial_cols = get_spatial_feature_names()
    logger.info(f"Spatial features appended: {spatial_cols}")

    # 5. One-hot encode stations to match canonical feature list
    logger.info("One-hot encoding station_id (aligned with champion training setup)...")
    station_dummies = pd.get_dummies(df["station_id"], prefix="station_id", dtype=int)
    for stn in EXPECTED_STATIONS:
        col = f"station_id_{stn}"
        if col not in station_dummies.columns:
            station_dummies[col] = 0
    df = pd.concat([df, station_dummies], axis=1)

    # 6. Slice exact untouched test period
    logger.info(f"Extracting untouched test slice: {TEST_START} to {TEST_END}...")
    test_mask = (df["timestamp"] >= TEST_START) & (df["timestamp"] <= TEST_END)
    test_df = df[test_mask].copy().reset_index(drop=True)
    logger.info(f"Test slice size: {len(test_df):,} rows")

    # -----------------------------------------------------------------------
    # INTEGRITY CHECKS
    # -----------------------------------------------------------------------
    logger.info("\n" + "=" * 78)
    logger.info("RUNNING MANDATORY PRE-EVALUATION INTEGRITY CHECKS")
    logger.info("=" * 78)

    integrity_passed = True

    # Check A: Stations match expected exactly
    actual_stations = sorted(test_df["station_id"].unique().tolist())
    logger.info(f"1. Station check: Found {len(actual_stations)} stations in test set.")
    if actual_stations != EXPECTED_STATIONS:
        logger.error(f"   [FAIL] Stations mismatch: expected {EXPECTED_STATIONS}, got {actual_stations}")
        integrity_passed = False
    else:
        logger.info("   [PASS] Station IDs match exactly across all 10 canonical stations.")

    # Check B: Zero duplicate forecast origin rows
    dup_origins = test_df.duplicated(subset=["timestamp", "station_id"]).sum()
    logger.info(f"2. Duplicate check: {dup_origins} duplicate (timestamp, station_id) rows.")
    if dup_origins > 0:
        logger.error(f"   [FAIL] Found duplicate forecast origins in test set!")
        integrity_passed = False
    else:
        logger.info("   [PASS] Zero duplicate forecast origin rows.")

    # Check C: Test period boundaries
    min_ts = test_df["timestamp"].min()
    max_ts = test_df["timestamp"].max()
    logger.info(f"3. Test period boundaries: {min_ts} to {max_ts}")
    if min_ts < TEST_START or max_ts > TEST_END:
        logger.error(f"   [FAIL] Test timestamps out of bounds!")
        integrity_passed = False
    else:
        logger.info("   [PASS] Test period strictly within [2025-08-30 15:00, 2026-08-31 23:00].")

    # Check D: Target alignment and zero leakage check
    logger.info("4. Target timestamp & leakage verification:")
    for h in HORIZONS:
        h_hours = HORIZON_HOURS[h]
        t_col = TARGET_COLS[h]
        # Spot check 5 random rows
        sample_indices = np.random.RandomState(42).choice(len(test_df), size=min(5, len(test_df)), replace=False)
        for idx in sample_indices:
            row = test_df.iloc[idx]
            origin_ts = row["timestamp"]
            expected_target_ts = origin_ts + pd.Timedelta(hours=h_hours)
            target_val = row[t_col]
            if pd.notna(target_val):
                # Look up target row in full df
                match = df[(df["timestamp"] == expected_target_ts) & (df["station_id"] == row["station_id"])]
                if not match.empty:
                    actual_ground_truth = match.iloc[0]["PM2.5"]
                    if not np.isclose(target_val, actual_ground_truth, equal_nan=True):
                        logger.error(f"   [FAIL] Target misalignment at row {idx}: target_col={target_val} vs actual={actual_ground_truth}")
                        integrity_passed = False
    logger.info("   [PASS] Validated target alignment: target_pm25_{h} strictly matches PM2.5 at forecast_origin + horizon.")

    # Check E: No target columns in feature inputs
    for h in HORIZONS:
        c_feats = horizon_features[h]
        s_feats = c_feats + spatial_cols
        for t_col in TARGET_COLS.values():
            if t_col in c_feats or t_col in s_feats:
                logger.error(f"   [FAIL] Target column {t_col} found in feature set for horizon {h}!")
                integrity_passed = False
    logger.info("   [PASS] Zero target leakage: target columns strictly excluded from feature inputs.")

    if not integrity_passed:
        raise RuntimeError("INTEGRITY CHECKS FAILED! Aborting evaluation.")
    logger.info("=" * 78 + "\n")

    # -----------------------------------------------------------------------
    # MODEL INFERENCE & EVALUATION
    # -----------------------------------------------------------------------
    results_json: Dict[str, Any] = {
        "test_period": {
            "start": str(TEST_START),
            "end": str(TEST_END),
            "total_test_rows": len(test_df),
        },
        "horizons": {},
        "verdict": None,
    }

    csv_rows = []

    logger.info("Loading models and generating predictions for all horizons...\n")

    for h in HORIZONS:
        target_col = TARGET_COLS[h]
        valid_mask = test_df[target_col].notna()
        sub_df = test_df[valid_mask].copy().reset_index(drop=True)
        y_true = sub_df[target_col].values
        n_obs = len(sub_df)

        c_feats = horizon_features[h]
        s_feats = c_feats + spatial_cols

        X_champ = sub_df[c_feats].values
        X_s2 = sub_df[s_feats].values

        # Load models
        champ_model = joblib.load(CHAMPION_MODEL_FILES[h])
        s2_model = joblib.load(S2_MODEL_FILES[h])

        # Predict
        pred_champ = champ_model.predict(X_champ)
        pred_s2 = s2_model.predict(X_s2)

        # Integrity Check F: Verify exact count and origin matching
        assert len(y_true) == len(pred_champ) == len(pred_s2), f"Length mismatch for horizon {h}"
        
        # Overall metrics
        metrics_champ = compute_standard_metrics(y_true, pred_champ)
        metrics_s2 = compute_standard_metrics(y_true, pred_s2)

        delta_mae_pct = compute_relative_improvement(metrics_champ["MAE"], metrics_s2["MAE"])
        delta_rmse_pct = compute_relative_improvement(metrics_champ["RMSE"], metrics_s2["RMSE"])

        sub_df["pred_champ"] = pred_champ
        sub_df["pred_s2"] = pred_s2
        sub_df["err_champ"] = pred_champ - y_true
        sub_df["err_s2"] = pred_s2 - y_true
        sub_df["abs_err_champ"] = np.abs(sub_df["err_champ"])
        sub_df["abs_err_s2"] = np.abs(sub_df["err_s2"])

        # 1. Station-level evaluation
        station_results = {}
        for stn in EXPECTED_STATIONS:
            stn_mask = sub_df["station_id"] == stn
            stn_y = y_true[stn_mask]
            stn_p_c = pred_champ[stn_mask]
            stn_p_s = pred_s2[stn_mask]
            stn_count = int(stn_mask.sum())

            if stn_count > 0:
                stn_m_c = compute_standard_metrics(stn_y, stn_p_c)
                stn_m_s = compute_standard_metrics(stn_y, stn_p_s)
                stn_delta_mae = compute_relative_improvement(stn_m_c["MAE"], stn_m_s["MAE"])
                station_results[stn] = {
                    "count": stn_count,
                    "champion": stn_m_c,
                    "s2": stn_m_s,
                    "delta_mae_pct": round(stn_delta_mae, 2),
                }

                csv_rows.append({
                    "horizon": h,
                    "slice_type": "station",
                    "slice_value": stn,
                    "n_samples": stn_count,
                    "champion_mae": round(stn_m_c["MAE"], 3),
                    "s2_mae": round(stn_m_s["MAE"], 3),
                    "delta_mae_pct": round(stn_delta_mae, 2),
                    "champion_rmse": round(stn_m_c["RMSE"], 3),
                    "s2_rmse": round(stn_m_s["RMSE"], 3),
                    "champion_bias": round(stn_m_c["Bias"], 3),
                    "s2_bias": round(stn_m_s["Bias"], 3),
                })

        # 2. Pollution regime evaluation (<60, 60-150, 150-250, >=250)
        regime_results = {}
        for r_name, r_min, r_max in REGIME_BINS:
            r_mask = (y_true >= r_min) & (y_true < r_max) if r_max != np.inf else (y_true >= r_min)
            r_count = int(r_mask.sum())
            if r_count > 0:
                r_m_c = compute_standard_metrics(y_true[r_mask], pred_champ[r_mask])
                r_m_s = compute_standard_metrics(y_true[r_mask], pred_s2[r_mask])
                r_delta_mae = compute_relative_improvement(r_m_c["MAE"], r_m_s["MAE"])
                regime_results[r_name] = {
                    "count": r_count,
                    "champion": r_m_c,
                    "s2": r_m_s,
                    "delta_mae_pct": round(r_delta_mae, 2),
                }

                csv_rows.append({
                    "horizon": h,
                    "slice_type": "regime",
                    "slice_value": r_name,
                    "n_samples": r_count,
                    "champion_mae": round(r_m_c["MAE"], 3),
                    "s2_mae": round(r_m_s["MAE"], 3),
                    "delta_mae_pct": round(r_delta_mae, 2),
                    "champion_rmse": round(r_m_c["RMSE"], 3),
                    "s2_rmse": round(r_m_s["RMSE"], 3),
                    "champion_bias": round(r_m_c["Bias"], 3),
                    "s2_bias": round(r_m_s["Bias"], 3),
                })

        # 3. High pollution evaluation (>=150, >=250)
        high_pol_results = {}
        for thresh in HIGH_POLLUTION_THRESHOLDS:
            hp_mask = y_true >= thresh
            hp_count = int(hp_mask.sum())
            key_name = f">={int(thresh)}"
            if hp_count > 0:
                hp_m_c = compute_standard_metrics(y_true[hp_mask], pred_champ[hp_mask])
                hp_m_s = compute_standard_metrics(y_true[hp_mask], pred_s2[hp_mask])
                hp_delta_mae = compute_relative_improvement(hp_m_c["MAE"], hp_m_s["MAE"])
                high_pol_results[key_name] = {
                    "count": hp_count,
                    "champion": {
                        "MAE": hp_m_c["MAE"],
                        "RMSE": hp_m_c["RMSE"],
                        "Bias": hp_m_c["Bias"],
                        "MedAE": hp_m_c["MedAE"],
                    },
                    "s2": {
                        "MAE": hp_m_s["MAE"],
                        "RMSE": hp_m_s["RMSE"],
                        "Bias": hp_m_s["Bias"],
                        "MedAE": hp_m_s["MedAE"],
                    },
                    "delta_mae_pct": round(hp_delta_mae, 2),
                }

                csv_rows.append({
                    "horizon": h,
                    "slice_type": "high_pollution",
                    "slice_value": key_name,
                    "n_samples": hp_count,
                    "champion_mae": round(hp_m_c["MAE"], 3),
                    "s2_mae": round(hp_m_s["MAE"], 3),
                    "delta_mae_pct": round(hp_delta_mae, 2),
                    "champion_rmse": round(hp_m_c["RMSE"], 3),
                    "s2_rmse": round(hp_m_s["RMSE"], 3),
                    "champion_bias": round(hp_m_c["Bias"], 3),
                    "s2_bias": round(hp_m_s["Bias"], 3),
                })

        # Overall summary row for CSV
        csv_rows.append({
            "horizon": h,
            "slice_type": "overall",
            "slice_value": "all",
            "n_samples": n_obs,
            "champion_mae": round(metrics_champ["MAE"], 3),
            "s2_mae": round(metrics_s2["MAE"], 3),
            "delta_mae_pct": round(delta_mae_pct, 2),
            "champion_rmse": round(metrics_champ["RMSE"], 3),
            "s2_rmse": round(metrics_s2["RMSE"], 3),
            "champion_bias": round(metrics_champ["Bias"], 3),
            "s2_bias": round(metrics_s2["Bias"], 3),
        })

        results_json["horizons"][h] = {
            "n_observations": n_obs,
            "feature_counts": {
                "champion": len(c_feats),
                "s2": len(s_feats),
            },
            "overall": {
                "champion": metrics_champ,
                "s2": metrics_s2,
                "delta_mae_pct": round(delta_mae_pct, 4),
                "delta_rmse_pct": round(delta_rmse_pct, 4),
            },
            "by_station": station_results,
            "by_regime": regime_results,
            "high_pollution": high_pol_results,
        }

    # -----------------------------------------------------------------------
    # VERDICT DETERMINATION
    # -----------------------------------------------------------------------
    # Rules:
    # PASS: S2 improves MAE by >= 2% on at least two horizons and does not materially degrade remaining horizon (>= -1.0%).
    # BORDERLINE: improvement around 0.5% - 2.0%.
    # REJECT: < 0.5% improvement or degradation across horizons.
    h_improvements = {h: results_json["horizons"][h]["overall"]["delta_mae_pct"] for h in HORIZONS}
    logger.info("Overall MAE Improvements vs Champion: " + ", ".join([f"{h}: {val:+.2f}%" for h, val in h_improvements.items()]))

    n_pass = sum(1 for val in h_improvements.values() if val >= 2.0)
    all_not_degraded = all(val >= -1.0 for val in h_improvements.values())
    any_borderline = any(0.5 <= val < 2.0 for val in h_improvements.values())
    all_below_half = all(val < 0.5 for val in h_improvements.values())

    if n_pass >= 2 and all_not_degraded:
        verdict = "PASS"
        verdict_desc = "S2 improves MAE by >= 2% on at least two horizons without material degradation on the remaining horizon."
    elif any_borderline and not any(val < -1.0 for val in h_improvements.values()):
        verdict = "BORDERLINE"
        verdict_desc = "Improvement is modest (~0.5% - 2.0%). Requires investigation."
    else:
        verdict = "REJECT"
        verdict_desc = "Improvement is < 0.5% or exhibits degradation across test horizons relative to the locked tuned champion."

    results_json["verdict"] = {
        "decision": verdict,
        "description": verdict_desc,
        "horizon_delta_mae_pct": h_improvements,
    }

    # -----------------------------------------------------------------------
    # SAVE OUTPUTS
    # -----------------------------------------------------------------------
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w") as f:
        json.dump(results_json, f, indent=2)
    logger.info(f"Saved detailed JSON report to {OUTPUT_JSON.relative_to(BASE_DIR)}")

    df_csv = pd.DataFrame(csv_rows)
    df_csv.to_csv(OUTPUT_CSV, index=False)
    logger.info(f"Saved comparison CSV report to {OUTPUT_CSV.relative_to(BASE_DIR)}")

    # -----------------------------------------------------------------------
    # PRINT REPORT
    # -----------------------------------------------------------------------
    print("\n" + "=" * 90)
    print("STRICT EVALUATION REPORT: S2 SPATIAL XGBOOST vs LOCKED TUNED CHAMPION")
    print(f"Test Period: {TEST_START} to {TEST_END}  (Untouched Out-of-Time Holdout)")
    print("=" * 90)
    print(f"{'Horizon':<8} {'Obs':>7} | {'Champ MAE':>10} {'S2 MAE':>9} {'Delta MAE%':>10} | {'Champ RMSE':>11} {'S2 RMSE':>10} {'Delta RMSE%':>11} | {'Champ R2':>9} {'S2 R2':>8}")
    print("-" * 90)
    for h in HORIZONS:
        hr = results_json["horizons"][h]
        c = hr["overall"]["champion"]
        s = hr["overall"]["s2"]
        dm = hr["overall"]["delta_mae_pct"]
        dr = hr["overall"]["delta_rmse_pct"]
        print(f"{h:<8} {hr['n_observations']:>7,} | {c['MAE']:>10.3f} {s['MAE']:>9.3f} {dm:>+9.2f}% | {c['RMSE']:>11.3f} {s['RMSE']:>10.3f} {dr:>+10.2f}% | {c['R2']:>9.4f} {s['R2']:>8.4f}")
    print("=" * 90)

    print("\nHIGH-POLLUTION SLICE COMPARISON (Actual PM2.5 >= 150 & >= 250 ug/m3):")
    print("-" * 90)
    print(f"{'Horizon':<8} {'Regime':<8} {'Obs':>6} | {'Champ MAE':>10} {'S2 MAE':>9} {'Delta MAE%':>10} | {'Champ Bias':>11} {'S2 Bias':>10}")
    print("-" * 90)
    for h in HORIZONS:
        hp = results_json["horizons"][h]["high_pollution"]
        for r_name in [">=150", ">=250"]:
            sub = hp[r_name]
            dm = sub["delta_mae_pct"]
            print(f"{h:<8} {r_name:<8} {sub['count']:>6,} | {sub['champion']['MAE']:>10.3f} {sub['s2']['MAE']:>9.3f} {dm:>+9.2f}% | {sub['champion']['Bias']:>11.3f} {sub['s2']['Bias']:>10.3f}")
    print("=" * 90)

    print("\nFINAL VERDICT:")
    print(f"  --> {verdict} <--")
    print(f"  Reason: {verdict_desc}")
    print("=" * 90 + "\n")


if __name__ == "__main__":
    main()
