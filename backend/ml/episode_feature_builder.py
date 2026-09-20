from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

DEFAULT_INPUT = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "processed"
    / "delhi_forecasting_weather.csv"
)

DEFAULT_OUTPUT = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "processed"
    / "fusion"
    / "delhi_forecasting_episode.csv"
)

STATION_COL = "station_id"
TIME_COL = "timestamp"
TARGET_COL = "PM2.5"
SEGMENT_COL = "segment_id"

THRESHOLD_150 = 150.0
THRESHOLD_250 = 250.0


# ---------------------------------------------------------------------
# Feature definitions
# ---------------------------------------------------------------------

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


# ---------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------

def _validate_input(df: pd.DataFrame) -> None:
    required = {
        STATION_COL,
        TIME_COL,
        TARGET_COL,
        SEGMENT_COL,
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    if not pd.api.types.is_datetime64_any_dtype(df[TIME_COL]):
        raise TypeError(
            f"{TIME_COL!r} must be a datetime column."
        )


# ---------------------------------------------------------------------
# Exact timestamp lag
# ---------------------------------------------------------------------

def _exact_lag(
    group: pd.DataFrame,
    hours: int,
) -> pd.Series:
    """
    Return PM2.5 at the exact timestamp t - hours.

    No positional shift is used.

    If the exact source timestamp does not exist,
    the result is NaN.
    """

    lookup = (
        group
        .set_index(TIME_COL)[TARGET_COL]
    )

    source_time = (
        group[TIME_COL]
        - pd.Timedelta(hours=hours)
    )

    return source_time.map(lookup)


# ---------------------------------------------------------------------
# Trailing rolling statistic
# ---------------------------------------------------------------------

def _trailing_rolling(
    group: pd.DataFrame,
    window_hours: int,
    statistic: str,
) -> pd.Series:
    """
    Calculate a trailing time-based statistic.

    Only observations at or before t are used.

    The calculation is performed within one station/segment
    group, so it cannot cross the known large data gap.
    """

    values = (
        group
        .set_index(TIME_COL)[TARGET_COL]
    )

    rolling = values.rolling(
        f"{window_hours}h",
        min_periods=1,
    )

    if statistic == "mean":
        result = rolling.mean()

    elif statistic == "std":
        result = rolling.std()

    elif statistic == "max":
        result = rolling.max()

    else:
        raise ValueError(
            f"Unsupported rolling statistic: {statistic}"
        )

    return (
        result
        .reindex(group[TIME_COL])
        .set_axis(group.index)
    )


# ---------------------------------------------------------------------
# Episode onset timer
# ---------------------------------------------------------------------

def _hours_since_threshold_onset(
    group: pd.DataFrame,
    threshold: float,
) -> pd.Series:
    """
    Calculate hours since the current threshold episode began.

    An onset is detected when:

        current PM2.5 >= threshold

    and the previous exact hour is below threshold.

    Missing PM2.5 resets the observable episode state.

    Below threshold:
        0

    Above threshold with an established episode:
        elapsed hours since onset
    """

    values = group[TARGET_COL]

    result = pd.Series(
        np.nan,
        index=group.index,
        dtype=float,
    )

    last_onset_time = None
    previous_value = None
    previous_timestamp = None

    for idx, timestamp, value in zip(
        group.index,
        group[TIME_COL],
        values,
    ):
        if pd.isna(value):
            last_onset_time = None
            previous_value = None
            previous_timestamp = timestamp
            continue

        # Below threshold.
        if value < threshold:
            result.loc[idx] = 0.0
            last_onset_time = None
            previous_value = value
            previous_timestamp = timestamp
            continue

        # Determine whether the previous observation is
        # exactly one hour earlier.
        previous_is_exact_hour = (
            previous_timestamp is not None
            and (
                timestamp - previous_timestamp
                == pd.Timedelta(hours=1)
            )
        )

        onset = (
            previous_is_exact_hour
            and previous_value is not None
            and previous_value < threshold
        )

        # If no observable episode is active, begin one.
        if onset or last_onset_time is None:
            last_onset_time = timestamp

        result.loc[idx] = (
            timestamp - last_onset_time
        ).total_seconds() / 3600.0

        previous_value = value
        previous_timestamp = timestamp

    return result


# ---------------------------------------------------------------------
# 24-hour threshold statistics
# ---------------------------------------------------------------------

def _hours_above_threshold_24h(
    group: pd.DataFrame,
    threshold: float,
) -> tuple[pd.Series, pd.Series]:
    """
    Calculate:

        hours above threshold in trailing 24h
        fraction above threshold in trailing 24h

    Only valid PM2.5 observations contribute to the denominator.
    """

    values = group[TARGET_COL]

    above = (
        values >= threshold
    ).astype(float)

    valid = (
        values.notna()
    ).astype(float)

    indexed_above = above.set_axis(
        group[TIME_COL]
    )

    indexed_valid = valid.set_axis(
        group[TIME_COL]
    )

    count = (
        indexed_above
        .rolling(
            "24h",
            min_periods=1,
        )
        .sum()
        .reindex(group[TIME_COL])
        .set_axis(group.index)
    )

    valid_count = (
        indexed_valid
        .rolling(
            "24h",
            min_periods=1,
        )
        .sum()
        .reindex(group[TIME_COL])
        .set_axis(group.index)
    )

    fraction = (
        count
        / valid_count.replace(
            0,
            np.nan,
        )
    )

    return count, fraction


# ---------------------------------------------------------------------
# Main feature builder
# ---------------------------------------------------------------------

def build_episode_features(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build causal episode-dynamics features.

    Required input columns:

        station_id
        timestamp
        PM2.5
        segment_id

    Every feature uses only PM2.5 information available at
    or before the current timestamp.

    No PM2.5 imputation is performed.

    Existing segment_id values are respected.
    """

    _validate_input(df)

    original_index = df.index

    work = df.copy()

    # Initialize feature columns.
    for feature in EPISODE_FEATURES:
        work[feature] = np.nan

    # -------------------------------------------------------------
    # Process each station/segment independently.
    # -------------------------------------------------------------

    grouped = work.groupby(
        [STATION_COL, SEGMENT_COL],
        sort=False,
    )

    for (_, _), group in grouped:
        group = group.sort_values(TIME_COL)

        # ---------------------------------------------------------
        # Exact PM2.5 deltas
        # ---------------------------------------------------------

        for hours in [
            1,
            3,
            6,
            12,
            24,
        ]:
            lag = _exact_lag(
                group,
                hours,
            )

            work.loc[
                group.index,
                f"pm25_delta_{hours}h",
            ] = (
                group[TARGET_COL].to_numpy()
                - lag.to_numpy()
            )

        # ---------------------------------------------------------
        # PM2.5 acceleration
        # ---------------------------------------------------------

        delta_1 = (
            group[TARGET_COL]
            - _exact_lag(group, 1)
        )

        delta_3 = (
            group[TARGET_COL]
            - _exact_lag(group, 3)
        )

        delta_6 = (
            group[TARGET_COL]
            - _exact_lag(group, 6)
        )

        delta_1_previous = (
            _exact_lag(group, 1)
            - _exact_lag(group, 2)
        )

        delta_3_previous = (
            _exact_lag(group, 3)
            - _exact_lag(group, 6)
        )

        delta_6_previous = (
            _exact_lag(group, 6)
            - _exact_lag(group, 12)
        )

        work.loc[
            group.index,
            "pm25_acceleration_1h",
        ] = (
            delta_1.to_numpy()
            - delta_1_previous.to_numpy()
        )

        work.loc[
            group.index,
            "pm25_acceleration_3h",
        ] = (
            delta_3.to_numpy()
            - delta_3_previous.to_numpy()
        )

        work.loc[
            group.index,
            "pm25_acceleration_6h",
        ] = (
            delta_6.to_numpy()
            - delta_6_previous.to_numpy()
        )

        # ---------------------------------------------------------
        # Trailing statistics
        # ---------------------------------------------------------

        for window in [
            6,
            12,
            24,
        ]:
            work.loc[
                group.index,
                f"pm25_mean_{window}h",
            ] = _trailing_rolling(
                group,
                window,
                "mean",
            ).to_numpy()

        for window in [
            6,
            24,
        ]:
            work.loc[
                group.index,
                f"pm25_std_{window}h",
            ] = _trailing_rolling(
                group,
                window,
                "std",
            ).to_numpy()

            work.loc[
                group.index,
                f"pm25_max_{window}h",
            ] = _trailing_rolling(
                group,
                window,
                "max",
            ).to_numpy()

        # ---------------------------------------------------------
        # Episode timers
        # ---------------------------------------------------------

        work.loc[
            group.index,
            "hours_since_150_onset",
        ] = _hours_since_threshold_onset(
            group,
            THRESHOLD_150,
        ).to_numpy()

        work.loc[
            group.index,
            "hours_since_250_onset",
        ] = _hours_since_threshold_onset(
            group,
            THRESHOLD_250,
        ).to_numpy()

        # ---------------------------------------------------------
        # 24-hour threshold statistics
        # ---------------------------------------------------------

        count_150, fraction_150 = (
            _hours_above_threshold_24h(
                group,
                THRESHOLD_150,
            )
        )

        count_250, fraction_250 = (
            _hours_above_threshold_24h(
                group,
                THRESHOLD_250,
            )
        )

        work.loc[
            group.index,
            "hours_above_150_24h",
        ] = count_150.to_numpy()

        work.loc[
            group.index,
            "fraction_above_150_24h",
        ] = fraction_150.to_numpy()

        work.loc[
            group.index,
            "hours_above_250_24h",
        ] = count_250.to_numpy()

        work.loc[
            group.index,
            "fraction_above_250_24h",
        ] = fraction_250.to_numpy()

    # Restore original row ordering.
    work = work.loc[original_index]

    return work


# ---------------------------------------------------------------------
# Command-line execution
# ---------------------------------------------------------------------

def main() -> None:
    print(
        f"Input:  {DEFAULT_INPUT}"
    )

    print(
        f"Output: {DEFAULT_OUTPUT}"
    )

    df = pd.read_csv(
        DEFAULT_INPUT,
        parse_dates=[TIME_COL],
    )

    print(
        f"Loaded rows: {len(df):,}"
    )

    print(
        f"Stations: {df[STATION_COL].nunique()}"
    )

    print(
        f"Segments: {df[SEGMENT_COL].nunique()}"
    )

    result = build_episode_features(df)

    DEFAULT_OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result.to_csv(
        DEFAULT_OUTPUT,
        index=False,
    )

    print(
        f"Saved {len(result):,} rows "
        f"to {DEFAULT_OUTPUT}"
    )

    print(
        "\nEpisode features:"
    )

    for feature in EPISODE_FEATURES:
        print(
            f"  {feature}"
        )

    print(
        "\nMissingness:"
    )

    print(
        result[EPISODE_FEATURES]
        .isna()
        .mean()
        .mul(100)
        .round(2)
        .sort_values(
            ascending=False
        )
        .to_string()
    )


if __name__ == "__main__":
    main()
