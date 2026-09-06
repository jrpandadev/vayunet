"""
Test whether promising physics features add predictive value to the CURRENT LOCKED TUNED CHAMPION.

Compares:
1. Champion (locked tuned model from models/horizon_features.json)
2. Champion + Atmospheric Transport (ventilation_index, log_ventilation_index, wind_u, wind_v, stagnation_proxy)
3. Champion + Particle Composition (PM25_PM10_fraction)

Uses the exact tuned hyperparameters from ml/results/xgb_best_params.json and the exact
temporal split on the untouched test set.
"""

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

from physics_features import add_physics_features


# ============================================================
# Paths & Setup
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "processed" / "delhi_forecasting_weather.csv"
MODELS_DIR = BASE_DIR / "models"
REPORTS_DIR = BASE_DIR / "reports"
RESULTS_DIR = BASE_DIR / "ml" / "results"

HORIZON_METADATA_FILE = MODELS_DIR / "horizon_features.json"
BEST_PARAMS_FILE = RESULTS_DIR / "xgb_best_params.json"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# Configuration & Constants
# ============================================================

HORIZONS = ["6h", "24h", "72h"]

TARGET_COLUMNS = {
    "6h": "target_pm25_6h",
    "24h": "target_pm25_24h",
    "72h": "target_pm25_72h",
}

# Exact final temporal split
TRAIN_END = pd.Timestamp("2024-10-01 13:00:00")
VALID_END = pd.Timestamp("2025-08-30 15:00:00")
TEST_END = pd.Timestamp("2026-08-31 23:00:00")

PHYSICS_GROUPS = {
    "atmospheric_transport": [
        "ventilation_index",
        "log_ventilation_index",
        "wind_u",
        "wind_v",
        "stagnation_proxy",
    ],
    "particle_composition": [
        "PM25_PM10_fraction",
    ],
}

REGIMES = [
    ("<60", 0, 60),
    ("60-150", 60, 150),
    ("150-250", 150, 250),
    (">=250", 250, np.inf),
]


# ============================================================
# Metrics Helpers
# ============================================================

def calculate_metrics(y_true: pd.Series | np.ndarray, y_pred: np.ndarray) -> dict:
    y_true_np = np.asarray(y_true)
    y_pred_np = np.asarray(y_pred)
    errors = y_pred_np - y_true_np

    return {
        "MAE": float(mean_absolute_error(y_true_np, y_pred_np)),
        "RMSE": float(np.sqrt(mean_squared_error(y_true_np, y_pred_np))),
        "R2": float(r2_score(y_true_np, y_pred_np)),
        "Bias": float(np.mean(errors)),
        "MedAE": float(median_absolute_error(y_true_np, y_pred_np)),
    }


def calculate_regime_metrics(y_true: pd.Series | np.ndarray, y_pred: np.ndarray) -> dict:
    y = np.asarray(y_true)
    p = np.asarray(y_pred)

    output = {}
    for name, lo, hi in REGIMES:
        mask = (y >= lo) & (y < hi) if hi != np.inf else (y >= lo)
        count = int(mask.sum())
        if count == 0:
            output[name] = {"count": 0, "MAE": None, "RMSE": None, "Bias": None}
            continue

        errors = p[mask] - y[mask]
        output[name] = {
            "count": count,
            "MAE": float(np.mean(np.abs(errors))),
            "RMSE": float(np.sqrt(np.mean(errors ** 2))),
            "Bias": float(np.mean(errors)),
        }

    return output


# ============================================================
# Main Validation Pipeline
# ============================================================

def main():
    print("=" * 80)
    print("VayuNet - Physics Features vs Locked Tuned Champion Evaluation")
    print("=" * 80)

    # 1. Load horizon features schema (champion features)
    with open(HORIZON_METADATA_FILE, "r") as f:
        meta = json.load(f)
    champion_features = meta["horizon_features"]

    print("\nChampion Feature Counts:")
    for h in HORIZONS:
        print(f"  {h}: {len(champion_features[h])} features")

    # 2. Load tuned hyperparameter configurations
    with open(BEST_PARAMS_FILE, "r") as f:
        best_params_meta = json.load(f)

    # 3. Load dataset and generate physics features
    print(f"\nLoading dataset from {DATA_PATH}...")
    df = pd.read_csv(DATA_PATH, parse_dates=["timestamp"])
    df = df.sort_values(by="timestamp").reset_index(drop=True)

    print("Generating physics features...")
    df = add_physics_features(df, copy=False)

    print("One-hot encoding station_id...")
    df_encoded = pd.get_dummies(df, columns=["station_id"], dtype=int)

    # 4. Temporal Split
    # Champion models were trained on TRAIN+VALID (< 2025-08-30 15:00:00) with n_estimators=best_iter
    train_val_df = df_encoded[df_encoded["timestamp"] < VALID_END].copy()
    test_df = df_encoded[
        (df_encoded["timestamp"] >= VALID_END) & (df_encoded["timestamp"] <= TEST_END)
    ].copy()

    print("\nDataset Split Summary:")
    print(f"  Train+Valid: {len(train_val_df):,} samples (up to {VALID_END})")
    print(f"  Untouched Test: {len(test_df):,} samples ({VALID_END} to {TEST_END})")

    # 5. Run comparisons
    experiments = [
        ("Champion", []),
        ("Champion + atmospheric transport", PHYSICS_GROUPS["atmospheric_transport"]),
        ("Champion + particle composition", PHYSICS_GROUPS["particle_composition"]),
    ]

    all_results = []
    regime_results = []

    for h in HORIZONS:
        target = TARGET_COLUMNS[h]
        champ_feats = champion_features[h]
        tuned_cfg = best_params_meta[h]
        params = tuned_cfg["params"]
        best_iter = tuned_cfg["best_iteration"]

        print()
        print("=" * 80)
        print(f"EVALUATING HORIZON: {h.upper()} (Target: {target})")
        print(f"Tuned Hyperparameters: {params} | n_estimators: {best_iter}")
        print("=" * 80)

        t_mask = train_val_df[target].notna()
        test_mask = test_df[target].notna()

        y_train_val = train_val_df.loc[t_mask, target]
        y_test = test_df.loc[test_mask, target]

        champion_mae = None
        champion_rmse = None

        for exp_name, extra_cols in experiments:
            curr_features = champ_feats + extra_cols
            feature_count = len(curr_features)

            print(f"\nExperiment: {exp_name} ({feature_count} features)")

            if exp_name == "Champion":
                # Evaluate the existing locked champion model directly
                champ_model_path = MODELS_DIR / f"xgb_weather_pm25_{h}_tuned.joblib"
                if champ_model_path.exists():
                    print(f"  Loading existing champion model from {champ_model_path.name}...")
                    model = joblib.load(champ_model_path)
                else:
                    print("  Training champion model from scratch...")
                    model = xgb.XGBRegressor(
                        **params,
                        n_estimators=best_iter,
                        objective="reg:squarederror",
                        random_state=42,
                        n_jobs=-1,
                    )
                    model.fit(train_val_df.loc[t_mask, curr_features], y_train_val, verbose=False)
            else:
                # Train a new comparison model with the expanded feature set
                print(f"  Training new model with {len(extra_cols)} extra physics features...")
                X_train_val = train_val_df.loc[t_mask, curr_features]
                model = xgb.XGBRegressor(
                    **params,
                    n_estimators=best_iter,
                    objective="reg:squarederror",
                    random_state=42,
                    n_jobs=-1,
                )
                model.fit(X_train_val, y_train_val, verbose=False)

            # Predict on untouched test set
            X_test = test_df.loc[test_mask, curr_features]
            y_pred = model.predict(X_test)

            metrics = calculate_metrics(y_test, y_pred)
            regimes = calculate_regime_metrics(y_test, y_pred)

            if exp_name == "Champion":
                champion_mae = metrics["MAE"]
                champion_rmse = metrics["RMSE"]
                mae_imp = 0.0
                rmse_imp = 0.0
            else:
                mae_imp = ((champion_mae - metrics["MAE"]) / champion_mae) * 100.0
                rmse_imp = ((champion_rmse - metrics["RMSE"]) / champion_rmse) * 100.0

            print(
                f"  Test Metrics: MAE={metrics['MAE']:.2f}, RMSE={metrics['RMSE']:.2f}, "
                f"R2={metrics['R2']:.4f}, Bias={metrics['Bias']:.2f}, MedAE={metrics['MedAE']:.2f} | "
                f"MAE Imp={mae_imp:+.2f}%, RMSE Imp={rmse_imp:+.2f}%"
            )
            print(
                f"  Severe (>=250): N={regimes['>=250']['count']}, "
                f"MAE={regimes['>=250']['MAE']:.2f}, RMSE={regimes['>=250']['RMSE']:.2f}, "
                f"Bias={regimes['>=250']['Bias']:.2f}"
            )

            all_results.append({
                "horizon": h,
                "experiment": exp_name,
                "feature_count": feature_count,
                "MAE": metrics["MAE"],
                "RMSE": metrics["RMSE"],
                "R2": metrics["R2"],
                "Bias": metrics["Bias"],
                "MedAE": metrics["MedAE"],
                "MAE_improvement_pct": mae_imp,
                "RMSE_improvement_pct": rmse_imp,
            })

            regime_entry = {
                "horizon": h,
                "experiment": exp_name,
                "regimes": regimes,
            }
            regime_results.append(regime_entry)

    # 6. Summary DataFrame
    results_df = pd.DataFrame(all_results)

    # 7. Print Final Comparison Table
    print()
    print("=" * 115)
    print("PHYSICS CHAMPION COMPARISON (UNTOUCHED TEST SET)")
    print("=" * 115)

    headers = f"{'Horizon':<8} | {'Experiment':<35} | {'MAE':>7} | {'RMSE':>7} | {'R2':>7} | {'Bias':>7} | {'MedAE':>7} | {'MAE Imp%':>9} | {'RMSE Imp%':>10}"
    print(headers)
    print("-" * 115)

    for _, row in results_df.iterrows():
        line = (
            f"{row['horizon']:<8} | {row['experiment']:<35} | "
            f"{row['MAE']:7.2f} | {row['RMSE']:7.2f} | {row['R2']:7.4f} | "
            f"{row['Bias']:7.2f} | {row['MedAE']:7.2f} | "
            f"{row['MAE_improvement_pct']:+8.2f}% | {row['RMSE_improvement_pct']:+9.2f}%"
        )
        print(line)

    print("=" * 115)

    # 8. Print Regime Breakdown Table (especially >= 250)
    print("\n" + "=" * 105)
    print("POLLUTION REGIME BREAKDOWN (MAE / RMSE / Bias)")
    print("=" * 105)
    print(f"{'Horizon':<8} | {'Experiment':<35} | {'Regime':<10} | {'Count':>7} | {'MAE':>8} | {'RMSE':>8} | {'Bias':>8}")
    print("-" * 105)

    for entry in regime_results:
        h = entry["horizon"]
        exp = entry["experiment"]
        for r_name in ["<60", "60-150", "150-250", ">=250"]:
            r_data = entry["regimes"][r_name]
            print(
                f"{h:<8} | {exp:<35} | {r_name:<10} | {r_data['count']:>7d} | "
                f"{r_data['MAE']:8.2f} | {r_data['RMSE']:8.2f} | {r_data['Bias']:8.2f}"
            )
        print("-" * 105)

    # 9. Determine and State Best Experiment for Each Horizon
    print("\n" + "=" * 80)
    print("BEST EXPERIMENT BY HORIZON (MAE on Untouched Test Set)")
    print("=" * 80)

    for h in HORIZONS:
        subset = results_df[results_df["horizon"] == h].copy()
        best_row = subset.loc[subset["MAE"].idxmin()]
        champ_row = subset[subset["experiment"] == "Champion"].iloc[0]

        diff_mae = champ_row["MAE"] - best_row["MAE"]
        pct_imp = best_row["MAE_improvement_pct"]

        print(f"\n{h.upper()} Horizon:")
        print(f"  Current Champion MAE: {champ_row['MAE']:.2f} (RMSE: {champ_row['RMSE']:.2f})")
        print(f"  Best Experiment     : {best_row['experiment']}")
        print(f"  Best Result MAE     : {best_row['MAE']:.2f} (RMSE: {best_row['RMSE']:.2f})")
        print(f"  Improvement         : {diff_mae:+.2f} µg/m³ ({pct_imp:+.2f}%)")

        if best_row["experiment"] == "Champion":
            print("  Conclusion          : Physics features did NOT improve upon the current champion.")
        elif pct_imp < 0.5:
            print("  Conclusion          : Marginally lower MAE (< 0.5%), but does not warrant model expansion.")
        else:
            print("  Conclusion          : Meaningful improvement observed.")

    print("\nNOTE: No models have been promoted to champion automatically.")
    print("Existing champion models and configuration remain completely untouched.")

    # 10. Save Outputs
    csv_path = REPORTS_DIR / "physics_champion_comparison.csv"
    results_df.to_csv(csv_path, index=False)
    print(f"\nSaved comparison summary to: {csv_path}")

    json_path = REPORTS_DIR / "physics_champion_comparison.json"
    full_report = {
        "experiment": "physics_vs_champion_validation",
        "split": {
            "train_end": str(TRAIN_END),
            "validation_end": str(VALID_END),
            "test_end": str(TEST_END),
        },
        "results": all_results,
        "regime_results": regime_results,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(full_report, f, indent=2)
    print(f"Saved detailed JSON report to: {json_path}")
    print("\nValidation completed successfully.")


if __name__ == "__main__":
    main()
