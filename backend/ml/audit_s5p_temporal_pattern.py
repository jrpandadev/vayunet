from pathlib import Path

import pandas as pd


INPUT_FILE = Path("data/raw/satellite/delhi_s5p_no2.csv")


df = pd.read_csv(INPUT_FILE)

df["timestamp"] = pd.to_datetime(
    df["timestamp"],
    utc=True,
    errors="coerce",
)

df["timestamp_ist"] = (
    df["timestamp"]
    .dt.tz_convert("Asia/Kolkata")
)

df["date_ist"] = df["timestamp_ist"].dt.date
df["utc_hour"] = df["timestamp"].dt.hour
df["ist_hour"] = df["timestamp_ist"].dt.hour
df["month"] = df["timestamp_ist"].dt.month
df["year"] = df["timestamp_ist"].dt.year


print("=" * 70)
print("SENTINEL-5P TEMPORAL PATTERN AUDIT")
print("=" * 70)


# ------------------------------------------------------------
# Observation counts
# ------------------------------------------------------------

print("\nBasic counts")

print(f"Total observations: {len(df):,}")

print(
    f"Unique station-days: "
    f"{df[['station_id', 'date_ist']].drop_duplicates().shape[0]:,}"
)

print(
    f"Unique dates: "
    f"{df['date_ist'].nunique():,}"
)


# ------------------------------------------------------------
# UTC observation time
# ------------------------------------------------------------

print("\nUTC observation hour distribution")

utc_hours = (
    df["utc_hour"]
    .value_counts()
    .sort_index()
)

print(utc_hours.to_string())


# ------------------------------------------------------------
# IST observation time
# ------------------------------------------------------------

print("\nIST observation hour distribution")

ist_hours = (
    df["ist_hour"]
    .value_counts()
    .sort_index()
)

print(ist_hours.to_string())


# ------------------------------------------------------------
# Observation time statistics
# ------------------------------------------------------------

minutes_ist = (
    df["timestamp_ist"].dt.hour * 60
    + df["timestamp_ist"].dt.minute
    + df["timestamp_ist"].dt.second / 60
)

print("\nIST overpass-time statistics")

print(
    f"Minimum: {minutes_ist.min() / 60:.2f} h"
)

print(
    f"Median: {minutes_ist.median() / 60:.2f} h"
)

print(
    f"Mean: {minutes_ist.mean() / 60:.2f} h"
)

print(
    f"Maximum: {minutes_ist.max() / 60:.2f} h"
)


# ------------------------------------------------------------
# Monthly coverage
# ------------------------------------------------------------

print("\nObservations by year/month")

monthly = (
    df.groupby(["year", "month"])
      .size()
      .reset_index(name="observations")
)

print(monthly.to_string(index=False))


# ------------------------------------------------------------
# Station × year
# ------------------------------------------------------------

print("\nStation/year coverage")

station_year = (
    df.groupby(["station_id", "year"])
      .size()
      .unstack(fill_value=0)
)

print(station_year.to_string())


# ------------------------------------------------------------
# Station-day multiplicity
# ------------------------------------------------------------

station_day_counts = (
    df.groupby(["station_id", "date_ist"])
      .size()
)

print("\nObservations per station-day")

print(
    station_day_counts
    .value_counts()
    .sort_index()
    .to_string()
)


# ------------------------------------------------------------
# Multiple observations on same station/date
# ------------------------------------------------------------

multi_station_days = (
    station_day_counts > 1
).sum()

print(
    f"\nStation-days with >1 observation: "
    f"{multi_station_days:,}"
)


# ------------------------------------------------------------
# Cross-station date coverage
# ------------------------------------------------------------

date_station_counts = (
    df.groupby("date_ist")["station_id"]
      .nunique()
)

print("\nNumber of stations observed per satellite date")

print(
    date_station_counts
    .value_counts()
    .sort_index()
    .to_string()
)


# ------------------------------------------------------------
# Summary
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("TEMPORAL PATTERN AUDIT COMPLETE")
print("=" * 70)
