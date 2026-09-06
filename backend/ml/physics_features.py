"""
Physics-informed feature engineering for VayuNet PM2.5 forecasting.

IMPORTANT:
- Experimental module only.
- Do NOT modify feature_builder.py.
- All features use information available at the forecast origin or earlier.
- No target_pm25_* columns are used.
- No future weather variables are used.
- Rolling/difference operations never cross station or segment boundaries.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GROUP_COLS = ["station_id", "segment_id"]

EPSILON = 1e-6


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _safe_divide(
    numerator: pd.Series,
    denominator: pd.Series,
    epsilon: float = EPSILON,
) -> pd.Series:
    """
    Numerically safe division.

    Returns NaN when the numerator or denominator is missing.
    Prevents division by zero.
    """
    denominator_safe = denominator.where(
        denominator.abs() > epsilon,
        np.nan,
    )

    return numerator / denominator_safe


def _rolling_slope(series: pd.Series, window: int = 6) -> pd.Series:
    """
    Calculate backward-looking linear trend slope.

    The x-axis represents equally spaced hourly observations:
        0, 1, 2, ..., window-1

    Therefore the result represents approximately:
        change in PM2.5 per hour

    Only past/current observations are used.
    """

    x = np.arange(window, dtype=float)
    x_mean = x.mean()

    denominator = np.sum((x - x_mean) ** 2)

    def slope(values: np.ndarray) -> float:
        if np.isnan(values).any():
            return np.nan

        if len(values) < window:
            return np.nan

        y_mean = values.mean()

        return np.sum((x - x_mean) * (values - y_mean)) / denominator

    return series.rolling(
        window=window,
        min_periods=window,
    ).apply(
        slope,
        raw=True,
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_input(df: pd.DataFrame) -> None:
    """Validate the dataframe before creating physics features."""

    required_columns = [
        "timestamp",
        "station_id",
        "segment_id",
        "PM2.5",
        "PM10",
        "WS",
        "WD",
        "AT",
        "RH",
    ]

    missing = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )

    if df.empty:
        raise ValueError("Input dataframe is empty.")

    if not df["timestamp"].is_monotonic_increasing:
        # We don't require global ordering because stations are interleaved.
        # Ordering is checked after sorting within each station/segment.
        pass


# ---------------------------------------------------------------------------
# Main feature builder
# ---------------------------------------------------------------------------

def add_physics_features(
    df: pd.DataFrame,
    copy: bool = True,
) -> pd.DataFrame:
    """
    Add physics-informed and physically motivated features.

    Features created:

    Atmospheric transport:
        ventilation_index
        log_ventilation_index
        wind_u
        wind_v

    PM2.5 dynamics:
        PM25_change_1h
        PM25_change_3h
        PM25_change_6h
        PM25_acceleration_1h
        PM25_rolling_slope_6h

    Atmospheric stagnation:
        stagnation_proxy

    Particle composition:
        PM25_PM10_fraction

    Meteorological interactions:
        temperature_RH_interaction
        RH_PBLH_interaction

    Pollution/transport interaction:
        PM25_ventilation_interaction
    """

    validate_input(df)

    if copy:
        df = df.copy()

    # -----------------------------------------------------------------------
    # Preserve original row order.
    # -----------------------------------------------------------------------

    df["_physics_original_order"] = np.arange(len(df))

    # Sort so that lag/rolling operations are chronological.
    df = df.sort_values(
        GROUP_COLS + ["timestamp"]
    ).copy()

    # -----------------------------------------------------------------------
    # Numeric conversion
    # -----------------------------------------------------------------------

    numeric_columns = [
        "PM2.5",
        "PM10",
        "WS",
        "WD",
        "AT",
        "RH",
        "boundary_layer_height",
    ]

    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce",
            )

    # -----------------------------------------------------------------------
    # 1. Atmospheric ventilation
    # -----------------------------------------------------------------------
    #
    # Ventilation index ≈ wind speed × boundary layer height.
    #
    # Higher values generally indicate stronger atmospheric dilution/
    # transport potential.
    #
    # This is a proxy, not a complete atmospheric dispersion model.
    # -----------------------------------------------------------------------

    if "boundary_layer_height" in df.columns:

        df["ventilation_index"] = (
            df["WS"] * df["boundary_layer_height"]
        )

        # Log transform reduces extreme skew.
        df["log_ventilation_index"] = np.log1p(
            df["ventilation_index"].clip(lower=0)
        )

    else:
        df["ventilation_index"] = np.nan
        df["log_ventilation_index"] = np.nan

    # -----------------------------------------------------------------------
    # 2. Wind vector components
    # -----------------------------------------------------------------------
    #
    # Meteorological wind direction:
    #   0°   = North
    #   90°  = East
    #   180° = South
    #   270° = West
    #
    # u = east-west component
    # v = north-south component
    #
    # Negative signs follow the meteorological convention where wind
    # direction indicates the direction FROM which the wind originates.
    # -----------------------------------------------------------------------

    wind_direction_rad = np.deg2rad(df["WD"])

    df["wind_u"] = (
        -df["WS"] * np.sin(wind_direction_rad)
    )

    df["wind_v"] = (
        -df["WS"] * np.cos(wind_direction_rad)
    )

    # -----------------------------------------------------------------------
    # 3. PM2.5 temporal dynamics
    # -----------------------------------------------------------------------
    #
    # All operations are performed independently for:
    #   station_id + segment_id
    #
    # Therefore they cannot cross the known CPCB data gap.
    # -----------------------------------------------------------------------

    grouped_pm25 = df.groupby(
        GROUP_COLS,
        sort=False,
    )["PM2.5"]

    df["PM25_change_1h"] = grouped_pm25.diff(1)

    df["PM25_change_3h"] = grouped_pm25.diff(3)

    df["PM25_change_6h"] = grouped_pm25.diff(6)

    # -----------------------------------------------------------------------
    # 4. PM2.5 acceleration
    # -----------------------------------------------------------------------
    #
    # First difference:
    #     ΔPM(t) = PM(t) - PM(t-1)
    #
    # Acceleration:
    #     Δ²PM(t) = ΔPM(t) - ΔPM(t-1)
    #
    # Positive values indicate increasing growth rate.
    # -----------------------------------------------------------------------

    df["PM25_acceleration_1h"] = (
        df["PM25_change_1h"]
        - df.groupby(
            GROUP_COLS,
            sort=False,
        )["PM25_change_1h"].shift(1)
    )

    # -----------------------------------------------------------------------
    # 5. Rolling PM2.5 trend
    # -----------------------------------------------------------------------
    #
    # Six-hour backward-looking linear trend.
    #
    # Positive slope:
    #     PM2.5 increasing
    #
    # Negative slope:
    #     PM2.5 decreasing
    # -----------------------------------------------------------------------

    df["PM25_rolling_slope_6h"] = np.nan

    for _, group_index in df.groupby(
        GROUP_COLS,
        sort=False,
    ).groups.items():

        # group_index contains the dataframe index labels.
        group = df.loc[group_index].sort_values("timestamp")

        slope = _rolling_slope(
            group["PM2.5"],
            window=6,
        )

        df.loc[
            group.index,
            "PM25_rolling_slope_6h"
        ] = slope.to_numpy()

    # -----------------------------------------------------------------------
    # 6. Atmospheric stagnation proxy
    # -----------------------------------------------------------------------
    #
    # This is intentionally a PROXY.
    #
    # It is NOT true atmospheric inversion strength.
    #
    # Low wind + shallow boundary layer -> greater stagnation potential.
    #
    # We define:
    #
    #     stagnation_proxy = 1 / (ventilation_index + epsilon)
    #
    # Higher value -> weaker ventilation.
    # -----------------------------------------------------------------------

    df["stagnation_proxy"] = _safe_divide(
        pd.Series(
            1.0,
            index=df.index,
        ),
        df["ventilation_index"],
    )

    # Keep extreme numerical values under control.
    df["stagnation_proxy"] = (
        df["stagnation_proxy"]
        .replace(
            [np.inf, -np.inf],
            np.nan,
        )
    )

    # -----------------------------------------------------------------------
    # 7. PM2.5 / PM10 fine-particle fraction
    # -----------------------------------------------------------------------
    #
    # Higher fraction means a larger share of measured particulate matter
    # is represented by PM2.5 rather than coarse particles.
    #
    # This is a descriptive feature, not a source-attribution mechanism.
    # -----------------------------------------------------------------------

    df["PM25_PM10_fraction"] = _safe_divide(
        df["PM2.5"],
        df["PM10"],
    )

    # Avoid physically nonsensical numerical values caused by bad input.
    df.loc[
        (df["PM25_PM10_fraction"] < 0)
        | (df["PM25_PM10_fraction"] > 1.5),
        "PM25_PM10_fraction",
    ] = np.nan

    # -----------------------------------------------------------------------
    # 8. Temperature × Relative Humidity interaction
    # -----------------------------------------------------------------------

    df["temperature_RH_interaction"] = (
        df["AT"] * df["RH"]
    )

    # -----------------------------------------------------------------------
    # 9. Relative Humidity × Boundary Layer Height
    # -----------------------------------------------------------------------

    if "boundary_layer_height" in df.columns:
        df["RH_PBLH_interaction"] = (
            df["RH"]
            * df["boundary_layer_height"]
        )
    else:
        df["RH_PBLH_interaction"] = np.nan

    # -----------------------------------------------------------------------
    # 10. PM2.5 × ventilation interaction
    # -----------------------------------------------------------------------
    #
    # Captures the relationship between current pollution concentration and
    # atmospheric dilution/transport conditions.
    # -----------------------------------------------------------------------

    df["PM25_ventilation_interaction"] = (
        df["PM2.5"]
        * df["ventilation_index"]
    )

    # -----------------------------------------------------------------------
    # Cleanup
    # -----------------------------------------------------------------------

    df = df.sort_values(
        "_physics_original_order"
    ).drop(
        columns=["_physics_original_order"]
    )

    # Reset index so downstream scripts receive a clean dataframe.
    df = df.reset_index(drop=True)

    return df


# ---------------------------------------------------------------------------
# Feature list
# ---------------------------------------------------------------------------

PHYSICS_FEATURES = [
    "ventilation_index",
    "log_ventilation_index",
    "wind_u",
    "wind_v",
    "PM25_change_1h",
    "PM25_change_3h",
    "PM25_change_6h",
    "PM25_acceleration_1h",
    "PM25_rolling_slope_6h",
    "stagnation_proxy",
    "PM25_PM10_fraction",
    "temperature_RH_interaction",
    "RH_PBLH_interaction",
    "PM25_ventilation_interaction",
]


def get_physics_feature_names() -> list[str]:
    """Return the canonical list of physics feature names."""
    return PHYSICS_FEATURES.copy()


# ---------------------------------------------------------------------------
# Simple standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[1]

    input_path = (
        project_root
        / "data"
        / "processed"
        / "delhi_forecasting_weather.csv"
    )

    print("=" * 70)
    print("VayuNet Physics Feature Test")
    print("=" * 70)

    print(f"\nLoading:")
    print(input_path)

    data = pd.read_csv(
        input_path,
        parse_dates=["timestamp"],
    )

    print(f"\nInput shape: {data.shape}")

    result = add_physics_features(data)

    print(f"Output shape: {result.shape}")

    print("\nPhysics features:")
    for feature in PHYSICS_FEATURES:
        print(
            f"  {feature:<35} "
            f"missing={result[feature].isna().sum():>7}"
        )

    print("\nFeature statistics:")
    print(
        result[PHYSICS_FEATURES]
        .describe()
        .T[
            ["count", "mean", "std", "min", "max"]
        ]
    )

    print("\n[OK] Physics feature generation completed.")