import os
import json
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

EVENTS_FILE = BASE_DIR / "data/processed/events/pollution_events.csv"
FUSION_DATA = BASE_DIR / "data/processed/fusion/delhi_multisource_fusion_dataset.csv"
FIRMS_FILES = [
    BASE_DIR / "data/raw/DL_FIRE_J1V-C2_803251/fire_archive_J1V-C2_803251.csv",
    BASE_DIR / "data/raw/DL_FIRE_J2V-C2_803252/fire_archive_J2V-C2_803252.csv",
    BASE_DIR / "data/raw/DL_FIRE_SV-C2_803253/fire_archive_SV-C2_803253.csv"
]
WASTEBURNED_FILE = BASE_DIR / "data/raw/Wasteburned.txt"

OUTPUT_DIR = BASE_DIR / "data/processed/evidence_bundles"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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

def haversine_vectorized(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c

def extract_station(row):
    for st in STATIONS.keys():
        col = f"station_id_{st}"
        if col in row and row[col] == 1:
            return st
    return "unknown"

def safe_mean(series):
    v = series.mean()
    return float(v) if pd.notna(v) else None

def safe_max(series):
    v = series.max()
    return float(v) if pd.notna(v) else None

def safe_val(val):
    return float(val) if pd.notna(val) else None

def main():
    print("Loading datasets...")
    # Load fusion
    df_fusion = pd.read_csv(FUSION_DATA)
    df_fusion["Timestamp"] = pd.to_datetime(df_fusion["Timestamp"])

    station_cols = [c for c in df_fusion.columns if c.startswith("station_id_")]
    if station_cols:
        df_fusion["station_id"] = df_fusion.apply(extract_station, axis=1)

    # Load FIRMS
    firms_dfs = []
    for f in FIRMS_FILES:
        if f.exists():
            firms_dfs.append(pd.read_csv(f))
    if firms_dfs:
        df_firms = pd.concat(firms_dfs, ignore_index=True)
        # ACQ_DATE and ACQ_TIME
        df_firms['acq_datetime'] = pd.to_datetime(df_firms['acq_date'] + ' ' + df_firms['acq_time'].astype(str).str.zfill(4), format='%Y-%m-%d %H%M')
    else:
        df_firms = pd.DataFrame(columns=['latitude', 'longitude', 'acq_datetime', 'frp'])

    # Load OWBEII (just check if available)
    waste_map = {}
    if WASTEBURNED_FILE.exists():
        df_wb = pd.read_csv(WASTEBURNED_FILE, sep="\t", header=0, names=["lat", "lon", "val"])
        for st, (lat, lon) in STATIONS.items():
            dist = haversine_vectorized(lat, lon, df_wb["lat"].values, df_wb["lon"].values)
            closest_idx = np.argmin(dist)
            waste_map[st] = float(df_wb.iloc[closest_idx]["val"])

    # Load Events
    df_events = pd.read_csv(EVENTS_FILE)
    df_events["start_time"] = pd.to_datetime(df_events["start_time"])
    df_events["end_time"] = pd.to_datetime(df_events["end_time"])

    total = len(df_events)
    print(f"Generating bundles for {total} events...")

    for i, ev in df_events.iterrows():
        ev_id = ev["event_id"]
        st = ev["station_id"]
        t_start = ev["start_time"]
        t_end = ev["end_time"]

        # 1. Fusion slice strictly during the event
        mask = (df_fusion["station_id"] == st) & (df_fusion["Timestamp"] >= t_start) & (df_fusion["Timestamp"] <= t_end)
        sub_df = df_fusion[mask]

        # 2. Onset slice (just the start hour to get forecasts/satellite age at onset)
        onset_mask = (df_fusion["station_id"] == st) & (df_fusion["Timestamp"] == t_start)
        onset_df = df_fusion[onset_mask]

        # 3. FIRMS 72h onset context
        if not df_firms.empty and st in STATIONS:
            s_lat, s_lon = STATIONS[st]
            t_start_minus_72 = t_start - pd.Timedelta(hours=72)
            f_mask = (df_firms['acq_datetime'] >= t_start_minus_72) & (df_firms['acq_datetime'] <= t_start)
            df_firms_time = df_firms[f_mask]

            dists = haversine_vectorized(s_lat, s_lon, df_firms_time['latitude'].values, df_firms_time['longitude'].values)
            fires_50km = np.sum(dists <= 50.0)
        else:
            fires_50km = None

        # Bundle construction
        bundle = {
            "event_id": ev_id,
            "station_id": st,
            "event": {
                "start_time": t_start.strftime("%Y-%m-%d %H:%M:%S"),
                "end_time": t_end.strftime("%Y-%m-%d %H:%M:%S"),
                "duration_hours": int(ev["duration_hours"]) if pd.notna(ev["duration_hours"]) else None,
                "severity": ev["severity"],
                "peak_pm25": safe_val(ev["peak_pm25"]),
                "mean_pm25": safe_val(ev["mean_pm25"]),
                "min_pm25": safe_val(ev["min_pm25"]),
                "onset_growth": safe_val(ev["onset_growth"])
            },
            "pollution_dynamics": {
                "pm25": {"mean": safe_mean(sub_df["PM2.5"]), "max": safe_max(sub_df["PM2.5"])},
                "pm10": {"mean": safe_mean(sub_df["PM10"]) if "PM10" in sub_df else None, "max": safe_max(sub_df["PM10"]) if "PM10" in sub_df else None},
                "no2": {"mean": safe_mean(sub_df["NO2"]) if "NO2" in sub_df else None, "max": safe_max(sub_df["NO2"]) if "NO2" in sub_df else None}
            },
            "meteorology": {
                "temperature": {"mean": safe_mean(sub_df["temperature_2m"])},
                "relative_humidity": {"mean": safe_mean(sub_df["relative_humidity_2m"])},
                "wind_speed": {"mean": safe_mean(sub_df["wind_speed_10m"])},
                "wind_direction": {"mean_sin": safe_mean(sub_df["WD_sin"]), "mean_cos": safe_mean(sub_df["WD_cos"])},
                "pblh": {"mean": safe_mean(sub_df["boundary_layer_height"])}
            },
            "nwp": {
                "forecast_6h": None,
                "forecast_24h": None,
                "forecast_72h": None,
                "provenance": "Missing (NWP forecasts removed due to future ground-truth leakage)"
            },
            "satellite": {
                "sentinel5p_no2_latest": safe_val(onset_df.iloc[0]["satellite_no2_latest"]) if not onset_df.empty and "satellite_no2_latest" in onset_df else None,
                "sentinel5p_no2_age_hours": safe_val(onset_df.iloc[0]["satellite_no2_age_hours"]) if not onset_df.empty and "satellite_no2_age_hours" in onset_df else None
            },
            "fire_activity": {
                "firms_detections_72h_50km": int(fires_50km) if fires_50km is not None else None
            },
            "source_context": {
                "owbeii_waste_burned": waste_map.get(st, None)
            }
        }

        # Save bundle
        out_path = OUTPUT_DIR / f"{ev_id}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(bundle, f, indent=2)

        if (i+1) % 500 == 0:
            print(f"Processed {i+1}/{total} events.")

    print(f"Successfully generated {total} evidence bundles in {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
