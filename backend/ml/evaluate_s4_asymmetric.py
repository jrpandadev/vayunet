import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path
from sklearn.metrics import mean_absolute_error, mean_squared_error, precision_score, recall_score, f1_score

ALPHA = 2.0

def asymmetric_squared_error(y_true, y_pred):
    residual = y_pred - y_true
    underpredict = residual < 0
    grad = np.where(underpredict, 2.0 * ALPHA * residual, 2.0 * residual)
    hess = np.where(underpredict, 2.0 * ALPHA, 2.0)
    return grad, hess


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
        "MedAE": float(np.median(np.abs(err))),
        "R2": float(1 - np.sum(err**2) / np.sum((y_true - y_true.mean())**2)) if len(y_true) > 1 else float("nan")
    }

def process_horizon(horizon, base_dir):
    data_dir = base_dir / "data" / "processed"
    models_dir = base_dir / "models"

    s4_data_path = data_dir / "fusion" / "delhi_forecasting_satellite_pm10.csv"

    with open(models_dir / "horizon_features.json", "r") as f:
        canonical_features = json.load(f)["horizon_features"][horizon]

    s3_features = canonical_features + ["satellite_no2_latest", "satellite_no2_age_hours"]
    s4_features = s3_features + [
        "PM10_lag_1h", "PM10_lag_3h", "PM10_lag_6h", "PM10_lag_12h", "PM10_lag_24h",
        "PM10_lag_48h", "PM10_lag_72h", "PM10_roll_mean_6h", "PM10_roll_mean_24h", "PM10_roll_std_24h"
    ]

    s4_model_path = models_dir / f"xgb_satellite_pm10_{horizon}_tuned.joblib"
    s4_asym_model_path = models_dir / "experiments" / f"xgb_s4_asym_{horizon}.joblib"

    s4_model = joblib.load(s4_model_path)
    s4_asym_model = joblib.load(s4_asym_model_path)

    val_end = pd.to_datetime("2025-08-30 15:00:00")
    test_end = pd.to_datetime("2026-08-31 23:00:00")
    target = f"target_pm25_{horizon}"

    df = pd.read_csv(s4_data_path, parse_dates=["timestamp"])
    if "timestamp" in df.columns and "Timestamp" not in df.columns:
        df.rename(columns={"timestamp": "Timestamp"}, inplace=True)
    df = df.sort_values(by="Timestamp").reset_index(drop=True)
    if "station_id" in df.columns:
        df = pd.get_dummies(df, columns=["station_id"], dtype=int)
    df = df.loc[:, ~df.columns.duplicated()].copy()

    test_df = df[(df["Timestamp"] >= val_end) & (df["Timestamp"] <= test_end)].copy()
    test_mask = test_df[target].notna()
    X_test = test_df.loc[test_mask, s4_features]
    y_test = test_df.loc[test_mask, target]

    s4_pred = s4_model.predict(X_test)
    s4_asym_pred = s4_asym_model.predict(X_test)

    df_eval = pd.DataFrame({
        "y_true": y_test.values,
        "S4_pred": s4_pred,
        "S4_Asym_pred": s4_asym_pred
    })

    df_eval["Regime"] = df_eval["y_true"].apply(get_regime)

    overall_results = []
    regime_results = []

    # Overall
    for model_name in ["S4", "S4_Asym"]:
        metrics = evaluate_predictions(df_eval["y_true"], df_eval[f"{model_name}_pred"])
        overall_results.append({
            "Horizon": horizon,
            "Model": model_name,
            "N": metrics["N"],
            "MAE": metrics["MAE"],
            "RMSE": metrics["RMSE"],
            "Bias": metrics["Bias"],
            "MedAE": metrics["MedAE"],
            "R2": metrics["R2"]
        })

    # Regimes
    regimes = ["<60", "60-150", "150-250", ">=250"]
    for reg in regimes:
        sub = df_eval[df_eval["Regime"] == reg]
        for model_name in ["S4", "S4_Asym"]:
            if len(sub) == 0:
                continue
            metrics = evaluate_predictions(sub["y_true"], sub[f"{model_name}_pred"])
            regime_results.append({
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
    for model_name in ["S4", "S4_Asym"]:
        y_pred_binary = (df_eval[f"{model_name}_pred"] >= 150).astype(int)
        binary_results.append({
            "Horizon": horizon,
            "Model": model_name,
            "Precision": float(precision_score(y_true_binary, y_pred_binary, zero_division=0)),
            "Recall": float(recall_score(y_true_binary, y_pred_binary, zero_division=0)),
            "F1": float(f1_score(y_true_binary, y_pred_binary, zero_division=0))
        })

    return overall_results, regime_results, binary_results

def main():
    base_dir = Path(__file__).resolve().parent.parent

    all_overall = []
    all_regimes = []
    all_binary = []

    for horizon in ["6h", "24h", "72h"]:
        ov_res, reg_res, bin_res = process_horizon(horizon, base_dir)
        all_overall.extend(ov_res)
        all_regimes.extend(reg_res)
        all_binary.extend(bin_res)

    df_ov = pd.DataFrame(all_overall)
    df_reg = pd.DataFrame(all_regimes)
    df_bin = pd.DataFrame(all_binary)

    summary = []
    summary.append("==============================================================")
    summary.append("OVERALL EVALUATION (S4 vs S4 Asym)")
    summary.append("==============================================================\n")
    summary.append(f"{'Horizon':<8} {'Model':<10} {'MAE':<10} {'RMSE':<10} {'R2':<10} {'Bias':<10} {'MedAE':<10}")

    for _, row in df_ov.iterrows():
        summary.append(f"{row['Horizon']:<8} {row['Model']:<10} {row['MAE']:<10.4f} {row['RMSE']:<10.4f} {row['R2']:<10.4f} {row['Bias']:<10.4f} {row['MedAE']:<10.4f}")

    summary.append("\n==============================================================")
    summary.append("REGIME EVALUATION")
    summary.append("==============================================================\n")

    for horizon in ["6h", "24h", "72h"]:
        summary.append(f"Horizon: {horizon}")
        summary.append(f"{'Regime':<12} {'Model':<10} {'N':<8} {'MAE':<10} {'RMSE':<10} {'Bias':<10}")
        sub_res = df_reg[df_reg["Horizon"] == horizon]

        for reg in ["<60", "60-150", "150-250", ">=250"]:
            sub_reg = sub_res[sub_res["Regime"] == reg]
            for i, row in sub_reg.iterrows():
                reg_str = reg if i == sub_reg.index[0] else ""
                summary.append(f"{reg_str:<12} {row['Model']:<10} {row['N']:<8} {row['MAE']:<10.4f} {row['RMSE']:<10.4f} {row['Bias']:<10.4f}")
            if not sub_reg.empty:
                summary.append("")

    summary.append("==============================================================")
    summary.append(">=150 EVENT CLASSIFICATION")
    summary.append("==============================================================\n")

    summary.append(f"{'Horizon':<8} {'Model':<10} {'Precision':<12} {'Recall':<10} {'F1':<10}")
    for horizon in ["6h", "24h", "72h"]:
        sub_bin = df_bin[df_bin["Horizon"] == horizon]
        for _, row in sub_bin.iterrows():
            summary.append(f"{row['Horizon']:<8} {row['Model']:<10} {row['Precision']:<12.4f} {row['Recall']:<10.4f} {row['F1']:<10.4f}")
        summary.append("")

    summary_text = "\n".join(summary)

    print(summary_text)

    reports_dir = base_dir / "reports" / "satellite"
    with open(reports_dir / "asymmetric_experiment_summary.txt", "w") as f:
        f.write(summary_text)

if __name__ == "__main__":
    main()
