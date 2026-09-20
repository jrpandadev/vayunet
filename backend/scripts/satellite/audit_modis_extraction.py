import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import matplotlib
matplotlib.use('Agg')

REPORT_DIR = "backend/reports/satellite/modis"
os.makedirs(REPORT_DIR, exist_ok=True)

# Load Extraction
print("Loading extracted MODIS data...")
df = pd.read_parquet("backend/data/processed/satellite/delhi_mcd19a2_maiac_station_aod.parquet")

# Load Inventory
print("Loading inventory...")
inv_df = pd.read_csv("backend/data/raw/satellite/modis_maiac/inventory.csv")

# Ensure date parsed
df['date_dt'] = pd.to_datetime(df['date'])

# Stats
total_granules = len(inv_df)
valid_granules = inv_df['is_valid'].sum()
invalid_granules = total_granules - valid_granules
duplicate_granules = inv_df['is_duplicate'].sum()

earliest_obs = df['date'].min()
latest_obs = df['date'].max()
num_obs = len(df)
stations_covered = df['station_name'].nunique()
obs_per_station = df.groupby('station_name').size().mean()

days_in_range = (pd.to_datetime(latest_obs) - pd.to_datetime(earliest_obs)).days + 1
obs_per_day = num_obs / days_in_range if days_in_range > 0 else 0

qa_accepted = df['qa_accepted'].sum()
qa_rejected = num_obs - qa_accepted
qa_acceptance_rate = (qa_accepted / num_obs) * 100 if num_obs > 0 else 0

missing_aod55 = df['aod_055'].isna().sum()

# CSV Output
audit_stats = [{
    "total_granules": total_granules,
    "valid_granules": valid_granules,
    "invalid_granules": invalid_granules,
    "duplicate_granules": duplicate_granules,
    "earliest_observation": earliest_obs,
    "latest_observation": latest_obs,
    "total_observations": num_obs,
    "stations_covered": stations_covered,
    "observations_per_station_mean": obs_per_station,
    "observations_per_day_mean": obs_per_day,
    "qa_accepted_count": qa_accepted,
    "qa_rejected_count": qa_rejected,
    "missing_aod55_count": missing_aod55
}]
pd.DataFrame(audit_stats).to_csv(os.path.join(REPORT_DIR, "extraction_audit.csv"), index=False)

# MD Output
md = f"""# MODIS MAIAC Extraction Audit

## Granule Inventory
- **Total Granules**: {total_granules}
- **Valid Granules**: {valid_granules}
- **Invalid Granules**: {invalid_granules}
- **Duplicate Filenames**: {duplicate_granules}

## Temporal & Spatial Coverage
- **Date Coverage**: {earliest_obs} to {latest_obs}
- **Stations Covered**: {stations_covered}
- **Observations / Day (Avg)**: {obs_per_day:.1f}
- **Observations / Station (Avg)**: {obs_per_station:.1f}

## Data Quality & Filtering
- **Total Extracted Records**: {num_obs}
- **Missing AOD 0.55**: {missing_aod55} (Out of bounds, fill value, or masked in HDF)
- **QA Accepted (Clear Sky + Best Quality)**: {qa_accepted} ({qa_acceptance_rate:.1f}%)
- **QA Rejected**: {qa_rejected}
"""

with open(os.path.join(REPORT_DIR, "extraction_audit.md"), 'w') as f:
    f.write(md)

print("Saved audit CSV and Markdown.")

# EDA PLOTS
print("Generating EDA Plots...")

valid_df = df[df['qa_accepted'] == True]

# 1. AOD distribution
plt.figure(figsize=(10,6))
sns.histplot(valid_df['aod_055'].dropna(), bins=50, kde=True)
plt.title("MODIS MAIAC AOD 0.55 Distribution (QA Accepted)")
plt.xlabel("AOD 0.55")
plt.savefig(os.path.join(REPORT_DIR, "01_aod_distribution.png"), dpi=300, bbox_inches='tight')
plt.close()

# 2. AOD distribution by station
plt.figure(figsize=(12,6))
sns.boxplot(data=valid_df, x='station_name', y='aod_055')
plt.xticks(rotation=45, ha='right')
plt.title("AOD 0.55 Distribution by Station (QA Accepted)")
plt.savefig(os.path.join(REPORT_DIR, "02_aod_by_station.png"), dpi=300, bbox_inches='tight')
plt.close()

# 3. AOD monthly distribution
valid_df['month'] = valid_df['date_dt'].dt.month
plt.figure(figsize=(10,6))
sns.boxplot(data=valid_df, x='month', y='aod_055')
plt.title("AOD 0.55 Monthly Distribution (QA Accepted)")
plt.savefig(os.path.join(REPORT_DIR, "03_aod_monthly_dist.png"), dpi=300, bbox_inches='tight')
plt.close()

# 4. AOD monthly observation count
monthly_counts = valid_df.groupby('month').size()
plt.figure(figsize=(10,6))
sns.barplot(x=monthly_counts.index, y=monthly_counts.values, color='steelblue')
plt.title("Monthly Observation Count (QA Accepted)")
plt.savefig(os.path.join(REPORT_DIR, "04_monthly_obs_count.png"), dpi=300, bbox_inches='tight')
plt.close()

# 5. AOD coverage by station
station_counts = valid_df.groupby('station_name').size().sort_values()
plt.figure(figsize=(10,6))
station_counts.plot(kind='barh', color='darkgreen')
plt.title("Total Valid Observations by Station")
plt.xlabel("Count")
plt.savefig(os.path.join(REPORT_DIR, "05_coverage_by_station.png"), dpi=300, bbox_inches='tight')
plt.close()

# 6. AOD coverage over time
daily_counts = valid_df.groupby('date_dt').size()
plt.figure(figsize=(14,4))
daily_counts.plot(color='black')
plt.title("Daily Valid Observations Over Time")
plt.ylabel("Observations")
plt.savefig(os.path.join(REPORT_DIR, "06_coverage_over_time.png"), dpi=300, bbox_inches='tight')
plt.close()

# 7. QA acceptance/rejection distribution
plt.figure(figsize=(8,8))
plt.pie([qa_accepted, qa_rejected], labels=['Accepted (Clear+Best)', 'Rejected (Cloud/Poor)'], autopct='%1.1f%%', colors=['#4CAF50', '#F44336'])
plt.title("QA Acceptance Rate")
plt.savefig(os.path.join(REPORT_DIR, "07_qa_acceptance.png"), dpi=300, bbox_inches='tight')
plt.close()

# 8/9. AOD vs PM2.5 scatter
# Try to load target PM2.5 to join
try:
    pm25_df = pd.read_parquet("backend/data/processed/cpcb/delhi_cpcb_pm25_imputed.parquet")
    pm25_df['date'] = pd.to_datetime(pm25_df['timestamp']).dt.date.astype(str)
    # daily average PM2.5 for scatter
    daily_pm25 = pm25_df.groupby(['date', 'station_id'])['pm25'].mean().reset_index()

    join_df = pd.merge(valid_df, daily_pm25, on=['date', 'station_id'], how='inner')

    if not join_df.empty:
        plt.figure(figsize=(8,8))
        sns.scatterplot(data=join_df, x='aod_055', y='pm25', alpha=0.3)
        plt.title("Daily AOD 0.55 vs Daily PM2.5")
        plt.savefig(os.path.join(REPORT_DIR, "08_aod_vs_pm25.png"), dpi=300, bbox_inches='tight')
        plt.close()

        # Season
        join_df['season'] = join_df['date_dt'].dt.month % 12 // 3 + 1
        season_map = {1: 'Winter', 2: 'Spring', 3: 'Summer', 4: 'Fall'}
        join_df['season_name'] = join_df['season'].map(season_map)

        plt.figure(figsize=(10,8))
        sns.scatterplot(data=join_df, x='aod_055', y='pm25', hue='season_name', alpha=0.4)
        plt.title("Daily AOD 0.55 vs Daily PM2.5 (By Season)")
        plt.savefig(os.path.join(REPORT_DIR, "09_aod_vs_pm25_season.png"), dpi=300, bbox_inches='tight')
        plt.close()
except Exception as e:
    print("Could not generate PM2.5 scatter plots:", e)

print("Done generating EDA plots.")
