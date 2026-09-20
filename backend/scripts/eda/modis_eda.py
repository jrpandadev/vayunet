import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import numpy as np
import datetime

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed" / "satellite"
REPORTS_DIR = BASE_DIR / "reports" / "satellite" / "modis"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

def run_eda():
    parquet_path = PROCESSED_DIR / "delhi_mcd19a2_maiac_station_aod.parquet"
    if not parquet_path.exists():
        print(f"Extraction dataset not found: {parquet_path}")
        return

    df = pd.read_parquet(parquet_path)
    if len(df) == 0:
        print("Empty dataset.")
        return

    df["date"] = pd.to_datetime(df["date"])
    df["observation_time"] = pd.to_datetime(df["observation_time"])
    df["month"] = df["date"].dt.month
    df["year"] = df["date"].dt.year
    df["year_month"] = df["date"].dt.to_period('M')

    # Separate valid and invalid QA for AOD
    valid_df = df[df["qa_accepted"]].copy()

    # 1. AOD distribution
    plt.figure(figsize=(10, 6))
    sns.histplot(valid_df["aod_055"].dropna(), bins=50, kde=True)
    plt.title("AOD 0.55 Distribution (Valid QA)")
    plt.xlabel("AOD")
    plt.savefig(REPORTS_DIR / "aod_distribution.png")
    plt.close()

    # 2. AOD distribution by station
    plt.figure(figsize=(12, 8))
    sns.boxplot(data=valid_df, x="station_id", y="aod_055")
    plt.title("AOD 0.55 by Station")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(REPORTS_DIR / "aod_by_station.png")
    plt.close()

    # 3. AOD monthly distribution
    plt.figure(figsize=(10, 6))
    sns.boxplot(data=valid_df, x="month", y="aod_055")
    plt.title("AOD 0.55 Monthly Distribution")
    plt.savefig(REPORTS_DIR / "aod_monthly_dist.png")
    plt.close()

    # 4. AOD monthly observation count
    monthly_counts = valid_df.groupby("year_month").size()
    plt.figure(figsize=(12, 6))
    monthly_counts.plot(kind="bar")
    plt.title("Valid AOD Observations per Month")
    plt.ylabel("Count")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(REPORTS_DIR / "aod_monthly_count.png")
    plt.close()

    # 5. AOD coverage by station
    station_counts = valid_df.groupby("station_id").size()
    plt.figure(figsize=(12, 6))
    station_counts.plot(kind="bar")
    plt.title("Valid AOD Observations by Station")
    plt.ylabel("Count")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(REPORTS_DIR / "aod_station_coverage.png")
    plt.close()

    # 6. AOD coverage over time
    daily_counts = valid_df.groupby("date").size()
    plt.figure(figsize=(12, 6))
    daily_counts.plot()
    plt.title("Valid AOD Observations Over Time")
    plt.ylabel("Daily Count")
    plt.savefig(REPORTS_DIR / "aod_over_time.png")
    plt.close()

    # 7. QA acceptance/rejection distribution
    qa_counts = df["qa_accepted"].value_counts()
    plt.figure(figsize=(8, 8))
    plt.pie(qa_counts, labels=["Rejected", "Accepted"] if qa_counts.index[0]==False else ["Accepted", "Rejected"], autopct='%1.1f%%')
    plt.title("QA Acceptance Ratio")
    plt.savefig(REPORTS_DIR / "qa_acceptance_ratio.png")
    plt.close()

    # 8. AOD vs PM2.5 scatter (Join with PM2.5 data)
    pm25_path = BASE_DIR / "data" / "processed" / "delhi_forecasting.csv"
    if pm25_path.exists():
        pm_df = pd.read_csv(pm25_path, usecols=["Timestamp", "station_id", "PM2.5"])
        pm_df["Timestamp"] = pd.to_datetime(pm_df["Timestamp"])
        pm_df["date"] = pm_df["Timestamp"].dt.normalize()

        # Merge daily average PM2.5 and AOD
        daily_pm = pm_df.groupby(["date", "station_id"])["PM2.5"].mean().reset_index()
        daily_aod = valid_df.groupby(["date", "station_id"])["aod_055"].mean().reset_index()

        merged = pd.merge(daily_aod, daily_pm, on=["date", "station_id"], how="inner")

        plt.figure(figsize=(10, 8))
        sns.scatterplot(data=merged, x="aod_055", y="PM2.5", alpha=0.5)

        # Add trendline
        if len(merged) > 1:
            z = np.polyfit(merged["aod_055"].dropna(), merged["PM2.5"].loc[merged["aod_055"].notna()], 1)
            p = np.poly1d(z)
            plt.plot(merged["aod_055"], p(merged["aod_055"]), "r--")

        plt.title("AOD 0.55 vs PM2.5 (Daily Averages)")
        plt.savefig(REPORTS_DIR / "aod_vs_pm25.png")
        plt.close()

        # 9. AOD vs PM2.5 by season
        merged["month"] = merged["date"].dt.month
        def get_season(m):
            if m in [12, 1, 2]: return "Winter"
            elif m in [3, 4, 5]: return "Summer"
            elif m in [6, 7, 8, 9]: return "Monsoon"
            else: return "Post-Monsoon"
        merged["season"] = merged["month"].apply(get_season)

        plt.figure(figsize=(12, 8))
        sns.scatterplot(data=merged, x="aod_055", y="PM2.5", hue="season", alpha=0.6)
        plt.title("AOD 0.55 vs PM2.5 by Season")
        plt.savefig(REPORTS_DIR / "aod_vs_pm25_season.png")
        plt.close()

    print(f"EDA plots saved to {REPORTS_DIR}")

if __name__ == "__main__":
    run_eda()
