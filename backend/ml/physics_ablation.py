from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    median_absolute_error,
)

from physics_features import (
    add_physics_features,
    get_physics_feature_names,
)


# ============================================================
# Paths
# ============================================================

BACKEND_DIR = Path(__file__).resolve().parents[1]

DATA_PATH = (
    BACKEND_DIR
    / "data"
    / "processed"
    / "delhi_forecasting_weather.csv"
)

REPORT_DIR = BACKEND_DIR / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# Configuration
# ============================================================

HORIZONS = [6, 24, 72]

TARGET_COLUMNS = {
    6: "target_pm25_6h",
    24: "target_pm25_24h",
    72: "target_pm25_72h",
}

# Exact final temporal split.
TRAIN_END = pd.Timestamp("2024-10-01 13:00:00")
VALID_END = pd.Timestamp("2025-08-30 15:00:00")
TEST_END = pd.Timestamp("2026-08-31 23:00:00")


# ============================================================
# Locked 42-feature baseline
# ============================================================

BASELINE_FEATURES = [
    "PM2.5",
    "PM2.5_lag_1h",
    "PM2.5_lag_3h",
    "PM2.5_lag_6h",
    "PM2.5_lag_12h",
    "PM2.5_lag_24h",
    "PM2.5_lag_48h",
    "PM2.5_lag_72h",
    "PM2.5_roll_mean_6h",
    "PM2.5_roll_mean_24h",
    "PM2.5_roll_std_24h",
    "hour",
    "day_of_week",
    "day_of_year",
    "month",
    "is_weekend",
    "WD_sin",
    "WD_cos",
    "PM10",
    "NO",
    "NO2",
    "NOx",
    "NH3",
    "SO2",
    "CO",
    "Ozone",
    "AT",
    "RH",
    "WS",
    "WD",
    "SR",
    "BP",
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "precipitation",
    "surface_pressure",
    "cloud_cover",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    "shortwave_radiation",
]


# ============================================================
# Physics feature groups
# ============================================================

PHYSICS_GROUPS = {
    "A_atmospheric_transport": [
        "ventilation_index",
        "log_ventilation_index",
        "wind_u",
        "wind_v",
        "stagnation_proxy",
    ],

    "B_pm25_dynamics": [
        "PM25_change_1h",
        "PM25_change_3h",
        "PM25_change_6h",
        "PM25_acceleration_1h",
        "PM25_rolling_slope_6h",
    ],

    "C_particle_composition": [
        "PM25_PM10_fraction",
    ],

    "D_meteorological_interactions": [
        "temperature_RH_interaction",
        "RH_PBLH_interaction",
    ],

    "E_pollution_transport_interaction": [
        "PM25_ventilation_interaction",
    ],
}


# ============================================================
# Validation
# ============================================================

def validate_columns(df: pd.DataFrame) -> None:

    required = (
        BASELINE_FEATURES
        + get_physics_feature_names()
        + list(TARGET_COLUMNS.values())
        + ["timestamp"]
    )

    missing = [
        col
        for col in required
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns:\n{missing}"
        )


# ============================================================
# Metrics
# ============================================================

def calculate_metrics(
    y_true: pd.Series,
    y_pred: np.ndarray,
) -> dict:

    y_true_np = y_true.to_numpy()
    y_pred_np = np.asarray(y_pred)

    errors = y_pred_np - y_true_np

    return {
        "MAE": float(
            mean_absolute_error(
                y_true_np,
                y_pred_np,
            )
        ),
        "RMSE": float(
            np.sqrt(
                mean_squared_error(
                    y_true_np,
                    y_pred_np,
                )
            )
        ),
        "R2": float(
            r2_score(
                y_true_np,
                y_pred_np,
            )
        ),
        "Bias": float(
            np.mean(errors)
        ),
        "MedAE": float(
            median_absolute_error(
                y_true_np,
                y_pred_np,
            )
        ),
    }


# ============================================================
# Pollution regime metrics
# ============================================================

def calculate_regime_metrics(
    y_true: pd.Series,
    y_pred: np.ndarray,
) -> dict:

    y = y_true.to_numpy()
    p = np.asarray(y_pred)

    regimes = {
        "below_60": y < 60,
        "60_to_150": (y >= 60) & (y < 150),
        "150_to_250": (y >= 150) & (y < 250),
        "above_250": y >= 250,
    }

    output = {}

    for name, mask in regimes.items():

        count = int(mask.sum())

        if count == 0:
            output[name] = {
                "count": 0,
                "MAE": None,
                "RMSE": None,
                "Bias": None,
            }
            continue

        errors = p[mask] - y[mask]

        output[name] = {
            "count": count,
            "MAE": float(
                np.mean(np.abs(errors))
            ),
            "RMSE": float(
                np.sqrt(np.mean(errors ** 2))
            ),
            "Bias": float(
                np.mean(errors)
            ),
        }

    return output


# ============================================================
# One experiment
# ============================================================

def run_experiment(
    df: pd.DataFrame,
    horizon: int,
    experiment_name: str,
    extra_features: list[str],
) -> dict:

    target = TARGET_COLUMNS[horizon]

    features = BASELINE_FEATURES + extra_features

    print()
    print("=" * 80)
    print(
        f"{experiment_name} - {horizon}H"
    )
    print("=" * 80)

    # --------------------------------------------------------
    # Remove rows without target.
    # --------------------------------------------------------

    data = df[
        df[target].notna()
    ].copy()

    # --------------------------------------------------------
    # Temporal split.
    # --------------------------------------------------------

    train = data[
        data["timestamp"] < TRAIN_END
    ]

    valid = data[
        (data["timestamp"] >= TRAIN_END)
        & (data["timestamp"] < VALID_END)
    ]

    test = data[
        (data["timestamp"] >= VALID_END)
        & (data["timestamp"] <= TEST_END)
    ]

    print(
        f"Train: {len(train):,} | "
        f"Valid: {len(valid):,} | "
        f"Test: {len(test):,}"
    )

    # --------------------------------------------------------
    # Data matrices.
    # --------------------------------------------------------

    X_train = train[features]
    y_train = train[target]

    X_valid = valid[features]
    y_valid = valid[target]

    X_test = test[features]
    y_test = test[target]

    # --------------------------------------------------------
    # Fixed model configuration.
    #
    # IMPORTANT:
    # We intentionally keep this fixed across every experiment.
    # --------------------------------------------------------

    model = xgb.XGBRegressor(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="reg:squarederror",
        eval_metric="mae",
        tree_method="hist",
        random_state=42,
        n_jobs=-1,
    )

    print(
        f"Features: {len(features)} "
        f"({len(extra_features)} additional)"
    )

    print("Training...")

    model.fit(
        X_train,
        y_train,
        eval_set=[
            (X_valid, y_valid),
        ],
        verbose=False,
    )

    # --------------------------------------------------------
    # Predictions.
    # --------------------------------------------------------

    valid_pred = model.predict(X_valid)
    test_pred = model.predict(X_test)

    # --------------------------------------------------------
    # Metrics.
    # --------------------------------------------------------

    validation_metrics = calculate_metrics(
        y_valid,
        valid_pred,
    )

    test_metrics = calculate_metrics(
        y_test,
        test_pred,
    )

    test_regimes = calculate_regime_metrics(
        y_test,
        test_pred,
    )

    # --------------------------------------------------------
    # Print results.
    # --------------------------------------------------------

    print("\nValidation:")
    print(
        f"  MAE   = {validation_metrics['MAE']:.4f}"
    )
    print(
        f"  RMSE  = {validation_metrics['RMSE']:.4f}"
    )
    print(
        f"  R2    = {validation_metrics['R2']:.4f}"
    )
    print(
        f"  Bias  = {validation_metrics['Bias']:.4f}"
    )

    print("\nTest:")
    print(
        f"  MAE   = {test_metrics['MAE']:.4f}"
    )
    print(
        f"  RMSE  = {test_metrics['RMSE']:.4f}"
    )
    print(
        f"  R2    = {test_metrics['R2']:.4f}"
    )
    print(
        f"  Bias  = {test_metrics['Bias']:.4f}"
    )
    print(
        f"  MedAE = {test_metrics['MedAE']:.4f}"
    )

    return {
        "experiment": experiment_name,
        "horizon": horizon,
        "extra_features": extra_features,
        "feature_count": len(features),
        "validation_metrics": validation_metrics,
        "test_metrics": test_metrics,
        "test_regimes": test_regimes,
    }


# ============================================================
# Main
# ============================================================

def main():

    print("=" * 80)
    print("VayuNet - Physics Feature Ablation")
    print("=" * 80)

    print("\nLoading:")
    print(DATA_PATH)

    df = pd.read_csv(
        DATA_PATH,
        parse_dates=["timestamp"],
    )

    print(
        f"Loaded {len(df):,} rows x "
        f"{len(df.columns)} columns"
    )

    # --------------------------------------------------------
    # Generate physics features once.
    # --------------------------------------------------------

    print("\nGenerating physics features...")

    df = add_physics_features(
        df,
        copy=False,
    )

    print("Physics features generated.")

    validate_columns(df)

    # --------------------------------------------------------
    # Experiments.
    #
    # Baseline is included as the reference.
    # --------------------------------------------------------

    experiments = {
        "Baseline": [],
        **PHYSICS_GROUPS,
    }

    all_results = []

    # --------------------------------------------------------
    # Run all horizons.
    # --------------------------------------------------------

    for horizon in HORIZONS:

        for experiment_name, extra_features in experiments.items():

            result = run_experiment(
                df=df,
                horizon=horizon,
                experiment_name=experiment_name,
                extra_features=extra_features,
            )

            all_results.append(result)

    # --------------------------------------------------------
    # Convert results to comparison table.
    # --------------------------------------------------------

    rows = []

    for result in all_results:

        metrics = result["test_metrics"]

        rows.append({
            "horizon": result["horizon"],
            "experiment": result["experiment"],
            "feature_count": result["feature_count"],
            "test_MAE": metrics["MAE"],
            "test_RMSE": metrics["RMSE"],
            "test_R2": metrics["R2"],
            "test_Bias": metrics["Bias"],
            "test_MedAE": metrics["MedAE"],
        })

    results_df = pd.DataFrame(rows)

    # --------------------------------------------------------
    # Calculate improvement relative to baseline.
    #
    # Positive MAE improvement = better.
    # --------------------------------------------------------

    results_df["MAE_change_vs_baseline_pct"] = np.nan
    results_df["RMSE_change_vs_baseline_pct"] = np.nan

    for horizon in HORIZONS:

        baseline_mask = (
            (results_df["horizon"] == horizon)
            & (results_df["experiment"] == "Baseline")
        )

        baseline_mae = float(
            results_df.loc[
                baseline_mask,
                "test_MAE",
            ].iloc[0]
        )

        baseline_rmse = float(
            results_df.loc[
                baseline_mask,
                "test_RMSE",
            ].iloc[0]
        )

        horizon_mask = (
            results_df["horizon"] == horizon
        )

        results_df.loc[
            horizon_mask,
            "MAE_change_vs_baseline_pct"
        ] = (
            (baseline_mae
             - results_df.loc[
                 horizon_mask,
                 "test_MAE",
             ])
            / baseline_mae
            * 100
        )

        results_df.loc[
            horizon_mask,
            "RMSE_change_vs_baseline_pct"
        ] = (
            (baseline_rmse
             - results_df.loc[
                 horizon_mask,
                 "test_RMSE",
             ])
            / baseline_rmse
            * 100
        )

    # --------------------------------------------------------
    # Print final table.
    # --------------------------------------------------------

    print()
    print("=" * 110)
    print("PHYSICS ABLATION - TEST RESULTS")
    print("=" * 110)

    display_columns = [
        "horizon",
        "experiment",
        "feature_count",
        "test_MAE",
        "test_RMSE",
        "test_R2",
        "test_Bias",
        "MAE_change_vs_baseline_pct",
        "RMSE_change_vs_baseline_pct",
    ]

    print(
        results_df[
            display_columns
        ].to_string(
            index=False,
            float_format=lambda x: f"{x:.3f}",
        )
    )

    # --------------------------------------------------------
    # Best experiment by horizon.
    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("BEST PHYSICS GROUP BY HORIZON")
    print("=" * 80)

    for horizon in HORIZONS:

        subset = results_df[
            results_df["horizon"] == horizon
        ].copy()

        best = subset.loc[
            subset["test_MAE"].idxmin()
        ]

        print(
            f"{horizon}h: "
            f"{best['experiment']} | "
            f"MAE={best['test_MAE']:.3f} | "
            f"change={best['MAE_change_vs_baseline_pct']:.2f}%"
        )

    # --------------------------------------------------------
    # Save CSV.
    # --------------------------------------------------------

    csv_path = (
        REPORT_DIR
        / "physics_ablation_results.csv"
    )

    results_df.to_csv(
        csv_path,
        index=False,
    )

    # --------------------------------------------------------
    # Save complete JSON.
    # --------------------------------------------------------

    json_path = (
        REPORT_DIR
        / "physics_ablation_results.json"
    )

    report = {
        "experiment": "physics_feature_ablation",
        "dataset": str(DATA_PATH),
        "baseline_feature_count": len(
            BASELINE_FEATURES
        ),
        "physics_groups": PHYSICS_GROUPS,
        "split": {
            "train_end": str(TRAIN_END),
            "validation_end": str(VALID_END),
            "test_end": str(TEST_END),
        },
        "results": all_results,
        "comparison_table": results_df.to_dict(
            orient="records"
        ),
    }

    with open(
        json_path,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            report,
            f,
            indent=2,
        )

    print()
    print("Saved:")
    print(f"  {csv_path}")
    print(f"  {json_path}")

    print()
    print("=" * 80)
    print("ABLATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
