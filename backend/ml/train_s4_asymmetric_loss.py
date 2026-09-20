from pathlib import Path
import json
import joblib
import numpy as np
import pandas as pd
from xgboost import XGBRegressor


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent


def resolve_path(rel_str: str) -> Path:
    p = Path(rel_str)

    if p.exists():
        return p

    if (Path("backend") / rel_str).exists():
        return Path("backend") / rel_str

    if (BASE_DIR / rel_str).exists():
        return BASE_DIR / rel_str

    return p


DATA_FILE = resolve_path(
    "data/processed/fusion/delhi_forecasting_satellite_pm10.csv"
)

HORIZON_METADATA_FILE = resolve_path(
    "models/horizon_features.json"
)

BEST_PARAMS_FILE = resolve_path(
    "ml/results/satellite/s4_best_params.json"
)


MODEL_DIR = (
    BASE_DIR / "models/experiments"
    if not Path("models/experiments").exists()
    else Path("models/experiments")
)

REPORT_DIR = (
    BASE_DIR / "reports/satellite"
    if not Path("reports/satellite").exists()
    else Path("reports/satellite")
)


HORIZONS = {
    "6h": "target_pm25_6h",
    "24h": "target_pm25_24h",
    "72h": "target_pm25_72h",
}


# ============================================================
# EXACT S4 SPLIT
# ============================================================

TRAIN_END = pd.Timestamp("2024-10-01 13:00:00")
VALID_END = pd.Timestamp("2025-08-30 15:00:00")
TEST_END = pd.Timestamp("2026-08-31 23:00:00")


# ============================================================
# ASYMMETRIC LOSS
# ============================================================

ALPHA = 2.0


def asymmetric_squared_error(y_true, y_pred):
    """
    Asymmetric squared error.

    Underprediction:
        y_pred < y_true

        gradient = 2 * ALPHA * (y_pred - y_true)
        hessian  = 2 * ALPHA

    Overprediction:
        y_pred >= y_true

        gradient = 2 * (y_pred - y_true)
        hessian  = 2

    ALPHA > 1 therefore penalizes underprediction more heavily.
    """

    residual = y_pred - y_true

    underpredict = residual < 0

    grad = np.where(
        underpredict,
        2.0 * ALPHA * residual,
        2.0 * residual
    )

    hess = np.where(
        underpredict,
        2.0 * ALPHA,
        2.0
    )

    return grad, hess


# ============================================================
# FEATURES
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


# ============================================================
# LOAD DATA
# ============================================================

print("=" * 70)
print("S4 ASYMMETRIC-LOSS XGBOOST EXPERIMENT")
print("=" * 70)

print(f"\nAsymmetric loss alpha: {ALPHA}")

df = pd.read_csv(
    DATA_FILE,
    parse_dates=["timestamp"]
)

print(f"Dataset rows: {len(df):,}")
print(f"Dataset columns: {len(df.columns)}")


# Match canonical pipeline convention
df = df.rename(
    columns={"timestamp": "Timestamp"}
)

df = df.sort_values(
    "Timestamp"
).reset_index(drop=True)


# Same station encoding as S4
if "station_id" in df.columns:
    df = pd.get_dummies(
        df,
        columns=["station_id"],
        dtype=int
    )


df = df.loc[
    :,
    ~df.columns.duplicated()
].copy()


print(f"Rows after preprocessing: {len(df):,}")


# ============================================================
# SPLIT
# ============================================================

train = df[
    df["Timestamp"] < TRAIN_END
].copy()


valid = df[
    (df["Timestamp"] >= TRAIN_END)
    & (df["Timestamp"] < VALID_END)
].copy()


test = df[
    (df["Timestamp"] >= VALID_END)
    & (df["Timestamp"] <= TEST_END)
].copy()


print("\nSplit:")
print(f"  Train:      {len(train):,}")
print(f"  Validation: {len(valid):,}")
print(f"  Test:       {len(test):,}")


# Exact S4 split assertions
assert len(train) == 229974
assert len(valid) == 76664
assert len(test) == 76665


assert train["Timestamp"].max() < valid["Timestamp"].min()
assert valid["Timestamp"].max() < test["Timestamp"].min()


# ============================================================
# LOAD METADATA
# ============================================================

with open(
    HORIZON_METADATA_FILE,
    "r",
    encoding="utf-8"
) as f:
    metadata = json.load(f)


with open(
    BEST_PARAMS_FILE,
    "r",
    encoding="utf-8"
) as f:
    best_params = json.load(f)


# ============================================================
# OUTPUT DIRECTORIES
# ============================================================

MODEL_DIR.mkdir(
    parents=True,
    exist_ok=True
)

REPORT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# TRAIN EACH HORIZON
# ============================================================

results = []


for horizon, target in HORIZONS.items():

    print("\n" + "=" * 70)
    print(f"TRAINING S4 ASYMMETRIC — {horizon}")
    print("=" * 70)

    # --------------------------------------------------------
    # FEATURES
    # --------------------------------------------------------

    canonical_features = metadata[
        "horizon_features"
    ][horizon]

    feature_cols = (
        canonical_features
        + SATELLITE_FEATURES
        + PM10_FEATURES
    )

    missing = [
        c for c in feature_cols
        if c not in df.columns
    ]

    if missing:
        raise ValueError(
            f"{horizon}: missing feature columns: {missing}"
        )


    # --------------------------------------------------------
    # TARGET
    # --------------------------------------------------------

    if target not in df.columns:

        alt_target = f"PM2.5_{horizon}"

        if alt_target in df.columns:
            target = alt_target

        else:
            raise ValueError(
                f"{horizon}: target column missing: {target}"
            )


    print(f"Canonical features: {len(canonical_features)}")
    print(f"Total S4 features:  {len(feature_cols)}")


    # --------------------------------------------------------
    # TARGET-VALID ROWS
    # --------------------------------------------------------

    train_mask = train[target].notna()
    valid_mask = valid[target].notna()
    test_mask = test[target].notna()


    X_train = train.loc[
        train_mask,
        feature_cols
    ]

    y_train = train.loc[
        train_mask,
        target
    ]


    X_valid = valid.loc[
        valid_mask,
        feature_cols
    ]

    y_valid = valid.loc[
        valid_mask,
        target
    ]


    X_test = test.loc[
        test_mask,
        feature_cols
    ]

    y_test = test.loc[
        test_mask,
        target
    ]


    print("\nTarget-valid rows:")
    print(f"  Train:      {len(X_train):,}")
    print(f"  Validation: {len(X_valid):,}")
    print(f"  Test:       {len(X_test):,}")


    # --------------------------------------------------------
    # AVAILABILITY
    # --------------------------------------------------------

    train_sat = (
        train.loc[
            train_mask,
            "satellite_no2_latest"
        ]
        .notna()
        .mean()
    )

    valid_sat = (
        valid.loc[
            valid_mask,
            "satellite_no2_latest"
        ]
        .notna()
        .mean()
    )

    test_sat = (
        test.loc[
            test_mask,
            "satellite_no2_latest"
        ]
        .notna()
        .mean()
    )


    train_pm10 = (
        train.loc[
            train_mask,
            "PM10_lag_1h"
        ]
        .notna()
        .mean()
    )

    valid_pm10 = (
        valid.loc[
            valid_mask,
            "PM10_lag_1h"
        ]
        .notna()
        .mean()
    )

    test_pm10 = (
        test.loc[
            test_mask,
            "PM10_lag_1h"
        ]
        .notna()
        .mean()
    )


    print("\nSatellite availability:")
    print(f"  Train:      {train_sat:.2%}")
    print(f"  Validation: {valid_sat:.2%}")
    print(f"  Test:       {test_sat:.2%}")


    print("\nPM10 availability:")
    print(f"  Train:      {train_pm10:.2%}")
    print(f"  Validation: {valid_pm10:.2%}")
    print(f"  Test:       {test_pm10:.2%}")


    # --------------------------------------------------------
    # EXACT S4 PARAMETERS
    # --------------------------------------------------------

    params_entry = best_params[horizon]

    params = (
        params_entry.get("params")
        or params_entry.get("best_params")
    )

    best_iteration = int(
        params_entry["best_iteration"]
    )


    print("\nS4 parameters:")
    print(params)

    print(
        f"S4 best iteration: {best_iteration}"
    )


    # --------------------------------------------------------
    # TRAIN + VALID
    #
    # IMPORTANT:
    # We deliberately keep the S4 iteration count.
    #
    # This experiment changes ONLY the objective.
    # --------------------------------------------------------

    train_valid = pd.concat(
        [
            train.loc[train_mask],
            valid.loc[valid_mask]
        ],
        axis=0
    )


    X_train_valid = train_valid[
        feature_cols
    ]

    y_train_valid = train_valid[
        target
    ]


    model = XGBRegressor(
        n_estimators=best_iteration,

        max_depth=params["max_depth"],
        min_child_weight=params["min_child_weight"],
        learning_rate=params["learning_rate"],
        subsample=params["subsample"],
        colsample_bytree=params[
            "colsample_bytree"
        ],

        objective=asymmetric_squared_error,

        random_state=42,
        n_jobs=-1,
    )


    print(
        "\nFitting asymmetric-loss model..."
    )

    model.fit(
        X_train_valid,
        y_train_valid
    )


    # --------------------------------------------------------
    # TEST
    # --------------------------------------------------------

    predictions = model.predict(
        X_test
    )


    y_test_array = y_test.to_numpy()


    errors = predictions - y_test_array


    mae = float(
        np.mean(np.abs(errors))
    )

    rmse = float(
        np.sqrt(np.mean(errors ** 2))
    )


    ss_res = float(
        np.sum(errors ** 2)
    )

    ss_tot = float(
        np.sum(
            (y_test_array - y_test_array.mean()) ** 2
        )
    )


    r2 = (
        1.0 - ss_res / ss_tot
        if ss_tot > 0
        else float("nan")
    )


    bias = float(
        np.mean(errors)
    )


    medae = float(
        np.median(np.abs(errors))
    )


    # --------------------------------------------------------
    # UNDERPREDICTION RATE
    # --------------------------------------------------------

    underprediction_rate = float(
        np.mean(predictions < y_test_array)
    )


    # --------------------------------------------------------
    # RESULTS
    # --------------------------------------------------------

    print("\nTEST RESULTS")

    print(f"  MAE:                   {mae:.4f}")
    print(f"  RMSE:                  {rmse:.4f}")
    print(f"  R²:                    {r2:.4f}")
    print(f"  Bias:                  {bias:.4f}")
    print(f"  MedAE:                 {medae:.4f}")
    print(
        f"  Underprediction rate:  "
        f"{underprediction_rate:.4%}"
    )


    # --------------------------------------------------------
    # SAVE MODEL
    # --------------------------------------------------------

    model_path = (
        MODEL_DIR
        / f"xgb_s4_asym_{horizon}.joblib"
    )


    joblib.dump(
        model,
        model_path
    )


    print("\nSaved model:")
    print(f"  {model_path}")


    # --------------------------------------------------------
    # SAVE RESULT
    # --------------------------------------------------------

    results.append({
        "experiment": "S4_asymmetric",
        "alpha": ALPHA,
        "horizon": horizon,

        "canonical_features":
            len(canonical_features),

        "s4_features":
            len(feature_cols),

        "best_iteration":
            best_iteration,

        "train_rows":
            len(X_train_valid),

        "test_rows":
            len(X_test),

        "satellite_test_availability":
            test_sat,

        "pm10_test_availability":
            test_pm10,

        "mae":
            mae,

        "rmse":
            rmse,

        "r2":
            r2,

        "bias":
            bias,

        "medae":
            medae,

        "underprediction_rate":
            underprediction_rate,
    })


# ============================================================
# SAVE SUMMARY
# ============================================================

results_df = pd.DataFrame(
    results
)


summary_path = (
    REPORT_DIR
    / "s4_asymmetric_test_results.csv"
)


results_df.to_csv(
    summary_path,
    index=False
)


# ============================================================
# COMPLETE
# ============================================================

print("\n" + "=" * 70)
print("S4 ASYMMETRIC-LOSS EXPERIMENT COMPLETE")
print("=" * 70)

print(
    results_df.to_string(
        index=False
    )
)

print("\nSaved summary:")
print(f"  {summary_path}")
