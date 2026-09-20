import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import matplotlib
matplotlib.use('Agg')

OUTPUT_DIR = "backend/reports/eda"
FIGURES_DIR = os.path.join(OUTPUT_DIR, "causal_figures")
os.makedirs(FIGURES_DIR, exist_ok=True)

print("Loading datasets...")
modis_df = pd.read_parquet("backend/data/processed/satellite/delhi_mcd19a2_maiac_station_aod.parquet")

# 1. Inspect Timestamp and Data
# Modis dataset has 'date' column as string e.g. "2022-01-01"
print("Min date in MODIS:", modis_df['date'].min())
print("Max date in MODIS:", modis_df['date'].max())
print("Total rows:", len(modis_df))

# MODIS timestamps represent acquisition time (daytime overpass).
# We approximate this as 12:00 PM UTC on the date.
# Forecast origins are 18:00 PM UTC.
# Latency: Assume 24 hours operational processing delay.
# Freshness rule: <= 72 hours age at forecast origin.

modis_df['obs_time_tznaive'] = pd.to_datetime(modis_df['date']) + pd.Timedelta(hours=12) # Approximate daytime overpass
modis_df['available_time'] = modis_df['obs_time_tznaive'] + pd.Timedelta(hours=24) # Latency assumption

start_date = pd.to_datetime('2022-01-01')
end_date = pd.to_datetime('2026-08-31')
# Simulate one forecast origin per day at 18:00 UTC (tz-naive)
forecast_origins = pd.date_range(start=start_date, end=end_date, freq='D') + pd.Timedelta(hours=18)

results = []

for T0 in forecast_origins:
    modis_avail_raw = modis_df[modis_df['obs_time_tznaive'] <= T0]
    modis_avail_latency = modis_df[modis_df['available_time'] <= T0]

    has_raw = not modis_avail_raw.empty
    has_latency_compliant = not modis_avail_latency.empty

    if has_latency_compliant:
        latest_obs = modis_avail_latency['obs_time_tznaive'].max()
        age_hours = (T0 - latest_obs).total_seconds() / 3600.0
        is_fresh = age_hours <= 72.0
    else:
        latest_obs = pd.NaT
        age_hours = np.nan
        is_fresh = False

    results.append({
        'forecast_origin': T0,
        'has_raw_observation': has_raw,
        'has_latency_compliant': has_latency_compliant,
        'latest_valid_modis_observation': latest_obs,
        'observation_age_hours': age_hours,
        'latency_cutoff': 24.0,
        'freshness_cutoff': 72.0,
        'is_72h_fresh': is_fresh,
        'usable_boolean': has_latency_compliant and is_fresh
    })

res_df = pd.DataFrame(results)

# Print calculations
total_origins = len(res_df)
origins_raw = res_df['has_raw_observation'].sum()
origins_latency = res_df['has_latency_compliant'].sum()
origins_fresh = res_df['is_72h_fresh'].sum()
usable_pct = (origins_fresh / total_origins) * 100.0

print(f"total forecast origins tested: {total_origins}")
print(f"forecast origins with at least one valid MODIS observation: {origins_raw}")
print(f"forecast origins with a valid observation satisfying the latency rule: {origins_latency}")
print(f"forecast origins with a valid observation satisfying the 72h freshness rule: {origins_fresh}")
print(f"usable coverage percentage: {usable_pct:.2f}%")

# Generate 100 rows sample for MODIS
modis_sample = res_df[['forecast_origin', 'latest_valid_modis_observation', 'observation_age_hours', 'latency_cutoff', 'freshness_cutoff', 'usable_boolean']].head(100)
modis_sample.to_csv(os.path.join(OUTPUT_DIR, "causal_availability_reconciliation.csv"), index=False)

# Diagnostic plots
plt.figure(figsize=(12, 6))
sns.scatterplot(data=res_df, x='forecast_origin', y='observation_age_hours', marker='o', alpha=0.5)
plt.title("Forecast Origin Time -> MODIS Observation Age")
plt.xlabel("Forecast Origin")
plt.ylabel("Observation Age (Hours)")
plt.axhline(y=72, color='red', linestyle='--', label='72h Freshness Cutoff')
plt.legend()
plt.savefig(os.path.join(FIGURES_DIR, "modis_age_diagnostic.png"), dpi=300, bbox_inches='tight')
plt.close()

res_df['month'] = res_df['forecast_origin'].dt.month
monthly_cov = res_df.groupby('month')['usable_boolean'].mean() * 100.0
plt.figure(figsize=(10, 6))
sns.barplot(x=monthly_cov.index, y=monthly_cov.values, color='blue')
plt.title("MODIS Usable Coverage % by Month")
plt.xlabel("Month")
plt.ylabel("Usable Coverage (%)")
plt.savefig(os.path.join(FIGURES_DIR, "modis_monthly_usable_coverage.png"), dpi=300, bbox_inches='tight')
plt.close()

# For FIRMS and S5P (sanity check)
# FIRMS
firms_df = pd.read_csv("backend/data/raw/firms_viirs.csv", low_memory=False)
acq_time_str = firms_df['acq_time'].astype(str).str.zfill(4)
firms_df['obs_time_tznaive'] = pd.to_datetime(firms_df['acq_date'] + ' ' + acq_time_str.str[:2] + ':' + acq_time_str.str[2:]).dt.tz_localize(None)
firms_df['source_product'] = firms_df['source_product'].fillna('SP')
firms_df['latency_hours'] = np.where(firms_df['source_product'].str.contains('NRT', na=False, case=False), 3, 48)
firms_df['available_time'] = firms_df['obs_time_tznaive'] + pd.to_timedelta(firms_df['latency_hours'], unit='h')

# S5P
s5p_df = pd.read_csv("backend/data/raw/satellite/delhi_s5p_no2.csv")
s5p_df['obs_time_tznaive'] = pd.to_datetime(s5p_df['timestamp']).dt.tz_localize(None)
s5p_df['available_time'] = s5p_df['obs_time_tznaive'] + pd.Timedelta(hours=24)

# Horizon table function
def calc_horizon_table(name, df, available_col, obs_col):
    rows = []
    for horiz in [6, 24, 72]:
        origins_fresh_h = 0
        origins_latency_h = 0
        origins_raw_h = 0

        for T0 in forecast_origins[::10]: # sampling for speed
            avail_raw = df[df[obs_col] <= T0]
            avail_lat = df[df[available_col] <= T0]

            if not avail_raw.empty:
                origins_raw_h += 1
            if not avail_lat.empty:
                origins_latency_h += 1
                latest_obs = avail_lat[obs_col].max()
                age = (T0 - latest_obs).total_seconds() / 3600.0
                if age <= horiz:
                    origins_fresh_h += 1

        total = len(forecast_origins[::10])
        pct = (origins_fresh_h / total) * 100.0
        status = 'INSUFFICIENT' if pct < 10 else ('USABLE WITH LIMITATIONS' if pct < 80 else 'OPERATIONALLY USABLE')

        rows.append({
            'Dataset': name,
            'Forecast Horizon': f'{horiz}h',
            'Total Origins': total,
            'Raw Observation Available': origins_raw_h,
            'Latency-Compliant': origins_latency_h,
            f'{horiz}h-Fresh': origins_fresh_h,
            'Usable %': f'{pct:.1f}%',
            'Status': status
        })
    return pd.DataFrame(rows)

modis_tbl = calc_horizon_table('MODIS MAIAC', modis_df, 'available_time', 'obs_time_tznaive')
firms_tbl = calc_horizon_table('NASA FIRMS', firms_df, 'available_time', 'obs_time_tznaive')
s5p_tbl = calc_horizon_table('Sentinel-5P', s5p_df, 'available_time', 'obs_time_tznaive')

# Generate Markdown
md = f"""# Causal Availability Audit Reconciliation

## 1. MODIS Calculation Breakdown

- **Total Forecast Origins Tested:** {total_origins}
- **Forecast Origins with Raw Observation:** {origins_raw}
- **Forecast Origins with Latency-Compliant Obs:** {origins_latency}
- **Forecast Origins with 72h-Fresh Obs:** {origins_fresh}
- **Usable Coverage:** {usable_pct:.2f}%

## 2. MODIS Rules & Properties
- **Latency Rule:** 24h operational delay. Obs available at T0 if `obs_time + 24h <= T0`.
- **Freshness Rule:** `(T0 - obs_time) <= 72h`
- **MODIS Obs Timestamp Column:** Extracted from `date` string (e.g., "2022-01-01"), assuming 12:00 PM overpass.
- **Timezones:** Both MODIS overpass approximations and forecast origins were strictly timezone-naive (local approximations).
- **Cause of 0.6%:** The `delhi_mcd19a2_maiac_station_aod.parquet` file only contains 10 days of extracted data (`2022-01-01` to `2022-01-10`). As a result, the overwhelming majority of simulated forecast origins over the 4.5 year period (2022-2026) simply do not have any historical data available in the current file, causing the usable percentage to correctly drop to 0.6%. It is **not** a timezone mismatch.

## 3. Candidate Horizon Availability

### 6h, 24h, 72h Summary Table
{pd.concat([modis_tbl, firms_tbl, s5p_tbl]).to_markdown(index=False)}

## 4. Final Conclusion for MODIS
**MODIS:** [INSUFFICIENT]

**Reasoning:** Although MODIS data passes latency and freshness tests during the extremely brief 10-day window present in the current `.parquet` extraction, the dataset itself is fundamentally incomplete for our 4.5 year period. It contains only 320 rows covering 10 days in January 2022, resulting in a 0.6% usable coverage over the operational test window. It cannot be used for operational ablation until the remainder of the 2022-2023 raw data is processed into the parquet.
"""

with open(os.path.join(OUTPUT_DIR, "causal_availability_reconciliation.md"), 'w') as f:
    f.write(md)

print("Reconciliation complete.")
