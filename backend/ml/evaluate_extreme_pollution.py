import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path
from sklearn.metrics import mean_absolute_error, mean_squared_error, precision_score, recall_score, f1_score

def get_regime(val):
    if val < 60:
        return "<60"
    elif val < 150:
        return "60-150"
    elif val < 250:
        return "150-250"
    else:
        return ">=250"

def evaluate_predictions(y_true, y_pred):
    err = y_pred - y_true
    return {
        "N": len(y_true),
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "Bias": float(np.mean(err)),
    }

def process_horizon(horizon, base_dir):
    # ----------------------------------------------------
    # Paths & Configurations
    # ----------------------------------------------------
    data_dir = base_dir / "data" / "processed"
    models_dir = base_dir / "models"

    s0_data_path = data_dir / "delhi_forecasting_weather.csv"
    s3_data_path = data_dir / "fusion" / "delhi_forecasting_satellite.csv"
    s4_data_path = data_dir / "fusion" / "delhi_forecasting_satellite_pm10.csv"

    with open(models_dir / "horizon_features.json", "r") as f:
        canonical_features = json.load(f)["horizon_features"][horizon]

    s3_features = canonical_features + ["satellite_no2_latest", "satellite_no2_age_hours"]
    s4_features = s3_features + [
        "PM10_lag_1h", "PM10_lag_3h", "PM10_lag_6h", "PM10_lag_12h", "PM10_lag_24h",
        "PM10_lag_48h", "PM10_lag_72h", "PM10_roll_mean_6h", "PM10_roll_mean_24h", "PM10_roll_std_24h"
    ]

    s0_model_path = models_dir / f"xgb_weather_pm25_{horizon}_tuned.joblib"
    s3_model_path = models_dir / f"xgb_satellite_pm25_{horizon}_tuned.joblib"
    s4_model_path = models_dir / f"xgb_satellite_pm10_{horizon}_tuned.joblib"

    # ----------------------------------------------------
    # Load Models
    # ----------------------------------------------------
    s0_model = joblib.load(s0_model_path)
    s3_model = joblib.load(s3_model_path)
    s4_model = joblib.load(s4_model_path)

    # ----------------------------------------------------
    # Load Datasets (Test split only)
    # ----------------------------------------------------
    val_end = pd.to_datetime("2025-08-30 15:00:00")
    test_end = pd.to_datetime("2026-08-31 23:00:00")
    target = f"target_pm25_{horizon}"

    def load_test_set(path, features):
        df = pd.read_csv(path, parse_dates=["timestamp"])
        if "timestamp" in df.columns and "Timestamp" not in df.columns:
            df.rename(columns={"timestamp": "Timestamp"}, inplace=True)
        df = df.sort_values(by="Timestamp").reset_index(drop=True)
        if "station_id" in df.columns:
            df = pd.get_dummies(df, columns=["station_id"], dtype=int)
        df = df.loc[:, ~df.columns.duplicated()].copy()

        test_df = df[(df["Timestamp"] >= val_end) & (df["Timestamp"] <= test_end)].copy()
        test_mask = test_df[target].notna()
        X_test = test_df.loc[test_mask, features]
        y_test = test_df.loc[test_mask, target]
        return X_test, y_test

    s0_X, s0_y = load_test_set(s0_data_path, canonical_features)
    s3_X, s3_y = load_test_set(s3_data_path, s3_features)
    s4_X, s4_y = load_test_set(s4_data_path, s4_features)

    # Generate predictions
    s0_pred = s0_model.predict(s0_X)
    s3_pred = s3_model.predict(s3_X)
    s4_pred = s4_model.predict(s4_X)

    df_eval = pd.DataFrame({
        "y_true": s0_y.values,
        "S0_pred": s0_pred,
        "S3_pred": s3_pred,
        "S4_pred": s4_pred
    })

    df_eval["Regime"] = df_eval["y_true"].apply(get_regime)

    results = []
    regimes = ["<60", "60-150", "150-250", ">=250"]
    for reg in regimes:
        sub = df_eval[df_eval["Regime"] == reg]
        for model_name in ["S0", "S3", "S4"]:
            if len(sub) == 0:
                continue
            metrics = evaluate_predictions(sub["y_true"], sub[f"{model_name}_pred"])
            results.append({
                "Horizon": horizon,
                "Regime": reg,
                "Model": model_name,
                "N": metrics["N"],
                "MAE": metrics["MAE"],
                "RMSE": metrics["RMSE"],
                "Bias": metrics["Bias"]
            })

    # Binary Classification (>= 150)
    binary_results = []
    y_true_binary = (df_eval["y_true"] >= 150).astype(int)
    for model_name in ["S0", "S3", "S4"]:
        y_pred_binary = (df_eval[f"{model_name}_pred"] >= 150).astype(int)
        binary_results.append({
            "Horizon": horizon,
            "Model": model_name,
            "Precision": float(precision_score(y_true_binary, y_pred_binary, zero_division=0)),
            "Recall": float(recall_score(y_true_binary, y_pred_binary, zero_division=0)),
            "F1": float(f1_score(y_true_binary, y_pred_binary, zero_division=0))
        })

    return results, binary_results

def main():
    base_dir = Path(__file__).resolve().parent.parent

    all_results = []
    all_binary_results = []

    for horizon in ["6h", "24h", "72h"]:
        res, bin_res = process_horizon(horizon, base_dir)
        all_results.extend(res)
        all_binary_results.extend(bin_res)

    df_res = pd.DataFrame(all_results)
    df_bin = pd.DataFrame(all_binary_results)

    reports_dir = base_dir / "reports" / "satellite"
    reports_dir.mkdir(parents=True, exist_ok=True)

    df_res.to_csv(reports_dir / "extreme_pollution_comparison.csv", index=False)

    # ----------------------------------------------------
    # Print Summary
    # ----------------------------------------------------
    summary = []
    summary.append("==============================================================")
    summary.append("EXTREME POLLUTION EVALUATION")
    summary.append("==============================================================\n")

    for horizon in ["6h", "24h", "72h"]:
        summary.append(horizon)
        summary.append(f"{'Regime':<12} {'Model':<8} {'N':<8} {'MAE':<10} {'RMSE':<10} {'Bias':<10}")
        sub_res = df_res[df_res["Horizon"] == horizon]

        for reg in ["<60", "60-150", "150-250", ">=250"]:
            sub_reg = sub_res[sub_res["Regime"] == reg]
            for i, row in sub_reg.iterrows():
                if i == sub_reg.index[0]:
                    reg_str = reg
                else:
                    reg_str = ""
                summary.append(f"{reg_str:<12} {row['Model']:<8} {row['N']:<8} {row['MAE']:<10.4f} {row['RMSE']:<10.4f} {row['Bias']:<10.4f}")
            if not sub_reg.empty:
                summary.append("")

    summary.append("==============================================================")
    summary.append(">=150 EVENT CLASSIFICATION")
    summary.append("==============================================================\n")

    summary.append(f"{'Horizon':<12} {'Model':<8} {'Precision':<12} {'Recall':<10} {'F1':<10}")
    for horizon in ["6h", "24h", "72h"]:
        sub_bin = df_bin[df_bin["Horizon"] == horizon]
        for i, row in sub_bin.iterrows():
            if i == sub_bin.index[0]:
                hor_str = horizon
            else:
                hor_str = ""
            summary.append(f"{hor_str:<12} {row['Model']:<8} {row['Precision']:<12.4f} {row['Recall']:<10.4f} {row['F1']:<10.4f}")
        summary.append("")

    summary_text = "\n".join(summary)

    with open(reports_dir / "extreme_pollution_summary.csv", "w") as f:
        f.write(summary_text)

    print(summary_text)

if __name__ == "__main__":
    main()
