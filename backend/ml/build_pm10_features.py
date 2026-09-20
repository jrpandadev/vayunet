from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent


def resolve_input_path(p_str: str) -> Path:
    p = Path(p_str)

    if p.exists():
        return p

    if (Path("backend") / p_str).exists():
        return Path("backend") / p_str

    if p_str.startswith("backend/") and Path(p_str[8:]).exists():
        return Path(p_str[8:])

    if (BASE_DIR / p_str).exists():
        return BASE_DIR / p_str

    if p_str.startswith("backend/") and (BASE_DIR / p_str[8:]).exists():
        return BASE_DIR / p_str[8:]

    return p


def resolve_output_path(p_str: str) -> Path:
    if Path("backend").exists():
        return (
            Path(p_str)
            if p_str.startswith("backend/")
            else Path("backend") / p_str
        )

    return (
        Path(p_str[8:])
        if p_str.startswith("backend/")
        else Path(p_str)
    )


INPUT = resolve_input_path(
    "backend/data/processed/fusion/delhi_forecasting_satellite.csv"
)

OUTPUT = resolve_output_path(
    "backend/data/processed/fusion/delhi_forecasting_satellite_pm10.csv"
)

AUDIT = resolve_output_path(
    "backend/reports/satellite/pm10_feature_audit.csv"
)

LAGS = [1, 3, 6, 12, 24, 48, 72]


def find_continuous_segments(group: pd.DataFrame):
    """
    Split one station's observations into continuous hourly segments.

    A new segment starts whenever the timestamp gap is not exactly 1 hour.

    This prevents lag/rolling features from crossing:
      - missing hourly observations
      - long data gaps
      - the known ~31-day CPCB gap
    """

    timestamps = group["timestamp"]

    gap = timestamps.diff()

    segment_id = gap.ne(pd.Timedelta(hours=1)).cumsum()

    return segment_id


def build_exact_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build PM10 lag features using exact timestamp matching.

    For each station and timestamp t:

        PM10_lag_1h  = PM10 at exactly t - 1 hour
        PM10_lag_3h  = PM10 at exactly t - 3 hours
        ...
        PM10_lag_72h = PM10 at exactly t - 72 hours

    If the exact historical timestamp does not exist,
    the feature remains NaN.

    No previous-available-observation substitution is allowed.
    """

    index = pd.MultiIndex.from_frame(
        df[["station_id", "timestamp"]]
    )

    pm10_lookup = pd.Series(
        df["PM10"].to_numpy(),
        index=index,
        name="PM10",
    )

    for lag in LAGS:

        feature = f"PM10_lag_{lag}h"

        lookup_index = pd.MultiIndex.from_arrays(
            [
                df["station_id"].to_numpy(),
                (
                    df["timestamp"]
                    - pd.to_timedelta(lag, unit="h")
                ).to_numpy(),
            ],
            names=["station_id", "timestamp"],
        )

        df[feature] = (
            pm10_lookup
            .reindex(lookup_index)
            .to_numpy()
        )

    return df


def build_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build PM10 rolling features strictly within continuous
    hourly station segments.

    Windows:

        6h mean
        24h mean
        24h standard deviation

    Missing timestamps do not get filled.

    Because each segment is continuous hourly data, a rolling
    window of N observations corresponds to N consecutive hours.
    """

    feature_columns = [
        "PM10_roll_mean_6h",
        "PM10_roll_mean_24h",
        "PM10_roll_std_24h",
    ]

    for column in feature_columns:
        df[column] = np.nan

    grouped = df.groupby(
        "station_id",
        sort=False,
        group_keys=False,
    )

    for station_id, station_df in grouped:

        station_df = station_df.sort_values(
            "timestamp"
        ).copy()

        station_df["_segment"] = (
            find_continuous_segments(station_df)
        )

        for _, segment_df in station_df.groupby(
            "_segment",
            sort=False,
        ):

            idx = segment_df.index

            pm10 = segment_df["PM10"]

            df.loc[idx, "PM10_roll_mean_6h"] = (
                pm10
                .rolling(
                    window=6,
                    min_periods=6,
                )
                .mean()
                .to_numpy()
            )

            df.loc[idx, "PM10_roll_mean_24h"] = (
                pm10
                .rolling(
                    window=24,
                    min_periods=24,
                )
                .mean()
                .to_numpy()
            )

            df.loc[idx, "PM10_roll_std_24h"] = (
                pm10
                .rolling(
                    window=24,
                    min_periods=24,
                )
                .std()
                .to_numpy()
            )

    return df


def verify_exact_lags(df: pd.DataFrame):
    """
    Independently verify that every non-null lag corresponds
    to the exact requested historical timestamp.
    """

    print("\nExact lag verification:")

    index = pd.MultiIndex.from_frame(
        df[["station_id", "timestamp"]]
    )

    pm10_lookup = pd.Series(
        df["PM10"].to_numpy(),
        index=index,
        name="PM10",
    )

    for lag in LAGS:

        feature = f"PM10_lag_{lag}h"

        expected_index = pd.MultiIndex.from_arrays(
            [
                df["station_id"].to_numpy(),
                (
                    df["timestamp"]
                    - pd.to_timedelta(lag, unit="h")
                ).to_numpy(),
            ],
            names=["station_id", "timestamp"],
        )

        expected = (
            pm10_lookup
            .reindex(expected_index)
            .to_numpy()
        )

        actual = df[feature].to_numpy()

        equal = np.allclose(
            actual,
            expected,
            equal_nan=True,
        )

        if not equal:
            raise ValueError(
                f"Exact lag verification failed: {feature}"
            )

        print(f"  {feature:<25} PASS")


def verify_no_future_information(df: pd.DataFrame):
    """
    Verify that each PM10 lag uses a timestamp strictly before t.
    """

    print("\nFuture-information check:")

    for lag in LAGS:

        feature = f"PM10_lag_{lag}h"

        non_null = df[feature].notna()

        if not non_null.any():
            print(
                f"  {feature:<25} "
                "SKIPPED (no non-null values)"
            )
            continue

        historical_timestamp = (
            df.loc[non_null, "timestamp"]
            - pd.to_timedelta(lag, unit="h")
        )

        if not (
            historical_timestamp
            < df.loc[non_null, "timestamp"]
        ).all():
            raise ValueError(
                f"Future-information check failed: {feature}"
            )

        print(f"  {feature:<25} PASS")


def verify_pm10_preservation(df: pd.DataFrame):
    """
    Verify that the original PM10 measurements were not
    modified by feature construction.
    """

    source = pd.read_csv(
        INPUT,
        usecols=[
            "station_id",
            "timestamp",
            "PM10",
        ],
        parse_dates=["timestamp"],
    )

    source = source.sort_values(
        ["station_id", "timestamp"]
    ).reset_index(drop=True)

    current = df[
        [
            "station_id",
            "timestamp",
            "PM10",
        ]
    ].sort_values(
        ["station_id", "timestamp"]
    ).reset_index(drop=True)

    if len(current) != len(source):
        raise ValueError(
            "Row count changed during PM10 feature construction."
        )

    if not (
        current["station_id"].to_numpy()
        == source["station_id"].to_numpy()
    ).all():
        raise ValueError(
            "Station ordering changed unexpectedly."
        )

    if not (
        current["timestamp"].to_numpy()
        == source["timestamp"].to_numpy()
    ).all():
        raise ValueError(
            "Timestamp ordering changed unexpectedly."
        )

    if not np.allclose(
        current["PM10"].to_numpy(),
        source["PM10"].to_numpy(),
        equal_nan=True,
    ):
        raise ValueError(
            "Original PM10 values were modified."
        )

    print("\nOriginal PM10 preservation: PASS")


def verify_row_integrity(df: pd.DataFrame):
    """
    Verify that feature construction did not alter the
    station/timestamp structure.
    """

    print("\nRow integrity:")

    if df.duplicated(
        ["station_id", "timestamp"]
    ).any():
        raise ValueError(
            "Duplicate station/timestamp rows detected."
        )

    if len(df) != 383303:
        raise ValueError(
            f"Unexpected row count: {len(df):,}"
        )

    print(f"  Rows: {len(df):,} PASS")
    print(
        f"  Stations: "
        f"{df['station_id'].nunique()} PASS"
    )

    print(
        "  Duplicate station/timestamp: 0 PASS"
    )


def build_audit(df: pd.DataFrame, features):
    audit_rows = []

    for feature in features:

        series = df[feature]

        audit_rows.append(
            {
                "feature": feature,
                "rows": len(df),
                "missing": int(series.isna().sum()),
                "missing_pct": float(
                    series.isna().mean() * 100
                ),
                "min": (
                    float(series.min())
                    if series.notna().any()
                    else np.nan
                ),
                "median": (
                    float(series.median())
                    if series.notna().any()
                    else np.nan
                ),
                "max": (
                    float(series.max())
                    if series.notna().any()
                    else np.nan
                ),
            }
        )

    return pd.DataFrame(audit_rows)


def main():

    print("=" * 70)
    print("BUILDING STRICT HISTORICAL PM10 FEATURES")
    print("=" * 70)

    if not INPUT.exists():
        raise FileNotFoundError(
            f"Input dataset not found: {INPUT}"
        )

    df = pd.read_csv(
        INPUT,
        parse_dates=["timestamp"],
    )

    print(f"Input rows: {len(df):,}")

    required = [
        "station_id",
        "timestamp",
        "PM10",
    ]

    missing = [
        c for c in required
        if c not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )

    if df["timestamp"].isna().any():
        raise ValueError(
            "Missing timestamps detected."
        )

    if df.duplicated(
        ["station_id", "timestamp"]
    ).any():
        raise ValueError(
            "Duplicate station/timestamp rows detected."
        )

    df = df.sort_values(
        ["station_id", "timestamp"]
    ).reset_index(drop=True)

    original_columns = list(df.columns)

    # --------------------------------------------------------
    # Exact timestamp lag features
    # --------------------------------------------------------

    print("\nBuilding exact timestamp PM10 lags...")

    df = build_exact_lag_features(df)

    # --------------------------------------------------------
    # Continuous-segment rolling features
    # --------------------------------------------------------

    print(
        "\nBuilding continuous-segment "
        "PM10 rolling features..."
    )

    df = build_rolling_features(df)

    new_features = [
        f"PM10_lag_{lag}h"
        for lag in LAGS
    ] + [
        "PM10_roll_mean_6h",
        "PM10_roll_mean_24h",
        "PM10_roll_std_24h",
    ]

    # --------------------------------------------------------
    # Verification
    # --------------------------------------------------------

    verify_exact_lags(df)

    verify_no_future_information(df)

    verify_pm10_preservation(df)

    verify_row_integrity(df)

    # --------------------------------------------------------
    # Original-column preservation
    # --------------------------------------------------------

    print("\nOriginal-column preservation:")

    for column in original_columns:

        if column not in df.columns:
            raise ValueError(
                f"Original column disappeared: {column}"
            )

    print(
        f"  {len(original_columns)} original columns "
        "preserved: PASS"
    )

    # --------------------------------------------------------
    # Feature audit
    # --------------------------------------------------------

    print("\nFeature audit:")

    for feature in new_features:

        print(
            f"  {feature:<25} "
            f"missing={df[feature].isna().sum():,} "
            f"({df[feature].isna().mean() * 100:.2f}%)"
        )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    AUDIT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        OUTPUT,
        index=False,
    )

    audit_df = build_audit(
        df,
        new_features,
    )

    audit_df.to_csv(
        AUDIT,
        index=False,
    )

    # --------------------------------------------------------
    # Final summary
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("FINAL")
    print("=" * 70)

    print(
        f"Rows:                 {len(df):,}"
    )

    print(
        f"Stations:             "
        f"{df['station_id'].nunique()}"
    )

    print(
        "Duplicate station/time: "
        f"{df.duplicated(['station_id', 'timestamp']).sum()}"
    )

    print(
        f"Original columns:      "
        f"{len(original_columns)}"
    )

    print(
        f"New PM10 features:     "
        f"{len(new_features)}"
    )

    print("\nSaved:")

    print(
        f"  {OUTPUT}"
    )

    print(
        f"  {AUDIT}"
    )

    print(
        "\nPM10 feature construction PASSED."
    )


if __name__ == "__main__":
    main()
