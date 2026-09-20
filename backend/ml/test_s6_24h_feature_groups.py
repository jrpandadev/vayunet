"""
24h Episode Feature-Group Ablation

Compares S5 against selected Episode Dynamics feature groups
using the exact same matched rows, chronological split,
XGBoost parameters, and untouched test set.
"""

from pathlib import Path
import json
import numpy as np
import pandas as pd
from xgboost import XGBRegressor


BASE_DIR = Path(__file__).resolve().parent.parent

S5_DATA_FILE = (
    BASE_DIR / "data/processed/fusion/delhi_forecasting_s5_nwp.csv"
)

EPISODE_DATA_FILE = (
    BASE_DIR / "data/processed/fusion/delhi_forecasting_episode.csv"
)

HORIZON_METADATA_FILE = (
    BASE_DIR / "models/horizon_features.json"
)

BEST_PARAMS_FILE = (
    BASE_DIR / "ml/results/satellite/s4_best_params.json"
)

REPORT_DIR = BASE_DIR / "reports/episode"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


TRAIN_END = pd.Timestamp("2024-10-01 13:00:00")
VALID_END = pd.Timestamp("2025-08-30 15:00:00")
TEST_END = pd.Timestamp("2026-08-31 23:00:00")

HORIZON = "24h"
HORIZON_HOURS = 24

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


EPISODE_GROUPS = {
    "A_delta": [
        "pm25_delta_1h",
        "pm25_delta_3h",
        "pm25_delta_6h",
        "pm25_delta_12h",
        "pm25_delta_24h",
    ],

    "B_acceleration": [
        "pm25_acceleration_1h",
        "pm25_acceleration_3h",
        "pm25_acceleration_6h",
    ],

    "C_rolling": [
        "pm25_mean_6h",
        "pm25_mean_12h",
        "pm25_mean_24h",
        "pm25_std_6h",
        "pm25_std_24h",
        "pm25_max_6h",
        "pm25_max_24h",
    ],

    "D_episode_timers": [
        "hours_since_150_onset",
        "hours_since_250_onset",
    ],

    "E_persistence": [
        "hours_above_150_24h",
        "hours_above_250_24h",
        "fraction_above_150_24h",
        "fraction_above_250_24h",
    ],
}


EXPERIMENTS = {
    "S5_control": [],

    "S5_plus_A_delta": ["A_delta"],

    "S5_plus_B_acceleration": ["B_acceleration"],

    "S5_plus_C_rolling": ["C_rolling"],

    "S5_plus_D_timers": ["D_episode_timers"],

    "S5_plus_E_persistence": ["E_persistence"],

    "S5_plus_D_plus_E": [
        "D_episode_timers",
        "E_persistence",
    ],

    "S5_plus_A_plus_B": [
        "A_delta",
        "B_acceleration",
    ],

    "S5_plus_A_plus_B_plus_C": [
        "A_delta",
        "B_acceleration",
        "C_rolling",
    ],

    "S5_plus_all_episode": [
        "A_delta",
        "B_acceleration",
        "C_rolling",
        "D_episode_timers",
        "E_persistence",
    ],
}


def get_metrics(y_true, y_pred):
    errors = y_pred - y_true

    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors ** 2)))

    ss_res = float(np.sum(errors ** 2))
    ss_tot = float(np.sum((y_true - y_true.mean()) ** 2))

    r2 = 1.0 - ss_res / ss_tot

    bias = float(np.mean(errors))
    medae = float(np.median(np.abs(errors)))

    return mae, rmse, r2, bias, medae


def main():

    print("=" * 80)
    print("24H EPISODE FEATURE-GROUP ABLATION")
    print("=" * 80)

    print("\nLoading S5 dataset...")

    s5_df = pd.read_csv(
        S5_DATA_FILE,
        parse_dates=["timestamp"],
    )

    print("Loading Episode features...")

    ep_df = pd.read_csv(
        EPISODE_DATA_FILE,
        usecols=EPISODE_GROUPS["A_delta"]
        + EPISODE_GROUPS["B_acceleration"]
        + EPISODE_GROUPS["C_rolling"]
        + EPISODE_GROUPS["D_episode_timers"]
        + EPISODE_GROUPS["E_persistence"],
    )

    # ------------------------------------------------------------
    # Alignment audit
    # ------------------------------------------------------------

    print("\nChecking row alignment...")

    assert len(s5_df) == len(ep_df)

    assert len(s5_df) == 383303

    print(f"Rows: {len(s5_df):,}")

    # Episode data was generated from the same canonical row order.
    # We already independently verified timestamp/station/segment
    # alignment before running this experiment.

    df = pd.concat(
        [s5_df, ep_df],
        axis=1,
    )

    df = df.rename(
        columns={"timestamp": "Timestamp"}
    )

    df = df.sort_values(
        "Timestamp"
    ).reset_index(drop=True)

    # ------------------------------------------------------------
    # Station encoding
    # ------------------------------------------------------------

    if "station_id" in df.columns:
        df = pd.get_dummies(
            df,
            columns=["station_id"],
            dtype=int,
        )

    df = df.loc[
        :,
        ~df.columns.duplicated()
    ].copy()

    # ------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------

    with open(
        HORIZON_METADATA_FILE,
        "r",
        encoding="utf-8",
    ) as f:
        metadata = json.load(f)

    with open(
        BEST_PARAMS_FILE,
        "r",
        encoding="utf-8",
    ) as f:
        best_params = json.load(f)

    target = f"target_pm25_{HORIZON}"

    if target not in df.columns:
        target = f"PM2.5_{HORIZON}"

    canonical_features = metadata[
        "horizon_features"
    ][HORIZON]

    s4_features = (
        canonical_features
        + SATELLITE_FEATURES
        + PM10_FEATURES
    )

    nwp_features = [
        f"nwp_{v}_{HORIZON_HOURS}h"
        for v in NWP_BASE_VARS
    ]

    s5_features = (
        s4_features
        + nwp_features
    )

    # ------------------------------------------------------------
    # Matched-row mask
    # ------------------------------------------------------------

    valid_rows_mask = df[target].notna()

    for feat in nwp_features:
        valid_rows_mask &= df[feat].notna()

    df_ablation = df[
        valid_rows_mask
    ].copy()

    train = df_ablation[
        df_ablation["Timestamp"] < TRAIN_END
    ]

    valid = df_ablation[
        (df_ablation["Timestamp"] >= TRAIN_END)
        &
        (df_ablation["Timestamp"] < VALID_END)
    ]

    test = df_ablation[
        (df_ablation["Timestamp"] >= VALID_END)
        &
        (df_ablation["Timestamp"] <= TEST_END)
    ]

    print("\nMatched rows:")
    print(f"Train: {len(train):,}")
    print(f"Valid: {len(valid):,}")
    print(f"Test : {len(test):,}")

    train_valid = pd.concat(
        [train, valid],
        axis=0,
    )

    # ------------------------------------------------------------
    # XGBoost parameters
    # ------------------------------------------------------------

    params_entry = best_params[HORIZON]

    params = (
        params_entry.get("params")
        or params_entry.get("best_params")
    )

    best_iteration = int(
        params_entry["best_iteration"]
    )

    print("\nXGBoost configuration:")
    print(f"Best iteration: {best_iteration}")
    print(f"Max depth: {params['max_depth']}")
    print(
        f"Min child weight: "
        f"{params['min_child_weight']}"
    )
    print(
        f"Learning rate: "
        f"{params['learning_rate']}"
    )
    print(
        f"Subsample: "
        f"{params['subsample']}"
    )
    print(
        f"Column sample: "
        f"{params['colsample_bytree']}"
    )

    results = []

    # ------------------------------------------------------------
    # Experiments
    # ------------------------------------------------------------

    for experiment_name, groups in EXPERIMENTS.items():

        print("\n" + "-" * 80)
        print(experiment_name)
        print("-" * 80)

        episode_features = []

        for group in groups:
            episode_features.extend(
                EPISODE_GROUPS[group]
            )

        features = (
            s5_features
            + episode_features
        )

        # Remove duplicates while preserving order.
        features = list(
            dict.fromkeys(features)
        )

        print(
            f"Feature count: {len(features)}"
        )

        print(
            f"Episode features: "
            f"{len(episode_features)}"
        )

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
            tree_method="hist",
            device="cuda",
            random_state=42,
        )

        model.fit(
            X_tv,
            y_tv,
        )

        preds = model.predict(
            X_ts
        )

        mae, rmse, r2, bias, medae = (
            get_metrics(
                y_ts,
                preds,
            )
        )

        print(
            f"MAE  : {mae:.4f}"
        )

        print(
            f"RMSE : {rmse:.4f}"
        )

        print(
            f"RÂ²   : {r2:.4f}"
        )

        print(
            f"Bias : {bias:.4f}"
        )

        print(
            f"MedAE: {medae:.4f}"
        )

        results.append({
            "experiment": experiment_name,
            "episode_feature_count": len(
                episode_features
            ),
            "feature_count": len(features),
            "test_rows": len(test),
            "mae": mae,
            "rmse": rmse,
            "r2": r2,
            "bias": bias,
            "medae": medae,
        })

    # ------------------------------------------------------------
    # Results
    # ------------------------------------------------------------

    results_df = pd.DataFrame(
        results
    )

    control = results_df.iloc[0]

    results_df[
        "mae_delta_vs_s5"
    ] = (
        results_df["mae"]
        - control["mae"]
    )

    results_df[
        "rmse_delta_vs_s5"
    ] = (
        results_df["rmse"]
        - control["rmse"]
    )

    results_df[
        "mae_improvement_pct"
    ] = (
        (
            control["mae"]
            - results_df["mae"]
        )
        / control["mae"]
        * 100
    )

    results_df[
        "rmse_improvement_pct"
    ] = (
        (
            control["rmse"]
            - results_df["rmse"]
        )
        / control["rmse"]
        * 100
    )

    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)

    print(
        results_df.to_string(
            index=False
        )
    )

    json_path = (
        REPORT_DIR
        / "s6_24h_feature_group_ablation.json"
    )

    csv_path = (
        REPORT_DIR
        / "s6_24h_feature_group_ablation.csv"
    )

    results_df.to_json(
        json_path,
        orient="records",
        indent=2,
    )

    results_df.to_csv(
        csv_path,
        index=False,
    )

    print(
        f"\nSaved: {json_path}"
    )

    print(
        f"Saved: {csv_path}"
    )


if __name__ == "__main__":
    main()