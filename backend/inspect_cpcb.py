"""
Script to download and inspect a sample CPCB air quality dataset from data.gov.in / public repo
and print column names, date range, and missing-value statistics.
"""

import os
import urllib.request
from pathlib import Path
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_CSV_PATH = DATA_DIR / "sample_cpcb_delhi.csv"

# Reliable CPCB open-data daily/hourly air quality sample mirror
CPCB_SAMPLE_URL = "https://raw.githubusercontent.com/datasets/air-quality-india/master/data/city_day.csv"

def download_and_inspect():
    print("=" * 60)
    print("VayuNet Data Ingestion: CPCB Sample Air Quality Inspector")
    print("=" * 60)
    
    if not SAMPLE_CSV_PATH.exists():
        print(f"[INFO] Downloading sample CPCB dataset to {SAMPLE_CSV_PATH}...")
        try:
            urllib.request.urlretrieve(CPCB_SAMPLE_URL, SAMPLE_CSV_PATH)
            print("[SUCCESS] Download complete!")
        except Exception as e:
            print(f"[ERROR] Failed to download from {CPCB_SAMPLE_URL}: {e}")
            print("[INFO] Generating synthetic standard CPCB structure for Delhi Anand Vihar as fallback...")
            generate_fallback_cpcb_csv(SAMPLE_CSV_PATH)
    else:
        print(f"[INFO] Using existing file at {SAMPLE_CSV_PATH}")

    # Inspect the dataset
    print("\n[INFO] Loading and inspecting dataset...")
    df = pd.read_csv(SAMPLE_CSV_PATH)
    
    print("\n--- 1. DATASET SHAPE & COLUMNS ---")
    print(f"Total Rows: {len(df)}")
    print(f"Total Columns: {len(df.columns)}")
    print("Columns:")
    for col in df.columns:
        print(f" - {col} ({df[col].dtype})")
        
    print("\n--- 2. DATE RANGE ---")
    date_cols = [c for c in df.columns if "date" in c.lower() or "time" in c.lower()]
    if date_cols:
        d_col = date_cols[0]
        df[d_col] = pd.to_datetime(df[d_col], errors="coerce")
        min_date = df[d_col].min()
        max_date = df[d_col].max()
        print(f"Date column identified: '{d_col}'")
        print(f"Start Date: {min_date}")
        print(f"End Date:   {max_date}")
    else:
        print("No explicit date column identified.")
        
    print("\n--- 3. MISSING VALUE SUMMARY ---")
    missing = df.isnull().sum()
    missing_pct = (missing / len(df)) * 100
    missing_summary = pd.DataFrame({"Missing Values": missing, "Percentage (%)": missing_pct.round(2)})
    print(missing_summary[missing_summary["Missing Values"] > 0])
    
    print("\n--- 4. SAMPLE ROWS (HEAD) ---")
    print(df.head(3))
    print("=" * 60)


def generate_fallback_cpcb_csv(filepath: Path):
    dates = pd.date_range(start="2025-01-01", periods=100, freq="D")
    data = {
        "City": ["Delhi"] * 100,
        "Station": ["DPCC_AnandVihar"] * 100,
        "Date": dates,
        "PM2.5": [180.5 + (i % 25) - (i % 10) for i in range(100)],
        "PM10": [245.0 + (i % 30) for i in range(100)],
        "NO2": [42.1 + (i % 15) for i in range(100)],
        "CO": [1.8 + (i % 3) * 0.2 for i in range(100)],
        "AQI": [310 + (i % 40) for i in range(100)],
        "AQI_Bucket": ["Very Poor"] * 100
    }
    pd.DataFrame(data).to_csv(filepath, index=False)


if __name__ == "__main__":
    download_and_inspect()
