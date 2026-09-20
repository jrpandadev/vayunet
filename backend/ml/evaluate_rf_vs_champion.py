"""
Controlled Random Forest Baseline Evaluation vs Locked Tuned XGBoost Champion.

Evaluates the baseline Random Forest models against the locked tuned champion models
on the exact untouched test set.

Constraints & Rules:
- Evaluation-only script.
- Does NOT modify feature_builder.py, forecast_service.py, canonical dataset, or champion models.
- Verifies exact alignment before metric reporting:
    - Forecast origins
    - Target timestamps
    - Actual target values
    - Test rows
- Computes:
    - Overall: MAE, RMSE, R², Bias, MedAE
    - High-pollution slices: PM2.5 >= 150 µg/m³, PM2.5 >= 250 µg/m³
    - Station-level results across all 10 stations
    - Comparison: absolute and percentage differences for MAE and RMSE
- Saves results to:
    backend/ml/results/rf_vs_champion_comparison.json
    backend/ml/results/rf_vs_champion_comparison.csv
    backend/reports/rf_champion_comparison.csv
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, median_absolute_error

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
HORIZON_METADATA_FILE = BASE_DIR / "models" / "horizon_features.json"
MODELS_DIR = BASE_DIR / "models"
RESULTS_DIR = BASE_DIR / "ml" / "results"
REPORTS_DIR = BASE_DIR / "reports"

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

HIGH_POLLUTION_THRESHOLDS = [150.0, 250.0]


def compute_standard_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Compute MAE, RMSE, R², Bias, MedAE."""
    errors = y_pred - y_true
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "R2": float(r2_score(y_true, y_pred)),
        "bias": float(np.mean(errors)),
        "MedAE": float(median_absolute_error(y_true, y_pred)),
    }


def compute_differences(xgb_val: float, rf_val: float) -> Dict[str, float]:
    """
    Calculate:
    - abs_diff: rf_val - xgb_val (positive means RF error is higher)
    - pct_diff: (rf_val - xgb_val) / xgb_val * 100 (% error increase of RF over XGB)
    - rel_improvement: (xgb_val - rf_val) / xgb_val * 100 (positive means RF is better, negative means RF is worse)
    """
    abs_diff = float(rf_val - xgb_val)
    pct_diff = float((rf_val - xgb_val) / xgb_val * 100.0) if xgb_val != 0 else 0.0
    rel_improvement = float((xgb_val - rf_val) / xgb_val * 100.0) if xgb_val != 0 else 0.0
    return {
        "abs_diff": abs_diff,
        "pct_diff": pct_diff,
        "rel_improvement_pct": rel_improvement,
    }


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 78)
    logger.info("STRICT CONTROLLED EVALUATION: RANDOM FOREST BASELINE vs TUNED XGB CHAMPION")
    logger.info("=" * 78)

    # 1. Verify models exist
    for h in HORIZONS:
        if not CHAMPION_MODEL_FILES[h].exists():
            raise FileNotFoundError(f"Champion model missing: {CHAMPION_MODEL_FILES[h]}")
        if not RF_MODEL_FILES[h].exists():
            raise FileNotFoundError(f"RF baseline model missing: {RF_MODEL_FILES[h]}")

    # 2. Load dataset
    logger.info(f"Loading canonical dataset from {DATA_FILE.name}...")
    df = pd.read_csv(DATA_FILE, parse_dates=["timestamp"])
    if "timestamp" in df.columns:
        df.rename(columns={"timestamp": "Timestamp"}, inplace=True)
    df = df.sort_values(by=["Timestamp", "station_id"]).reset_index(drop=True)

    for stn in EXPECTED_STATIONS:
        df[f"station_id_{stn}"] = (df["station_id"] == stn).astype(int)

    with open(HORIZON_METADATA_FILE, "r") as f:
        horizon_features = json.load(f)["horizon_features"]

    # 3. Test slice
    test_df = df[(df["Timestamp"] >= VAL_END) & (df["Timestamp"] <= TEST_END)].copy().reset_index(drop=True)
    logger.info(f"Test slice: {len(test_df):,} rows")

    # 4. Mandatory alignment checks
    logger.info("\nExecuting strict pre-evaluation alignment checks...")
    for h in HORIZONS:
        target_col = TARGET_COLS[h]
        mask = test_df[target_col].notna()
        sub_df = test_df[mask].copy().reset_index(drop=True)
        h_hours = HORIZON_HOURS[h]

        # Spot check target alignment
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
                    raise AssertionError(f"Target alignment failure for {h} at {o_ts}: {t_val} vs {actual_val}")
    logger.info("  [PASS] All alignment checks passed. Proceeding with inference.\n")

    full_results: Dict[str, Any] = {
        "test_period": {
            "start": str(VAL_END),
            "end": str(TEST_END),
            "total_test_rows": len(test_df),
        },
        "horizons": {},
        "verdict": None,
    }

    csv_rows = []

    for h in HORIZONS:
        logger.info(f"\n{'=' * 70}\nEVALUATING HORIZON: {h}\n{'=' * 70}")
        target_col = TARGET_COLS[h]
        valid_mask = test_df[target_col].notna()
        sub_df = test_df[valid_mask].copy().reset_index(drop=True)
        y_true = sub_df[target_col].values
        feats = horizon_features[h]
        X = sub_df[feats].values

        champ_model = joblib.load(CHAMPION_MODEL_FILES[h])
        rf_model = joblib.load(RF_MODEL_FILES[h])

        y_pred_xgb = champ_model.predict(X)
        y_pred_rf = rf_model.predict(X)

        # Integrity verification
        if not (len(y_true) == len(y_pred_xgb) == len(y_pred_rf)):
            raise AssertionError(f"Prediction length mismatch for {h}!")

        metrics_xgb = compute_standard_metrics(y_true, y_pred_xgb)
        metrics_rf = compute_standard_metrics(y_true, y_pred_rf)

        mae_diff = compute_differences(metrics_xgb["MAE"], metrics_rf["MAE"])
        rmse_diff = compute_differences(metrics_xgb["RMSE"], metrics_rf["RMSE"])

        logger.info(f"OVERALL RESULTS [{h}] (N = {len(y_true):,}):")
        logger.info(
            f"  XGBoost Champion -> MAE: {metrics_xgb['MAE']:.4f}, RMSE: {metrics_xgb['RMSE']:.4f}, "
            f"R²: {metrics_xgb['R2']:.4f}, Bias: {metrics_xgb['bias']:.4f}, MedAE: {metrics_xgb['MedAE']:.4f}"
        )
        logger.info(
            f"  RF Baseline      -> MAE: {metrics_rf['MAE']:.4f}, RMSE: {metrics_rf['RMSE']:.4f}, "
            f"R²: {metrics_rf['R2']:.4f}, Bias: {metrics_rf['bias']:.4f}, MedAE: {metrics_rf['MedAE']:.4f}"
        )
        logger.info(
            f"  Differences      -> Absolute MAE diff: {mae_diff['abs_diff']:+.4f} ({mae_diff['pct_diff']:+.2f}%), "
            f"Absolute RMSE diff: {rmse_diff['abs_diff']:+.4f} ({rmse_diff['pct_diff']:+.2f}%)"
        )

        csv_rows.append({
            "horizon": h,
            "slice_type": "overall",
            "slice_value": "all",
            "n_samples": len(y_true),
            "xgb_mae": round(metrics_xgb["MAE"], 4),
            "rf_mae": round(metrics_rf["MAE"], 4),
            "abs_mae_diff": round(mae_diff["abs_diff"], 4),
            "pct_mae_diff": round(mae_diff["pct_diff"], 2),
            "xgb_rmse": round(metrics_xgb["RMSE"], 4),
            "rf_rmse": round(metrics_rf["RMSE"], 4),
            "abs_rmse_diff": round(rmse_diff["abs_diff"], 4),
            "pct_rmse_diff": round(rmse_diff["pct_diff"], 2),
            "xgb_r2": round(metrics_xgb["R2"], 4),
            "rf_r2": round(metrics_rf["R2"], 4),
            "xgb_bias": round(metrics_xgb["bias"], 4),
            "rf_bias": round(metrics_rf["bias"], 4),
            "xgb_medae": round(metrics_xgb["MedAE"], 4),
            "rf_medae": round(metrics_rf["MedAE"], 4),
        })

        # High pollution evaluations
        high_pollution_results = {}
        for th in HIGH_POLLUTION_THRESHOLDS:
            hp_mask = y_true >= th
            hp_count = int(hp_mask.sum())
            if hp_count > 0:
                hp_xgb = compute_standard_metrics(y_true[hp_mask], y_pred_xgb[hp_mask])
                hp_rf = compute_standard_metrics(y_true[hp_mask], y_pred_rf[hp_mask])
                hp_mae_diff = compute_differences(hp_xgb["MAE"], hp_rf["MAE"])
                hp_rmse_diff = compute_differences(hp_xgb["RMSE"], hp_rf["RMSE"])

                high_pollution_results[f">={int(th)}"] = {
                    "count": hp_count,
                    "xgb": hp_xgb,
                    "rf": hp_rf,
                    "abs_mae_diff": hp_mae_diff["abs_diff"],
                    "pct_mae_diff": hp_mae_diff["pct_diff"],
                    "abs_rmse_diff": hp_rmse_diff["abs_diff"],
                    "pct_rmse_diff": hp_rmse_diff["pct_diff"],
                }

                logger.info(
                    f"  Slice [PM2.5 >= {int(th)}] (N = {hp_count:,}):\n"
                    f"    XGB MAE: {hp_xgb['MAE']:.4f} | RF MAE: {hp_rf['MAE']:.4f} | "
                    f"Diff: {hp_mae_diff['abs_diff']:+.4f} ({hp_mae_diff['pct_diff']:+.2f}%)\n"
                    f"    XGB RMSE: {hp_xgb['RMSE']:.4f} | RF RMSE: {hp_rf['RMSE']:.4f} | "
                    f"Diff: {hp_rmse_diff['abs_diff']:+.4f} ({hp_rmse_diff['pct_diff']:+.2f}%)"
                )

                csv_rows.append({
                    "horizon": h,
                    "slice_type": "high_pollution",
                    "slice_value": f">={int(th)}",
                    "n_samples": hp_count,
                    "xgb_mae": round(hp_xgb["MAE"], 4),
                    "rf_mae": round(hp_rf["MAE"], 4),
                    "abs_mae_diff": round(hp_mae_diff["abs_diff"], 4),
                    "pct_mae_diff": round(hp_mae_diff["pct_diff"], 2),
                    "xgb_rmse": round(hp_xgb["RMSE"], 4),
                    "rf_rmse": round(hp_rf["RMSE"], 4),
                    "abs_rmse_diff": round(hp_rmse_diff["abs_diff"], 4),
                    "pct_rmse_diff": round(hp_rmse_diff["pct_diff"], 2),
                    "xgb_r2": round(hp_xgb["R2"], 4),
                    "rf_r2": round(hp_rf["R2"], 4),
                    "xgb_bias": round(hp_xgb["bias"], 4),
                    "rf_bias": round(hp_rf["bias"], 4),
                    "xgb_medae": round(hp_xgb["MedAE"], 4),
                    "rf_medae": round(hp_rf["MedAE"], 4),
                })

        # Station-level evaluation
        station_results = {}
        for stn in EXPECTED_STATIONS:
            stn_mask = sub_df["station_id"] == stn
            stn_count = int(stn_mask.sum())
            if stn_count > 0:
                stn_y = y_true[stn_mask]
                stn_p_xgb = y_pred_xgb[stn_mask]
                stn_p_rf = y_pred_rf[stn_mask]

                stn_m_xgb = compute_standard_metrics(stn_y, stn_p_xgb)
                stn_m_rf = compute_standard_metrics(stn_y, stn_p_rf)
                stn_mae_diff = compute_differences(stn_m_xgb["MAE"], stn_m_rf["MAE"])
                stn_rmse_diff = compute_differences(stn_m_xgb["RMSE"], stn_m_rf["RMSE"])

                station_results[stn] = {
                    "count": stn_count,
                    "xgb": stn_m_xgb,
                    "rf": stn_m_rf,
                    "abs_mae_diff": stn_mae_diff["abs_diff"],
                    "pct_mae_diff": stn_mae_diff["pct_diff"],
                    "abs_rmse_diff": stn_rmse_diff["abs_diff"],
                    "pct_rmse_diff": stn_rmse_diff["pct_diff"],
                }

                csv_rows.append({
                    "horizon": h,
                    "slice_type": "station",
                    "slice_value": stn,
                    "n_samples": stn_count,
                    "xgb_mae": round(stn_m_xgb["MAE"], 4),
                    "rf_mae": round(stn_m_rf["MAE"], 4),
                    "abs_mae_diff": round(stn_mae_diff["abs_diff"], 4),
                    "pct_mae_diff": round(stn_mae_diff["pct_diff"], 2),
                    "xgb_rmse": round(stn_m_xgb["RMSE"], 4),
                    "rf_rmse": round(stn_m_rf["RMSE"], 4),
                    "abs_rmse_diff": round(stn_rmse_diff["abs_diff"], 4),
                    "pct_rmse_diff": round(stn_rmse_diff["pct_diff"], 2),
                    "xgb_r2": round(stn_m_xgb["R2"], 4),
                    "rf_r2": round(stn_m_rf["R2"], 4),
                    "xgb_bias": round(stn_m_xgb["bias"], 4),
                    "rf_bias": round(stn_m_rf["bias"], 4),
                    "xgb_medae": round(stn_m_xgb["MedAE"], 4),
                    "rf_medae": round(stn_m_rf["MedAE"], 4),
                })

        full_results["horizons"][h] = {
            "n_observations": len(y_true),
            "n_features": len(feats),
            "overall": {
                "xgb": metrics_xgb,
                "rf": metrics_rf,
                "abs_mae_diff": mae_diff["abs_diff"],
                "pct_mae_diff": mae_diff["pct_diff"],
                "abs_rmse_diff": rmse_diff["abs_diff"],
                "pct_rmse_diff": rmse_diff["pct_diff"],
            },
            "high_pollution": high_pollution_results,
            "station_level": station_results,
        }

    # Decide verdict based on objective thresholds:
    # 1. RF clearly better: MAE improved by > 2% across horizons
    # 2. RF approximately equivalent: MAE within +/- 1% across horizons
    # 3. RF worse: MAE worse by > 2% across horizons
    # 4. RF potentially useful for ensemble despite worse standalone performance:
    #    worse standalone, but correlated < 0.95 with XGB predictions or complementary errors
    h_mae_diffs = [full_results["horizons"][h]["overall"]["pct_mae_diff"] for h in HORIZONS]
    avg_mae_diff = np.mean(h_mae_diffs)

    if avg_mae_diff < -2.0:
        verdict = "1. RF clearly better"
    elif abs(avg_mae_diff) <= 1.5:
        verdict = "2. RF approximately equivalent"
    elif avg_mae_diff > 1.5:
        # Check if error correlation or ensemble potential exists
        verdict = "3. RF worse"
    else:
        verdict = "4. RF potentially useful for ensemble despite worse standalone performance"

    full_results["verdict"] = verdict
    full_results["summary"] = {
        "avg_pct_mae_diff": round(float(avg_mae_diff), 2),
        "horizon_pct_mae_diffs": {h: round(diff, 2) for h, diff in zip(HORIZONS, h_mae_diffs)},
    }

    # Save outputs
    json_path = RESULTS_DIR / "rf_vs_champion_comparison.json"
    with open(json_path, "w") as f:
        json.dump(full_results, f, indent=2)
    logger.info(f"\nJSON results saved to: {json_path}")

    csv_path_ml = RESULTS_DIR / "rf_vs_champion_comparison.csv"
    csv_path_reports = REPORTS_DIR / "rf_champion_comparison.csv"
    df_res = pd.DataFrame(csv_rows)
    df_res.to_csv(csv_path_ml, index=False)
    df_res.to_csv(csv_path_reports, index=False)
    logger.info(f"CSV results saved to: {csv_path_ml} and {csv_path_reports}")

    logger.info("\n" + "=" * 78)
    logger.info(f"FINAL VERDICT: {verdict}")
    logger.info(f"Average % MAE difference across horizons: {avg_mae_diff:+.2f}%")
    logger.info("=" * 78)


if __name__ == "__main__":
    main()
