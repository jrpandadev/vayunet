"""
XGBoost Hyperparameter Tuning Pipeline for VayuNet PM2.5 Forecasting.

Executes horizon-independent hyperparameter tuning using early stopping
on the chronological validation set (60% Train / 20% Valid / 20% Test).

Logs all trials to ml/results/model_experiments.csv.
Evaluates selected winning configurations on the untouched test set.
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple

import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

DATA_FILE = BASE_DIR / "data" / "processed" / "delhi_forecasting_weather.csv"
HORIZON_METADATA_FILE = BASE_DIR / "models" / "horizon_features.json"
RESULTS_DIR = BASE_DIR / "ml" / "results"
EXPERIMENTS_CSV = RESULTS_DIR / "model_experiments.csv"

TARGETS = {
    "6h": "target_pm25_6h",
    "24h": "target_pm25_24h",
    "72h": "target_pm25_72h",
}

HORIZONS = ["6h", "24h", "72h"]

CSV_COLUMNS = [
    "horizon",
    "feature_set",
    "split_evaluated",
    "max_depth",
    "learning_rate",
    "n_estimators",
    "best_iteration",
    "min_child_weight",
    "subsample",
    "colsample_bytree",
    "reg_alpha",
    "reg_lambda",
    "gamma",
    "MAE",
    "RMSE",
    "R2",
    "bias",
    "MedAE",
    "duration_sec",
]


def load_and_split_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load dataset, one-hot encode station_id, and split chronologically (60/20/20)."""
    print(f"Loading data from {DATA_FILE}...")
    df = pd.read_csv(DATA_FILE, parse_dates=["timestamp"])
    if "timestamp" in df.columns and "Timestamp" not in df.columns:
        df.rename(columns={"timestamp": "Timestamp"}, inplace=True)
    df = df.sort_values(by="Timestamp").reset_index(drop=True)

    # One-hot encode station_id (same as baseline and weather pipelines)
    df_encoded = pd.get_dummies(df, columns=["station_id"], dtype=int)

    n = len(df_encoded)
    train_end = int(n * 0.60)
    val_end = train_end + int(n * 0.20)

    train_df = df_encoded.iloc[:train_end].copy()
    val_df = df_encoded.iloc[train_end:val_end].copy()
    test_df = df_encoded.iloc[val_end:].copy()

    print(f"  Train: {train_df['Timestamp'].min()} to {train_df['Timestamp'].max()} (N={len(train_df)})")
    print(f"  Valid: {val_df['Timestamp'].min()} to {val_df['Timestamp'].max()} (N={len(val_df)})")
    print(f"  Test : {test_df['Timestamp'].min()} to {test_df['Timestamp'].max()} (N={len(test_df)})")

    return train_df, val_df, test_df


def evaluate_predictions(y_true: pd.Series, y_pred: np.ndarray) -> Dict[str, float]:
    """Compute standard metrics: MAE, RMSE, R2, bias, MedAE."""
    err = y_pred - y_true
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "R2": float(r2_score(y_true, y_pred)),
        "bias": float(np.mean(err)),
        "MedAE": float(np.median(np.abs(err))),
    }


def init_experiments_csv():
    """Ensure ml/results/model_experiments.csv exists with exact headers."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    if not EXPERIMENTS_CSV.exists():
        df = pd.DataFrame(columns=CSV_COLUMNS)
        df.to_csv(EXPERIMENTS_CSV, index=False)
        print(f"Initialized experiment log at {EXPERIMENTS_CSV}")


def log_experiment(record: Dict[str, Any]):
    """Append a single experiment record to CSV."""
    df_row = pd.DataFrame([record])
    # Ensure all columns present
    for col in CSV_COLUMNS:
        if col not in df_row.columns:
            df_row[col] = np.nan
    df_row = df_row[CSV_COLUMNS]
    df_row.to_csv(EXPERIMENTS_CSV, mode="a", header=False, index=False)


def run_trial(
    horizon: str,
    feature_cols: List[str],
    params: Dict[str, Any],
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    feature_set_name: str,
    early_stopping_rounds: int = 50,
) -> Tuple[Dict[str, Any], xgb.XGBRegressor]:
    """Fit model with early stopping on validation set and evaluate validation metrics."""
    target_col = TARGETS[horizon]

    t_mask = train_df[target_col].notna()
    v_mask = val_df[target_col].notna()

    X_train = train_df.loc[t_mask, feature_cols]
    y_train = train_df.loc[t_mask, target_col]

    X_val = val_df.loc[v_mask, feature_cols]
    y_val = val_df.loc[v_mask, target_col]

    start_t = time.time()

    model = xgb.XGBRegressor(
        **params,
        early_stopping_rounds=early_stopping_rounds,
        eval_metric="mae",
        objective="reg:squarederror",
        random_state=42,
        n_jobs=-1,
    )

    model.fit(
        X_train,
        y_train,
        eval_set=[(X_val, y_val)],
        verbose=False,
    )

    duration = time.time() - start_t

    y_pred_val = model.predict(X_val)
    metrics = evaluate_predictions(y_val, y_pred_val)

    best_iter = getattr(model, "best_iteration", params.get("n_estimators", 2000))

    record = {
        "horizon": horizon,
        "feature_set": feature_set_name,
        "split_evaluated": "VALID",
        "max_depth": params["max_depth"],
        "learning_rate": params["learning_rate"],
        "n_estimators": params["n_estimators"],
        "best_iteration": int(best_iter) if best_iter is not None else params["n_estimators"],
        "min_child_weight": params.get("min_child_weight", 1),
        "subsample": params.get("subsample", 1.0),
        "colsample_bytree": params.get("colsample_bytree", 1.0),
        "reg_alpha": params.get("reg_alpha", 0.0),
        "reg_lambda": params.get("reg_lambda", 1.0),
        "gamma": params.get("gamma", 0.0),
        "MAE": metrics["MAE"],
        "RMSE": metrics["RMSE"],
        "R2": metrics["R2"],
        "bias": metrics["bias"],
        "MedAE": metrics["MedAE"],
        "duration_sec": round(duration, 2),
    }

    log_experiment(record)
    return record, model


def evaluate_on_test(
    horizon: str,
    feature_cols: List[str],
    best_params: Dict[str, Any],
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    feature_set_name: str,
) -> Dict[str, Any]:
    """
    Final evaluation on the untouched TEST set using the winning parameters
    and the optimal tree count (best_iteration) determined from validation.
    """
    target_col = TARGETS[horizon]

    t_mask = train_df[target_col].notna()
    v_mask = val_df[target_col].notna()
    test_mask = test_df[target_col].notna()

    X_train = train_df.loc[t_mask, feature_cols]
    y_train = train_df.loc[t_mask, target_col]

    X_val = val_df.loc[v_mask, feature_cols]
    y_val = val_df.loc[v_mask, target_col]

    X_test = test_df.loc[test_mask, feature_cols]
    y_test = test_df.loc[test_mask, target_col]

    # Train model on Train using early stopping on Val
    start_t = time.time()
    model = xgb.XGBRegressor(
        **best_params,
        early_stopping_rounds=50,
        eval_metric="mae",
        objective="reg:squarederror",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_val, y_val)],
        verbose=False,
    )
    duration = time.time() - start_t

    # Predict on untouched Test
    y_pred_test = model.predict(X_test)
    metrics = evaluate_predictions(y_test, y_pred_test)

    best_iter = getattr(model, "best_iteration", best_params.get("n_estimators", 2000))

    record = {
        "horizon": horizon,
        "feature_set": feature_set_name,
        "split_evaluated": "TEST",
        "max_depth": best_params["max_depth"],
        "learning_rate": best_params["learning_rate"],
        "n_estimators": best_params["n_estimators"],
        "best_iteration": int(best_iter) if best_iter is not None else best_params["n_estimators"],
        "min_child_weight": best_params.get("min_child_weight", 1),
        "subsample": best_params.get("subsample", 1.0),
        "colsample_bytree": best_params.get("colsample_bytree", 1.0),
        "reg_alpha": best_params.get("reg_alpha", 0.0),
        "reg_lambda": best_params.get("reg_lambda", 1.0),
        "gamma": best_params.get("gamma", 0.0),
        "MAE": metrics["MAE"],
        "RMSE": metrics["RMSE"],
        "R2": metrics["R2"],
        "bias": metrics["bias"],
        "MedAE": metrics["MedAE"],
        "duration_sec": round(duration, 2),
    }

    log_experiment(record)
    return record


def tune_horizon(
    horizon: str,
    feature_cols: List[str],
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """Execute complete 4-stage coordinate tuning for a single horizon."""
    feat_count = len(feature_cols)
    feature_set_name = f"locked_{horizon}_{feat_count}f"
    print("\n" + "=" * 75)
    print(f"STARTING TUNING FOR HORIZON: {horizon} ({feat_count} features)")
    print("=" * 75)

    # Initial baseline configuration (before tuning)
    base_params = {
        "max_depth": 5,
        "min_child_weight": 1,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_alpha": 0.0,
        "reg_lambda": 1.0,
        "gamma": 0.0,
        "n_estimators": 2000,
    }

    # Record baseline validation performance
    print("\n--- Baseline Reference (Default Parameters) ---")
    base_val_rec, _ = run_trial(
        horizon, feature_cols, base_params, train_df, val_df, feature_set_name
    )
    print(f"  Default Valid MAE: {base_val_rec['MAE']:.4f} (best_iter={base_val_rec['best_iteration']})")

    # Baseline test performance (for final untouched A/B comparison)
    base_test_rec = evaluate_on_test(
        horizon, feature_cols, base_params, train_df, val_df, test_df, f"{feature_set_name}_baseline_default"
    )
    print(f"  Default Test  MAE: {base_test_rec['MAE']:.4f} (R2={base_test_rec['R2']:.4f})")

    curr_best_params = dict(base_params)
    best_val_mae = base_val_rec["MAE"]

    # -------------------------------------------------------------
    # STAGE 1: Tree Structure (max_depth x min_child_weight)
    # -------------------------------------------------------------
    print("\n--- Stage 1: Tree Structure (max_depth x min_child_weight) ---")
    depths = [3, 4, 5, 6, 7, 8]
    child_weights = [1, 3, 5, 7, 10]

    for d in depths:
        for cw in child_weights:
            trial_params = dict(curr_best_params)
            trial_params["max_depth"] = d
            trial_params["min_child_weight"] = cw
            
            rec, _ = run_trial(horizon, feature_cols, trial_params, train_df, val_df, feature_set_name)
            is_new_best = rec["MAE"] < best_val_mae
            status = "★ NEW BEST" if is_new_best else ""
            print(f"  depth={d}, child_w={cw:2d} -> Valid MAE: {rec['MAE']:.4f} (iter={rec['best_iteration']:3d}) {status}")
            
            if is_new_best:
                best_val_mae = rec["MAE"]
                curr_best_params["max_depth"] = d
                curr_best_params["min_child_weight"] = cw

    print(f"  Stage 1 Winner: depth={curr_best_params['max_depth']}, child_w={curr_best_params['min_child_weight']} (MAE: {best_val_mae:.4f})")

    # -------------------------------------------------------------
    # STAGE 2: Stochastic Sampling (subsample x colsample_bytree)
    # -------------------------------------------------------------
    print("\n--- Stage 2: Stochastic Sampling (subsample x colsample_bytree) ---")
    subsamples = [0.7, 0.8, 0.9, 1.0]
    colsamples = [0.7, 0.8, 0.9, 1.0]

    for ss in subsamples:
        for cs in colsamples:
            if ss == curr_best_params["subsample"] and cs == curr_best_params["colsample_bytree"]:
                continue
            trial_params = dict(curr_best_params)
            trial_params["subsample"] = ss
            trial_params["colsample_bytree"] = cs

            rec, _ = run_trial(horizon, feature_cols, trial_params, train_df, val_df, feature_set_name)
            is_new_best = rec["MAE"] < best_val_mae
            status = "★ NEW BEST" if is_new_best else ""
            print(f"  subsample={ss:.1f}, colsample={cs:.1f} -> Valid MAE: {rec['MAE']:.4f} (iter={rec['best_iteration']:3d}) {status}")

            if is_new_best:
                best_val_mae = rec["MAE"]
                curr_best_params["subsample"] = ss
                curr_best_params["colsample_bytree"] = cs

    print(f"  Stage 2 Winner: subsample={curr_best_params['subsample']}, colsample={curr_best_params['colsample_bytree']} (MAE: {best_val_mae:.4f})")

    # -------------------------------------------------------------
    # STAGE 3: Regularization (reg_alpha, reg_lambda, gamma)
    # -------------------------------------------------------------
    print("\n--- Stage 3: Regularization (reg_alpha, reg_lambda, gamma) ---")
    alphas = [0.0, 0.1, 1.0, 5.0]
    lambdas = [1.0, 3.0, 10.0]

    for a in alphas:
        for l in lambdas:
            if a == curr_best_params["reg_alpha"] and l == curr_best_params["reg_lambda"]:
                continue
            trial_params = dict(curr_best_params)
            trial_params["reg_alpha"] = a
            trial_params["reg_lambda"] = l

            rec, _ = run_trial(horizon, feature_cols, trial_params, train_df, val_df, feature_set_name)
            is_new_best = rec["MAE"] < best_val_mae
            status = "★ NEW BEST" if is_new_best else ""
            print(f"  alpha={a:3.1f}, lambda={l:4.1f} -> Valid MAE: {rec['MAE']:.4f} (iter={rec['best_iteration']:3d}) {status}")

            if is_new_best:
                best_val_mae = rec["MAE"]
                curr_best_params["reg_alpha"] = a
                curr_best_params["reg_lambda"] = l

    gammas = [0.0, 0.1, 0.5, 1.0]
    for g in gammas:
        if g == curr_best_params["gamma"]:
            continue
        trial_params = dict(curr_best_params)
        trial_params["gamma"] = g

        rec, _ = run_trial(horizon, feature_cols, trial_params, train_df, val_df, feature_set_name)
        is_new_best = rec["MAE"] < best_val_mae
        status = "★ NEW BEST" if is_new_best else ""
        print(f"  gamma={g:3.1f} -> Valid MAE: {rec['MAE']:.4f} (iter={rec['best_iteration']:3d}) {status}")

        if is_new_best:
            best_val_mae = rec["MAE"]
            curr_best_params["gamma"] = g

    print(f"  Stage 3 Winner: alpha={curr_best_params['reg_alpha']}, lambda={curr_best_params['reg_lambda']}, gamma={curr_best_params['gamma']} (MAE: {best_val_mae:.4f})")

    # -------------------------------------------------------------
    # STAGE 4: Learning Rate Refinement
    # -------------------------------------------------------------
    print("\n--- Stage 4: Learning Rate Refinement ---")
    lrs = [0.02, 0.05, 0.08, 0.1]

    for lr in lrs:
        if lr == curr_best_params["learning_rate"]:
            continue
        trial_params = dict(curr_best_params)
        trial_params["learning_rate"] = lr

        rec, _ = run_trial(horizon, feature_cols, trial_params, train_df, val_df, feature_set_name)
        is_new_best = rec["MAE"] < best_val_mae
        status = "★ NEW BEST" if is_new_best else ""
        print(f"  lr={lr:.2f} -> Valid MAE: {rec['MAE']:.4f} (iter={rec['best_iteration']:3d}) {status}")

        if is_new_best:
            best_val_mae = rec["MAE"]
            curr_best_params["learning_rate"] = lr

    print(f"  Stage 4 Winner: lr={curr_best_params['learning_rate']} (MAE: {best_val_mae:.4f})")

    # -------------------------------------------------------------
    # FINAL UNTOUCHED TEST EVALUATION
    # -------------------------------------------------------------
    print(f"\n--- Final Evaluation on Untouched TEST Set for {horizon} ---")
    tuned_test_rec = evaluate_on_test(
        horizon, feature_cols, curr_best_params, train_df, val_df, test_df, f"{feature_set_name}_tuned_winner"
    )

    print(f"  Default Test MAE: {base_test_rec['MAE']:.4f} | R2: {base_test_rec['R2']:.4f}")
    print(f"  Tuned   Test MAE: {tuned_test_rec['MAE']:.4f} | R2: {tuned_test_rec['R2']:.4f}")
    mae_diff = base_test_rec['MAE'] - tuned_test_rec['MAE']
    mae_pct = (mae_diff / base_test_rec['MAE']) * 100
    print(f"  Out-of-sample MAE Improvement: {mae_pct:+.2f}% ({mae_diff:+.4f} µg/m³)")

    return curr_best_params, base_test_rec, tuned_test_rec


def main():
    init_experiments_csv()

    # Load canonical horizon feature definitions
    with open(HORIZON_METADATA_FILE, "r") as f:
        meta = json.load(f)
    horizon_features = meta["horizon_features"]

    train_df, val_df, test_df = load_and_split_data()

    all_winners = {}
    summary_comparisons = []

    for h in HORIZONS:
        feat_cols = horizon_features[h]
        best_p, base_test, tuned_test = tune_horizon(
            h, feat_cols, train_df, val_df, test_df
        )
        all_winners[h] = {
            "best_params": best_p,
            "baseline_test": base_test,
            "tuned_test": tuned_test,
        }

        summary_comparisons.append({
            "Horizon": h,
            "Features": len(feat_cols),
            "Default Test MAE": round(base_test["MAE"], 4),
            "Tuned Test MAE": round(tuned_test["MAE"], 4),
            "MAE Improvement (%)": round(((base_test["MAE"] - tuned_test["MAE"]) / base_test["MAE"]) * 100, 2),
            "Default Test RMSE": round(base_test["RMSE"], 4),
            "Tuned Test RMSE": round(tuned_test["RMSE"], 4),
            "Default Test R2": round(base_test["R2"], 4),
            "Tuned Test R2": round(tuned_test["R2"], 4),
            "Best Depth": best_p["max_depth"],
            "Best Min Child W": best_p["min_child_weight"],
            "Best Subsample": best_p["subsample"],
            "Best Colsample": best_p["colsample_bytree"],
            "Best Alpha": best_p["reg_alpha"],
            "Best Lambda": best_p["reg_lambda"],
            "Best Gamma": best_p["gamma"],
            "Best LR": best_p["learning_rate"],
        })

    # Save winners to JSON for persistence and subsequent model training
    winners_file = RESULTS_DIR / "tuned_hyperparameters.json"
    with open(winners_file, "w") as f:
        json.dump(all_winners, f, indent=2)
    print(f"\nTuned parameters saved to {winners_file}")

    print("\n" + "=" * 80)
    print("SUMMARY COMPARISON: DEFAULT vs TUNED ON UNTOUCHED TEST SET")
    print("=" * 80)
    summary_df = pd.DataFrame(summary_comparisons)
    print(summary_df.to_string(index=False))

    summary_df.to_csv(RESULTS_DIR / "tuning_summary.csv", index=False)
    print(f"\nSummary table saved to {RESULTS_DIR / 'tuning_summary.csv'}")
    print(f"All trial records logged to {EXPERIMENTS_CSV}")


if __name__ == "__main__":
    main()
