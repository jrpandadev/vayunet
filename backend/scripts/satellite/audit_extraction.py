import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed" / "satellite"
RAW_DIR = BASE_DIR / "data" / "raw" / "satellite" / "modis_maiac"
REPORTS_DIR = BASE_DIR / "reports" / "satellite" / "modis"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

def generate_audit():
    # Load extraction dataset
    parquet_path = PROCESSED_DIR / "delhi_mcd19a2_maiac_station_aod.parquet"
    if not parquet_path.exists():
        print(f"Extraction dataset not found: {parquet_path}")
        return

    df = pd.read_parquet(parquet_path)

    # Load inventory
    inventory_path = RAW_DIR / "inventory.csv"
    if inventory_path.exists():
        inv_df = pd.read_csv(inventory_path)
        total_granules = len(inv_df)
        valid_granules = inv_df["is_valid"].sum()
        invalid_granules = total_granules - valid_granules
        duplicate_granules = inv_df["is_duplicate"].sum()
    else:
        total_granules = valid_granules = invalid_granules = duplicate_granules = "N/A"

    # Audit statistics
    df["date"] = pd.to_datetime(df["date"])

    total_obs = len(df)
    valid_qa_obs = df["qa_accepted"].sum()
    invalid_qa_obs = total_obs - valid_qa_obs

    stations_covered = df["station_id"].nunique()
    obs_per_station = df.groupby("station_id").size().mean()

    # Only accepted QA for AOD missingness
    df_valid = df[df["qa_accepted"]]
    missing_aod55 = df_valid["aod_055"].isna().sum()

    earliest_obs = df["observation_time"].min()
    latest_obs = df["observation_time"].min() if total_obs == 0 else df["observation_time"].max()

    # Missing days
    if total_obs > 0:
        date_range = pd.date_range(df["date"].min(), df["date"].max())
        missing_days = len(date_range) - df["date"].nunique()
    else:
        missing_days = "N/A"

    # Write MD report
    md_report = f"""# MODIS MAIAC Extraction Audit

## Granule Inventory
- **Total Granules**: {total_granules}
- **Valid Granules**: {valid_granules}
- **Invalid Granules**: {invalid_granules}
- **Duplicate Granules**: {duplicate_granules}

## Extraction Statistics
- **Total Raw Observations**: {total_obs:,}
- **Accepted QA Observations**: {valid_qa_obs:,} ({(valid_qa_obs/total_obs*100) if total_obs>0 else 0:.1f}%)
- **Rejected QA Observations**: {invalid_qa_obs:,} ({(invalid_qa_obs/total_obs*100) if total_obs>0 else 0:.1f}%)
- **Missing AOD55 (in Valid QA)**: {missing_aod55:,}
- **Stations Covered**: {stations_covered}
- **Avg Obs per Station**: {obs_per_station:.1f}

## Temporal Coverage
- **Earliest Observation**: {earliest_obs}
- **Latest Observation**: {latest_obs}
- **Missing Days in Date Range**: {missing_days}
"""
    with open(REPORTS_DIR / "extraction_audit.md", "w") as f:
        f.write(md_report)

    # Write CSV
    audit_dict = {
        "metric": [
            "total_granules", "valid_granules", "invalid_granules", "duplicate_granules",
            "total_obs", "valid_qa_obs", "invalid_qa_obs", "missing_aod55",
            "stations_covered", "obs_per_station", "earliest_obs", "latest_obs", "missing_days"
        ],
        "value": [
            total_granules, valid_granules, invalid_granules, duplicate_granules,
            total_obs, valid_qa_obs, invalid_qa_obs, missing_aod55,
            stations_covered, obs_per_station, earliest_obs, latest_obs, missing_days
        ]
    }
    pd.DataFrame(audit_dict).to_csv(REPORTS_DIR / "extraction_audit.csv", index=False)

    print(f"Audit complete. Reports saved to {REPORTS_DIR}")

if __name__ == "__main__":
    generate_audit()
