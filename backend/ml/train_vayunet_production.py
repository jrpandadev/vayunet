"""
VayuNet Production PM2.5 Forecasting Models

Production configuration:
    6h  -> S6 = S5 + Episode Dynamics
    24h -> S5 = S4 + Satellite + PM10 + NWP
    72h -> S6 = S5 + Episode Dynamics

This trainer preserves the feature composition, chronological split,
matched-row evaluation protocol, and XGBoost parameters used in the
validated S4/S5/S6 experiments.
"""

from pathlib import Path
import json
import time

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

S5_DATA_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "fusion"
    / "delhi_forecasting_s5_nwp.csv"
)

EPISODE_DATA_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "fusion"
    / "delhi_forecasting_episode.csv"
)

HORIZON_METADATA_FILE = (
    BASE_DIR
    / "models"
    / "horizon_features.json"
)

BEST_PARAMS_FILE = (
    BASE_DIR
    / "ml"
    / "results"
    / "satellite"
    / "s4_best_params.json"
)

MODELS_DIR = BASE_DIR / "models"

REPORT_DIR = (
    BASE_DIR
    / "reports"
    / "final_production"
)

MODELS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

REPORT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# HORIZONS
# ============================================================

HORIZONS = {
    "6h": 6,
    "24h": 24,
    "72h": 72,
}

TARGETS = {
    "6h": "target_pm25_6h",
    "24h": "target_pm25_24h",
    "72h": "target_pm25_72h",
}


# ============================================================
# CHRONOLOGICAL SPLIT
# ============================================================

TRAIN_END = pd.Timestamp(
    "2024-10-01 13:00:00"
)

VALID_END = pd.Timestamp(
    "2025-08-30 15:00:00"
)

TEST_END = pd.Timestamp(
    "2026-08-31 23:00:00"
)


# ============================================================
# FEATURE GROUPS
# ============================================================

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

NWP_BASE_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "surface_pressure",
    "wind_speed_10m",
    "wind_direction_10m",
    "boundary_layer_height",
]

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


# ============================================================
# PRODUCTION EPISODE GATING
# ============================================================

USE_EPISODE = {
    "6h": True,
    "24h": False,
    "72h": True,
}


# ============================================================
# METRICS
# ============================================================

def evaluate_predictions(
    y_true,
    y_pred,
):
    errors = y_pred - y_true

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
            np.mean(errors)
        ),
        "MedAE": float(
            np.median(
                np.abs(errors)
            )
        ),
    }


# ============================================================
# LOAD DATA
# ============================================================

def load_data():

    print(
        f"Loading S5 data:\n  {S5_DATA_FILE}"
    )

    s5_df = pd.read_csv(
        S5_DATA_FILE,
        parse_dates=["timestamp"],
    )

    print(
        f"S5 rows: {len(s5_df):,}"
    )

    print(
        f"Loading Episode data:\n  "
        f"{EPISODE_DATA_FILE}"
    )

    ep_df = pd.read_csv(
        EPISODE_DATA_FILE,
        usecols=EPISODE_FEATURES,
    )

    print(
        f"Episode rows: {len(ep_df):,}"
    )

    # --------------------------------------------------------
    # Mandatory row-alignment check
    # --------------------------------------------------------

    if len(s5_df) != len(ep_df):
        raise RuntimeError(
            "S5 and Episode row counts differ."
        )

    if len(s5_df) != 383303:
        raise RuntimeError(
            "Unexpected canonical row count."
        )

    print(
        "Row counts aligned: PASS"
    )

    # --------------------------------------------------------
    # Concatenate only after alignment was verified
    # --------------------------------------------------------

    df = pd.concat(
        [
            s5_df,
            ep_df,
        ],
        axis=1,
    )

    df = df.rename(
        columns={
            "timestamp": "Timestamp"
        }
    )

    df = df.sort_values(
        "Timestamp"
    ).reset_index(
        drop=True
    )

    # --------------------------------------------------------
    # Station encoding
    # --------------------------------------------------------

    if "station_id" in df.columns:

        df = pd.get_dummies(
            df,
            columns=["station_id"],
            dtype=int,
        )

    # Remove accidental duplicate columns.
    df = df.loc[
        :,
        ~df.columns.duplicated()
    ].copy()

    return df


# ============================================================
# BUILD FEATURE SET
# ============================================================

def build_features(
    metadata,
    horizon,
    use_episode,
):

    canonical_features = metadata[
        "horizon_features"
    ][horizon]

    horizon_hours = HORIZONS[horizon]

    nwp_features = [
        f"nwp_{variable}_{horizon_hours}h"
        for variable in NWP_BASE_VARS
    ]

    s4_features = (
        canonical_features
        + SATELLITE_FEATURES
        + PM10_FEATURES
    )

    s5_features = (
        s4_features
        + nwp_features
    )

    if use_episode:

        final_features = (
            s5_features
            + EPISODE_FEATURES
        )

    else:

        final_features = s5_features

    # Preserve order while removing duplicates.
    final_features = list(
        dict.fromkeys(
            final_features
        )
    )

    return (
        s4_features,
        s5_features,
        final_features,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print("VAYUNET PRODUCTION MODEL TRAINING")
    print("=" * 80)

    print("\nProduction configuration:")

    for horizon in HORIZONS:

        model_type = (
            "S6 (S5 + Episode)"
            if USE_EPISODE[horizon]
            else "S5 (S4 + Satellite + PM10 + NWP)"
        )

        print(
            f"  {horizon}: {model_type}"
        )

    # --------------------------------------------------------
    # Load metadata
    # --------------------------------------------------------

    with open(
        HORIZON_METADATA_FILE,
        "r",
        encoding="utf-8",
    ) as f:

        metadata = json.load(f)

    # --------------------------------------------------------
    # Load exact validated parameters
    # --------------------------------------------------------

    with open(
        BEST_PARAMS_FILE,
        "r",
        encoding="utf-8",
    ) as f:

        best_params = json.load(f)

    # --------------------------------------------------------
    # Load combined dataset
    # --------------------------------------------------------

    df = load_data()

    print(
        f"\nCombined rows: {len(df):,}"
    )

    results = []

    # ========================================================
    # TRAIN EACH HORIZON
    # ========================================================

    for horizon, horizon_hours in HORIZONS.items():

        print("\n" + "=" * 80)
        print(
            f"PRODUCTION MODEL — {horizon}"
        )
        print("=" * 80)

        target = TARGETS[horizon]

        use_episode = USE_EPISODE[horizon]

        # ----------------------------------------------------
        # Feature composition
        # ----------------------------------------------------

        (
            s4_features,
            s5_features,
            final_features,
        ) = build_features(
            metadata,
            horizon,
            use_episode,
        )

        nwp_features = [
            f"nwp_{variable}_{horizon_hours}h"
            for variable in NWP_BASE_VARS
        ]

        print(
            f"\nModel family: "
            f"{'S6' if use_episode else 'S5'}"
        )

        print(
            f"S4 feature count: "
            f"{len(s4_features)}"
        )

        print(
            f"S5 feature count: "
            f"{len(s5_features)}"
        )

        print(
            f"Episode enabled: "
            f"{use_episode}"
        )

        print(
            f"Final feature count: "
            f"{len(final_features)}"
        )

        # ----------------------------------------------------
        # Verify all required columns exist
        # ----------------------------------------------------

        missing_features = [
            feature
            for feature in final_features
            if feature not in df.columns
        ]

        if missing_features:

            raise RuntimeError(
                f"Missing features for {horizon}: "
                f"{missing_features}"
            )

        if target not in df.columns:

            raise RuntimeError(
                f"Missing target: {target}"
            )

        # ----------------------------------------------------
        # Matched-row protocol
        #
        # Same protocol used in rigorous S5/S6 validation:
        #
        # target must exist
        # AND all NWP variables must exist
        # ----------------------------------------------------

        matched_mask = df[target].notna()

        for feature in nwp_features:

            if feature not in df.columns:

                raise RuntimeError(
                    f"Missing NWP feature: "
                    f"{feature}"
                )

            matched_mask &= (
                df[feature].notna()
            )

        matched_df = df[
            matched_mask
        ].copy()

        print(
            f"\nMatched rows: "
            f"{len(matched_df):,}"
        )

        # ----------------------------------------------------
        # Chronological split
        # ----------------------------------------------------

        train = matched_df[
            matched_df["Timestamp"]
            < TRAIN_END
        ]

        valid = matched_df[
            (
                matched_df["Timestamp"]
                >= TRAIN_END
            )
            &
            (
                matched_df["Timestamp"]
                < VALID_END
            )
        ]

        test = matched_df[
            (
                matched_df["Timestamp"]
                >= VALID_END
            )
            &
            (
                matched_df["Timestamp"]
                <= TEST_END
            )
        ]

        print(
            f"Train: {len(train):,}"
        )

        print(
            f"Valid: {len(valid):,}"
        )

        print(
            f"Test : {len(test):,}"
        )

        # ----------------------------------------------------
        # Final training set = TRAIN + VALID
        # ----------------------------------------------------

        train_valid = pd.concat(
            [
                train,
                valid,
            ],
            axis=0,
        )

        X_train = train_valid[
            final_features
        ]

        y_train = train_valid[
            target
        ]

        X_test = test[
            final_features
        ]

        y_test = test[
            target
        ].to_numpy()

        # ----------------------------------------------------
        # Parameters
        # ----------------------------------------------------

        params_entry = best_params[
            horizon
        ]

        params = params_entry[
            "params"
        ]

        best_iteration = int(
            params_entry[
                "best_iteration"
            ]
        )

        print(
            "\nXGBoost parameters:"
        )

        print(
            json.dumps(
                params,
                indent=2,
            )
        )

        print(
            f"n_estimators: "
            f"{best_iteration}"
        )

        # ----------------------------------------------------
        # Model
        # ----------------------------------------------------

        model = xgb.XGBRegressor(
            **params,
            n_estimators=best_iteration,
            objective="reg:squarederror",
            random_state=42,
            tree_method="hist",
            device="cuda",
        )

        print(
            "\nStarting GPU training..."
        )

        start_time = time.time()

        model.fit(
            X_train,
            y_train,
            verbose=False,
        )

        training_seconds = (
            time.time()
            - start_time
        )

        print(
            f"Training completed in "
            f"{training_seconds:.1f}s"
        )

        # ----------------------------------------------------
        # Test evaluation
        # ----------------------------------------------------

        predictions = model.predict(
            X_test
        )

        metrics = evaluate_predictions(
            y_test,
            predictions,
        )

        print(
            "\nFINAL TEST METRICS"
        )

        for name, value in metrics.items():

            print(
                f"  {name}: "
                f"{value:.6f}"
            )

        # ----------------------------------------------------
        # Save model
        # ----------------------------------------------------

        model_family = (
            "s6"
            if use_episode
            else "s5"
        )

        model_path = (
            MODELS_DIR
            / (
                f"xgb_vayunet_pm25_"
                f"{horizon}_{model_family}_production.joblib"
            )
        )

        joblib.dump(
            model,
            model_path,
        )

        print(
            f"\nSaved model:\n  "
            f"{model_path}"
        )

        # ----------------------------------------------------
        # Record results
        # ----------------------------------------------------

        results.append(
            {
                "horizon": horizon,
                "model_family": model_family,
                "episode_enabled": use_episode,
                "feature_count": len(
                    final_features
                ),
                "train_rows": len(train),
                "valid_rows": len(valid),
                "test_rows": len(test),
                "best_iteration": best_iteration,
                "training_seconds": training_seconds,
                "MAE": metrics["MAE"],
                "RMSE": metrics["RMSE"],
                "R2": metrics["R2"],
                "bias": metrics["bias"],
                "MedAE": metrics["MedAE"],
                "model_path": str(
                    model_path
                ),
            }
        )

    # ========================================================
    # SAVE FINAL REPORT
    # ========================================================

    results_df = pd.DataFrame(
        results
    )

    csv_path = (
        REPORT_DIR
        / "vayunet_production_test_results.csv"
    )

    json_path = (
        REPORT_DIR
        / "vayunet_production_test_results.json"
    )

    results_df.to_csv(
        csv_path,
        index=False,
    )

    results_df.to_json(
        json_path,
        orient="records",
        indent=2,
    )

    print("\n" + "=" * 80)
    print(
        "VAYUNET PRODUCTION TRAINING COMPLETE"
    )
    print("=" * 80)

    print(
        results_df.to_string(
            index=False
        )
    )

    print(
        f"\nCSV report: {csv_path}"
    )

    print(
        f"JSON report: {json_path}"
    )


if __name__ == "__main__":
    main()
