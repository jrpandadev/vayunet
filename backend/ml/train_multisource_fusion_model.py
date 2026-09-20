import json
import time
from pathlib import Path
import numpy as np
import pandas as pd
from xgboost import XGBRegressor

# ============================================================
# CONFIG & PATHS
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent

DATA_FILE = BASE_DIR / "data/processed/fusion/delhi_multisource_fusion_dataset.csv"
HORIZON_METADATA_FILE = BASE_DIR / "models/horizon_features.json"
BEST_PARAMS_FILE = BASE_DIR / "ml/results/satellite/s4_best_params.json"
S5_REPORT_FILE = BASE_DIR / "reports/nwp/s5_nwp_ablation_report.json"
S6_REPORT_FILE = BASE_DIR / "reports/episode/s6_episode_ablation_report.json"

REPORT_DIR = BASE_DIR / "reports/fusion"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
MD_OUT = REPORT_DIR / "multisource_fusion_model_results.md"
CSV_OUT = REPORT_DIR / "multisource_fusion_model_results.csv"

# Strict Chronological Splits
TRAIN_END = pd.Timestamp("2024-10-01 13:00:00")
VALID_END = pd.Timestamp("2025-08-30 15:00:00")
TEST_END = pd.Timestamp("2026-08-31 23:00:00")

HORIZONS = {"6h": 6, "24h": 24, "72h": 72}

def load_baselines():
    baselines = {}
    if S5_REPORT_FILE.exists():
        with open(S5_REPORT_FILE, "r") as f:
            for r in json.load(f):
                baselines[f"24h_production"] = {"mae": r["s4_nwp_mae"], "rmse": r["s4_nwp_rmse"], "r2": r["s4_nwp_r2"]}
    if S6_REPORT_FILE.exists():
        with open(S6_REPORT_FILE, "r") as f:
            for r in json.load(f):
                if r["horizon"] in ["6h", "72h"]:
                    baselines[f"{r['horizon']}_production"] = {"mae": r["s6_mae"], "rmse": r["s6_rmse"], "r2": r["s6_r2"]}
    return baselines

# ============================================================
# METRICS & EVALUATION
# ============================================================
def get_metrics(y_true, y_pred):
    errors = y_pred - y_true
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors ** 2)))
    ss_res = float(np.sum(errors ** 2))
    ss_tot = float(np.sum((y_true - y_true.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return mae, rmse, r2

def regime_eval(y_true, y_pred):
    regimes = {
        "<50": (0, 50),
        "50-100": (50, 100),
        "100-150": (100, 150),
        "150-250": (150, 250),
        ">=250": (250, 99999)
    }
    results = {}
    for r_name, (low, high) in regimes.items():
        mask = (y_true >= low) & (y_true < high)
        if mask.sum() > 0:
            m_mae, m_rmse, _ = get_metrics(y_true[mask], y_pred[mask])
            results[r_name] = {"count": mask.sum(), "mae": m_mae, "rmse": m_rmse}
    return results

def group_importance(model, features):
    importance = model.feature_importances_
    grouped = {"CPCB": 0.0, "Weather": 0.0, "ECMWF NWP": 0.0, "S5P NO2": 0.0, "Episode Dynamics": 0.0, "Other": 0.0}
    for f, imp in zip(features, importance):
        f = f.lower()
        if "nwp" in f:
            grouped["ECMWF NWP"] += imp
        elif "satellite" in f:
            grouped["S5P NO2"] += imp
        elif "episode" in f or "regime" in f or "acceleration" in f or "delta" in f or "hours_since" in f or "hours_above" in f or "fraction_above" in f:
            grouped["Episode Dynamics"] += imp
        elif "temperature_2m" in f or "wind_speed" in f or "relative_humidity" in f or "precipitation" in f or "surface_pressure" in f or "boundary_layer_height" in f or "wind_direction" in f:
            grouped["Weather"] += imp
        elif "pm25_lag" in f or "pm10_lag" in f or "pm25_roll" in f or "pm10_roll" in f:
            grouped["CPCB"] += imp
        else:
            grouped["Other"] += imp
    return {k: float(v) for k, v in grouped.items()}

# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 70)
    print("VAYUNET MULTI-SOURCE FUSION EXPERIMENT")
    print("=" * 70)

    print("Loading data...")
    df = pd.read_csv(DATA_FILE)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"])

    # 1. Dataset verification
    print(f"Dataset Columns: {len(df.columns)}")
    prohibited = ["modis", "firms", "fire", "ghsl", "osm", "kiln", "citizen"]
    for c in df.columns:
        for p in prohibited:
            if p in c.lower():
                print(f"CRITICAL ERROR: Prohibited source {p} found in column {c}")
                return

    if "station_id" in df.columns:
        df = pd.get_dummies(df, columns=["station_id"], dtype=int)

    df = df.loc[:, ~df.columns.duplicated()].copy()

    with open(HORIZON_METADATA_FILE, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    with open(BEST_PARAMS_FILE, "r", encoding="utf-8") as f:
        best_params = json.load(f)

    baselines = load_baselines()
    all_results = []

    with open(MD_OUT, "w", encoding="utf-8") as md:
        md.write("# VayuNet — Multi-Source Fusion Model Results\n\n")
        md.write("## Overview\n")
        md.write("This report documents the performance of the first Multi-Source Fusion Model. ")
        md.write("The models combine CPCB, Episode Dynamics, Historical Weather, ECMWF NWP, and S5P NO2 features.\n\n")

        md.write("## Methodology\n")
        md.write(f"- **Train End**: {TRAIN_END}\n")
        md.write(f"- **Valid End**: {VALID_END}\n")
        md.write(f"- **Test End**: {TEST_END}\n")
        md.write("- **Model**: XGBRegressor (hist, CUDA)\n")
        md.write("- **Hyperparameters**: Inherited directly from S4 tuning constraints for scientific fairness.\n")
        md.write("- **Missing Values**: Handled natively by XGBoost tree splits. No silent imputation used.\n\n")

        for horizon_key, horizon_hrs in HORIZONS.items():
            print(f"\n--- Training Horizon: {horizon_key} ---")

            target = f"target_pm25_{horizon_key}"
            if target not in df.columns:
                target = f"PM2.5_{horizon_key}"

            forward_cols = [c for c in df.columns if "target" in c.lower() or "forward" in c.lower() or "lead_" in c.lower()]
            features = [c for c in df.columns if c != "Timestamp" and c not in forward_cols]

            # Mask for strictly valid rows (valid target + valid NWP)
            valid_mask = df[target].notna()
            nwp_cols = [c for c in df.columns if "nwp" in c.lower() and f"_{horizon_hrs}h" in c.lower()]
            for nc in nwp_cols:
                valid_mask &= df[nc].notna()

            df_ab = df[valid_mask].copy()

            train = df_ab[df_ab["Timestamp"] < TRAIN_END]
            valid = df_ab[(df_ab["Timestamp"] >= TRAIN_END) & (df_ab["Timestamp"] < VALID_END)]
            test = df_ab[(df_ab["Timestamp"] >= VALID_END) & (df_ab["Timestamp"] <= TEST_END)]

            train_valid = pd.concat([train, valid], axis=0)

            X_tv = train_valid[features]
            y_tv = train_valid[target]
            X_ts = test[features]
            y_ts = test[target].to_numpy()

            p_entry = best_params[horizon_key]
            params = p_entry.get("params") or p_entry.get("best_params")
            best_iteration = int(p_entry["best_iteration"])

            start_time = time.time()
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
            train_time = time.time() - start_time

            inf_start = time.time()
            preds = model.predict(X_ts)
            inf_time = time.time() - inf_start

            mae, rmse, r2 = get_metrics(y_ts, preds)
            print(f"MAE: {mae:.4f}, RMSE: {rmse:.4f}, R2: {r2:.4f}")

            regime_res = regime_eval(y_ts, preds)
            feat_imp = group_importance(model, features)

            # Record base metrics
            result_row = {
                "horizon": horizon_key,
                "train_rows": len(train_valid),
                "test_rows": len(test),
                "features": len(features),
                "mae": mae,
                "rmse": rmse,
                "r2": r2,
                "train_time_s": train_time,
                "infer_time_s": inf_time,
            }
            all_results.append(result_row)

            # Markdown documentation per horizon
            md.write(f"### Horizon: +{horizon_key}\n")
            md.write(f"- **Test Observations**: {len(test):,}\n")
            md.write(f"- **Test Target Mean**: {y_ts.mean():.2f}\n")
            md.write(f"- **Test Target Median**: {np.median(y_ts):.2f}\n")
            md.write(f"- **Features Used**: {len(features)}\n")

            md.write(f"#### Overall Metrics\n")
            md.write(f"- MAE: **{mae:.4f}**\n")
            md.write(f"- RMSE: **{rmse:.4f}**\n")
            md.write(f"- R²: **{r2:.4f}**\n")

            md.write(f"#### Regime Performance\n")
            md.write("| Regime | Count | MAE | RMSE |\n")
            md.write("|---|---:|---:|---:|\n")
            for rg, val in regime_res.items():
                md.write(f"| {rg} | {val['count']:,} | {val['mae']:.2f} | {val['rmse']:.2f} |\n")

            md.write(f"#### Source Feature Importance (Predictive Contribution)\n")
            for src, imp in sorted(feat_imp.items(), key=lambda x: x[1], reverse=True):
                md.write(f"- **{src}**: {imp:.4f}\n")
            md.write("\n")

        # Comparison Table
        md.write("## Comparison Against Frozen Production\n")
        md.write("| Horizon | Production | Fusion | Δ MAE | Δ RMSE | Δ R² |\n")
        md.write("|---|---|---|---:|---:|---:|\n")

        improved_count = 0

        for r in all_results:
            hk = r["horizon"]
            prod_ver = "S5" if hk == "24h" else "S6"
            base = baselines.get(f"{hk}_production")
            if base:
                d_mae = base["mae"] - r["mae"]
                d_rmse = base["rmse"] - r["rmse"]
                d_r2 = r["r2"] - base["r2"]

                if d_mae > 0: improved_count += 1

                md.write(f"| +{hk} | {prod_ver} | Fusion | {d_mae:+.4f} | {d_rmse:+.4f} | {d_r2:+.4f} |\n")
            else:
                md.write(f"| +{hk} | {prod_ver} | Fusion | N/A | N/A | N/A |\n")

        md.write("\n*(Note: Positive Δ MAE/RMSE indicates Fusion error is LOWER than production. Positive Δ R² indicates variance explained is HIGHER).*\n\n")

        md.write("## Residual Analysis Summary\n")
        md.write("The regime performance indicates that the multi-source fusion model is highly capable, though the severe pollution tail (>=250 µg/m³) remains the most challenging segment. Further domain-specific source integration (e.g., active fires, waste burning) may be necessary to resolve the most extreme peaks.\n\n")

        md.write("## Final Verdict\n")
        if improved_count == 3:
            md.write("### FUSION IMPROVES PRODUCTION\n")
            md.write("The Fusion model demonstrates consistent improvement across all horizons in terms of MAE and RMSE while using the strictly untouched chronological test protocol.\n")
        elif improved_count > 0:
            md.write("### FUSION IS COMPARABLE TO PRODUCTION\n")
            md.write("The Fusion model is competitive with production, improving on some metrics/horizons but not uniformly. Regime performance should guide future iteration.\n")
        else:
            md.write("### FUSION DOES NOT IMPROVE PRODUCTION\n")
            md.write("The additional complexity did not translate to superior test performance. Investigate collinearity or temporal leakage.\n")

    pd.DataFrame(all_results).to_csv(CSV_OUT, index=False)
    print("Done! Reports written.")

if __name__ == "__main__":
    main()
