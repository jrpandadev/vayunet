from pathlib import Path
import pandas as pd

# ============================================================
# Configuration
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent

# Base features (CPCB and weather)
BASE_FILE = BASE_DIR / "data" / "processed" / "delhi_forecasting.csv"
EPISODE_FILE = BASE_DIR / "data" / "processed" / "fusion" / "delhi_forecasting_episode.csv"
SATELLITE_FILE = BASE_DIR / "data" / "processed" / "fusion" / "delhi_forecasting_satellite.csv"
NWP_FILE = BASE_DIR / "data" / "processed" / "fusion" / "delhi_forecasting_s5_nwp.csv"

OUTPUT_FILE = BASE_DIR / "data" / "processed" / "fusion" / "delhi_multisource_fusion_dataset.csv"

def load_and_merge():
    print("=" * 70)
    print("BUILDING MULTI-SOURCE FUSION DATASET")
    print("=" * 70)

    # 1. Base CPCB Data
    print("\nLoading Base CPCB and Weather Dataset...")
    if not BASE_FILE.exists():
        raise FileNotFoundError(f"Base file missing: {BASE_FILE}")
    base_df = pd.read_csv(BASE_FILE)
    base_df["Timestamp"] = pd.to_datetime(base_df["Timestamp"], errors="coerce")
    base_rows = len(base_df)
    print(f"Base rows: {base_rows:,}")

    # Create the unified df
    unified_df = base_df.copy()
    unified_df = unified_df.rename(columns={"Timestamp": "timestamp"})

    # 2. Episode Dynamics
    print("\nLoading Episode Dynamics Dataset...")
    if EPISODE_FILE.exists():
        episode_df = pd.read_csv(EPISODE_FILE)
        episode_df["timestamp"] = pd.to_datetime(episode_df["timestamp"], errors="coerce")
        # Find new columns from episode_df that are not in unified_df (except join keys)
        join_keys = ["station_id", "timestamp"]
        episode_cols = [c for c in episode_df.columns if c not in unified_df.columns]
        print(f"Merging {len(episode_cols)} episode features...")
        unified_df = unified_df.merge(episode_df[join_keys + episode_cols], on=join_keys, how="left")
    else:
        print("WARNING: Episode Dynamics file not found.")

    # 3. Satellite (S5P NO2)
    print("\nLoading Sentinel-5P NO2 Dataset...")
    if SATELLITE_FILE.exists():
        sat_df = pd.read_csv(SATELLITE_FILE)
        # Satellite file might use 'Timestamp' or 'timestamp'
        time_col = "Timestamp" if "Timestamp" in sat_df.columns else "timestamp"
        sat_df["timestamp"] = pd.to_datetime(sat_df[time_col], errors="coerce")
        join_keys = ["station_id", "timestamp"]
        sat_cols = [c for c in sat_df.columns if c not in unified_df.columns and c != time_col]
        print(f"Merging {len(sat_cols)} satellite features...")
        unified_df = unified_df.merge(sat_df[join_keys + sat_cols], on=join_keys, how="left")
    else:
        print("WARNING: Satellite NO2 file not found.")

    # 4. NWP (ECMWF S5)
    print("\nLoading ECMWF NWP Dataset...")
    if NWP_FILE.exists():
        nwp_df = pd.read_csv(NWP_FILE)
        time_col = "Timestamp" if "Timestamp" in nwp_df.columns else "timestamp"
        nwp_df["timestamp"] = pd.to_datetime(nwp_df[time_col], errors="coerce")
        join_keys = ["station_id", "timestamp"]
        nwp_cols = [c for c in nwp_df.columns if c not in unified_df.columns and c != time_col]
        print(f"Merging {len(nwp_cols)} NWP features...")
        unified_df = unified_df.merge(nwp_df[join_keys + nwp_cols], on=join_keys, how="left")
    else:
        print("WARNING: ECMWF NWP file not found.")

    # 5. Assertions and Validation
    print("\nRunning causal validation assertions...")
    if len(unified_df) != base_rows:
        raise RuntimeError(f"Row count mismatch! Expected {base_rows}, got {len(unified_df)}.")

    # Check that base target columns are uncorrupted
    original_target_sum = base_df["PM2.5"].sum()
    new_target_sum = unified_df["PM2.5"].sum()
    if pd.isna(original_target_sum) and pd.isna(new_target_sum):
        pass # both all na
    elif abs(original_target_sum - new_target_sum) > 1e-4:
        raise RuntimeError(f"PM2.5 values were modified! Expected sum {original_target_sum}, got {new_target_sum}")

    duplicates = unified_df.duplicated(subset=["station_id", "timestamp"]).sum()
    if duplicates > 0:
        raise RuntimeError(f"Found {duplicates} duplicate rows based on station_id and timestamp.")

    print("All validation checks passed.")
    print(f"Total features collected: {len(unified_df.columns)}")

    # Rename timestamp back to Timestamp to match legacy base dataframe if needed
    unified_df = unified_df.rename(columns={"timestamp": "Timestamp"})

    # Export
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    unified_df.to_csv(OUTPUT_FILE, index=False)
    print(f"\nUnified Multi-Source Fusion Dataset saved to: {OUTPUT_FILE}")
    print("=" * 70)

if __name__ == "__main__":
    load_and_merge()
