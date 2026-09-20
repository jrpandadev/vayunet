import os
import json
import time
import io
from pathlib import Path
from datetime import datetime, timedelta

import requests
import pandas as pd
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from dotenv import load_dotenv

# ============================================================
# CONFIG
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "raw"
DATA_DIR.mkdir(parents=True, exist_ok=True)

OUT_FILE = DATA_DIR / "firms_viirs.csv"
PROGRESS_FILE = DATA_DIR / "firms_download_progress.json"

# West,South,East,North
AREA = "74.0,27.0,78.5,32.5"

START_DATE = datetime(2020, 1, 1)
END_DATE = datetime(2026, 8, 31)
CHUNK_DAYS = 5

SNPP_SP_CUTOFF = datetime(2026, 4, 27)
NOAA20_SP_CUTOFF = datetime(2026, 5, 31)
NOAA21_START = datetime(2024, 1, 17)

def get_session():
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

def determine_source(sensor, chunk_start):
    if sensor == "SNPP":
        if chunk_start <= SNPP_SP_CUTOFF:
            return "VIIRS_SNPP_SP"
        return "VIIRS_SNPP_NRT"
    elif sensor == "NOAA20":
        if chunk_start <= NOAA20_SP_CUTOFF:
            return "VIIRS_NOAA20_SP"
        return "VIIRS_NOAA20_NRT"
    elif sensor == "NOAA21":
        if chunk_start < NOAA21_START:
            return None
        return "VIIRS_NOAA21_NRT"
    return None

def load_progress():
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE, "r") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_progress(progress_set):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(list(progress_set), f)

def fetch_chunk(session, map_key, source, start_date_str, day_range):
    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{map_key}/{source}/{AREA}/{day_range}/{start_date_str}"
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return response.text

def process_chunk(csv_text, source):
    if not csv_text.strip():
        return None
    # FIRMS returns CSV. Sometimes it returns a single line of header if no data.
    # We load it with pandas to check if there are rows.
    try:
        df = pd.read_csv(io.StringIO(csv_text))
        if df.empty:
            return None
        # Add provenance
        df["source_product"] = source
        return df
    except pd.errors.EmptyDataError:
        return None

def main():
    load_dotenv(BASE_DIR / ".env")
    map_key = os.getenv("FIRMS_API_KEY")
    if not map_key:
        raise ValueError("FIRMS_API_KEY not found in backend/.env")

    session = get_session()
    progress = load_progress()

    current_date = START_DATE
    sensors = ["SNPP", "NOAA20", "NOAA21"]

    print("=" * 80)
    print("FIRMS VIIRS HISTORICAL DOWNLOADER")
    print("=" * 80)
    print(f"Target Area: {AREA}")
    print(f"Timeframe: {START_DATE.strftime('%Y-%m-%d')} to {END_DATE.strftime('%Y-%m-%d')}")
    print(f"Output File: {OUT_FILE}")
    print(f"Progress File: {PROGRESS_FILE}")
    print("-" * 80)

    total_chunks = 0
    successful_chunks = 0

    while current_date <= END_DATE:
        # Calculate day range for the current chunk (max CHUNK_DAYS, or remaining days to END_DATE)
        delta = (END_DATE - current_date).days + 1
        day_range = min(CHUNK_DAYS, delta)
        start_date_str = current_date.strftime("%Y-%m-%d")

        for sensor in sensors:
            source = determine_source(sensor, current_date)
            if not source:
                continue # Skip NOAA21 before its start date

            chunk_id = f"{source}_{start_date_str}_{day_range}"
            if chunk_id in progress:
                continue

            total_chunks += 1
            print(f"Fetching {chunk_id} ... ", end="")

            try:
                # To be gentle to the API, sleep a little
                time.sleep(1.0)

                csv_text = fetch_chunk(session, map_key, source, start_date_str, day_range)

                # Check for rate limit or authentication text response if status was 200 but content is error message
                # FIRMS sometimes returns plain text error instead of 4xx
                if "Error" in csv_text[:50] or "Invalid" in csv_text[:50]:
                    print(f"API Error: {csv_text.strip()}")
                    continue

                df = process_chunk(csv_text, source)

                if df is not None:
                    # Append to CSV
                    header = not OUT_FILE.exists()
                    df.to_csv(OUT_FILE, mode='a', index=False, header=header)
                    print(f"Saved {len(df)} rows")
                else:
                    print("No fires detected")

                progress.add(chunk_id)
                save_progress(progress)
                successful_chunks += 1

            except Exception as e:
                print(f"FAILED: {e}")
                # Optional: could sleep more here
                time.sleep(5.0)

        current_date += timedelta(days=day_range)

    print("=" * 80)
    print(f"DOWNLOAD COMPLETE. Processed {successful_chunks} new chunks.")
    if OUT_FILE.exists():
        df_final = pd.read_csv(OUT_FILE)
        print(f"Total records in {OUT_FILE.name}: {len(df_final)}")
    print("=" * 80)

if __name__ == "__main__":
    main()
