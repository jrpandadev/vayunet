import os
from pathlib import Path
import pandas as pd
import numpy as np

# Coordinates for the 10 stations in the dataset
STATIONS = {
    "anand vihar": (28.6468, 77.3157),
    "aya nagar": (28.4707, 77.1099),
    "bawana": (28.7762, 77.0511),
    "ito": (28.6286, 77.2411),
    "jahangirpuri": (28.7328, 77.1706),
    "narela": (28.8228, 77.1019),
    "punjabi bagh": (28.6740, 77.1310),
    "r k puram": (28.5633, 77.1869),
    "vivek vihar": (28.6723, 77.3153),
    "wazirpur": (28.6998, 77.1654)
}

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
REPORT_DIR = BASE_DIR / "reports/investigation"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

FUSION_DATA = DATA_DIR / "processed/fusion/delhi_multisource_fusion_dataset.csv"
FIRMS_FILES = [
    DATA_DIR / "raw/DL_FIRE_J1V-C2_803251/fire_archive_J1V-C2_803251.csv",
    DATA_DIR / "raw/DL_FIRE_J2V-C2_803252/fire_archive_J2V-C2_803252.csv",
    DATA_DIR / "raw/DL_FIRE_SV-C2_803253/fire_archive_SV-C2_803253.csv"
]
HCL_FILE = DATA_DIR / "raw/HCL.txt"
WASTEBURNED_FILE = DATA_DIR / "raw/Wasteburned.txt"

TEST_START = pd.Timestamp("2025-08-30 15:00:00")
TEST_END = pd.Timestamp("2026-08-31 23:00:00")

def haversine_vectorized(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c

def get_station_id(row):
    for st in STATIONS.keys():
        col = f"station_id_{st}"
        if col in row and row[col] == 1:
            return st
    return "unknown"

def main():
    print("Loading fusion data...")
    df = pd.read_csv(FUSION_DATA)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"])
    df = df[(df["Timestamp"] >= TEST_START) & (df["Timestamp"] <= TEST_END)].copy()

    # Extract active station for each row
    station_cols = [c for c in df.columns if c.startswith("station_id_")]
    if station_cols:
        def match_station(r):
            for sc in station_cols:
                if r[sc] == 1:
                    return sc.replace("station_id_", "")
            return "unknown"
        df["active_station"] = df.apply(match_station, axis=1)
    else:
        df["active_station"] = "anand vihar" # Fallback if not dummy encoded

    df["lat"] = df["active_station"].map(lambda x: STATIONS.get(x, (28.6, 77.2))[0])
    df["lon"] = df["active_station"].map(lambda x: STATIONS.get(x, (28.6, 77.2))[1])

    # Define extremes on actual target
    # In test set, we just use PM2.5 itself if target isn't present, but let's use the actual PM2.5 of that hour.
    # The prompt says "where the actual target PM2.5 is >=250".
    df["is_extreme"] = df["PM2.5"] >= 250

    print(f"Test events: {len(df)}. Extreme: {df['is_extreme'].sum()}, Non-extreme: {(~df['is_extreme']).sum()}")

    print("Loading FIRMS data...")
    firms_dfs = []
    for f in FIRMS_FILES:
        if f.exists():
            tdf = pd.read_csv(f)
            # FIRMS has acq_date and acq_time
            tdf["acq_datetime"] = pd.to_datetime(tdf["acq_date"] + " " + tdf["acq_time"].astype(str).str.zfill(4).apply(lambda x: x[:2] + ":" + x[2:]))
            firms_dfs.append(tdf)

    if firms_dfs:
        firms_df = pd.concat(firms_dfs, ignore_index=True)
        firms_df.sort_values("acq_datetime", inplace=True)
    else:
        firms_df = pd.DataFrame(columns=["latitude", "longitude", "acq_datetime", "frp"])

    print("Loading OWBEII data...")
    # OWBEII files typically have lat, lon, value
    # Format: lon lat value (space separated)
    owbeii_hcl = pd.DataFrame(columns=["lon", "lat", "hcl"])
    owbeii_wb = pd.DataFrame(columns=["lon", "lat", "waste"])

    if HCL_FILE.exists():
        try:
            owbeii_hcl = pd.read_csv(HCL_FILE, sep="\s+", names=["lon", "lat", "hcl"], comment="#")
            owbeii_hcl["lon"] = pd.to_numeric(owbeii_hcl["lon"], errors="coerce")
            owbeii_hcl["lat"] = pd.to_numeric(owbeii_hcl["lat"], errors="coerce")
            owbeii_hcl["hcl"] = pd.to_numeric(owbeii_hcl["hcl"], errors="coerce")
            owbeii_hcl = owbeii_hcl.dropna()
        except:
            pass
    if WASTEBURNED_FILE.exists():
        try:
            owbeii_wb = pd.read_csv(WASTEBURNED_FILE, sep="\s+", names=["lon", "lat", "waste"], comment="#")
            owbeii_wb["lon"] = pd.to_numeric(owbeii_wb["lon"], errors="coerce")
            owbeii_wb["lat"] = pd.to_numeric(owbeii_wb["lat"], errors="coerce")
            owbeii_wb["waste"] = pd.to_numeric(owbeii_wb["waste"], errors="coerce")
            owbeii_wb = owbeii_wb.dropna()
        except:
            pass

    # Assign OWBEII priors to stations
    station_owbeii = {}
    for st, (lat, lon) in STATIONS.items():
        hcl_val = 0
        wb_val = 0
        if not owbeii_hcl.empty:
            dists = haversine_vectorized(lat, lon, owbeii_hcl["lat"].values, owbeii_hcl["lon"].values)
            hcl_val = owbeii_hcl.iloc[np.argmin(dists)]["hcl"]
        if not owbeii_wb.empty:
            dists = haversine_vectorized(lat, lon, owbeii_wb["lat"].values, owbeii_wb["lon"].values)
            wb_val = owbeii_wb.iloc[np.argmin(dists)]["waste"]
        station_owbeii[st] = {"hcl_prior": hcl_val, "wb_prior": wb_val}

    df["hcl_prior"] = df["active_station"].map(lambda x: station_owbeii.get(x, {}).get("hcl_prior", 0))
    df["wb_prior"] = df["active_station"].map(lambda x: station_owbeii.get(x, {}).get("wb_prior", 0))

    print("Mapping FIRMS to observations...")
    # To optimize, we will only map a subset of non-extreme to balance, or just do vectorization
    # We will compute for all extreme events, and a random sample of 2000 non-extreme events to save time
    ext_df = df[df["is_extreme"]].copy()
    non_ext_df = df[~df["is_extreme"]].sample(n=min(2000, (~df["is_extreme"]).sum()), random_state=42).copy()

    eval_df = pd.concat([ext_df, non_ext_df])

    # Calculate FIRMS metrics for each row
    def get_firms_metrics(row):
        t = row["Timestamp"]
        lat = row["lat"]
        lon = row["lon"]

        # Causal constraint: fire must be BEFORE the observation time
        # We look at fires in the past 72 hours
        past_72h = t - pd.Timedelta(hours=72)
        valid_fires = firms_df[(firms_df["acq_datetime"] >= past_72h) & (firms_df["acq_datetime"] < t)]

        if valid_fires.empty:
            return pd.Series([0, 0, 0, np.nan])

        dists = haversine_vectorized(lat, lon, valid_fires["latitude"].values, valid_fires["longitude"].values)

        count_10km = np.sum(dists <= 10)
        count_50km = np.sum(dists <= 50)

        # FRP for fires within 50km
        near_fires = valid_fires[dists <= 50]
        avg_frp = near_fires["frp"].mean() if not near_fires.empty else 0

        # min time diff in hours
        min_time_diff = (t - valid_fires.iloc[np.argmin(dists)]["acq_datetime"]).total_seconds() / 3600.0 if len(dists) > 0 else np.nan

        return pd.Series([count_10km, count_50km, avg_frp, min_time_diff])

    eval_df[["fire_count_10km", "fire_count_50km", "avg_frp_50km", "min_time_diff_hrs"]] = eval_df.apply(get_firms_metrics, axis=1)

    eval_df.to_csv(REPORT_DIR / "extreme_event_source_evidence.csv", index=False)

    # Summarize
    summary = eval_df.groupby("is_extreme").agg({
        "PM2.5": ["count", "mean"],
        "fire_count_10km": "mean",
        "fire_count_50km": "mean",
        "avg_frp_50km": "mean",
        "hcl_prior": "mean",
        "wb_prior": "mean"
    }).reset_index()

    summary.columns = ["is_extreme", "obs_count", "avg_pm25", "avg_fire_10km", "avg_fire_50km", "avg_frp_50km", "avg_hcl_prior", "avg_wb_prior"]
    summary.to_csv(REPORT_DIR / "extreme_event_source_evidence_summary.csv", index=False)

    # Write Markdown
    md = []
    md.append("# Extreme Pollution Event Investigation Audit")
    md.append("This report investigates potential spatial and temporal source alignments for extreme pollution events (PM2.5 >= 250 µg/m³) in the test period.")
    md.append("Note: The metrics represent contextual priors and temporal alignments. They do not claim causality.")
    md.append("")
    md.append("## 1. FIRMS Active Fire Evidence")
    md.append("We investigated FIRMS detections within 72 hours prior to the observation, filtering for spatial proximity (10km and 50km).")
    md.append("")

    ext_fire_50 = summary[summary["is_extreme"] == True]["avg_fire_50km"].values[0]
    non_ext_fire_50 = summary[summary["is_extreme"] == False]["avg_fire_50km"].values[0]

    md.append(f"- **Extreme Events (>=250)**: Averaged {ext_fire_50:.1f} prior fire detections within 50km.")
    md.append(f"- **Non-Extreme Events (<250)**: Averaged {non_ext_fire_50:.1f} prior fire detections within 50km.")
    md.append("")

    md.append("## 2. OWBEII Waste Burning Evidence")
    md.append("OWBEII (Open Waste Burning Emissions Inventory for India) grids were mapped to station locations as static contextual priors (2015 base year).")

    ext_wb = summary[summary["is_extreme"] == True]["avg_wb_prior"].values[0]
    non_ext_wb = summary[summary["is_extreme"] == False]["avg_wb_prior"].values[0]

    md.append(f"- **Extreme Events (>=250)**: Occurred at stations with an average Wasteburned static prior of {ext_wb:.4f}.")
    md.append(f"- **Non-Extreme Events (<250)**: Occurred at stations with an average Wasteburned static prior of {non_ext_wb:.4f}.")
    md.append("")

    md.append("## 3. Final Investigation Decision")

    # Logic for FIRMS
    if ext_fire_50 > non_ext_fire_50 * 1.5:
        md.append("**FIRMS**: provides useful extreme-event investigation evidence.")
    else:
        md.append("**FIRMS**: provides weak evidence.")

    # Logic for OWBEII
    if ext_wb > non_ext_wb * 1.1:
        md.append("**OWBEII**: provides useful spatial source context.")
    else:
        md.append("**OWBEII**: provides weak context.")

    md.append("")
    md.append("None of these datasets are currently authorized to become XGBoost forecasting features. They remain strictly contextual evidence artifacts.")

    with open(REPORT_DIR / "extreme_event_source_evidence_report.md", "w") as f:
        f.write("\n".join(md))

    print("Audit complete.")

if __name__ == "__main__":
    main()
