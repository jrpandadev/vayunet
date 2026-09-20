from __future__ import annotations

import json
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")

# ============================================================
# S8-B1 — Severe-Event Specialist
#
# Goal:
# Train a specialist to predict future PM2.5 >= 250, and
# evaluate its ability to provide early warning (lead time)
# BEFORE the event begins (i.e. current PM2.5 < 250).
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

DATA_S5 = ROOT / "data" / "processed" / "fusion" / "delhi_forecasting_s5_nwp.csv"
DATA_EPISODE = ROOT / "data" / "processed" / "fusion" / "delhi_forecasting_episode.csv"

MODEL_DIR = ROOT / "models"

REPORT_DIR = ROOT / "reports" / "extreme_pollution"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

SEED = 42
EXTREME_THRESHOLD = 250.0

TRAIN_END = pd.Timestamp("2024-10-01 13:00:00")
VALID_END = pd.Timestamp("2025-08-30 15:00:00")
TEST_END = pd.Timestamp("2026-08-31 23:00:00")

HORIZONS = {
    6: {
        "target": "target_pm25_6h",
        "model": MODEL_DIR / "xgb_vayunet_pm25_6h_s6_production.joblib",
        "nwp": [
            "nwp_temperature_2m_6h",
            "nwp_relative_humidity_2m_6h",
            "nwp_precipitation_6h",
            "nwp_surface_pressure_6h",
            "nwp_wind_speed_10m_6h",
            "nwp_wind_direction_10m_6h",
            "nwp_boundary_layer_height_6h",
        ],
    },
    24: {
        "target": "target_pm25_24h",
        "model": MODEL_DIR / "xgb_vayunet_pm25_24h_s5_production.joblib",
        "nwp": [
            "nwp_temperature_2m_24h",
            "nwp_relative_humidity_2m_24h",
            "nwp_precipitation_24h",
            "nwp_surface_pressure_24h",
            "nwp_wind_speed_10m_24h",
            "nwp_wind_direction_10m_24h",
            "nwp_boundary_layer_height_24h",
        ],
    },
    72: {
        "target": "target_pm25_72h",
        "model": MODEL_DIR / "xgb_vayunet_pm25_72h_s6_production.joblib",
        "nwp": [
            "nwp_temperature_2m_72h",
            "nwp_relative_humidity_2m_72h",
            "nwp_precipitation_72h",
            "nwp_surface_pressure_72h",
            "nwp_wind_speed_10m_72h",
            "nwp_wind_direction_10m_72h",
            "nwp_boundary_layer_height_72h",
        ],
    },
}

EPISODE_FEATURES = [
    "pm25_delta_1h",
    "pm25_delta_3h",
    "pm25_delta_6h",
    "pm25_delta_12h",
    "pm25_delta_24h",
    "pm25_acceleration_1h",
    "pm25_acceleration_3h",
    "pm25_acceleration_6h",
    "pm25_mean_6h",
    "pm25_mean_12h",
    "pm25_mean_24h",
    "pm25_std_6h",
    "pm25_std_24h",
    "pm25_max_6h",
    "pm25_max_24h",
    "hours_since_150_onset",
    "hours_since_250_onset",
    "hours_above_150_24h",
    "hours_above_250_24h",
    "fraction_above_150_24h",
    "fraction_above_250_24h",
]

SATELLITE_FEATURES = [
    "satellite_no2_latest",
    "satellite_no2_age_hours",
]

PM10_FEATURES = [
    "PM10",
    "PM10_lag_1h",
    "PM10_lag_3h",
    "PM10_lag_6h",
    "PM10_lag_12h",
    "PM10_lag_24h",
    "PM10_lag_48h",
    "PM10_lag_72h",
    "PM10_roll_mean_6h",
    "PM10_roll_mean_24h",
    "PM10_roll_std_24h",
]

def load_data() -> pd.DataFrame:
    s5 = pd.read_csv(DATA_S5)
    episode = pd.read_csv(DATA_EPISODE)

    s5["timestamp"] = pd.to_datetime(s5["timestamp"])
    episode["timestamp"] = pd.to_datetime(episode["timestamp"])

    keys = ["timestamp", "station_id"]

    episode_extra = [
        c for c in EPISODE_FEATURES
        if c in episode.columns and c not in s5.columns
    ]

    merged = s5.merge(
        episode[keys + episode_extra],
        on=keys,
        how="left",
        validate="one_to_one",
    )
    merged = merged.sort_values(["station_id", "timestamp"]).reset_index(drop=True)
    return merged

def get_base_features(model) -> list[str]:
    if hasattr(model, "feature_names_in_"):
        return list(model.feature_names_in_)
    booster = model.get_booster()
    return list(booster.feature_names)

def validate_feature_columns(df: pd.DataFrame, cols: list[str], label: str):
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise RuntimeError(f"{label}: missing columns: {missing}")

def chronological_split(df: pd.DataFrame, target: str):
    valid_target = df[target].notna()
    train_mask = valid_target & (df["timestamp"] < TRAIN_END)
    valid_mask = valid_target & (df["timestamp"] >= TRAIN_END) & (df["timestamp"] < VALID_END)
    test_mask = valid_target & (df["timestamp"] >= VALID_END) & (df["timestamp"] <= TEST_END)
    return train_mask, valid_mask, test_mask

def train_production_prediction(df: pd.DataFrame, horizon: int, cfg: dict) -> np.ndarray:
    model = joblib.load(cfg["model"])
    base_features = get_base_features(model)
    validate_feature_columns(df, base_features, f"{horizon}h production")
    X = df[base_features]
    pred = np.full(len(df), np.nan, dtype=float)
    valid_rows = X.notna().any(axis=1)
    if valid_rows.any():
        pred[valid_rows.to_numpy()] = model.predict(X.loc[valid_rows])
    return pred

def evaluate_binary(y_true: np.ndarray, probability: np.ndarray, threshold: float, current_pm25: np.ndarray) -> dict:
    predicted = probability >= threshold
    tn, fp, fn, tp = confusion_matrix(y_true, predicted, labels=[0, 1]).ravel()

    y_true_bool = y_true == 1
    current_clean = current_pm25 < EXTREME_THRESHOLD

    onset_events = y_true_bool & current_clean
    onset_detected = onset_events & predicted

    n_onset = int(onset_events.sum())
    n_onset_detected = int(onset_detected.sum())
    n_onset_missed = n_onset - n_onset_detected

    onset_rate = n_onset_detected / n_onset if n_onset > 0 else 0.0

    return {
        "threshold": float(threshold),
        "n": int(len(y_true)),
        "extreme_events": int(y_true.sum()),
        "predicted_extreme": int(predicted.sum()),
        "true_positive": int(tp),
        "false_positive": int(fp),
        "true_negative": int(tn),
        "false_negative": int(fn),
        "precision": float(precision_score(y_true, predicted, zero_division=0)),
        "recall": float(recall_score(y_true, predicted, zero_division=0)),
        "f1": float(f1_score(y_true, predicted, zero_division=0)),
        "onset_events": n_onset,
        "onset_detected": n_onset_detected,
        "onset_missed": n_onset_missed,
        "onset_rate": float(onset_rate)
    }

def threshold_search(y_true: np.ndarray, probability: np.ndarray, current_pm25: np.ndarray) -> tuple[float, list[dict]]:
    thresholds = [x/100.0 for x in range(5, 96, 5)]
    results = [evaluate_binary(y_true, probability, t, current_pm25) for t in thresholds]

    eligible = [r for r in results if r["precision"] >= 0.40]
    if eligible:
        best = max(eligible, key=lambda r: (r["recall"], r["f1"], r["precision"]))
    else:
        best = max(results, key=lambda r: (r["f1"], r["recall"]))
    return best["threshold"], results

def fit_gate(X_train: pd.DataFrame, y_train: np.ndarray, X_valid: pd.DataFrame, y_valid: np.ndarray):
    positives = int(y_train.sum())
    negatives = int(len(y_train) - positives)
    scale_pos_weight = negatives / positives

    model = XGBClassifier(
        n_estimators=500,
        max_depth=4,
        learning_rate=0.03,
        min_child_weight=5,
        subsample=0.9,
        colsample_bytree=0.8,
        reg_lambda=1.0,
        objective="binary:logistic",
        eval_metric="aucpr",
        tree_method="hist",
        device="cuda",
        random_state=SEED,
        scale_pos_weight=scale_pos_weight,
        n_jobs=1,
    )
    model.fit(X_train, y_train, eval_set=[(X_valid, y_valid)], verbose=False)
    return model, model.predict_proba(X_valid)[:, 1]

def run_horizon(df: pd.DataFrame, horizon: int, cfg: dict):
    target = cfg["target"]
    print(f"\n{'='*72}\nS8-B1 — {horizon}H EXTREME SPECIALIST\n{'='*72}")

    prediction = train_production_prediction(df, horizon, cfg)
    pred_col = f"production_prediction_{horizon}h"
    df = df.copy()
    df[pred_col] = prediction

    gate_a = list(dict.fromkeys([pred_col]))
    gate_b = list(dict.fromkeys(gate_a + EPISODE_FEATURES))
    gate_c = list(dict.fromkeys(gate_b + cfg["nwp"] + SATELLITE_FEATURES + PM10_FEATURES))

    for label, features in [("Gate A", gate_a), ("Gate B", gate_b), ("Gate C", gate_c)]:
        validate_feature_columns(df, features, f"{horizon}h {label}")

    train_mask, valid_mask, test_mask = chronological_split(df, target)
    train_mask &= df[pred_col].notna()
    valid_mask &= df[pred_col].notna()
    test_mask &= df[pred_col].notna()

    y = (df[target].to_numpy() >= EXTREME_THRESHOLD).astype(np.int8)
    current_pm25 = df["PM2.5"].to_numpy()

    gate_results = []
    for gate_name, features in [("A_prediction_only", gate_a), ("B_prediction_episode", gate_b), ("C_prediction_episode_environment", gate_c)]:
        print(f"\n{'-'*72}\n{gate_name}\nFeatures: {len(features)}")

        X_train = df.loc[train_mask, features].copy()
        X_valid = df.loc[valid_mask, features].copy()
        X_test = df.loc[test_mask, features].copy()

        y_train = y[train_mask.to_numpy()]
        y_valid = y[valid_mask.to_numpy()]
        y_test = y[test_mask.to_numpy()]

        pm25_train = current_pm25[train_mask.to_numpy()]
        pm25_valid = current_pm25[valid_mask.to_numpy()]
        pm25_test = current_pm25[test_mask.to_numpy()]

        train_usable = X_train.notna().any(axis=1)
        valid_usable = X_valid.notna().any(axis=1)
        test_usable = X_test.notna().any(axis=1)

        X_train = X_train.loc[train_usable]
        y_train = y_train[train_usable.to_numpy()]
        pm25_train = pm25_train[train_usable.to_numpy()]

        X_valid = X_valid.loc[valid_usable]
        y_valid = y_valid[valid_usable.to_numpy()]
        pm25_valid = pm25_valid[valid_usable.to_numpy()]

        X_test = X_test.loc[test_usable]
        y_test = y_test[test_usable.to_numpy()]
        pm25_test = pm25_test[test_usable.to_numpy()]

        model, valid_prob = fit_gate(X_train, y_train, X_valid, y_valid)

        selected_threshold, _ = threshold_search(y_valid, valid_prob, pm25_valid)

        test_prob = model.predict_proba(X_test)[:, 1]
        test_ap = average_precision_score(y_test, test_prob)
        test_auc = roc_auc_score(y_test, test_prob)
        tm = evaluate_binary(y_test, test_prob, selected_threshold, pm25_test)

        print("\nUNTOUCHED TEST:")
        print(f"PR-AUC: {test_ap:.4f}")
        print(f"ROC-AUC: {test_auc:.4f}")
        print(f"Precision: {tm['precision']:.4f}")
        print(f"Recall: {tm['recall']:.4f}")
        print(f"F1: {tm['f1']:.4f}")
        print(f"Confusion Matrix:")
        print(f"  TN: {tm['true_negative']} | FP (False alarms): {tm['false_positive']}")
        print(f"  FN (Missed events): {tm['false_negative']} | TP (Detected): {tm['true_positive']}")
        print(f"Lead Time (Onset) Metrics:")
        print(f"  Total Onset Events (current PM2.5 < 250): {tm['onset_events']}")
        print(f"  Onset Detected: {tm['onset_detected']}")
        print(f"  Onset Missed: {tm['onset_missed']}")
        print(f"  Onset Detection Rate: {tm['onset_rate']:.4f}")

        gate_results.append({
            "gate": gate_name,
            "test_pr_auc": test_ap,
            "test_precision": tm['precision'],
            "test_recall": tm['recall'],
            "test_f1": tm['f1'],
            "false_alarms": tm['false_positive'],
            "detected": tm['true_positive'],
            "missed": tm['false_negative'],
            "onset_events": tm['onset_events'],
            "onset_detected": tm['onset_detected'],
            "onset_rate": tm['onset_rate']
        })
    return df, gate_results

def main():
    df = load_data()
    all_results = []

    for horizon, cfg in HORIZONS.items():
        _, results = run_horizon(df, horizon, cfg)
        for r in results:
            all_results.append({"horizon": f"{horizon}h", **r})

    results_df = pd.DataFrame(all_results)
    output_csv = REPORT_DIR / "s8b1_severe_specialist_results.csv"
    results_df.to_csv(output_csv, index=False)

    print(f"\n{'='*72}\nS8-B1 COMPLETE\n{'='*72}")
    print("\nFinal comparison:")
    print(results_df[[
        "horizon", "gate", "test_pr_auc", "test_precision", "test_recall", "test_f1",
        "false_alarms", "detected", "onset_rate"
    ]].to_string(index=False))

if __name__ == "__main__":
    main()
