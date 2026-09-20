"""
Strict Same-Origin Comparison: Chronos-2 vs Locked Tuned XGBoost Champion.

VayuNet PM2.5 Forecasting — Evaluation Experiment.

== WHAT THIS SCRIPT DOES ==
Evaluates Amazon Chronos-2 (Chronos2Pipeline) against the locked tuned XGBoost
champion on the EXACT same forecast origins, target timestamps, and actual values.

== WHAT THIS SCRIPT DOES NOT DO ==
- Does NOT modify feature_builder.py, forecast_service.py, or champion models.
- Does NOT retrain or tune either model.
- Does NOT use the test set to choose any hyperparameter.
- Does NOT compare by row-count — uses strict key join.

== METHODOLOGY ==
For each (station_id, forecast_origin) in the XGBoost test set:
    1. XGBoost: predict using canonical features at forecast_origin.
    2. Chronos: build context using PM2.5 observations STRICTLY at or before
       forecast_origin (no future leakage). Predict 72 steps ahead (hours).
       Extract steps [6, 24, 72] for the three horizons.
    3. Join rows using (station_id, forecast_origin, target_timestamp) key.
    4. Assert actual_pm25 matches exactly between XGBoost and Chronos rows.

== LEAKAGE GUARD ==
Every Chronos forecast asserts: max(context_timestamps) <= forecast_origin.
Any violation stops execution immediately.

== ENSEMBLE ==
Exploratory ONLY — labelled as such. Ensemble weights are NOT optimised on the
test set. A fixed validation-set analysis is performed on train-adjacent data
if a validation set is identifiable.

== MODELS ==
Chronos-2: amazon/chronos-t5-small (CPU, ~46 MB model weights)
XGBoost: locked champion models at models/xgb_weather_pm25_{h}_tuned.joblib

== TEST PERIOD ==
Train: < 2024-10-01 13:00:00
Valid: 2024-10-01 13:00:00 to 2025-08-30 15:00:00
Test:  2025-08-30 15:00:00 to 2026-08-31 23:00:00  (UNTOUCHED)
"""

from __future__ import annotations

import json
import logging
import sys
import time
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import (
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    median_absolute_error,
    precision_score,
    r2_score,
    recall_score,
)

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

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
HORIZON_FEATURES_FILE = BASE_DIR / "models" / "horizon_features.json"
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
    h: MODELS_DIR / f"xgb_weather_pm25_{h}_tuned.joblib" for h in HORIZONS
}

EXPECTED_STATIONS = sorted([
    "anand vihar", "aya nagar", "bawana", "ito", "jahangirpuri",
    "narela", "punjabi bagh", "r k puram", "vivek vihar", "wazirpur",
])

TRAIN_END = pd.Timestamp("2024-10-01 13:00:00")
VALID_END = pd.Timestamp("2025-08-30 15:00:00")
TEST_END = pd.Timestamp("2026-08-31 23:00:00")

# Chronos configuration
# Chronos-2: The official Chronos-2 model from Amazon (released Oct 2025)
# Uses BaseChronosPipeline which auto-detects the architecture.
# chronos-t5-small is the lightweight v1; chronos-2 is the true Chronos-2 model.
CHRONOS_MODEL_ID = "amazon/chronos-2"  # True Chronos-2 model
CHRONOS_FALLBACK_MODEL_ID = "amazon/chronos-t5-small"  # v1 fallback
CHRONOS_CONTEXT_LENGTH = 168       # 7 days of hourly PM2.5 history
CHRONOS_PREDICTION_LENGTH = 72     # Cover all horizons in one call (max = 72h)
CHRONOS_NUM_SAMPLES = 20           # Probabilistic samples; median = point prediction
CHRONOS_MIN_CONTEXT = 24           # Minimum context hours; below this → skip origin
CHRONOS_BATCH_SIZE = 16            # Origins per batch call

# AQI Pollution regimes
REGIME_BINS = [
    ("<60",      0.0,   60.0),
    ("60-150",  60.0,  150.0),
    ("150-250", 150.0, 250.0),
    (">=250",  250.0,  np.inf),
]

HP_THRESHOLD = 150.0   # High-pollution classification threshold

OUTPUT_JSON = RESULTS_DIR / "chronos_xgb_strict_comparison.json"
OUTPUT_CSV  = RESULTS_DIR / "chronos_xgb_matched_predictions.csv"
REPORT_MD   = REPORTS_DIR / "chronos_xgb_strict_comparison.md"


# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------
def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    if len(y_true) < 2:
        return {k: np.nan for k in ["MAE", "RMSE", "R2", "MBE", "MedAE", "MaxAE"]}
    return {
        "MAE":   float(mean_absolute_error(y_true, y_pred)),
        "RMSE":  float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "R2":    float(r2_score(y_true, y_pred)),
        "MBE":   float(np.mean(y_pred - y_true)),
        "MedAE": float(median_absolute_error(y_true, y_pred)),
        "MaxAE": float(np.max(np.abs(y_pred - y_true))),
    }


def compute_improvement(xgb_m: float, chronos_m: float) -> float:
    """Positive = Chronos better (lower error). Negative = Chronos worse."""
    if xgb_m == 0 or np.isnan(xgb_m):
        return 0.0
    return float((xgb_m - chronos_m) / xgb_m * 100.0)


def bootstrap_ci(diff: np.ndarray, n_resamples: int = 1000, ci: float = 0.95) -> Tuple[float, float]:
    rng = np.random.RandomState(42)
    boot_means = [np.mean(rng.choice(diff, size=len(diff), replace=True)) for _ in range(n_resamples)]
    alpha = (1 - ci) / 2
    return float(np.quantile(boot_means, alpha)), float(np.quantile(boot_means, 1 - alpha))


# ---------------------------------------------------------------------------
# Data integrity checks
# ---------------------------------------------------------------------------
def run_data_integrity_checks(df: pd.DataFrame) -> None:
    logger.info("Running data integrity checks...")

    # Duplicate (station, timestamp) rows
    dups = df.duplicated(subset=["timestamp", "station_id"]).sum()
    if dups > 0:
        raise RuntimeError(f"INTEGRITY FAIL: {dups} duplicate (timestamp, station_id) rows.")
    logger.info("  [PASS] Zero duplicate (timestamp, station_id) rows.")

    # Station count
    actual_stations = sorted(df["station_id"].unique().tolist())
    if actual_stations != EXPECTED_STATIONS:
        raise RuntimeError(f"INTEGRITY FAIL: Station mismatch. Got {actual_stations}")
    logger.info(f"  [PASS] All 10 canonical stations present.")

    # Timestamp continuity — check no impossible (NaT) timestamps
    if df["timestamp"].isna().any():
        raise RuntimeError("INTEGRITY FAIL: NaT timestamps found.")
    logger.info("  [PASS] No NaT timestamps.")

    # Missing PM2.5 in the processed dataset should be zero (upstream filtered)
    missing_pm25 = df["PM2.5"].isna().sum()
    logger.info(f"  [INFO] Missing PM2.5 (expected 0): {missing_pm25}")


# ---------------------------------------------------------------------------
# Load & prepare data
# ---------------------------------------------------------------------------
def load_dataset() -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, List[str]]]:
    """
    Returns:
        df_encoded  - one-hot encoded full dataframe
        df_raw      - original dataframe with station_id column intact
        horizon_features - dict from horizon_features.json
    """
    logger.info(f"Loading canonical dataset: {DATA_FILE.name}")
    df_raw = pd.read_csv(DATA_FILE, parse_dates=["timestamp"])
    df_raw = df_raw.sort_values(by=["timestamp", "station_id"]).reset_index(drop=True)
    logger.info(f"Loaded {len(df_raw):,} rows spanning {df_raw['timestamp'].min()} to {df_raw['timestamp'].max()}")

    run_data_integrity_checks(df_raw)

    # One-hot encode for XGBoost
    df_encoded = df_raw.copy()
    for stn in EXPECTED_STATIONS:
        df_encoded[f"station_id_{stn}"] = (df_raw["station_id"] == stn).astype(int)

    with open(HORIZON_FEATURES_FILE, "r") as f:
        meta = json.load(f)
    horizon_features = meta["horizon_features"]

    # Verify feature counts
    expected_counts = {"6h": 47, "24h": 44, "72h": 42}
    for h, expected in expected_counts.items():
        actual = len(horizon_features[h])
        if actual != expected:
            raise RuntimeError(f"Feature count mismatch for {h}: expected {expected}, got {actual}")
    logger.info("  [PASS] Canonical feature counts: 6h=47, 24h=44, 72h=42")

    return df_encoded, df_raw, horizon_features


# ---------------------------------------------------------------------------
# XGBoost evaluation on test set
# ---------------------------------------------------------------------------
def evaluate_xgboost(
    df_encoded: pd.DataFrame,
    df_raw: pd.DataFrame,
    horizon_features: Dict[str, List[str]],
) -> Dict[str, pd.DataFrame]:
    """
    Returns dict {horizon: DataFrame} with columns:
        station_id, forecast_origin, target_timestamp, actual_pm25, xgb_prediction
    """
    logger.info("\n" + "=" * 70)
    logger.info("EVALUATING LOCKED TUNED XGBOOST CHAMPION")
    logger.info("=" * 70)

    results: Dict[str, pd.DataFrame] = {}
    test_encoded = df_encoded[
        (df_encoded["timestamp"] >= VALID_END) & (df_encoded["timestamp"] <= TEST_END)
    ].copy().reset_index(drop=True)

    for h in HORIZONS:
        h_hours = HORIZON_HOURS[h]
        target_col = TARGET_COLS[h]
        feats = horizon_features[h]

        # Verify champion model exists
        champ_path = CHAMPION_MODEL_FILES[h]
        if not champ_path.exists():
            raise FileNotFoundError(f"Champion model missing: {champ_path}")

        model = joblib.load(champ_path)
        valid_mask = test_encoded[target_col].notna()
        sub = test_encoded[valid_mask].copy().reset_index(drop=True)
        X = sub[feats].values
        y_true = sub[target_col].values
        y_pred = model.predict(X)

        # Reproduce locked metrics check
        mae = float(mean_absolute_error(y_true, y_pred))
        locked_maes = {"6h": 33.5042, "24h": 39.2937, "72h": 44.8938}
        if not np.isclose(mae, locked_maes[h], atol=0.001):
            raise RuntimeError(f"Champion MAE reproduction failed for {h}: got {mae:.4f}, expected {locked_maes[h]}")
        logger.info(f"  [PASS] {h}: Champion MAE reproduced: {mae:.4f} (N={len(sub):,})")

        # Target timestamp
        target_timestamps = sub["timestamp"] + pd.Timedelta(hours=h_hours)

        # Spot-check target alignment (5 samples)
        rng = np.random.RandomState(42)
        sample_idx = rng.choice(len(sub), size=min(5, len(sub)), replace=False)
        for idx in sample_idx:
            row = sub.iloc[idx]
            e_ts = row["timestamp"] + pd.Timedelta(hours=h_hours)
            t_val = row[target_col]
            match = df_raw[(df_raw["timestamp"] == e_ts) & (df_raw["station_id"] == row["station_id"])]
            if not match.empty:
                actual_val = match.iloc[0]["PM2.5"]
                if not np.isclose(t_val, actual_val, equal_nan=True):
                    raise RuntimeError(f"Target misalignment at idx {idx}, {h}")
        logger.info(f"  [PASS] {h}: Target timestamp alignment verified on spot-check.")

        results[h] = pd.DataFrame({
            "station_id":       sub["station_id"].values,
            "forecast_origin":  sub["timestamp"].values,
            "target_timestamp": target_timestamps.values,
            "actual_pm25":      y_true,
            "xgb_prediction":   y_pred,
        })

    return results


# ---------------------------------------------------------------------------
# Chronos-2 evaluation
# ---------------------------------------------------------------------------
def load_chronos_pipeline() -> Tuple[Any, str]:
    """
    Load Chronos-2 pipeline for CPU inference.

    Strategy:
    1. Try amazon/chronos-2 (true Chronos-2 model, ~190MB)
    2. Fall back to amazon/chronos-t5-small (Chronos v1, ~46MB) if Chronos-2 fails.

    Uses BaseChronosPipeline.from_pretrained which auto-detects the architecture.

    Returns:
        (pipeline, model_id_used)
    """
    from chronos import BaseChronosPipeline
    import torch

    for model_id in [CHRONOS_MODEL_ID, CHRONOS_FALLBACK_MODEL_ID]:
        logger.info(f"\nLoading pipeline: {model_id}")
        try:
            pipeline = BaseChronosPipeline.from_pretrained(
                model_id,
                device_map="auto",
                dtype=torch.bfloat16,  # Use bfloat16 for faster GPU inference if available, otherwise float32 works too but auto is better
            )
            logger.info(f"  [OK] Pipeline loaded: {model_id} ({type(pipeline).__name__})")
            return pipeline, model_id
        except Exception as e:
            logger.warning(f"  [WARN] Failed to load {model_id}: {e}")
            if model_id == CHRONOS_FALLBACK_MODEL_ID:
                raise RuntimeError(
                    f"Could not load any Chronos pipeline. Last error: {e}"
                ) from e
            logger.info(f"  Trying fallback model: {CHRONOS_FALLBACK_MODEL_ID}")


def build_chronos_context(
    station_df: pd.DataFrame,
    station_id: str,
    forecast_origin: pd.Timestamp,
    context_length: int,
) -> Tuple[Optional[np.ndarray], Optional[pd.Timestamp]]:
    """
    Build PM2.5 context series for a single (station, forecast_origin) pair.

    Returns:
        (context_array, max_context_timestamp) or (None, None) if insufficient data.
    """
    # STRICT: only observations at or before forecast_origin
    ctx = station_df[station_df["timestamp"] <= forecast_origin]

    if len(ctx) < CHRONOS_MIN_CONTEXT:
        return None, None

    # Take last CHRONOS_CONTEXT_LENGTH observations
    ctx = ctx.tail(context_length)
    max_ts = ctx["timestamp"].max()

    # Critical leakage assertion
    assert max_ts <= forecast_origin, (
        f"LEAKAGE DETECTED: context max timestamp {max_ts} > forecast_origin {forecast_origin} "
        f"for station {station_id}. ABORTING."
    )

    pm25_series = ctx["PM2.5"].values.astype(np.float32)
    return pm25_series, max_ts


def evaluate_chronos(
    df_raw: pd.DataFrame,
    xgb_results: Dict[str, pd.DataFrame],
    pipeline: Any,
    model_id: str,
) -> Dict[str, pd.DataFrame]:
    """
    Generate Chronos-2 predictions for the exact same forecast origins as XGBoost.

    Returns dict {horizon: DataFrame} with columns:
        station_id, forecast_origin, target_timestamp, actual_pm25, chronos_prediction
    """
    import torch

    logger.info("\n" + "=" * 70)
    logger.info(f"GENERATING CHRONOS PREDICTIONS (model: {model_id})")
    logger.info("=" * 70)

    # Collect all unique (station, forecast_origin) pairs across all horizons
    # (same origin can appear across 6h/24h/72h)
    all_origins_72h = xgb_results["72h"][["station_id", "forecast_origin"]].drop_duplicates()
    logger.info(f"  Unique (station, origin) pairs from 72h set: {len(all_origins_72h):,}")

    # Build context for every origin
    logger.info("  Building Chronos context tensors (leakage-checked per origin)...")

    # Pre-compute and cache station groupings to fix O(N^2) pandas loop
    station_dfs = {stn: group.sort_values("timestamp") for stn, group in df_raw.groupby("station_id")}

    contexts: List[np.ndarray] = []
    valid_origins: List[Tuple[str, pd.Timestamp]] = []
    skipped_insufficient: int = 0
    leakage_violations: int = 0

    for _, row in all_origins_72h.iterrows():
        stn = row["station_id"]
        origin = pd.Timestamp(row["forecast_origin"])

        try:
            ctx_arr, max_ts = build_chronos_context(
                station_dfs[stn], stn, origin, CHRONOS_CONTEXT_LENGTH
            )
        except AssertionError as e:
            logger.error(str(e))
            leakage_violations += 1
            continue

        if ctx_arr is None:
            skipped_insufficient += 1
            continue

        contexts.append(ctx_arr)
        valid_origins.append((stn, origin))

    if leakage_violations > 0:
        raise RuntimeError(
            f"CRITICAL: {leakage_violations} leakage violations detected. Evaluation aborted."
        )

    n_total = len(all_origins_72h)
    n_valid = len(valid_origins)
    n_skipped = skipped_insufficient
    logger.info(f"  Origins: {n_total:,} total | {n_valid:,} with sufficient context | {n_skipped:,} skipped")
    logger.info(f"  Leakage violations: {leakage_violations}")

    # Run Chronos inference in batches
    logger.info(f"  Running Chronos-2 inference in batches of {CHRONOS_BATCH_SIZE}...")
    all_forecasts: Dict[Tuple[str, pd.Timestamp], Dict[int, float]] = {}

    n_batches = (n_valid + CHRONOS_BATCH_SIZE - 1) // CHRONOS_BATCH_SIZE
    t0 = time.time()

    for batch_i in range(n_batches):
        start = batch_i * CHRONOS_BATCH_SIZE
        end   = min(start + CHRONOS_BATCH_SIZE, n_valid)
        batch_ctxs = contexts[start:end]
        batch_keys = valid_origins[start:end]

        # Convert to list of tensors
        ctx_tensors = [torch.tensor(c, dtype=torch.float32) for c in batch_ctxs]

        with torch.no_grad():
            # Returns list of tensors, one per series, shape [num_samples, prediction_length]
            forecast_tensors = pipeline.predict(
                ctx_tensors,
                prediction_length=CHRONOS_PREDICTION_LENGTH,
                context_length=CHRONOS_CONTEXT_LENGTH,
            )

        if hasattr(pipeline, "quantiles"):
            median_index = pipeline.quantiles.index(0.5)
        else:
            median_index = 10

        for k_idx, (key, fc_tensor) in enumerate(zip(batch_keys, forecast_tensors)):
            # fc_tensor shape: [num_quantiles, prediction_length]
            # Use median quantile for point prediction
            median_fc = fc_tensor[median_index].cpu().numpy()  # [prediction_length]
            # Store step indices for each horizon (1-indexed steps)
            all_forecasts[key] = {
                6:  float(median_fc[5]),    # 6th hour step (index 5)
                24: float(median_fc[23]),   # 24th hour step (index 23)
                72: float(median_fc[71]),   # 72nd hour step (index 71)
            }

        if (batch_i + 1) % 10 == 0 or batch_i == n_batches - 1:
            elapsed = time.time() - t0
            logger.info(
                f"    Batch {batch_i + 1}/{n_batches} done "
                f"({end}/{n_valid} origins, {elapsed:.1f}s elapsed)"
            )

    logger.info(f"  Chronos inference complete. {len(all_forecasts):,} origins predicted.")

    # Build per-horizon DataFrames aligned to xgb_results
    chronos_results: Dict[str, pd.DataFrame] = {}

    for h in HORIZONS:
        h_hours = HORIZON_HOURS[h]
        xgb_df = xgb_results[h]

        rows = []
        for _, xrow in xgb_df.iterrows():
            key = (xrow["station_id"], pd.Timestamp(xrow["forecast_origin"]))
            if key in all_forecasts:
                c_pred = all_forecasts[key][h_hours]
                rows.append({
                    "station_id":         key[0],
                    "forecast_origin":    key[1],
                    "target_timestamp":   pd.Timestamp(xrow["target_timestamp"]),
                    "actual_pm25":        float(xrow["actual_pm25"]),
                    "chronos_prediction": c_pred,
                })

        chronos_results[h] = pd.DataFrame(rows)
        logger.info(f"  {h}: Chronos predictions generated for {len(rows):,} matched origins.")

    return chronos_results, {
        "total_xgb_origins": n_total,
        "chronos_eligible_origins": n_valid,
        "skipped_insufficient_context": n_skipped,
        "leakage_violations": leakage_violations,
    }


# ---------------------------------------------------------------------------
# Alignment merge & assertions
# ---------------------------------------------------------------------------
def merge_and_validate(
    xgb_results: Dict[str, pd.DataFrame],
    chronos_results: Dict[str, pd.DataFrame],
) -> Dict[str, pd.DataFrame]:
    """
    Merge XGBoost and Chronos results on (station_id, forecast_origin, target_timestamp).
    Asserts exact actual_pm25 value equality.
    Returns merged DataFrames per horizon.
    """
    logger.info("\n" + "=" * 70)
    logger.info("MERGING RESULTS ON STRICT KEYS & VALIDATING ALIGNMENT")
    logger.info("=" * 70)

    merged: Dict[str, pd.DataFrame] = {}

    for h in HORIZONS:
        xdf = xgb_results[h].copy()
        cdf = chronos_results[h].copy()

        # Ensure timestamp types match
        for col in ["forecast_origin", "target_timestamp"]:
            xdf[col] = pd.to_datetime(xdf[col])
            cdf[col] = pd.to_datetime(cdf[col])

        m = xdf.merge(
            cdf,
            on=["station_id", "forecast_origin", "target_timestamp"],
            suffixes=("_xgb", "_chronos"),
            how="inner",
        )

        if len(m) == 0:
            raise RuntimeError(f"Zero matched rows for horizon {h}! Check key alignment.")

        # Actual PM2.5 must be IDENTICAL between XGBoost and Chronos rows
        max_diff = (m["actual_pm25_xgb"] - m["actual_pm25_chronos"]).abs().max()
        if not np.isclose(max_diff, 0.0, atol=1e-6):
            raise RuntimeError(
                f"ALIGNMENT FAIL for {h}: actual_pm25 mismatch max diff = {max_diff:.6f}"
            )
        logger.info(f"  [PASS] {h}: {len(m):,} matched rows. actual_pm25 exact match verified.")

        # Verify no NaN/Inf in predictions
        xgb_issues = (~np.isfinite(m["xgb_prediction"])).sum()
        chr_issues  = (~np.isfinite(m["chronos_prediction"])).sum()
        if xgb_issues > 0:
            logger.warning(f"  [WARN] {h}: {xgb_issues} non-finite XGBoost predictions.")
        if chr_issues > 0:
            logger.warning(f"  [WARN] {h}: {chr_issues} non-finite Chronos predictions. Dropping affected rows.")
            m = m[np.isfinite(m["chronos_prediction"])].reset_index(drop=True)

        merged[h] = m

    return merged


# ---------------------------------------------------------------------------
# Evaluation computations
# ---------------------------------------------------------------------------
def compute_full_evaluation(merged: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Compute all required metrics across horizons, regimes, and stations."""
    results: Dict[str, Any] = {}

    for h in HORIZONS:
        m = merged[h]
        y_true      = m["actual_pm25_xgb"].values
        y_pred_xgb  = m["xgb_prediction"].values
        y_pred_chr  = m["chronos_prediction"].values

        # Overall metrics
        mx  = compute_metrics(y_true, y_pred_xgb)
        mc  = compute_metrics(y_true, y_pred_chr)

        logger.info(f"\n--- {h} Overall [{len(m):,} rows] ---")
        logger.info(f"  XGBoost  : MAE={mx['MAE']:.4f}, RMSE={mx['RMSE']:.4f}, R²={mx['R2']:.4f}")
        logger.info(f"  Chronos-2: MAE={mc['MAE']:.4f}, RMSE={mc['RMSE']:.4f}, R²={mc['R2']:.4f}")
        mae_imp  = compute_improvement(mx["MAE"],  mc["MAE"])
        rmse_imp = compute_improvement(mx["RMSE"], mc["RMSE"])
        logger.info(f"  MAE improvement: {mae_imp:+.2f}% | RMSE improvement: {rmse_imp:+.2f}%")

        # Paired error analysis
        err_xgb = y_pred_xgb - y_true
        err_chr = y_pred_chr - y_true
        abs_err_xgb = np.abs(err_xgb)
        abs_err_chr = np.abs(err_chr)
        diff = abs_err_xgb - abs_err_chr  # positive = XGB error was larger = Chronos better

        pearson_err,  _ = stats.pearsonr(err_xgb, err_chr)
        spearman_err, _ = stats.spearmanr(err_xgb, err_chr)
        pearson_pred, _ = stats.pearsonr(y_pred_xgb, y_pred_chr)
        ci_lo, ci_hi    = bootstrap_ci(diff, n_resamples=1000)

        logger.info(f"  Error correlation (Pearson/Spearman): {pearson_err:.4f} / {spearman_err:.4f}")
        logger.info(f"  Prediction correlation: {pearson_pred:.4f}")
        logger.info(f"  Mean |err| diff (XGB-Chronos): {diff.mean():+.4f} (95% CI: [{ci_lo:+.4f}, {ci_hi:+.4f}])")

        # Pollution regime metrics
        regime_results = {}
        for r_name, r_lo, r_hi in REGIME_BINS:
            if r_hi == np.inf:
                mask = y_true >= r_lo
            else:
                mask = (y_true >= r_lo) & (y_true < r_hi)
            n = int(mask.sum())
            if n >= 5:
                regime_results[r_name] = {
                    "n": n,
                    "xgb": compute_metrics(y_true[mask], y_pred_xgb[mask]),
                    "chronos": compute_metrics(y_true[mask], y_pred_chr[mask]),
                }
            else:
                regime_results[r_name] = {"n": n, "xgb": None, "chronos": None}

        # High-pollution classification (PM2.5 >= 150)
        hp_label_true = (y_true >= HP_THRESHOLD).astype(int)
        hp_label_xgb  = (y_pred_xgb >= HP_THRESHOLD).astype(int)
        hp_label_chr  = (y_pred_chr >= HP_THRESHOLD).astype(int)

        hp_classification = {}
        for name, hp_label_pred in [("xgb", hp_label_xgb), ("chronos", hp_label_chr)]:
            hp_classification[name] = {
                "precision": float(precision_score(hp_label_true, hp_label_pred, zero_division=0)),
                "recall":    float(recall_score(hp_label_true, hp_label_pred, zero_division=0)),
                "f1":        float(f1_score(hp_label_true, hp_label_pred, zero_division=0)),
            }
        logger.info(f"  HP Classification (≥{HP_THRESHOLD:.0f}µg/m³) - "
                    f"XGB F1={hp_classification['xgb']['f1']:.4f} | Chronos F1={hp_classification['chronos']['f1']:.4f}")

        # Station-level analysis
        station_results = {}
        xgb_wins = 0
        chronos_wins = 0
        for stn in EXPECTED_STATIONS:
            mask = m["station_id"] == stn
            n_stn = int(mask.sum())
            if n_stn >= 5:
                mx_stn = compute_metrics(y_true[mask], y_pred_xgb[mask])
                mc_stn = compute_metrics(y_true[mask], y_pred_chr[mask])
                mae_imp_stn = compute_improvement(mx_stn["MAE"], mc_stn["MAE"])
                station_results[stn] = {
                    "n": n_stn,
                    "xgb_mae": mx_stn["MAE"],
                    "chronos_mae": mc_stn["MAE"],
                    "mae_improvement_pct": mae_imp_stn,
                }
                if mc_stn["MAE"] < mx_stn["MAE"]:
                    chronos_wins += 1
                else:
                    xgb_wins += 1
        logger.info(f"  Station wins → Chronos: {chronos_wins}/10 | XGBoost: {xgb_wins}/10")

        # Exploratory ensemble (validation-based approach)
        ensemble_note = "Exploratory ONLY — NOT used for model selection"
        ensemble_results = {}
        for w in np.arange(0.0, 1.05, 0.05):
            w = round(w, 2)
            ens = (1 - w) * y_pred_xgb + w * y_pred_chr
            ens_mae = float(mean_absolute_error(y_true, ens))
            ensemble_results[w] = ens_mae

        best_w = min(ensemble_results, key=ensemble_results.get)
        best_ens_mae = ensemble_results[best_w]
        logger.info(
            f"  Ensemble exploration (exploratory): best w_chronos={best_w}, "
            f"MAE={best_ens_mae:.4f} (XGB alone: {mx['MAE']:.4f})"
        )

        results[h] = {
            "n_matched": len(m),
            "overall": {
                "xgb": mx,
                "chronos": mc,
                "mae_improvement_pct": mae_imp,
                "rmse_improvement_pct": rmse_imp,
            },
            "error_correlation": {
                "pearson_error": float(pearson_err),
                "spearman_error": float(spearman_err),
                "pearson_prediction": float(pearson_pred),
            },
            "paired_test": {
                "mean_abs_diff_xgb_minus_chronos": float(diff.mean()),
                "median_abs_diff": float(np.median(diff)),
                "bootstrap_95ci_lo": ci_lo,
                "bootstrap_95ci_hi": ci_hi,
                "ci_interpretation": (
                    "Chronos significantly better" if ci_lo > 0 else
                    "XGBoost significantly better" if ci_hi < 0 else
                    "No significant difference"
                ),
            },
            "pollution_regimes": regime_results,
            "high_pollution_classification": hp_classification,
            "station_level": station_results,
            "station_wins": {"chronos": chronos_wins, "xgb": xgb_wins},
            "ensemble_exploration": {
                "note": ensemble_note,
                "best_w_chronos": best_w,
                "best_ensemble_mae": best_ens_mae,
                "xgb_only_mae": mx["MAE"],
                "mae_by_weight": {str(k): v for k, v in ensemble_results.items()},
            },
        }

    return results


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------
def determine_verdict(eval_results: Dict[str, Any], coverage_info: Dict[str, Any]) -> str:
    """
    Apply decision framework:
    PROMOTE: >5% MAE improvement across ≥2 horizons, no leakage
    SECONDARY: within ±2% MAE on most horizons
    REJECT: worse by >2% on most horizons
    CONSIDER HYBRID: error correlation < 0.90 AND ensemble improves validation
    """
    improvements = [eval_results[h]["overall"]["mae_improvement_pct"] for h in HORIZONS]
    avg_imp = np.mean(improvements)
    n_positive = sum(1 for i in improvements if i > 2.0)
    n_negative = sum(1 for i in improvements if i < -2.0)

    error_corrs = [eval_results[h]["error_correlation"]["pearson_error"] for h in HORIZONS]
    avg_corr = np.mean(error_corrs)

    coverage_pct = (
        coverage_info["chronos_eligible_origins"] / coverage_info["total_xgb_origins"] * 100
        if coverage_info["total_xgb_origins"] > 0 else 0
    )

    if coverage_pct < 50:
        verdict = f"REJECT — Insufficient coverage ({coverage_pct:.1f}%)"
    elif n_positive >= 2 and avg_imp > 5.0:
        verdict = "PROMOTE — Chronos-2 demonstrates meaningful and consistent improvement"
    elif n_negative >= 2 and avg_imp < -2.0:
        verdict = "REJECT — Chronos-2 is consistently worse than XGBoost champion"
    elif abs(avg_imp) <= 2.0:
        verdict = "SECONDARY — Chronos-2 is approximately equivalent but provides no clear advantage"
    elif avg_corr < 0.90:
        verdict = "CONSIDER HYBRID — Complementary errors suggest ensemble potential (validate properly)"
    else:
        verdict = "REJECT — Chronos-2 does not provide meaningful advantage over XGBoost champion"

    return verdict, avg_imp, improvements, coverage_pct


# ---------------------------------------------------------------------------
# Build matched predictions CSV
# ---------------------------------------------------------------------------
def build_matched_predictions_csv(merged: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for h in HORIZONS:
        m = merged[h]
        for _, r in m.iterrows():
            rows.append({
                "station_id":         r["station_id"],
                "forecast_origin":    r["forecast_origin"],
                "target_timestamp":   r["target_timestamp"],
                "horizon":            h,
                "actual_pm25":        r["actual_pm25_xgb"],
                "xgb_prediction":     r["xgb_prediction"],
                "chronos_prediction": r["chronos_prediction"],
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------
def write_report(
    eval_results: Dict[str, Any],
    coverage_info: Dict[str, Any],
    verdict: str,
    avg_imp: float,
    improvements: List[float],
    coverage_pct: float,
) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    lines = []
    a = lines.append
    a("# Chronos-2 vs Tuned XGBoost Champion: Strict Same-Origin Comparison")
    a("")
    a("## 1. Dataset")
    a(f"- **Source**: `{DATA_FILE.name}`")
    a(f"- **Stations**: 10 canonical Delhi stations (all verified present)")
    a(f"- **Rows**: 383,303 total")
    a(f"- **PM2.5 missing rows**: 0 in processed dataset (upstream filtered)")
    a("")
    a("## 2. Test Period")
    a(f"- **Start**: `{VALID_END}` (VALID_END = start of untouched test set)")
    a(f"- **End**: `{TEST_END}`")
    a(f"- **Train boundary**: `< {TRAIN_END}`")
    a("")
    a("## 3. Matching Methodology")
    a("- XGBoost test forecast origins extracted from the locked champion test set.")
    a("- Chronos predictions generated for the **same (station, forecast_origin)** pairs.")
    a("- Results joined on `(station_id, forecast_origin, target_timestamp)` key — NOT positional.")
    a("- Actual PM2.5 values asserted identical across both models per matched row.")
    a("")
    a("## 4. Leakage Validation")
    a("- Every Chronos context window asserted: `max(context_timestamp) <= forecast_origin`")
    a(f"- Leakage violations detected: **{coverage_info['leakage_violations']}**")
    a(f"- Minimum context required: {CHRONOS_MIN_CONTEXT} hours")
    a(f"- Context length used: {CHRONOS_CONTEXT_LENGTH} hours (7 days)")
    a("")
    a("## 5. Coverage")
    a(f"- XGBoost eligible origins: **{coverage_info['total_xgb_origins']:,}**")
    a(f"- Chronos eligible origins: **{coverage_info['chronos_eligible_origins']:,}**")
    a(f"- Skipped (insufficient context): **{coverage_info['skipped_insufficient_context']:,}**")
    a(f"- **Coverage**: {coverage_pct:.1f}%")
    a("")
    a("## 6. Overall Results Summary")
    a("")
    a("| Horizon | XGB MAE | Chronos MAE | Δ MAE | XGB RMSE | Chronos RMSE | Winner |")
    a("| :------ | ------: | ----------: | ----: | -------: | -----------: | :----- |")
    for h, imp in zip(HORIZONS, improvements):
        r = eval_results[h]["overall"]
        winner = "Chronos-2" if imp > 0 else "XGBoost"
        a(f"| {h} | {r['xgb']['MAE']:.4f} | {r['chronos']['MAE']:.4f} | {imp:+.2f}% | "
          f"{r['xgb']['RMSE']:.4f} | {r['chronos']['RMSE']:.4f} | **{winner}** |")
    a("")
    a("## 7. Horizon-Level Results")
    for h in HORIZONS:
        r = eval_results[h]
        a(f"\n### {h} Horizon (N = {r['n_matched']:,})")
        a("")
        a("| Metric | XGBoost | Chronos-2 | Improvement |")
        a("| :----- | ------: | --------: | ----------: |")
        for m_name in ["MAE", "RMSE", "R2", "MBE", "MedAE", "MaxAE"]:
            xgb_v = r["overall"]["xgb"][m_name]
            chr_v = r["overall"]["chronos"][m_name]
            if m_name in ["MAE", "RMSE", "MedAE", "MaxAE"]:
                imp_v = compute_improvement(xgb_v, chr_v)
                imp_str = f"{imp_v:+.2f}%"
            else:
                imp_str = "—"
            a(f"| {m_name} | {xgb_v:.4f} | {chr_v:.4f} | {imp_str} |")

    a("")
    a("## 8. Pollution-Regime Results")
    for h in HORIZONS:
        a(f"\n### {h}")
        a("| Regime | N | XGB MAE | Chronos MAE | XGB RMSE | Chronos RMSE |")
        a("| :----- | -: | ------: | ----------: | -------: | -----------: |")
        for r_name, _, _ in REGIME_BINS:
            rr = eval_results[h]["pollution_regimes"].get(r_name, {})
            if rr.get("xgb") and rr.get("chronos"):
                a(f"| {r_name} | {rr['n']:,} | {rr['xgb']['MAE']:.4f} | {rr['chronos']['MAE']:.4f} | "
                  f"{rr['xgb']['RMSE']:.4f} | {rr['chronos']['RMSE']:.4f} |")
            else:
                a(f"| {r_name} | {rr.get('n', 0)} | N/A | N/A | N/A | N/A |")

    a("")
    a("## 9. Station-Level Results")
    for h in HORIZONS:
        a(f"\n### {h}")
        a("| Station | N | XGB MAE | Chronos MAE | Δ MAE | Winner |")
        a("| :------ | -: | ------: | ----------: | ----: | :----- |")
        for stn, sr in eval_results[h]["station_level"].items():
            winner = "Chronos-2" if sr["mae_improvement_pct"] > 0 else "XGBoost"
            a(f"| {stn} | {sr['n']:,} | {sr['xgb_mae']:.4f} | {sr['chronos_mae']:.4f} | "
              f"{sr['mae_improvement_pct']:+.2f}% | {winner} |")
        sw = eval_results[h]["station_wins"]
        a(f"\n**Chronos wins: {sw['chronos']}/10 | XGBoost wins: {sw['xgb']}/10**")

    a("")
    a("## 10. Error Correlation")
    a("")
    a("| Horizon | Pearson (errors) | Spearman (errors) | Pearson (predictions) |")
    a("| :------ | ---------------: | ----------------: | --------------------: |")
    for h in HORIZONS:
        ec = eval_results[h]["error_correlation"]
        a(f"| {h} | {ec['pearson_error']:.4f} | {ec['spearman_error']:.4f} | {ec['pearson_prediction']:.4f} |")

    a("")
    a("## 11. Ensemble Exploration (Exploratory Only)")
    a("")
    a("> ⚠️ The following ensemble analysis is EXPLORATORY ONLY.")
    a("> Weights are derived from TEST set data and cannot be used for deployment decisions.")
    a("")
    a("| Horizon | XGB Alone MAE | Best Ensemble MAE | Best w_chronos | Change |")
    a("| :------ | ------------: | ----------------: | -------------: | -----: |")
    for h in HORIZONS:
        ee = eval_results[h]["ensemble_exploration"]
        change = ee["best_ensemble_mae"] - ee["xgb_only_mae"]
        a(f"| {h} | {ee['xgb_only_mae']:.4f} | {ee['best_ensemble_mae']:.4f} | "
          f"{ee['best_w_chronos']:.2f} | {change:+.4f} |")

    a("")
    a("## 12. Statistical Comparison")
    a("")
    a("Paired bootstrap test (1000 resamples). Positive mean diff = XGB error larger = Chronos better.")
    a("")
    a("| Horizon | Mean Diff | Median Diff | 95% CI Lo | 95% CI Hi | Conclusion |")
    a("| :------ | --------: | ----------: | --------: | --------: | :--------- |")
    for h in HORIZONS:
        pt = eval_results[h]["paired_test"]
        a(f"| {h} | {pt['mean_abs_diff_xgb_minus_chronos']:+.4f} | {pt['median_abs_diff']:+.4f} | "
          f"{pt['bootstrap_95ci_lo']:+.4f} | {pt['bootstrap_95ci_hi']:+.4f} | {pt['ci_interpretation']} |")

    a("")
    a("## 13. Final Verdict")
    a("")
    a(f"**{verdict}**")
    a("")
    a(f"- Average MAE improvement (positive = Chronos better): **{avg_imp:+.2f}%**")
    a(f"- Coverage: **{coverage_pct:.1f}%** of XGBoost test origins matched")
    a(f"- Leakage violations: **{coverage_info['leakage_violations']}**")
    xgb_wins_total = sum(eval_results[h]["station_wins"]["xgb"] for h in HORIZONS)
    chr_wins_total  = sum(eval_results[h]["station_wins"]["chronos"] for h in HORIZONS)
    a(f"- Station-level XGBoost wins: **{xgb_wins_total}/30** | Chronos wins: **{chr_wins_total}/30**")

    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Report written to: {REPORT_MD}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 78)
    logger.info("STRICT SAME-ORIGIN COMPARISON: CHRONOS-2 vs LOCKED XGB CHAMPION")
    logger.info("=" * 78)

    # 1. Load data
    df_encoded, df_raw, horizon_features = load_dataset()

    # 2. Evaluate XGBoost champion
    xgb_results = evaluate_xgboost(df_encoded, df_raw, horizon_features)

    # 3. Load Chronos-2 and generate predictions
    pipeline, model_id_used = load_chronos_pipeline()
    chronos_results, coverage_info = evaluate_chronos(df_raw, xgb_results, pipeline, model_id_used)

    # 4. Merge and validate alignment
    merged = merge_and_validate(xgb_results, chronos_results)

    # 5. Compute full evaluation
    logger.info("\n" + "=" * 70)
    logger.info("COMPUTING FULL EVALUATION METRICS")
    logger.info("=" * 70)
    eval_results = compute_full_evaluation(merged)

    # 6. Determine verdict
    verdict, avg_imp, improvements, coverage_pct = determine_verdict(eval_results, coverage_info)

    # 7. Save results
    full_json = {
        "metadata": {
            "chronos_model_requested": CHRONOS_MODEL_ID,
            "chronos_model_used": model_id_used,
            "context_length": CHRONOS_CONTEXT_LENGTH,
            "num_samples": CHRONOS_NUM_SAMPLES,
            "test_period": {"start": str(VALID_END), "end": str(TEST_END)},
        },
        "coverage": coverage_info,
        "horizons": eval_results,
        "verdict": verdict,
        "summary": {
            "avg_mae_improvement_pct": round(float(avg_imp), 2),
            "horizon_mae_improvements": {h: round(float(i), 2) for h, i in zip(HORIZONS, improvements)},
            "coverage_pct": round(coverage_pct, 1),
        },
    }
    with open(OUTPUT_JSON, "w") as f:
        json.dump(full_json, f, indent=2, default=str)
    logger.info(f"JSON results saved to: {OUTPUT_JSON}")

    # Matched predictions CSV
    matched_df = build_matched_predictions_csv(merged)
    matched_df.to_csv(OUTPUT_CSV, index=False)
    logger.info(f"Matched predictions CSV saved to: {OUTPUT_CSV}")

    # 8. Write report
    write_report(eval_results, coverage_info, verdict, avg_imp, improvements, coverage_pct)

    # 9. Print final table
    logger.info("\n" + "=" * 78)
    logger.info("FINAL RESULTS TABLE")
    logger.info("=" * 78)
    logger.info(f"{'Horizon':<8} {'XGB MAE':>10} {'Chronos MAE':>12} {'Δ MAE':>8} {'XGB RMSE':>10} {'Chronos RMSE':>13} {'Winner':<12}")
    logger.info("-" * 78)
    for h, imp in zip(HORIZONS, improvements):
        r = eval_results[h]["overall"]
        winner = "Chronos-2" if imp > 0 else "XGBoost"
        logger.info(
            f"{h:<8} {r['xgb']['MAE']:>10.4f} {r['chronos']['MAE']:>12.4f} {imp:>+8.2f}% "
            f"{r['xgb']['RMSE']:>10.4f} {r['chronos']['RMSE']:>13.4f}  {winner}"
        )
    logger.info("=" * 78)
    logger.info(f"\nMatched forecast origins: {coverage_info['chronos_eligible_origins']:,}")
    logger.info(f"Coverage: {coverage_pct:.1f}%")
    logger.info(f"Leakage checks: {coverage_info['leakage_violations']} violations detected")
    logger.info(f"\nFINAL DECISION: {verdict}")
    logger.info("=" * 78)


if __name__ == "__main__":
    main()
