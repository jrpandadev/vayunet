from pathlib import Path

import pandas as pd

from episode_feature_builder import (
    build_episode_features,
    EPISODE_FEATURES,
)


INPUT = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "processed"
    / "delhi_forecasting_weather.csv"
)


def main():
    print("=" * 70)
    print("EPISODE FEATURE BUILDER — SMALL SAMPLE TEST")
    print("=" * 70)

    # ---------------------------------------------------------------
    # Load only a small sample.
    # ---------------------------------------------------------------

    print(f"\nInput: {INPUT}")

    df = pd.read_csv(
        INPUT,
        parse_dates=["timestamp"],
        nrows=5000,
    )

    print(f"Loaded sample rows: {len(df):,}")

    # ---------------------------------------------------------------
    # Basic source inspection.
    # ---------------------------------------------------------------

    print("\nSource columns:")
    print(df.columns.tolist())

    required = {
        "station_id",
        "timestamp",
        "PM2.5",
    }

    missing = required - set(df.columns)

    if missing:
        raise AssertionError(
            f"Missing required columns: {sorted(missing)}"
        )

    print("\nRequired columns: PASS")

    # ---------------------------------------------------------------
    # Build episode features.
    # ---------------------------------------------------------------

    result = build_episode_features(df)

    print(
        f"\nOutput rows: {len(result):,}"
    )

    # ---------------------------------------------------------------
    # Row-count check.
    # ---------------------------------------------------------------

    assert len(result) == len(df), (
        "Row count changed during feature construction."
    )

    print("Row-count integrity: PASS")

    # ---------------------------------------------------------------
    # Original columns must remain unchanged.
    # ---------------------------------------------------------------

    for column in df.columns:
        if column not in result.columns:
            raise AssertionError(
                f"Original column disappeared: {column}"
            )

    print("Original columns preserved: PASS")

    # ---------------------------------------------------------------
    # Episode features must exist.
    # ---------------------------------------------------------------

    missing_features = [
        feature
        for feature in EPISODE_FEATURES
        if feature not in result.columns
    ]

    assert not missing_features, (
        f"Missing episode features: {missing_features}"
    )

    print(
        f"Episode feature columns: "
        f"{len(EPISODE_FEATURES)}"
    )

    print("Episode feature existence: PASS")

    # ---------------------------------------------------------------
    # Station/timestamp integrity.
    # ---------------------------------------------------------------

    assert (
        result["station_id"].to_numpy()
        == df["station_id"].to_numpy()
    ).all()

    assert (
        result["timestamp"].to_numpy()
        == df["timestamp"].to_numpy()
    ).all()

    print("Station/timestamp integrity: PASS")

    # ---------------------------------------------------------------
    # Check for infinite values.
    # ---------------------------------------------------------------

    numeric_features = result[
        EPISODE_FEATURES
    ].select_dtypes(
        include="number"
    )

    infinite_count = (
        numeric_features
        .isin([float("inf"), float("-inf")])
        .sum()
        .sum()
    )

    assert infinite_count == 0, (
        f"Found {infinite_count} infinite values."
    )

    print("Infinite-value check: PASS")

    # ---------------------------------------------------------------
    # Threshold fractions must remain between 0 and 1.
    # ---------------------------------------------------------------

    for column in [
        "fraction_above_150_24h",
        "fraction_above_250_24h",
    ]:
        valid = result[column].dropna()

        if not valid.empty:
            assert (
                (valid >= 0)
                & (valid <= 1)
            ).all(), (
                f"{column} contains values outside [0, 1]."
            )

    print("Threshold fraction bounds: PASS")

    # ---------------------------------------------------------------
    # Episode timers must be non-negative.
    # ---------------------------------------------------------------

    for column in [
        "hours_since_150_onset",
        "hours_since_250_onset",
    ]:
        valid = result[column].dropna()

        if not valid.empty:
            assert (
                valid >= 0
            ).all(), (
                f"{column} contains negative values."
            )

    print("Episode timer bounds: PASS")

    # ---------------------------------------------------------------
    # Display a small preview.
    # ---------------------------------------------------------------

    print("\nFeature preview:")

    preview_columns = [
        "station_id",
        "timestamp",
        "PM2.5",
        "pm25_delta_1h",
        "pm25_delta_6h",
        "pm25_mean_6h",
        "pm25_max_24h",
        "hours_since_150_onset",
        "hours_since_250_onset",
        "fraction_above_150_24h",
        "fraction_above_250_24h",
    ]

    print(
        result[
            preview_columns
        ].head(15).to_string(index=False)
    )

    # ---------------------------------------------------------------
    # Missingness report.
    # ---------------------------------------------------------------

    print("\nEpisode feature missingness:")

    missingness = (
        result[EPISODE_FEATURES]
        .isna()
        .mean()
        .mul(100)
        .round(2)
        .sort_values(
            ascending=False
        )
    )

    print(missingness.to_string())

    print("\n" + "=" * 70)
    print("SMALL SAMPLE TEST: PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()
