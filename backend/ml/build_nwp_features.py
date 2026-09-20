import pandas as pd
import numpy as np
from pathlib import Path
from tqdm import tqdm

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DATASET = BASE_DIR / "data" / "processed" / "fusion" / "delhi_forecasting_satellite_pm10.csv"
NWP_DIR = BASE_DIR / "data" / "raw" / "nwp"
OUTPUT_DATASET = BASE_DIR / "data" / "processed" / "fusion" / "delhi_forecasting_s5_nwp.csv"

NWP_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "surface_pressure",
    "wind_speed_10m",
    "wind_direction_10m",
    "boundary_layer_height",
]

LATENCY_BUFFER_HOURS = 6
HORIZONS = [6, 24, 72]

def load_nwp_archive():
    print("Loading NWP historical archive...")
    csv_files = list(NWP_DIR.rglob("*.csv"))
    dfs = []
    for f in tqdm(csv_files, desc="Reading NWP CSVs"):
        try:
            df = pd.read_csv(f)
            dfs.append(df)
        except Exception:
            pass
    if not dfs:
        raise ValueError("No NWP data found.")

    nwp_df = pd.concat(dfs, ignore_index=True)
    nwp_df["run_time"] = pd.to_datetime(nwp_df["run_time"], format="mixed", utc=True).dt.tz_localize(None)
    nwp_df["valid_time"] = pd.to_datetime(nwp_df["valid_time"], format="mixed", utc=True).dt.tz_localize(None)

    # Drop rows where NWP data is entirely missing (using temperature_2m as proxy)
    # This automatically handles the fallback logic when we use merge_asof
    nwp_df = nwp_df.dropna(subset=["temperature_2m"]).copy()

    # Sort for merge_asof
    nwp_df = nwp_df.sort_values(by="run_time")
    return nwp_df

def build_nwp_dataset():
    print(f"Loading base S4 dataset: {INPUT_DATASET}")
    s4_df = pd.read_csv(INPUT_DATASET)
    s4_df["timestamp"] = pd.to_datetime(s4_df["timestamp"])

    nwp_df = load_nwp_archive()

    print("Applying causal NWP alignment using vectorized merge_asof...")

    # We will build the NWP features for each horizon and join them back
    s5_df = s4_df.copy()

    for horizon in HORIZONS:
        print(f"  Processing {horizon}h horizon...")

        # Create a unique lookup frame
        lookup_df = s4_df[["timestamp"]].drop_duplicates().copy()
        lookup_df["max_allowed_run_time"] = lookup_df["timestamp"] - pd.Timedelta(hours=LATENCY_BUFFER_HOURS)
        lookup_df["target_valid_time"] = lookup_df["timestamp"] + pd.Timedelta(hours=horizon)

        # Sort for merge_asof
        lookup_df = lookup_df.sort_values(by="max_allowed_run_time")

        # Perform exact match on valid_time, and backward nearest match on run_time
        merged = pd.merge_asof(
            left=lookup_df,
            right=nwp_df[["run_time", "valid_time"] + NWP_VARIABLES],
            left_on="max_allowed_run_time",
            right_on="run_time",
            left_by="target_valid_time",
            right_by="valid_time",
            direction="backward"
        )

        # Count missing
        missing_count = merged["temperature_2m"].isna().sum()
        print(f"    Missing NWP data: {missing_count}/{len(merged)} rows")

        # Rename columns
        rename_dict = {v: f"nwp_{v}_{horizon}h" for v in NWP_VARIABLES}
        merged = merged.rename(columns=rename_dict)

        # Drop join keys from merged to avoid duplicates
        cols_to_keep = ["timestamp"] + list(rename_dict.values())
        merged = merged[cols_to_keep]

        # Merge back to s5_df
        # Since we sorted lookup_df, we must merge on timestamp to align properly
        s5_df = s5_df.merge(merged, on="timestamp", how="left")

    s5_df.to_csv(OUTPUT_DATASET, index=False)
    print(f"\nSaved S5 dataset to {OUTPUT_DATASET}")

if __name__ == "__main__":
    build_nwp_dataset()
