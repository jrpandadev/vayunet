import os
import json
import joblib
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.linear_model import LinearRegression
from sklearn.isotonic import IsotonicRegression

BASE_DIR = Path(__file__).resolve().parent.parent
S5_DATA_FILE = BASE_DIR / "data/processed/fusion/delhi_forecasting_s5_nwp.csv"
EPISODE_DATA_FILE = BASE_DIR / "data/processed/fusion/delhi_forecasting_episode.csv"
HORIZON_METADATA_FILE = BASE_DIR / "models/horizon_features.json"
MODELS_DIR = BASE_DIR / "models"
REPORT_DIR = BASE_DIR / "reports/extreme_pollution/s8_calibration"

HORIZONS = {"6h": 6, "24h": 24, "72h": 72}
TARGETS = {"6h": "target_pm25_6h", "24h": "target_pm25_24h", "72h": "target_pm25_72h"}
USE_EPISODE = {"6h": True, "24h": False, "72h": True}

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

def get_actual_regime(val):
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
        "MAE": mean_absolute_error(y_t, y_p),
        "RMSE": np.sqrt(mean_squared_error(y_t, y_p)),
        "R2": r2_score(y_t, y_p) if len(y_t) > 1 else np.nan,
        "Bias": np.mean(err),
        "MedAE": np.median(np.abs(err)),
        "Actual Mean": np.mean(y_t),
        "Pred Mean": np.mean(y_p),
        "Ratio": np.mean(y_p) / np.mean(y_t) if np.mean(y_t) > 0 else np.nan
    }

class PiecewiseLinearCalibration:
    def __init__(self):
        self.models = {}

    def get_regime(self, pred):
        if pred < 60: return 0
        elif pred < 150: return 1
        elif pred < 250: return 2
        else: return 3

    def fit(self, y_pred, y_true):
        regimes = np.array([self.get_regime(p) for p in y_pred])
        for r in range(4):
            idx = regimes == r
            if np.sum(idx) > 10:
                lr = LinearRegression()
                lr.fit(y_pred[idx].reshape(-1, 1), y_true[idx])
                self.models[r] = lr
            else:
                self.models[r] = None

    def predict(self, y_pred):
        y_cal = np.copy(y_pred)
        regimes = np.array([self.get_regime(p) for p in y_pred])
        for r in range(4):
            idx = regimes == r
            if np.sum(idx) > 0:
                if self.models.get(r) is not None:
                    y_cal[idx] = self.models[r].predict(y_pred[idx].reshape(-1, 1))
        return y_cal

def select_best_method(metrics_dict):
    methods = ["A", "B", "C", "D"]
    rmses = {m: metrics_dict[m]["RMSE"] for m in methods}
    min_rmse = min(rmses.values())

    threshold = 0.5
    for m in methods:
        if rmses[m] <= min_rmse + threshold:
            return m, rmses[m]

    return "A", rmses["A"]

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

    decision_summary = []

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

        valid = matched_df[(matched_df["Timestamp"] >= TRAIN_END) & (matched_df["Timestamp"] < VALID_END)]
        test = matched_df[(matched_df["Timestamp"] >= VALID_END) & (matched_df["Timestamp"] <= TEST_END)]

        X_valid, y_valid = valid[final_features], valid[target].to_numpy()
        X_test, y_test = test[final_features], test[target].to_numpy()

        model_path = MODELS_DIR / f"xgb_vayunet_pm25_{horizon}_{model_family}_production.joblib"
        model = joblib.load(model_path)

        y_val_pred_raw = model.predict(X_valid)
        y_test_pred_raw = model.predict(X_test)

        cals = {}
        cals["A"] = {"name": "No Calibration (Control)", "pred_val": y_val_pred_raw, "pred_test": y_test_pred_raw}

        lr = LinearRegression()
        lr.fit(y_val_pred_raw.reshape(-1, 1), y_valid)
        cals["B"] = {
            "name": "Global Linear Calibration",
            "pred_val": lr.predict(y_val_pred_raw.reshape(-1, 1)),
            "pred_test": lr.predict(y_test_pred_raw.reshape(-1, 1))
        }

        pl = PiecewiseLinearCalibration()
        pl.fit(y_val_pred_raw, y_valid)
        cals["C"] = {
            "name": "Piecewise Linear Calibration",
            "pred_val": pl.predict(y_val_pred_raw),
            "pred_test": pl.predict(y_test_pred_raw)
        }

        iso = IsotonicRegression(out_of_bounds='clip')
        iso.fit(y_val_pred_raw, y_valid)
        cals["D"] = {
            "name": "Isotonic Regression",
            "pred_val": iso.predict(y_val_pred_raw),
            "pred_test": iso.predict(y_test_pred_raw)
        }

        val_metrics = {k: get_metrics(y_valid, v["pred_val"]) for k, v in cals.items()}

        best_method, best_rmse = select_best_method(val_metrics)
        best_name = cals[best_method]["name"]

        improvement_vs_A = val_metrics["A"]["RMSE"] - val_metrics[best_method]["RMSE"]

        baseline_test = get_metrics(y_test, y_test_pred_raw)
        cal_test = get_metrics(y_test, cals[best_method]["pred_test"])

        regimes = np.array([get_actual_regime(y) for y in y_test])
        reg_labels = ["<60", "60-150", "150-250", ">=250"]

        out = []
        out.append(f"# S8-A Calibration Experiment: {horizon}")
        out.append("## Validation Results (Candidates)")
        out.append("| Method | MAE | RMSE | R² | Bias | MedAE |")
        out.append("| :--- | ---: | ---: | ---: | ---: | ---: |")
        for k in ["A", "B", "C", "D"]:
            m = val_metrics[k]
            bold = "**" if k == best_method else ""
            out.append(f"| {bold}{k} - {cals[k]['name']}{bold} | {m['MAE']:.3f} | {m['RMSE']:.3f} | {m['R2']:.3f} | {m['Bias']:+.3f} | {m['MedAE']:.3f} |")

        out.append(f"\n**Selected Method:** {best_method} ({best_name})")
        out.append(f"**Improvement over Control:** {improvement_vs_A:.3f} RMSE")

        decision = "KEEP"
        if improvement_vs_A < 0.5:
            decision = "REJECT / PROCEED TO SPECIALIST"

        decision_summary.append(f"- **{horizon}**: Selected {best_method}. Improvement = {improvement_vs_A:.3f}. Decision: **{decision}**")

        out.append(f"\n## Untouched Test Results (Baseline vs Calibrated)")
        out.append("| Metric | Baseline | Calibrated | Diff |")
        out.append("| :--- | ---: | ---: | ---: |")
        for metric in ["MAE", "RMSE", "R2", "Bias", "MedAE"]:
            diff = cal_test[metric] - baseline_test[metric]
            out.append(f"| {metric} | {baseline_test[metric]:.3f} | {cal_test[metric]:.3f} | {diff:+.3f} |")

        out.append("\n## Test Regime Evaluation (Calibrated)")
        out.append("| Regime | Count | MAE | RMSE | Bias | Actual Mean | Pred Mean | Ratio |")
        out.append("| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")

        for reg in reg_labels:
            idx = (regimes == reg)
            m = get_metrics(y_test[idx], cals[best_method]["pred_test"][idx])
            if m:
                out.append(f"| **{reg}** | {m['Count']:,} | {m['MAE']:.2f} | {m['RMSE']:.2f} | {m['Bias']:+.2f} | {m['Actual Mean']:.2f} | {m['Pred Mean']:.2f} | {m['Ratio']:.3f} |")

        with open(REPORT_DIR / f"s8a_{horizon}_report.md", "w") as f:
            f.write("\n".join(out))

    with open(REPORT_DIR / "s8a_final_decision.md", "w") as f:
        f.write("# S8-A Final Calibration Decision\n\n")
        f.write("\n".join(decision_summary))

    print(f"Calibration experiment completed. Check {REPORT_DIR}")

if __name__ == "__main__":
    main()
