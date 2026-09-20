import json
import joblib
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error

BASE_DIR = Path(__file__).resolve().parent.parent
S5_DATA_FILE = BASE_DIR / "data/processed/fusion/delhi_forecasting_s5_nwp.csv"
EPISODE_DATA_FILE = BASE_DIR / "data/processed/fusion/delhi_forecasting_episode.csv"
HORIZON_METADATA_FILE = BASE_DIR / "models/horizon_features.json"
MODELS_DIR = BASE_DIR / "models"
REPORT_DIR = BASE_DIR / "reports/extreme_pollution"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = REPORT_DIR / "production_tail_audit.md"

HORIZONS = {"6h": 6, "24h": 24, "72h": 72}
TARGETS = {"6h": "target_pm25_6h", "24h": "target_pm25_24h", "72h": "target_pm25_72h"}
USE_EPISODE = {"6h": True, "24h": False, "72h": True}

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

def get_regime(val):
    if val < 60: return "<60"
    elif val < 150: return "60-150"
    elif val < 250: return "150-250"
    else: return ">=250"

def get_metrics(y_t, y_p):
    if len(y_t) == 0:
        return None
    err = y_p - y_t
    return {
        "Count": len(y_t),
        "Actual Mean": np.mean(y_t),
        "Pred Mean": np.mean(y_p),
        "MAE": mean_absolute_error(y_t, y_p),
        "RMSE": np.sqrt(mean_squared_error(y_t, y_p)),
        "Bias": np.mean(err),
        "MedAE": np.median(np.abs(err)),
        "Ratio": np.mean(y_p) / np.mean(y_t) if np.mean(y_t) > 0 else np.nan
    }

def main():
    s5_df = pd.read_csv(S5_DATA_FILE, parse_dates=["timestamp"])
    ep_df = pd.read_csv(EPISODE_DATA_FILE, usecols=EPISODE_FEATURES)
    df = pd.concat([s5_df, ep_df], axis=1)
    df = df.rename(columns={"timestamp": "Timestamp"}).sort_values("Timestamp").reset_index(drop=True)
    if "station_id" in df.columns:
        df = pd.get_dummies(df, columns=["station_id"], dtype=int)
    df = df.loc[:, ~df.columns.duplicated()].copy()

    with open(HORIZON_METADATA_FILE, "r") as f:
        metadata = json.load(f)

    out = []
    out.append("# VayuNet Production Models: Extreme Pollution Tail Audit\n")

    for horizon, horizon_hours in HORIZONS.items():
        use_episode = USE_EPISODE[horizon]
        target = TARGETS[horizon]
        model_family = "s6" if use_episode else "s5"

        canonical_features = metadata["horizon_features"][horizon]
        nwp_features = [f"nwp_{v}_{horizon_hours}h" for v in NWP_BASE_VARS]
        final_features = list(dict.fromkeys(canonical_features + SATELLITE_FEATURES + PM10_FEATURES + nwp_features + (EPISODE_FEATURES if use_episode else [])))

        matched_mask = df[target].notna()
        for f in nwp_features:
            matched_mask &= df[f].notna()

        matched_df = df[matched_mask].copy()
        test = matched_df[(matched_df["Timestamp"] >= VALID_END) & (matched_df["Timestamp"] <= TEST_END)]

        X_test = test[final_features]
        y_test = test[target].to_numpy()

        model_path = MODELS_DIR / f"xgb_vayunet_pm25_{horizon}_{model_family}_production.joblib"
        model = joblib.load(model_path)

        y_pred = model.predict(X_test)

        regimes = np.array([get_regime(y) for y in y_test])
        regime_labels = ["<60", "60-150", "150-250", ">=250"]

        out.append(f"## Horizon: {horizon} (Model: {model_family.upper()})")
        out.append("| Regime | Count | Actual Mean | Pred Mean | MAE | RMSE | Bias | MedAE | Ratio (Pred/Actual) |")
        out.append("| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")

        for reg in regime_labels:
            idx = (regimes == reg)
            m = get_metrics(y_test[idx], y_pred[idx])
            if m:
                out.append(f"| **{reg}** | {m['Count']:,} | {m['Actual Mean']:.2f} | {m['Pred Mean']:.2f} | {m['MAE']:.2f} | {m['RMSE']:.2f} | {m['Bias']:+.2f} | {m['MedAE']:.2f} | {m['Ratio']:.3f} |")

        # Overall
        m = get_metrics(y_test, y_pred)
        out.append(f"| **OVERALL** | {m['Count']:,} | {m['Actual Mean']:.2f} | {m['Pred Mean']:.2f} | {m['MAE']:.2f} | {m['RMSE']:.2f} | {m['Bias']:+.2f} | {m['MedAE']:.2f} | {m['Ratio']:.3f} |\n")

    with open(OUT_FILE, "w") as f:
        f.write("\n".join(out))

    print(f"Audit completed. Report saved to {OUT_FILE}")
    print("\n" + "\n".join(out))

if __name__ == "__main__":
    main()
