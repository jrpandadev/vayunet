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
# S8-B0 — Extreme Event Gate Analysis
#
# Goal:
# Determine whether causal information available at forecast
# time can identify future PM2.5 >= 250 µg/m³ events.
#
# IMPORTANT:
# - Production regression models remain frozen.
# - Test data is NEVER used for threshold/model selection.
# - Future actual PM2.5 is used ONLY as the classification target.
# - No future-derived features are allowed.
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

# ============================================================
# Feature definitions
# ============================================================

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

# ============================================================
# Helpers
# ============================================================


def load_data() -> pd.DataFrame:
    print("\nLoading datasets...")

    s5 = pd.read_csv(DATA_S5)
    episode = pd.read_csv(DATA_EPISODE)

    s5["timestamp"] = pd.to_datetime(s5["timestamp"])
    episode["timestamp"] = pd.to_datetime(episode["timestamp"])

    keys = ["timestamp", "station_id"]

    # Keep only Episode columns not already present in S5.
    episode_extra = [
        c for c in EPISODE_FEATURES
        if c in episode.columns and c not in s5.columns
    ]

    if len(episode_extra) != len(EPISODE_FEATURES):
        missing = sorted(set(EPISODE_FEATURES) - set(episode_extra))
        raise RuntimeError(f"Missing Episode features: {missing}")

    merged = s5.merge(
        episode[keys + episode_extra],
        on=keys,
        how="left",
        validate="one_to_one",
    )

    merged = merged.sort_values(
        ["station_id", "timestamp"]
    ).reset_index(drop=True)

    print(f"Rows: {len(merged):,}")
    print(f"Columns: {len(merged.columns)}")

    return merged


def get_base_features(model) -> list[str]:
    """
    Recover the feature names used by the frozen production model.
    """
    if hasattr(model, "feature_names_in_"):
        return list(model.feature_names_in_)

    booster = model.get_booster()

    names = booster.feature_names

    if names is None:
        raise RuntimeError(
            "Frozen production model does not expose feature names."
        )

    return list(names)


def validate_feature_columns(df: pd.DataFrame, cols: list[str], label: str):
    missing = [c for c in cols if c not in df.columns]

    if missing:
        raise RuntimeError(
            f"{label}: missing {len(missing)} columns:\n"
            + "\n".join(missing)
        )


def chronological_split(df: pd.DataFrame, target: str):
    valid_target = df[target].notna()

    train_mask = (
        valid_target
        & (df["timestamp"] < TRAIN_END)
    )

    valid_mask = (
        valid_target
        & (df["timestamp"] >= TRAIN_END)
        & (df["timestamp"] < VALID_END)
    )

    test_mask = (
        valid_target
        & (df["timestamp"] >= VALID_END)
        & (df["timestamp"] <= TEST_END)
    )

    return train_mask, valid_mask, test_mask


def train_production_prediction(
    df: pd.DataFrame,
    horizon: int,
    cfg: dict,
) -> np.ndarray:
    """
    Generate predictions from the frozen production model.

    This does NOT retrain the production model.
    """

    model = joblib.load(cfg["model"])

    base_features = get_base_features(model)

    validate_feature_columns(
        df,
        base_features,
        f"{horizon}h production model",
    )

    X = df[base_features]

    # XGBoost handles NaNs natively.
    pred = np.full(len(df), np.nan, dtype=float)

    valid_rows = X.notna().any(axis=1)

    if valid_rows.any():
        pred[valid_rows.to_numpy()] = model.predict(
            X.loc[valid_rows]
        )

    print(
        f"{horizon}h production model: "
        f"{len(base_features)} features"
    )

    return pred


def evaluate_binary(
    y_true: np.ndarray,
    probability: np.ndarray,
    threshold: float,
) -> dict:

    predicted = probability >= threshold

    tn, fp, fn, tp = confusion_matrix(
        y_true,
        predicted,
        labels=[0, 1],
    ).ravel()

    return {
        "threshold": float(threshold),
        "n": int(len(y_true)),
        "extreme_events": int(y_true.sum()),
        "predicted_extreme": int(predicted.sum()),
        "true_positive": int(tp),
        "false_positive": int(fp),
        "true_negative": int(tn),
        "false_negative": int(fn),
        "precision": float(
            precision_score(
                y_true,
                predicted,
                zero_division=0,
            )
        ),
        "recall": float(
            recall_score(
                y_true,
                predicted,
                zero_division=0,
            )
        ),
        "f1": float(
            f1_score(
                y_true,
                predicted,
                zero_division=0,
            )
        ),
    }


def threshold_search(
    y_true: np.ndarray,
    probability: np.ndarray,
) -> tuple[float, list[dict]]:

    thresholds = [
        0.05,
        0.10,
        0.15,
        0.20,
        0.25,
        0.30,
        0.35,
        0.40,
        0.45,
        0.50,
        0.55,
        0.60,
        0.65,
        0.70,
        0.75,
        0.80,
        0.85,
        0.90,
        0.95,
    ]

    results = [
        evaluate_binary(
            y_true,
            probability,
            threshold,
        )
        for threshold in thresholds
    ]

    # Operational preference:
    # maximize recall subject to precision >= 0.40.
    #
    # If no threshold reaches 0.40 precision,
    # maximize F1 instead.
    eligible = [
        r for r in results
        if r["precision"] >= 0.40
    ]

    if eligible:
        best = max(
            eligible,
            key=lambda r: (
                r["recall"],
                r["f1"],
                r["precision"],
            ),
        )
    else:
        best = max(
            results,
            key=lambda r: (
                r["f1"],
                r["recall"],
            ),
        )

    return best["threshold"], results


def fit_gate(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_valid: pd.DataFrame,
    y_valid: np.ndarray,
    label: str,
):
    print(f"\nTraining {label}...")

    # Class imbalance correction.
    positives = int(y_train.sum())
    negatives = int(len(y_train) - positives)

    if positives == 0:
        raise RuntimeError(
            f"{label}: training set contains zero extreme events."
        )

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

    model.fit(
        X_train,
        y_train,
        eval_set=[(X_valid, y_valid)],
        verbose=False,
    )

    valid_prob = model.predict_proba(X_valid)[:, 1]

    return model, valid_prob


# ============================================================
# Main experiment
# ============================================================


def run_horizon(df: pd.DataFrame, horizon: int, cfg: dict):

    target = cfg["target"]

    print("\n" + "=" * 72)
    print(f"S8-B0 — {horizon}H EXTREME GATE")
    print("=" * 72)

    # --------------------------------------------------------
    # Frozen production regression prediction
    # --------------------------------------------------------

    prediction = train_production_prediction(
        df,
        horizon,
        cfg,
    )

    pred_col = f"production_prediction_{horizon}h"

    df = df.copy()
    df[pred_col] = prediction

    # --------------------------------------------------------
    # Causal feature groups
    # --------------------------------------------------------

    # Gate A
    gate_a = [
        pred_col,
    ]

    # Gate B
    gate_b = gate_a + EPISODE_FEATURES

    # Gate C
    gate_c = (
        gate_b
        + cfg["nwp"]
        + SATELLITE_FEATURES
        + PM10_FEATURES
    )

    # Remove duplicates while preserving order.
    gate_a = list(dict.fromkeys(gate_a))
    gate_b = list(dict.fromkeys(gate_b))
    gate_c = list(dict.fromkeys(gate_c))

    for label, features in [
        ("Gate A", gate_a),
        ("Gate B", gate_b),
        ("Gate C", gate_c),
    ]:
        validate_feature_columns(
            df,
            features,
            f"{horizon}h {label}",
        )

    # --------------------------------------------------------
    # Exact chronological split
    # --------------------------------------------------------

    train_mask, valid_mask, test_mask = chronological_split(
        df,
        target,
    )

    # Production prediction must exist.
    train_mask &= df[pred_col].notna()
    valid_mask &= df[pred_col].notna()
    test_mask &= df[pred_col].notna()

    print("\nSplit:")
    print(f"Train:      {train_mask.sum():,}")
    print(f"Validation: {valid_mask.sum():,}")
    print(f"Test:       {test_mask.sum():,}")

    # --------------------------------------------------------
    # Extreme classification target
    # --------------------------------------------------------

    y = (
        df[target].to_numpy() >= EXTREME_THRESHOLD
    ).astype(np.int8)

    print("\nExtreme-event counts:")
    print(f"Train:      {y[train_mask].sum():,}")
    print(f"Validation: {y[valid_mask].sum():,}")
    print(f"Test:       {y[test_mask].sum():,}")

    gate_results = []

    for gate_name, features in [
        ("A_prediction_only", gate_a),
        ("B_prediction_episode", gate_b),
        ("C_prediction_episode_environment", gate_c),
    ]:

        print("\n" + "-" * 72)
        print(f"{gate_name}")
        print(f"Features: {len(features)}")

        X_train = df.loc[train_mask, features].copy()
        X_valid = df.loc[valid_mask, features].copy()
        X_test = df.loc[test_mask, features].copy()

        y_train = y[train_mask.to_numpy()]
        y_valid = y[valid_mask.to_numpy()]
        y_test = y[test_mask.to_numpy()]

        # Require at least one usable feature per row.
        train_usable = X_train.notna().any(axis=1)
        valid_usable = X_valid.notna().any(axis=1)
        test_usable = X_test.notna().any(axis=1)

        X_train = X_train.loc[train_usable]
        y_train = y_train[train_usable.to_numpy()]

        X_valid = X_valid.loc[valid_usable]
        y_valid = y_valid[valid_usable.to_numpy()]

        X_test = X_test.loc[test_usable]
        y_test = y_test[test_usable.to_numpy()]

        print(
            f"Usable rows: "
            f"train={len(X_train):,}, "
            f"valid={len(X_valid):,}, "
            f"test={len(X_test):,}"
        )

        if y_valid.sum() == 0 or y_test.sum() == 0:
            raise RuntimeError(
                f"{gate_name}: insufficient positive events."
            )

        model, valid_prob = fit_gate(
            X_train,
            y_train,
            X_valid,
            y_valid,
            gate_name,
        )

        # ----------------------------------------------------
        # Validation metrics
        # ----------------------------------------------------

        valid_ap = average_precision_score(
            y_valid,
            valid_prob,
        )

        valid_auc = roc_auc_score(
            y_valid,
            valid_prob,
        )

        selected_threshold, threshold_results = threshold_search(
            y_valid,
            valid_prob,
        )

        selected_validation = evaluate_binary(
            y_valid,
            valid_prob,
            selected_threshold,
        )

        print("\nValidation:")
        print(f"PR-AUC: {valid_ap:.4f}")
        print(f"ROC-AUC: {valid_auc:.4f}")
        print(
            f"Selected threshold: "
            f"{selected_threshold:.2f}"
        )
        print(
            f"Precision: "
            f"{selected_validation['precision']:.4f}"
        )
        print(
            f"Recall: "
            f"{selected_validation['recall']:.4f}"
        )
        print(
            f"F1: "
            f"{selected_validation['f1']:.4f}"
        )

        # ----------------------------------------------------
        # TEST — threshold is now frozen
        # ----------------------------------------------------

        test_prob = model.predict_proba(X_test)[:, 1]

        test_ap = average_precision_score(
            y_test,
            test_prob,
        )

        test_auc = roc_auc_score(
            y_test,
            test_prob,
        )

        test_metrics = evaluate_binary(
            y_test,
            test_prob,
            selected_threshold,
        )

        print("\nUNTOUCHED TEST:")
        print(f"PR-AUC: {test_ap:.4f}")
        print(f"ROC-AUC: {test_auc:.4f}")
        print(
            f"Precision: "
            f"{test_metrics['precision']:.4f}"
        )
        print(
            f"Recall: "
            f"{test_metrics['recall']:.4f}"
        )
        print(
            f"F1: "
            f"{test_metrics['f1']:.4f}"
        )
        print(
            f"Extreme events: "
            f"{test_metrics['extreme_events']:,}"
        )
        print(
            f"Detected: "
            f"{test_metrics['true_positive']:,}"
        )
        print(
            f"False alarms: "
            f"{test_metrics['false_positive']:,}"
        )

        gate_results.append(
            {
                "gate": gate_name,
                "n_features": len(features),
                "train_rows": int(len(X_train)),
                "validation_rows": int(len(X_valid)),
                "test_rows": int(len(X_test)),
                "validation_pr_auc": float(valid_ap),
                "validation_roc_auc": float(valid_auc),
                "selected_threshold": float(selected_threshold),
                "validation_precision": selected_validation[
                    "precision"
                ],
                "validation_recall": selected_validation[
                    "recall"
                ],
                "validation_f1": selected_validation[
                    "f1"
                ],
                "test_pr_auc": float(test_ap),
                "test_roc_auc": float(test_auc),
                "test_precision": test_metrics[
                    "precision"
                ],
                "test_recall": test_metrics[
                    "recall"
                ],
                "test_f1": test_metrics["f1"],
                "test_extreme_events": test_metrics[
                    "extreme_events"
                ],
                "test_detected": test_metrics[
                    "true_positive"
                ],
                "test_false_alarms": test_metrics[
                    "false_positive"
                ],
                "test_false_negatives": test_metrics[
                    "false_negative"
                ],
            }
        )

    return df, gate_results


def main():

    df = load_data()

    all_results = {}

    for horizon, cfg in HORIZONS.items():

        df_h, results = run_horizon(
            df,
            horizon,
            cfg,
        )

        all_results[f"{horizon}h"] = results

    # --------------------------------------------------------
    # Save report
    # --------------------------------------------------------

    output_json = (
        REPORT_DIR
        / "s8b0_extreme_gate_results.json"
    )

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(
            all_results,
            f,
            indent=2,
        )

    rows = []

    for horizon, results in all_results.items():
        for result in results:
            rows.append(
                {
                    "horizon": horizon,
                    **result,
                }
            )

    results_df = pd.DataFrame(rows)

    output_csv = (
        REPORT_DIR
        / "s8b0_extreme_gate_results.csv"
    )

    results_df.to_csv(
        output_csv,
        index=False,
    )

    # --------------------------------------------------------
    # Human-readable summary
    # --------------------------------------------------------

    report_md = (
        REPORT_DIR
        / "s8b0_extreme_gate_report.md"
    )

    lines = [
        "# S8-B0 Extreme Event Gate Analysis",
        "",
        "Target: future PM2.5 >= 250 µg/m³.",
        "",
        "Threshold selection was performed on validation only.",
        "The test set was evaluated after threshold selection.",
        "",
        "## Results",
        "",
        "| Horizon | Gate | Test PR-AUC | Test Precision | "
        "Test Recall | Test F1 | False Alarms |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]

    for _, row in results_df.iterrows():

        lines.append(
            f"| {row['horizon']} | "
            f"{row['gate']} | "
            f"{row['test_pr_auc']:.4f} | "
            f"{row['test_precision']:.4f} | "
            f"{row['test_recall']:.4f} | "
            f"{row['test_f1']:.4f} | "
            f"{row['test_false_alarms']} |"
        )

    lines.extend(
        [
            "",
            "## Decision rule",
            "",
            "This experiment is diagnostic only.",
            "No production model was modified.",
            "No specialist model was introduced.",
            "",
            "A specialist should only be considered if the "
            "causal gate demonstrates useful out-of-sample "
            "extreme-event discrimination on the untouched test set.",
        ]
    )

    report_md.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    print("\n" + "=" * 72)
    print("S8-B0 COMPLETE")
    print("=" * 72)

    print(f"JSON: {output_json}")
    print(f"CSV:  {output_csv}")
    print(f"MD:   {report_md}")

    print("\nFinal comparison:")
    print(
        results_df[
            [
                "horizon",
                "gate",
                "test_pr_auc",
                "test_precision",
                "test_recall",
                "test_f1",
                "test_false_alarms",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
