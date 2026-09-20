"""
S8-A: Post-hoc calibration experiment for VayuNet PM2.5 production models.

IMPORTANT:
- Production models are NOT modified.
- Production feature metadata is NOT modified.
- Calibration is fitted ONLY on the validation period.
- Test data is used ONLY for final evaluation.
- Calibration regimes use RAW PREDICTION, never future actual PM2.5.
- S8-A is an experiment, not production code.

Models:
    6h  -> S6
    24h -> S5
    72h -> S6

Validation:
    2024-10-01 13:00 <= timestamp < 2025-08-30 15:00

Test:
    2025-08-30 15:00 <= timestamp <= 2026-08-31 23:00
"""

from pathlib import Path
import json
import warnings

import joblib
import numpy as np
import pandas as pd

from sklearn.linear_model import LinearRegression
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


# ============================================================
# PATHS
# ============================================================

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

MODEL_DIR = BASE_DIR / "models"

REPORT_DIR = BASE_DIR / "reports/calibration"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# FROZEN PRODUCTION MODELS
# ============================================================

PRODUCTION_MODELS = {
    "6h": MODEL_DIR / "xgb_vayunet_pm25_6h_s6_production.joblib",
    "24h": MODEL_DIR / "xgb_vayunet_pm25_24h_s5_production.joblib",
    "72h": MODEL_DIR / "xgb_vayunet_pm25_72h_s6_production.joblib",
}


# ============================================================
# SPLITS
# ============================================================

TRAIN_END = pd.Timestamp("2024-10-01 13:00:00")
VALID_END = pd.Timestamp("2025-08-30 15:00:00")
TEST_END = pd.Timestamp("2026-08-31 23:00:00")


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


HORIZONS = {
    "6h": 6,
    "24h": 24,
    "72h": 72,
}


# ============================================================
# METRICS
# ============================================================

def calculate_metrics(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    errors = y_pred - y_true

    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "R2": float(r2_score(y_true, y_pred)),
        "Bias": float(np.mean(errors)),
        "MedAE": float(np.median(np.abs(errors))),
    }


def regime_mask(predictions, regime):
    """
    IMPORTANT:
    Regimes are determined ONLY from the model prediction.
    Future actual PM2.5 is never used for regime selection.
    """

    p = np.asarray(predictions)

    if regime == "<60":
        return p < 60

    if regime == "60-150":
        return (p >= 60) & (p < 150)

    if regime == "150-250":
        return (p >= 150) & (p < 250)

    if regime == ">=250":
        return p >= 250

    raise ValueError(f"Unknown regime: {regime}")


REGIMES = [
    "<60",
    "60-150",
    "150-250",
    ">=250",
]


# ============================================================
# LOAD / PREPARE DATA
# ============================================================

def load_dataset():
    print("=" * 80)
    print("S8-A CALIBRATION")
    print("=" * 80)

    print("\nLoading S5 NWP dataset...")
    s5_df = pd.read_csv(
        S5_DATA_FILE,
        parse_dates=["timestamp"],
    )

    print("Loading Episode dataset...")
    ep_df = pd.read_csv(
        EPISODE_DATA_FILE,
    )

    print(f"S5 rows:      {len(s5_df):,}")
    print(f"Episode rows: {len(ep_df):,}")

    if len(s5_df) != len(ep_df):
        raise ValueError(
            "S5 and Episode row counts differ. "
            "Refusing to continue because positional concatenation "
            "would be unsafe."
        )

    # Episode builder was constructed to preserve row order.
    # Verify timestamp alignment if available.
    if "timestamp" in ep_df.columns:
        ep_ts = pd.to_datetime(ep_df["timestamp"])

        if not ep_ts.equals(s5_df["timestamp"]):
            raise ValueError(
                "S5 and Episode timestamps are not exactly aligned. "
                "Refusing to continue."
            )

    # Avoid duplicate base columns from Episode file.
    ep_only = ep_df[
        [c for c in EPISODE_FEATURES if c in ep_df.columns]
    ].copy()

    missing_episode = [
        c for c in EPISODE_FEATURES
        if c not in ep_only.columns
    ]

    if missing_episode:
        raise ValueError(
            f"Missing Episode features: {missing_episode}"
        )

    df = pd.concat(
        [
            s5_df.reset_index(drop=True),
            ep_only.reset_index(drop=True),
        ],
        axis=1,
    )

    # Remove duplicate columns defensively.
    df = df.loc[:, ~df.columns.duplicated()].copy()

    print(f"Combined rows: {len(df):,}")

    return df


# ============================================================
# FEATURE CONSTRUCTION
# ============================================================

def get_features(metadata, horizon):
    canonical = metadata["horizon_features"][horizon]

    s4 = canonical + SATELLITE_FEATURES + PM10_FEATURES

    horizon_hours = HORIZONS[horizon]

    nwp = [
        f"nwp_{v}_{horizon_hours}h"
        for v in NWP_BASE_VARS
    ]

    # Production architecture:
    #
    # 6h  = S6 = S4 + NWP + Episode
    # 24h = S5 = S4 + NWP
    # 72h = S6 = S4 + NWP + Episode

    if horizon in ("6h", "72h"):
        features = s4 + nwp + EPISODE_FEATURES
        expected_variant = "S6"

    elif horizon == "24h":
        features = s4 + nwp
        expected_variant = "S5"

    else:
        raise ValueError(horizon)

    return features, expected_variant


# ============================================================
# BUILD SPLITS
# ============================================================

def split_data(df, target, nwp_features):
    required = ["Timestamp", target] + nwp_features

    missing = [
        c for c in required
        if c not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Required columns missing: {missing}"
        )

    # Exact same matched-row principle used by S5/S6 validation:
    # target must exist and all horizon NWP features must exist.
    matched = df[target].notna().copy()

    for feature in nwp_features:
        matched &= df[feature].notna()

    df = df.loc[matched].copy()

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

    return train, valid, test


# ============================================================
# VALIDATION-TRAINED MODEL
# ============================================================

def train_validation_model(
    production_model,
    X_train,
    y_train,
):
    """
    Reconstruct the same model configuration as the frozen
    production model, but fit ONLY on TRAIN.

    This model exists only to generate honest validation
    predictions for calibration fitting.
    """

    # Load the frozen model to recover exact XGBoost parameters.
    production_booster = production_model

    params = production_booster.get_params()

    # Keep only parameters relevant to reconstruction.
    allowed = [
        "max_depth",
        "min_child_weight",
        "learning_rate",
        "subsample",
        "colsample_bytree",
        "objective",
        "random_state",
        "n_jobs",
        "tree_method",
        "device",
        "reg_alpha",
        "reg_lambda",
        "gamma",
        "max_delta_step",
    ]

    reconstructed_params = {
        k: params[k]
        for k in allowed
        if k in params and params[k] is not None
    }

    # Production model stores n_estimators as the trained tree count.
    reconstructed_params["n_estimators"] = production_booster.n_estimators

    # We intentionally do NOT use early stopping here.
    # We use the already-frozen production tree count.
    from xgboost import XGBRegressor

    model = XGBRegressor(
        **reconstructed_params
    )

    model.fit(
        X_train,
        y_train,
    )

    return model


# ============================================================
# CALIBRATION METHODS
# ============================================================

def fit_global_linear(y_true, raw_pred):
    model = LinearRegression()
    model.fit(
        np.asarray(raw_pred).reshape(-1, 1),
        np.asarray(y_true),
    )
    return model


def apply_global_linear(model, predictions):
    return model.predict(
        np.asarray(predictions).reshape(-1, 1)
    )


def fit_piecewise(y_true, raw_pred):
    models = {}

    raw_pred = np.asarray(raw_pred)
    y_true = np.asarray(y_true)

    for regime in REGIMES:
        mask = regime_mask(raw_pred, regime)

        if mask.sum() < 2:
            raise ValueError(
                f"Not enough validation observations "
                f"for piecewise regime {regime}: {mask.sum()}"
            )

        model = LinearRegression()

        model.fit(
            raw_pred[mask].reshape(-1, 1),
            y_true[mask],
        )

        models[regime] = model

    return models


def apply_piecewise(models, predictions):
    predictions = np.asarray(predictions)
    calibrated = np.empty_like(
        predictions,
        dtype=float,
    )

    for regime in REGIMES:
        mask = regime_mask(predictions, regime)

        if mask.any():
            calibrated[mask] = models[regime].predict(
                predictions[mask].reshape(-1, 1)
            )

    return calibrated


def fit_isotonic(y_true, raw_pred):
    model = IsotonicRegression(
        increasing=True,
        out_of_bounds="clip",
    )

    model.fit(
        np.asarray(raw_pred),
        np.asarray(y_true),
    )

    return model


# ============================================================
# EVALUATION TABLE
# ============================================================

def evaluate_method(
    horizon,
    split_name,
    method,
    y_true,
    raw_pred,
    calibrated_pred,
):
    rows = []

    # Overall
    metrics = calculate_metrics(
        y_true,
        calibrated_pred,
    )

    rows.append({
        "horizon": horizon,
        "split": split_name,
        "method": method,
        "regime": "overall",
        "N": len(y_true),
        **metrics,
    })

    # Prediction-defined regimes
    for regime in REGIMES:
        mask = regime_mask(
            calibrated_pred if method != "A_raw"
            else raw_pred,
            regime,
        )

        # NOTE:
        # For calibrated methods, we use calibrated predictions
        # only to report the resulting regime breakdown.
        # This does not affect calibration fitting.
        #
        # We additionally report raw-prediction regimes separately
        # below for the primary causal tail analysis.

        if mask.sum() == 0:
            continue

        regime_metrics = calculate_metrics(
            np.asarray(y_true)[mask],
            np.asarray(calibrated_pred)[mask],
        )

        rows.append({
            "horizon": horizon,
            "split": split_name,
            "method": method,
            "regime": regime,
            "N": int(mask.sum()),
            **regime_metrics,
        })

    return rows


def evaluate_raw_prediction_regimes(
    horizon,
    split_name,
    method,
    y_true,
    raw_pred,
    calibrated_pred,
):
    """
    Report regime performance using RAW prediction bins.

    This is the scientifically important tail comparison because
    the regime is defined using information available at prediction
    time.
    """

    rows = []

    y_true = np.asarray(y_true)
    raw_pred = np.asarray(raw_pred)
    calibrated_pred = np.asarray(calibrated_pred)

    for regime in REGIMES:
        mask = regime_mask(
            raw_pred,
            regime,
        )

        if mask.sum() == 0:
            continue

        metrics = calculate_metrics(
            y_true[mask],
            calibrated_pred[mask],
        )

        rows.append({
            "horizon": horizon,
            "split": split_name,
            "method": method,
            "regime": regime,
            "regime_definition": "raw_prediction",
            "N": int(mask.sum()),
            **metrics,
        })

    return rows


# ============================================================
# MAIN
# ============================================================

def main():

    df = load_dataset()

    # Ensure timestamp naming matches previous validators.
    if "Timestamp" not in df.columns:
        if "timestamp" in df.columns:
            df = df.rename(
                columns={"timestamp": "Timestamp"}
            )
        else:
            raise ValueError(
                "No timestamp/Timestamp column found."
            )

    metadata = json.loads(
        HORIZON_METADATA_FILE.read_text(
            encoding="utf-8"
        )
    )

    all_results = []
    calibration_parameters = {}

    for horizon, horizon_hours in HORIZONS.items():

        print("\n" + "=" * 80)
        print(f"HORIZON: {horizon}")
        print("=" * 80)

        target = f"target_pm25_{horizon}"

        # Fallback used in some earlier datasets.
        if target not in df.columns:
            alt = f"PM2.5_{horizon}"

            if alt in df.columns:
                target = alt
            else:
                raise ValueError(
                    f"No target found for {horizon}. "
                    f"Tried {target} and {alt}."
                )

        features, expected_variant = get_features(
            metadata,
            horizon,
        )

        print(f"Production variant: {expected_variant}")
        print(f"Feature count:       {len(features)}")

        missing_features = [
            c for c in features
            if c not in df.columns
        ]

        if missing_features:
            raise ValueError(
                f"{horizon}: missing features: "
                f"{missing_features}"
            )

        nwp_features = [
            f"nwp_{v}_{horizon_hours}h"
            for v in NWP_BASE_VARS
        ]

        train, valid, test = split_data(
            df,
            target,
            nwp_features,
        )

        print("\nMatched split:")
        print(f"  Train:      {len(train):,}")
        print(f"  Validation: {len(valid):,}")
        print(f"  Test:       {len(test):,}")

        # ----------------------------------------------------
        # LOAD FROZEN PRODUCTION MODEL
        # ----------------------------------------------------

        production_path = PRODUCTION_MODELS[horizon]

        if not production_path.exists():
            raise FileNotFoundError(
                production_path
            )

        print(
            f"\nLoading frozen production model:\n"
            f"  {production_path.name}"
        )

        production_model = joblib.load(
            production_path
        )

        # ----------------------------------------------------
        # HONEST VALIDATION PREDICTIONS
        # ----------------------------------------------------

        print("\nTraining validation-only reconstruction...")

        validation_model = train_validation_model(
            production_model,
            train[features],
            train[target],
        )

        valid_raw_pred = validation_model.predict(
            valid[features]
        )

        y_valid = valid[target].to_numpy(
            dtype=float
        )

        print("\nValidation raw metrics:")
        print(
            calculate_metrics(
                y_valid,
                valid_raw_pred,
            )
        )

        # ----------------------------------------------------
        # PRODUCTION TEST PREDICTIONS
        # ----------------------------------------------------

        test_raw_pred = production_model.predict(
            test[features]
        )

        y_test = test[target].to_numpy(
            dtype=float
        )

        print("\nProduction test metrics:")
        print(
            calculate_metrics(
                y_test,
                test_raw_pred,
            )
        )

        # ----------------------------------------------------
        # SAVE RAW PREDICTIONS
        # ----------------------------------------------------

        prediction_df_valid = pd.DataFrame({
            "Timestamp": valid["Timestamp"].to_numpy(),
            "station_id": (
                valid["station_id"].to_numpy()
                if "station_id" in valid.columns
                else np.nan
            ),
            "y_true": y_valid,
            "raw_prediction": valid_raw_pred,
        })

        prediction_df_test = pd.DataFrame({
            "Timestamp": test["Timestamp"].to_numpy(),
            "station_id": (
                test["station_id"].to_numpy()
                if "station_id" in test.columns
                else np.nan
            ),
            "y_true": y_test,
            "raw_prediction": test_raw_pred,
        })

        prediction_df_valid.to_csv(
            REPORT_DIR /
            f"s8a_{horizon}_validation_predictions.csv",
            index=False,
        )

        prediction_df_test.to_csv(
            REPORT_DIR /
            f"s8a_{horizon}_test_predictions.csv",
            index=False,
        )

        # ----------------------------------------------------
        # METHOD A — RAW CONTROL
        # ----------------------------------------------------

        methods = {
            "A_raw": None,
        }

        # ----------------------------------------------------
        # METHOD B — GLOBAL LINEAR
        # ----------------------------------------------------

        print("\nFitting Method B: global linear...")

        global_model = fit_global_linear(
            y_valid,
            valid_raw_pred,
        )

        methods["B_global_linear"] = global_model

        # ----------------------------------------------------
        # METHOD C — PIECEWISE LINEAR
        # ----------------------------------------------------

        print("Fitting Method C: piecewise linear...")

        piecewise_models = fit_piecewise(
            y_valid,
            valid_raw_pred,
        )

        methods["C_piecewise_linear"] = piecewise_models

        # ----------------------------------------------------
        # METHOD D — ISOTONIC
        # ----------------------------------------------------

        print("Fitting Method D: isotonic...")

        isotonic_model = fit_isotonic(
            y_valid,
            valid_raw_pred,
        )

        methods["D_isotonic"] = isotonic_model

        # ----------------------------------------------------
        # VALIDATION EVALUATION
        # ----------------------------------------------------

        print("\n" + "-" * 80)
        print("VALIDATION RESULTS")
        print("-" * 80)

        validation_predictions = {
            "A_raw": valid_raw_pred,
            "B_global_linear": apply_global_linear(
                global_model,
                valid_raw_pred,
            ),
            "C_piecewise_linear": apply_piecewise(
                piecewise_models,
                valid_raw_pred,
            ),
            "D_isotonic": isotonic_model.predict(
                valid_raw_pred
            ),
        }

        for method, preds in validation_predictions.items():

            metrics = calculate_metrics(
                y_valid,
                preds,
            )

            print(
                f"{method:22s} "
                f"MAE={metrics['MAE']:.4f} "
                f"RMSE={metrics['RMSE']:.4f} "
                f"Bias={metrics['Bias']:.4f} "
                f"R2={metrics['R2']:.4f}"
            )

            all_results.extend(
                evaluate_raw_prediction_regimes(
                    horizon,
                    "validation",
                    method,
                    y_valid,
                    valid_raw_pred,
                    preds,
                )
            )

        # ----------------------------------------------------
        # SELECT METHOD USING VALIDATION ONLY
        # ----------------------------------------------------

        validation_method_metrics = {}

        for method, preds in validation_predictions.items():
            validation_method_metrics[method] = calculate_metrics(
                y_valid,
                preds,
            )

        # Primary selection metric = validation RMSE.
        # Simplicity breaks ties.
        simplicity_rank = {
            "A_raw": 0,
            "B_global_linear": 1,
            "C_piecewise_linear": 2,
            "D_isotonic": 3,
        }

        selected_method = min(
            validation_method_metrics.keys(),
            key=lambda method: (
                validation_method_metrics[method]["RMSE"],
                simplicity_rank[method],
            ),
        )

        print("\nSELECTED CALIBRATION:")
        print(
            f"  {selected_method}"
        )

        print(
            f"  Validation RMSE: "
            f"{validation_method_metrics[selected_method]['RMSE']:.4f}"
        )

        # ----------------------------------------------------
        # APPLY FROZEN CALIBRATION TO TEST
        # ----------------------------------------------------

        if selected_method == "A_raw":
            calibrated_test = test_raw_pred.copy()

        elif selected_method == "B_global_linear":
            calibrated_test = apply_global_linear(
                global_model,
                test_raw_pred,
            )

        elif selected_method == "C_piecewise_linear":
            calibrated_test = apply_piecewise(
                piecewise_models,
                test_raw_pred,
            )

        elif selected_method == "D_isotonic":
            calibrated_test = isotonic_model.predict(
                test_raw_pred
            )

        else:
            raise RuntimeError(
                f"Unknown selected method: {selected_method}"
            )

        # Prevent impossible negative PM2.5 predictions.
        # This is only a physical output guard, not a fitted parameter.
        calibrated_test = np.maximum(
            calibrated_test,
            0.0,
        )

        # ----------------------------------------------------
        # TEST RESULTS
        # ----------------------------------------------------

        print("\n" + "-" * 80)
        print("UNTOUCHED TEST RESULTS")
        print("-" * 80)

        raw_test_metrics = calculate_metrics(
            y_test,
            test_raw_pred,
        )

        calibrated_test_metrics = calculate_metrics(
            y_test,
            calibrated_test,
        )

        print("\nRAW PRODUCTION:")
        for key, value in raw_test_metrics.items():
            print(f"  {key:8s}: {value:.4f}")

        print("\nCALIBRATED:")
        for key, value in calibrated_test_metrics.items():
            print(f"  {key:8s}: {value:.4f}")

        print("\nDelta:")
        print(
            f"  MAE improvement:  "
            f"{raw_test_metrics['MAE'] - calibrated_test_metrics['MAE']:.4f}"
        )

        print(
            f"  RMSE improvement: "
            f"{raw_test_metrics['RMSE'] - calibrated_test_metrics['RMSE']:.4f}"
        )

        print(
            f"  Bias improvement:  "
            f"{abs(raw_test_metrics['Bias']) - abs(calibrated_test_metrics['Bias']):.4f}"
        )

        # ----------------------------------------------------
        # TEST REGIME RESULTS
        # ----------------------------------------------------

        print("\nTEST REGIME RESULTS")
        print("(Regimes defined from RAW prediction)")

        regime_rows = evaluate_raw_prediction_regimes(
            horizon,
            "test",
            selected_method,
            y_test,
            test_raw_pred,
            calibrated_test,
        )

        for row in regime_rows:
            print(
                f"  {row['regime']:10s} "
                f"N={row['N']:6d} "
                f"MAE={row['MAE']:8.3f} "
                f"RMSE={row['RMSE']:8.3f} "
                f"Bias={row['Bias']:8.3f}"
            )

        all_results.extend(regime_rows)

        # ----------------------------------------------------
        # SAVE CALIBRATED TEST PREDICTIONS
        # ----------------------------------------------------

        output_predictions = test[
            [
                c for c in
                ["Timestamp", "station_id"]
                if c in test.columns
            ]
        ].copy()

        output_predictions["y_true"] = y_test
        output_predictions["raw_prediction"] = test_raw_pred
        output_predictions["calibrated_prediction"] = calibrated_test
        output_predictions["selected_method"] = selected_method

        output_predictions.to_csv(
            REPORT_DIR /
            f"s8a_{horizon}_calibrated_test_predictions.csv",
            index=False,
        )

        # ----------------------------------------------------
        # SAVE PARAMETERS
        # ----------------------------------------------------

        calibration_parameters[horizon] = {
            "selected_method": selected_method,
            "validation_metrics": validation_method_metrics,
            "global_linear": {
                "coef": float(global_model.coef_[0]),
                "intercept": float(global_model.intercept_),
            },
            "piecewise_linear": {
                regime: {
                    "coef": float(
                        piecewise_models[regime].coef_[0]
                    ),
                    "intercept": float(
                        piecewise_models[regime].intercept_
                    ),
                }
                for regime in REGIMES
            },
            "test_raw_metrics": raw_test_metrics,
            "test_calibrated_metrics": calibrated_test_metrics,
        }

    # ========================================================
    # SAVE COMPLETE RESULTS
    # ========================================================

    results_df = pd.DataFrame(all_results)

    results_df.to_csv(
        REPORT_DIR / "s8a_calibration_results.csv",
        index=False,
    )

    (REPORT_DIR / "s8a_calibration_parameters.json").write_text(
        json.dumps(
            calibration_parameters,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\n" + "=" * 80)
    print("S8-A COMPLETE")
    print("=" * 80)

    print(
        f"\nResults saved to:\n"
        f"  {REPORT_DIR}"
    )

    print(
        "\nIMPORTANT:"
        "\n  Production .joblib models were NOT modified."
        "\n  horizon_features.json was NOT modified."
        "\n  Test data was NOT used for calibration fitting."
    )


if __name__ == "__main__":
    main()
