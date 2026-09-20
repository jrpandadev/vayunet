#!/usr/bin/env python3
"""
VayuNet — MODIS MCD19A2 V061 MAIAC Station AOD Extractor
Extracts station-level 1km AOD (0.55 um and 0.47 um) from raw HDF4 granules
for the 10 Delhi CAAQMS monitoring stations using exact Sinusoidal projection.
Preserves raw data untouched and outputs a clean intermediate representation.
"""

import math
import os
import re
import datetime
from pathlib import Path
import netCDF4
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent.parent
RAW_MAIAC_DIR = BASE_DIR / "data" / "raw" / "satellite" / "modis_maiac"
STATION_COORDS_FILE = BASE_DIR / "data" / "metadata" / "delhi_station_coordinates.csv"
PROCESSED_DIR = BASE_DIR / "data" / "processed" / "satellite"
OUTPUT_PARQUET = PROCESSED_DIR / "delhi_mcd19a2_maiac_station_aod.parquet"
OUTPUT_CSV = PROCESSED_DIR / "delhi_mcd19a2_maiac_station_aod.csv"

# Sinusoidal Projection Constants (MODIS Sphere)
R = 6371007.181
TILE_WIDTH = 1111950.519667
PIXEL_SIZE = TILE_WIDTH / 1200.0
TILE_H = 24
TILE_V = 6
X_MIN = -20015109.354 + TILE_H * TILE_WIDTH
Y_MAX = 10007554.677 - TILE_V * TILE_WIDTH

def latlon_to_pixel(lat, lon):
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    x = R * lon_rad * math.cos(lat_rad)
    y = R * lat_rad
    col = int((x - X_MIN) / PIXEL_SIZE)
    row = int((Y_MAX - y) / PIXEL_SIZE)
    return row, col

def parse_granule_date(filename):
    match = re.search(r"MCD19A2\.A(\d{4})(\d{3})\.h24v06", filename)
    if not match:
        return None
    year = int(match.group(1))
    doy = int(match.group(2))
    dt = datetime.datetime(year, 1, 1) + datetime.timedelta(days=doy - 1)
    return dt.strftime("%Y-%m-%d")

def extract_station_aod(limit=None):
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    if not STATION_COORDS_FILE.exists():
        raise FileNotFoundError(f"Station coordinates file not found: {STATION_COORDS_FILE}")

    stations_df = pd.read_csv(STATION_COORDS_FILE)
    station_pixels = {}
    for _, row in stations_df.iterrows():
        r, c = latlon_to_pixel(row["latitude"], row["longitude"])
        if 0 <= r < 1200 and 0 <= c < 1200:
            station_pixels[row["station_id"]] = {
                "name": row["station_name"],
                "row": r,
                "col": c,
                "lat": row["latitude"],
                "lon": row["longitude"],
            }

    hdf_files = sorted(list(RAW_MAIAC_DIR.glob("*.hdf")))
    if limit:
        hdf_files = hdf_files[:limit]

    print(f"Total HDF granules to process: {len(hdf_files)}")
    records = []

    for idx, fpath in enumerate(hdf_files):
        date_str = parse_granule_date(fpath.name)
        if not date_str:
            continue

        try:
            ds = netCDF4.Dataset(str(fpath), mode="r")

            # Read Orbit_time_stamp
            orbit_times = []
            if "Orbit_time_stamp" in ds.ncattrs():
                attr = ds.getncattr("Orbit_time_stamp")
                if isinstance(attr, str):
                    orbit_times = [x.strip() for x in attr.split() if x.strip()]

            aod55 = ds.variables.get("Optical_Depth_055")
            aod47 = ds.variables.get("Optical_Depth_047")
            qa = ds.variables.get("AOD_QA")

            if aod55 is None:
                ds.close()
                continue

            scale = getattr(aod55, "scale_factor", 0.001)

            # shape: (Orbits, 1200, 1200)
            aod55_data = aod55[:]
            aod47_data = aod47[:] if aod47 is not None else None
            qa_data = qa[:] if qa is not None else None

            num_orbits = aod55_data.shape[0]

            for orbit_idx in range(num_orbits):
                orbit_time_str = orbit_times[orbit_idx] if orbit_idx < len(orbit_times) else None
                obs_time = None
                if orbit_time_str:
                    try:
                        dt_obj = datetime.datetime.strptime(orbit_time_str[:11], "%Y%j%H%M")
                        obs_time = dt_obj.strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        pass
                if not obs_time:
                    obs_time = date_str + " 12:00:00"

                for sid, sinfo in station_pixels.items():
                    val55 = aod55_data[orbit_idx, sinfo["row"], sinfo["col"]]
                    val47 = aod47_data[orbit_idx, sinfo["row"], sinfo["col"]] if aod47_data is not None else np.nan
                    qa_val = qa_data[orbit_idx, sinfo["row"], sinfo["col"]] if qa_data is not None else np.nan

                    if np.ma.is_masked(val55) or np.isnan(val55) or val55 < -100 or val55 > 6000:
                        aod55_scaled = np.nan
                    else:
                        aod55_scaled = float(val55 * scale)

                    if np.ma.is_masked(val47) or np.isnan(val47) or val47 < -100 or val47 > 6000:
                        aod47_scaled = np.nan
                    else:
                        aod47_scaled = float(val47 * scale)

                    # Extract raw QA value
                    raw_qa = int(qa_val) if not (np.ma.is_masked(qa_val) or np.isnan(qa_val)) else -1

                    # Apply scientific bitwise QA filtering
                    # Bit 0-2 (Cloud Mask): 001 == Clear (1)
                    # Bit 8-11 (QA AOD): 0000 == Best quality (0)
                    is_clear = (raw_qa & 0x07) == 1
                    is_best_qa = ((raw_qa >> 8) & 0x0F) == 0
                    qa_accepted = is_clear and is_best_qa and (raw_qa != -1)

                    records.append({
                        "date": date_str,
                        "observation_time": obs_time,
                        "station_id": sid,
                        "station_name": sinfo["name"],
                        "orbit_index": orbit_idx,
                        "granule_file": fpath.name,
                        "latitude": sinfo["lat"],
                        "longitude": sinfo["lon"],
                        "aod_055": aod55_scaled,
                        "aod_047": aod47_scaled,
                        "aod_qa": raw_qa,
                        "qa_accepted": qa_accepted
                    })
            ds.close()
        except Exception as e:
            # gracefully skip corrupt or locked files
            continue

        if (idx + 1) % 200 == 0 or (idx + 1) == len(hdf_files):
            print(f"Processed {idx + 1}/{len(hdf_files)} granules... Records: {len(records):,}")

    df_out = pd.DataFrame(records)
    print(f"\nExtraction complete: {len(df_out):,} records.")

    # Save parquet and CSV
    df_out.to_parquet(OUTPUT_PARQUET, index=False)
    # Save a summarized daily average per station for easy ML joining, only for accepted QA
    valid_df = df_out[df_out["qa_accepted"]]
    daily_df = valid_df.groupby(["date", "station_id"]).agg(
        aod_055_mean=("aod_055", "mean"),
        aod_047_mean=("aod_047", "mean"),
        valid_soundings=("aod_055", lambda s: s.notna().sum())
    ).reset_index()
    daily_summary_path = PROCESSED_DIR / "delhi_mcd19a2_maiac_daily_station_aod.parquet"
    daily_df.to_parquet(daily_summary_path, index=False)

    print(f"Saved station AOD intermediate table to: {OUTPUT_PARQUET}")
    print(f"Saved daily station summary to: {daily_summary_path}")

if __name__ == "__main__":
    import sys
    limit_arg = int(sys.argv[1]) if len(sys.argv) > 1 else None
    extract_station_aod(limit=limit_arg)
