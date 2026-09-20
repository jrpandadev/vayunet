import socket
orig_getaddrinfo = socket.getaddrinfo
def getaddrinfo_ipv4(host, port, family=0, type=0, proto=0, flags=0):
    return orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = getaddrinfo_ipv4

import urllib.request
import urllib.error
import json
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
RAW_PILOT_DIR = BASE_DIR / "data" / "raw" / "nwp" / "vertical_pilot"
REPORTS_DIR = BASE_DIR / "reports" / "nwp"

RAW_PILOT_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

LAT = 28.6139
LON = 77.2090
VARS = [
    "temperature_925hPa",
    "temperature_850hPa",
    "wind_speed_925hPa",
    "wind_speed_850hPa",
    "wind_direction_925hPa",
    "wind_direction_850hPa",
    "wind_u_component_925hPa",
    "wind_v_component_925hPa",
    "wind_u_component_850hPa",
    "wind_v_component_850hPa",
    "geopotential_height_925hPa",
    "geopotential_height_850hPa"
]
HOURLY_PARAM = ",".join(VARS)

def fetch_url(url):
    req = urllib.request.Request(url, headers={"User-Agent": "VayuNet-NWP-Pilot/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return resp.status, data
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            data = json.loads(body)
        except Exception:
            data = {"error_raw": body}
        return e.code, data
    except Exception as e:
        return 500, {"error": str(e)}

def run_pilot():
    print("=== STARTING PRESSURE-LEVEL NWP ACQUISITION PILOT ===")

    # 1. Target Single-Run on ecmwf_ifs (HRES 9km archive) for 2025-09-01T00:00
    url_ifs9km = (
        f"https://single-runs-api.open-meteo.com/v1/forecast?"
        f"latitude={LAT}&longitude={LON}&models=ecmwf_ifs&run=2025-09-01T00:00&"
        f"hourly={HOURLY_PARAM}&timezone=UTC"
    )
    status_ifs9km, data_ifs9km = fetch_url(url_ifs9km)
    path_ifs9km = RAW_PILOT_DIR / "ecmwf_ifs_9km_single_run_20250901T00_raw.json"
    with open(path_ifs9km, "w", encoding="utf-8") as f:
        json.dump(data_ifs9km, f, indent=2)
    print(f"1. ecmwf_ifs single-run 2025-09-01T00:00: status={status_ifs9km}, saved to {path_ifs9km.name}")

    # 2. Target Single-Run on ecmwf_ifs025 (IFS 0.25°) for 2025-09-01T00:00
    url_ifs025_single = (
        f"https://single-runs-api.open-meteo.com/v1/forecast?"
        f"latitude={LAT}&longitude={LON}&models=ecmwf_ifs025&run=2025-09-01T00:00&"
        f"hourly={HOURLY_PARAM}&timezone=UTC"
    )
    status_ifs025_single, data_ifs025_single = fetch_url(url_ifs025_single)
    path_ifs025_single = RAW_PILOT_DIR / "ecmwf_ifs025_single_run_20250901T00_error.json"
    with open(path_ifs025_single, "w", encoding="utf-8") as f:
        json.dump(data_ifs025_single, f, indent=2)
    print(f"2. ecmwf_ifs025 single-run 2025-09-01T00:00: status={status_ifs025_single}, saved to {path_ifs025_single.name}")

    # 3. Archive API seamless for ecmwf_ifs025 for 2025-09-01 to 2025-09-07
    url_ifs025_archive = (
        f"https://archive-api.open-meteo.com/v1/archive?"
        f"latitude={LAT}&longitude={LON}&models=ecmwf_ifs025&start_date=2025-09-01&end_date=2025-09-07&"
        f"hourly={HOURLY_PARAM}&timezone=UTC"
    )
    status_ifs025_archive, data_ifs025_archive = fetch_url(url_ifs025_archive)
    path_ifs025_archive = RAW_PILOT_DIR / "ecmwf_ifs025_archive_seamless_20250901_20250907_raw.json"
    with open(path_ifs025_archive, "w", encoding="utf-8") as f:
        json.dump(data_ifs025_archive, f, indent=2)
    print(f"3. ecmwf_ifs025 archive seamless 2025-09-01..07: status={status_ifs025_archive}, saved to {path_ifs025_archive.name}")

    # 4. Previous-Runs API error check with run=2025-09-01T00:00
    url_prev_run = (
        f"https://previous-runs-api.open-meteo.com/v1/forecast?"
        f"latitude={LAT}&longitude={LON}&models=ecmwf_ifs025&run=2025-09-01T00:00&"
        f"hourly={HOURLY_PARAM}&timezone=UTC"
    )
    status_prev_run, data_prev_run = fetch_url(url_prev_run)
    path_prev_run = RAW_PILOT_DIR / "ecmwf_ifs025_previous_runs_run_param_error.json"
    with open(path_prev_run, "w", encoding="utf-8") as f:
        json.dump(data_prev_run, f, indent=2)
    print(f"4. previous-runs-api run param check: status={status_prev_run}, saved to {path_prev_run.name}")

    # 5. Earliest / verified single run for ecmwf_ifs025 (e.g. 2026-06-01T00:00) to verify schema & lead time preservation
    url_ifs025_valid_run = (
        f"https://single-runs-api.open-meteo.com/v1/forecast?"
        f"latitude={LAT}&longitude={LON}&models=ecmwf_ifs025&run=2026-06-01T00:00&"
        f"hourly={HOURLY_PARAM}&timezone=UTC"
    )
    status_ifs025_valid, data_ifs025_valid = fetch_url(url_ifs025_valid_run)
    path_ifs025_valid = RAW_PILOT_DIR / "ecmwf_ifs025_single_run_20260601T00_raw.json"
    with open(path_ifs025_valid, "w", encoding="utf-8") as f:
        json.dump(data_ifs025_valid, f, indent=2)
    print(f"5. ecmwf_ifs025 verified single run 2026-06-01T00:00: status={status_ifs025_valid}, saved to {path_ifs025_valid.name}")

    # Now create the CSV pilot audit dataset
    # We will build a unified comparison CSV containing:
    # 1) The requested run (2025-09-01T00:00) as fetched from single-runs-api (ecmwf_ifs)
    # 2) The seamless values from archive-api (ecmwf_ifs025)
    # 3) Mathematical U/V derivation from wind_speed and wind_direction to verify agreement

    rows = []
    # Parse ecmwf_ifs single run (run_time = 2025-09-01 00:00 UTC)
    h_ifs = data_ifs9km.get("hourly", {})
    times_ifs = h_ifs.get("time", [])

    # Parse ecmwf_ifs025 archive seamless
    h_arch = data_ifs025_archive.get("hourly", {})
    times_arch = h_arch.get("time", [])

    for i, t_str in enumerate(times_ifs):
        valid_dt = pd.to_datetime(t_str, utc=True)
        run_dt = pd.to_datetime("2025-09-01 00:00", utc=True)
        lead_h = int((valid_dt - run_dt).total_seconds() / 3600)

        # Values from ecmwf_ifs (HRES 9km)
        ifs_t925 = h_ifs.get("temperature_925hPa", [None]*168)[i]
        ifs_t850 = h_ifs.get("temperature_850hPa", [None]*168)[i]

        # Values from ecmwf_ifs025 (Archive seamless)
        arch_t925 = h_arch.get("temperature_925hPa", [None]*168)[i] if i < len(times_arch) else None
        arch_t850 = h_arch.get("temperature_850hPa", [None]*168)[i] if i < len(times_arch) else None
        arch_ws925 = h_arch.get("wind_speed_925hPa", [None]*168)[i] if i < len(times_arch) else None
        arch_wd925 = h_arch.get("wind_direction_925hPa", [None]*168)[i] if i < len(times_arch) else None
        arch_u925 = h_arch.get("wind_u_component_925hPa", [None]*168)[i] if i < len(times_arch) else None
        arch_v925 = h_arch.get("wind_v_component_925hPa", [None]*168)[i] if i < len(times_arch) else None
        arch_z925 = h_arch.get("geopotential_height_925hPa", [None]*168)[i] if i < len(times_arch) else None

        arch_ws850 = h_arch.get("wind_speed_850hPa", [None]*168)[i] if i < len(times_arch) else None
        arch_wd850 = h_arch.get("wind_direction_850hPa", [None]*168)[i] if i < len(times_arch) else None
        arch_u850 = h_arch.get("wind_u_component_850hPa", [None]*168)[i] if i < len(times_arch) else None
        arch_v850 = h_arch.get("wind_v_component_850hPa", [None]*168)[i] if i < len(times_arch) else None
        arch_z850 = h_arch.get("geopotential_height_850hPa", [None]*168)[i] if i < len(times_arch) else None

        # Derive U and V from speed and direction (meteorological: wind from direction theta)
        # u = -ws * sin(theta_rad), v = -ws * cos(theta_rad)
        derived_u925 = None
        derived_v925 = None
        if arch_ws925 is not None and arch_wd925 is not None:
            rad925 = np.deg2rad(arch_wd925)
            derived_u925 = round(-arch_ws925 * np.sin(rad925), 1)
            derived_v925 = round(-arch_ws925 * np.cos(rad925), 1)

        derived_u850 = None
        derived_v850 = None
        if arch_ws850 is not None and arch_wd850 is not None:
            rad850 = np.deg2rad(arch_wd850)
            derived_u850 = round(-arch_ws850 * np.sin(rad850), 1)
            derived_v850 = round(-arch_ws850 * np.cos(rad850), 1)

        row = {
            "run_time_utc": "2025-09-01T00:00:00Z",
            "valid_time_utc": valid_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "lead_hours": lead_h,
            "ecmwf_ifs_9km_lat": data_ifs9km.get("latitude"),
            "ecmwf_ifs_9km_lon": data_ifs9km.get("longitude"),
            "ecmwf_ifs_9km_t925": ifs_t925,
            "ecmwf_ifs_9km_t850": ifs_t850,
            "ecmwf_ifs025_lat": data_ifs025_archive.get("latitude"),
            "ecmwf_ifs025_lon": data_ifs025_archive.get("longitude"),
            "archive_ecmwf_ifs025_t925_C": arch_t925,
            "archive_ecmwf_ifs025_ws925_kmh": arch_ws925,
            "archive_ecmwf_ifs025_wd925_deg": arch_wd925,
            "archive_ecmwf_ifs025_u925_native_kmh": arch_u925,
            "archive_ecmwf_ifs025_v925_native_kmh": arch_v925,
            "archive_ecmwf_ifs025_u925_derived_kmh": derived_u925,
            "archive_ecmwf_ifs025_v925_derived_kmh": derived_v925,
            "archive_ecmwf_ifs025_z925_m": arch_z925,
            "archive_ecmwf_ifs025_t850_C": arch_t850,
            "archive_ecmwf_ifs025_ws850_kmh": arch_ws850,
            "archive_ecmwf_ifs025_wd850_deg": arch_wd850,
            "archive_ecmwf_ifs025_u850_native_kmh": arch_u850,
            "archive_ecmwf_ifs025_v850_native_kmh": arch_v850,
            "archive_ecmwf_ifs025_u850_derived_kmh": derived_u850,
            "archive_ecmwf_ifs025_v850_derived_kmh": derived_v850,
            "archive_ecmwf_ifs025_z850_m": arch_z850,
            "single_runs_api_preserves_run": False, # for ifs025 on 2025-09-01
            "archive_api_preserves_run": False      # seamless stream only
        }
        rows.append(row)

    df_pilot = pd.DataFrame(rows)
    csv_path = REPORTS_DIR / "vertical_nwp_pilot.csv"
    df_pilot.to_csv(csv_path, index=False)
    print(f"Saved pilot CSV with {len(df_pilot)} rows to {csv_path}")

if __name__ == "__main__":
    run_pilot()
