import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from xgboost import XGBRegressor


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

def resolve_path(rel_str: str) -> Path:
    p = Path(rel_str)
    if p.exists():
        return p
    if (Path("backend") / rel_str).exists():
        return Path("backend") / rel_str
    if (BASE_DIR / rel_str).exists():
        return BASE_DIR / rel_str
    return p

DATA_FILE = resolve_path("data/processed/fusion/delhi_forecasting_s5_nwp.csv")
HORIZON_METADATA_FILE = resolve_path("models/horizon_features.json")
BEST_PARAMS_FILE = resolve_path("ml/results/satellite/s4_best_params.json")

REPORT_DIR = BASE_DIR / "reports/nwp"
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

# ============================================================
# LOAD DATA
# ============================================================

print("=" * 70)
print("S5 NWP ABLATION EXPERIMENT")
print("=" * 70)

df = pd.read_csv(DATA_FILE, parse_dates=["timestamp"])
df = df.rename(columns={"timestamp": "Timestamp"})
df = df.sort_values("Timestamp").reset_index(drop=True)

if "station_id" in df.columns:
    df = pd.get_dummies(df, columns=["station_id"], dtype=int)

df = df.loc[:, ~df.columns.duplicated()].copy()

# ============================================================
# LOAD METADATA
# ============================================================

with open(HORIZON_METADATA_FILE, "r", encoding="utf-8") as f:
    metadata = json.load(f)

with open(BEST_PARAMS_FILE, "r", encoding="utf-8") as f:
    best_params = json.load(f)

# ============================================================
# TRAIN EACH HORIZON
# ============================================================

results = []

def get_metrics(y_true, y_pred):
    errors = y_pred - y_true
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors ** 2)))
    ss_res = float(np.sum(errors ** 2))
    ss_tot = float(np.sum((y_true - y_true.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return mae, rmse, r2

for horizon_key, horizon_hrs in HORIZONS.items():
    print("\n" + "=" * 70)
    print(f"ABLATION — {horizon_key}")
    print("=" * 70)

    target = f"target_pm25_{horizon_key}"
    if target not in df.columns:
        target = f"PM2.5_{horizon_key}"

    # Features
    canonical_features = metadata["horizon_features"][horizon_key]
    s4_features = canonical_features + SATELLITE_FEATURES + PM10_FEATURES
    nwp_features = [f"nwp_{v}_{horizon_hrs}h" for v in NWP_BASE_VARS]
    all_features = s4_features + nwp_features

    # Mask: we must ensure rows have valid target AND no missing NWP features
    # so that we evaluate on the exact same rows for control vs treatment.
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

    # Combine Train + Valid for final fit (as in S4)
    train_valid = pd.concat([train, valid], axis=0)

    # Parameters
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
            random_state=42,
            n_jobs=-1,
        )
        model.fit(X_tv, y_tv)
        preds = model.predict(X_ts)
        mae, rmse, r2 = get_metrics(y_ts, preds)

        print(f"  [{name}] MAE: {mae:.4f} | RMSE: {rmse:.4f} | R²: {r2:.4f}")
        return mae, rmse, r2

    print("\nTraining Control (S4 Features)...")
    mae_c, rmse_c, r2_c = train_and_eval(s4_features, "Control (S4)")

    print("\nTraining Treatment (S4 + NWP Features)...")
    mae_t, rmse_t, r2_t = train_and_eval(all_features, "Treatment (S4+NWP)")

    results.append({
        "horizon": horizon_key,
        "test_rows": len(test),
        "s4_mae": mae_c,
        "s4_rmse": rmse_c,
        "s4_r2": r2_c,
        "s4_nwp_mae": mae_t,
        "s4_nwp_rmse": rmse_t,
        "s4_nwp_r2": r2_t,
        "mae_improvement": mae_c - mae_t,
        "rmse_improvement": rmse_c - rmse_t
    })

# ============================================================
# SAVE SUMMARY
# ============================================================

results_df = pd.DataFrame(results)
summary_path = REPORT_DIR / "s5_nwp_ablation_report.json"

results_df.to_json(summary_path, orient="records", indent=2)

print("\n" + "=" * 70)
print("S5 NWP ABLATION EXPERIMENT COMPLETE")
print("=" * 70)
print(results_df.to_string(index=False))
print(f"\nSaved summary: {summary_path}")
