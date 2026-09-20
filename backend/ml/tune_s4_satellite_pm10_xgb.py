import os
import sys
import json
import random
import time
from pathlib import Path
from typing import Dict, Any

import pandas as pd
import numpy as np
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
import xgboost as xgb


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

DATA_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "fusion"
    / "delhi_forecasting_satellite_pm10.csv"
)

HORIZON_METADATA_FILE = (
    BASE_DIR
    / "models"
    / "horizon_features.json"
)

RESULTS_DIR = (
    BASE_DIR
    / "ml"
    / "results"
    / "satellite"
)

RESULTS_CSV = RESULTS_DIR / "s4_tuning_results.csv"
BEST_PARAMS_JSON = RESULTS_DIR / "s4_best_params.json"


TARGETS = {
    "6h": "target_pm25_6h",
    "24h": "target_pm25_24h",
    "72h": "target_pm25_72h",
}

HORIZONS = ["6h", "24h", "72h"]

SATELLITE_FEATURES = [
    "satellite_no2_latest",
    "satellite_no2_age_hours",
]

PM10_FEATURES = [
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
# DATA LOADING
# ============================================================

def load_data():

    print(f"Loading data from:\n{DATA_FILE}")

    df = pd.read_csv(
        DATA_FILE,
        parse_dates=["timestamp"],
    )

    if "timestamp" in df.columns and "Timestamp" not in df.columns:
        df.rename(
            columns={"timestamp": "Timestamp"},
            inplace=True,
        )

    df = (
        df
        .sort_values(by="Timestamp")
        .reset_index(drop=True)
    )

    # --------------------------------------------------------
    # Encode station ID exactly as in the original tuner
    # --------------------------------------------------------

    existing_dummies = [c for c in df.columns if c.startswith("station_id_")]
    if existing_dummies:
        df = df.drop(columns=existing_dummies)

    df_encoded = pd.get_dummies(
        df,
        columns=["station_id"],
        dtype=int,
    )

    # --------------------------------------------------------
    # EXACT SAME TEMPORAL SPLIT AS S0
    # --------------------------------------------------------

    train_end = pd.to_datetime(
        "2024-10-01 13:00:00"
    )

    val_end = pd.to_datetime(
        "2025-08-30 15:00:00"
    )

    test_end = pd.to_datetime(
        "2026-08-31 23:00:00"
    )

    train_df = df_encoded[
        df_encoded["Timestamp"] < train_end
    ].copy()

    val_df = df_encoded[
        (df_encoded["Timestamp"] >= train_end)
        &
        (df_encoded["Timestamp"] < val_end)
    ].copy()

    test_df = df_encoded[
        (df_encoded["Timestamp"] >= val_end)
        &
        (df_encoded["Timestamp"] <= test_end)
    ].copy()

    # --------------------------------------------------------
    # Sanity checks
    # --------------------------------------------------------

    assert (
        train_df["Timestamp"].max()
        <
        val_df["Timestamp"].min()
    ), "Leakage: Train/Validation overlap."

    assert (
        val_df["Timestamp"].max()
        <
        test_df["Timestamp"].min()
    ), "Leakage: Validation/Test overlap."

    print("\nSplit sizes:")
    print(f"Train:      {len(train_df):,}")
    print(f"Validation: {len(val_df):,}")
    print(f"Test:       {len(test_df):,}")

    return train_df, val_df, test_df


# ============================================================
# METRICS
# ============================================================

def evaluate_predictions(y_true, y_pred):

    err = y_pred - y_true

    return {
        "MAE": float(
            mean_absolute_error(
                y_true,
                y_pred,
            )
        ),

        "RMSE": float(
            np.sqrt(
                mean_squared_error(
                    y_true,
                    y_pred,
                )
            )
        ),

        "R2": float(
            r2_score(
                y_true,
                y_pred,
            )
        ),

        "bias": float(
            np.mean(err)
        ),

        "MedAE": float(
            np.median(
                np.abs(err)
            )
        ),
    }


# ============================================================
# MAIN
# ============================================================

def main():

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # Load canonical S0 feature metadata
    # --------------------------------------------------------

    with open(
        HORIZON_METADATA_FILE,
        "r",
    ) as f:

        meta = json.load(f)

    horizon_features = meta[
        "horizon_features"
    ]

    # --------------------------------------------------------
    # Load data
    # --------------------------------------------------------

    train_df, val_df, test_df = load_data()

    # --------------------------------------------------------
    # Verify satellite features
    # --------------------------------------------------------

    for feature in SATELLITE_FEATURES:

        assert (
            feature in train_df.columns
        ), f"Missing satellite feature: {feature}"

    # --------------------------------------------------------
    # Verify PM10 features
    # --------------------------------------------------------

    for feature in PM10_FEATURES:

        assert (
            feature in train_df.columns
        ), f"Missing PM10 feature: {feature}"

    # --------------------------------------------------------
    # Verify canonical S0 features
    # --------------------------------------------------------

    for horizon in HORIZONS:

        assert (
            horizon in horizon_features
        ), f"Missing metadata for {horizon}"

        missing = [
            f
            for f in horizon_features[horizon]
            if f not in train_df.columns
        ]

        assert not missing, (
            f"Missing canonical features for "
            f"{horizon}: {missing}"
        )

    # ========================================================
    # SAME SEARCH SPACE AS ORIGINAL S0 TUNER
    # ========================================================

    param_grid = {

        "max_depth": [
            3, 4, 5, 6, 7, 8
        ],

        "min_child_weight": [
            1, 3, 5, 7, 10
        ],

        "learning_rate": [
            0.02,
            0.05,
            0.08,
            0.1,
        ],

        "subsample": [
            0.7,
            0.8,
            0.9,
            1.0,
        ],

        "colsample_bytree": [
            0.7,
            0.8,
            0.9,
            1.0,
        ],
    }

    # EXACT SAME NUMBER OF TRIALS
    n_iter = 20

    # EXACT SAME RANDOM SEED
    random.seed(42)

    results_list = []

    best_params_all = {}

    print("\n" + "=" * 72)
    print("S4 SATELLITE + PM10 XGBOOST TUNING")
    print("=" * 72)

    print(
        f"\nRandom Search: "
        f"{n_iter} trials per horizon"
    )

    print(
        "\nS4 feature definition:"
    )

    print(
        "S0 canonical features"
        "\n+ satellite_no2_latest"
        "\n+ satellite_no2_age_hours"
        "\n+ historical PM10 features"
    )

    # ========================================================
    # HORIZON LOOP
    # ========================================================

    for horizon in HORIZONS:

        print("\n" + "=" * 72)
        print(f"HORIZON: {horizon}")
        print("=" * 72)

        canonical_features = (
            horizon_features[horizon]
        )

        features = (
            canonical_features
            +
            SATELLITE_FEATURES
            +
            PM10_FEATURES
        )

        target = TARGETS[horizon]

        print(
            f"\nCanonical features: "
            f"{len(canonical_features)}"
        )

        print(
            f"Satellite features: "
            f"{len(SATELLITE_FEATURES)}"
        )

        print(
            f"PM10 features:      "
            f"{len(PM10_FEATURES)}"
        )

        print(
            f"Total S4 features: "
            f"{len(features)}"
        )

        # ----------------------------------------------------
        # Target-valid masks
        # ----------------------------------------------------

        t_mask = (
            train_df[target].notna()
        )

        v_mask = (
            val_df[target].notna()
        )

        X_train = train_df.loc[
            t_mask,
            features,
        ]

        y_train = train_df.loc[
            t_mask,
            target,
        ]

        X_val = val_df.loc[
            v_mask,
            features,
        ]

        y_val = val_df.loc[
            v_mask,
            target,
        ]

        print(
            f"\nTarget-valid rows:"
        )

        print(
            f"  Train:      {len(X_train):,}"
        )

        print(
            f"  Validation: {len(X_val):,}"
        )

        # ----------------------------------------------------
        # Satellite coverage
        # ----------------------------------------------------

        train_sat_available = (
            X_train[
                "satellite_no2_latest"
            ].notna().mean()
            * 100
        )

        val_sat_available = (
            X_val[
                "satellite_no2_latest"
            ].notna().mean()
            * 100
        )

        print(
            f"\nSatellite availability:"
        )

        print(
            f"  Train:      "
            f"{train_sat_available:.2f}%"
        )

        print(
            f"  Validation: "
            f"{val_sat_available:.2f}%"
        )

        # ----------------------------------------------------
        # PM10 coverage
        # ----------------------------------------------------

        train_pm10_available = (
            X_train[
                "PM10_lag_1h"
            ].notna().mean()
            * 100
        )

        val_pm10_available = (
            X_val[
                "PM10_lag_1h"
            ].notna().mean()
            * 100
        )

        print(
            f"\nPM10 feature availability:"
        )

        print(
            f"  Train:      "
            f"{train_pm10_available:.2f}%"
        )

        print(
            f"  Validation: "
            f"{val_pm10_available:.2f}%"
        )

        # ----------------------------------------------------
        # Search
        # ----------------------------------------------------

        best_mae = float("inf")

        best_params = None

        best_iter_round = None

        best_metrics = None

        horizon_start = time.time()

        for i in range(n_iter):

            params = {
                k: random.choice(v)
                for k, v in param_grid.items()
            }

            model = xgb.XGBRegressor(

                **params,

                # SAME AS ORIGINAL TUNER
                n_estimators=2000,

                # SAME EARLY STOPPING
                early_stopping_rounds=50,

                # SAME METRIC
                eval_metric="mae",

                objective="reg:squarederror",

                # SAME SEED
                random_state=42,

                n_jobs=-1,
            )

            model.fit(
                X_train,
                y_train,

                eval_set=[
                    (X_val, y_val)
                ],

                verbose=False,
            )

            best_iter = getattr(
                model,
                "best_iteration",
                2000,
            )

            y_pred_val = model.predict(
                X_val
            )

            metrics = evaluate_predictions(
                y_val,
                y_pred_val,
            )

            results_list.append({

                "horizon": horizon,

                "feature_set":
                    f"s4_{len(features)}",

                "canonical_feature_count":
                    len(canonical_features),

                "satellite_feature_count":
                    len(SATELLITE_FEATURES),

                "pm10_feature_count":
                    len(PM10_FEATURES),

                "total_feature_count":
                    len(features),

                "max_depth":
                    params["max_depth"],

                "min_child_weight":
                    params["min_child_weight"],

                "learning_rate":
                    params["learning_rate"],

                "subsample":
                    params["subsample"],

                "colsample_bytree":
                    params["colsample_bytree"],

                "best_iteration":
                    best_iter,

                "validation MAE":
                    metrics["MAE"],

                "validation RMSE":
                    metrics["RMSE"],

                "validation R2":
                    metrics["R2"],

                "validation bias":
                    metrics["bias"],

                "validation MedAE":
                    metrics["MedAE"],
            })

            if (
                metrics["MAE"]
                <
                best_mae
            ):

                best_mae = (
                    metrics["MAE"]
                )

                best_params = params

                best_iter_round = (
                    best_iter
                )

                best_metrics = metrics

            print(
                f"Trial {i + 1:02d}/{n_iter} | "
                f"MAE: {metrics['MAE']:.4f} | "
                f"RMSE: {metrics['RMSE']:.4f} | "
                f"Best iteration: {best_iter} | "
                f"Params: {params}"
            )

        elapsed = (
            time.time()
            - horizon_start
        )

        # ----------------------------------------------------
        # Save best configuration
        # ----------------------------------------------------

        best_params_all[horizon] = {

            "params": best_params,

            "best_iteration":
                best_iter_round,

            "validation_metrics":
                best_metrics,

            "canonical_feature_count":
                len(canonical_features),

            "satellite_features":
                SATELLITE_FEATURES,

            "pm10_features":
                PM10_FEATURES,

            "total_feature_count":
                len(features),

            "train_satellite_availability_pct":
                float(train_sat_available),

            "validation_satellite_availability_pct":
                float(val_sat_available),

            "train_pm10_availability_pct":
                float(train_pm10_available),

            "validation_pm10_availability_pct":
                float(val_pm10_available),

            "tuning_seconds":
                float(elapsed),
        }

        print(
            f"\nBEST {horizon}"
        )

        print(
            f"Parameters: "
            f"{best_params}"
        )

        print(
            f"Best iteration: "
            f"{best_iter_round}"
        )

        print(
            f"Validation metrics: "
            f"{best_metrics}"
        )

        print(
            f"Tuning time: "
            f"{elapsed / 60:.1f} minutes"
        )

    # ========================================================
    # SAVE RESULTS
    # ========================================================

    results_df = pd.DataFrame(
        results_list
    )

    results_df.to_csv(
        RESULTS_CSV,
        index=False,
    )

    print(
        f"\nTrial results saved to:"
        f"\n{RESULTS_CSV}"
    )

    with open(
        BEST_PARAMS_JSON,
        "w",
    ) as f:

        json.dump(
            best_params_all,
            f,
            indent=2,
        )

    print(
        f"\nBest configurations saved to:"
        f"\n{BEST_PARAMS_JSON}"
    )

    # ========================================================
    # FINAL REPORT
    # ========================================================

    print("\n" + "=" * 72)
    print("S4 TUNING COMPLETE")
    print("=" * 72)

    for horizon in HORIZONS:

        best = (
            best_params_all[horizon]
        )

        print(
            f"\n{horizon}"
        )

        print(
            f"  Best params: "
            f"{best['params']}"
        )

        print(
            f"  Best iteration: "
            f"{best['best_iteration']}"
        )

        print(
            f"  Validation MAE: "
            f"{best['validation_metrics']['MAE']:.4f}"
        )

        print(
            f"  Validation RMSE: "
            f"{best['validation_metrics']['RMSE']:.4f}"
        )

        print(
            f"  Validation R²: "
            f"{best['validation_metrics']['R2']:.4f}"
        )

    print(
        "\nNo test-set data was used during tuning."
    )

    print(
        "S0 remains frozen."
    )


if __name__ == "__main__":
    main()
