import json
import glob
import os
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
BUNDLE_DIR = BASE_DIR / "data/processed/evidence_bundles"
FUSION_DATA = BASE_DIR / "data/processed/fusion/delhi_multisource_fusion_dataset.csv"

def run_audit():
    bundle_files = sorted(glob.glob(str(BUNDLE_DIR / "*.json")))
    print(f"Total bundle files found: {len(bundle_files)}")

    if not bundle_files:
        print("No bundle files found!")
        return

    # Check against fusion dataset columns
    df_fusion_sample = pd.read_csv(FUSION_DATA, nrows=5)
    fusion_cols = set(df_fusion_sample.columns)
    print(f"Total columns in fusion dataset: {len(fusion_cols)}")

    # Audit tracking metrics
    stats = {
        "total_bundles": len(bundle_files),
        "stations": {},
        "severities": {},
        "temporal_inversions": 0,
        "missing_fields": {},
        "null_counts": {},
        "duration_min": float("inf"),
        "duration_max": float("-inf"),
        "duration_sum": 0,
        "peak_pm25_min": float("inf"),
        "peak_pm25_max": float("-inf"),
        "nan_inf_counts": 0,
        "nwp_leakage_detected": 0,
        "firms_empty_or_zero": 0,
        "firms_positive": 0,
        "firms_null": 0,
        "owbeii_null": 0,
        "satellite_null": 0,
        "satellite_present": 0,
        "years": {},
        "schema_keys_mismatch": 0,
    }

    expected_top_keys = {
        "event_id", "station_id", "event", "pollution_dynamics",
        "meteorology", "nwp", "satellite", "fire_activity", "source_context"
    }

    expected_event_keys = {
        "start_time", "end_time", "duration_hours", "severity",
        "peak_pm25", "mean_pm25", "min_pm25", "onset_growth"
    }

    sample_bundles = []

    for idx, fpath in enumerate(bundle_files):
        with open(fpath, "r", encoding="utf-8") as f:
            try:
                b = json.load(f)
            except Exception as e:
                print(f"Error parsing JSON {fpath}: {e}")
                continue

        top_keys = set(b.keys())
        if top_keys != expected_top_keys:
            stats["schema_keys_mismatch"] += 1

        st = b.get("station_id")
        stats["stations"][st] = stats["stations"].get(st, 0) + 1

        ev = b.get("event", {})
        sev = ev.get("severity")
        stats["severities"][sev] = stats["severities"].get(sev, 0) + 1

        # Temporal check
        try:
            start_t = pd.to_datetime(ev.get("start_time"))
            end_t = pd.to_datetime(ev.get("end_time"))
            if end_t < start_t:
                stats["temporal_inversions"] += 1
            yr = start_t.year
            stats["years"][yr] = stats["years"].get(yr, 0) + 1
        except Exception:
            stats["temporal_inversions"] += 1

        dur = ev.get("duration_hours", 0)
        stats["duration_min"] = min(stats["duration_min"], dur)
        stats["duration_max"] = max(stats["duration_max"], dur)
        stats["duration_sum"] += dur

        peak = ev.get("peak_pm25", 0)
        if peak is not None:
            stats["peak_pm25_min"] = min(stats["peak_pm25_min"], peak)
            stats["peak_pm25_max"] = max(stats["peak_pm25_max"], peak)

        # NWP / Target leakage check
        nwp = b.get("nwp", {})
        # Check if nwp forecast matches target_pm25 in fusion dataset
        f6 = nwp.get("forecast_6h")
        f24 = nwp.get("forecast_24h")
        f72 = nwp.get("forecast_72h")
        if f6 is not None or f24 is not None or f72 is not None:
            stats["nwp_leakage_detected"] += 1

        # Satellite
        sat = b.get("satellite", {})
        if sat.get("sentinel5p_no2_latest") is None:
            stats["satellite_null"] += 1
        else:
            stats["satellite_present"] += 1

        # Fire
        fire = b.get("fire_activity", {})
        fc = fire.get("firms_detections_72h_50km")
        if fc is None:
            stats["firms_null"] += 1
        elif fc == 0:
            stats["firms_empty_or_zero"] += 1
        else:
            stats["firms_positive"] += 1

        # OWBEII
        src = b.get("source_context", {})
        if src.get("owbeii_waste_burned") is None:
            stats["owbeii_null"] += 1

        if idx in [0, 1000, 3000, 6000]:
            sample_bundles.append(b)

    print("--- AUDIT SUMMARY ---")
    print(f"Total Bundles: {stats['total_bundles']}")
    print(f"Stations ({len(stats['stations'])}): {stats['stations']}")
    print(f"Severities: {stats['severities']}")
    print(f"Years: {stats['years']}")
    print(f"Temporal Inversions: {stats['temporal_inversions']}")
    print(f"Schema Key Mismatches: {stats['schema_keys_mismatch']}")
    print(f"Duration Range: {stats['duration_min']}h to {stats['duration_max']}h (mean: {stats['duration_sum']/stats['total_bundles']:.2f}h)")
    print(f"Peak PM2.5 Range: {stats['peak_pm25_min']} to {stats['peak_pm25_max']}")
    print(f"Satellite NO2: Present={stats['satellite_present']}, Null={stats['satellite_null']} ({stats['satellite_null']/stats['total_bundles']*100:.1f}% missing)")
    print(f"FIRMS Detections: Positive={stats['firms_positive']}, Zero={stats['firms_empty_or_zero']}, Null={stats['firms_null']}")
    print(f"OWBEII Missing: {stats['owbeii_null']}")
    print(f"Bundles with 'nwp' containing target fields: {stats['nwp_leakage_detected']}")

    return stats, sample_bundles

if __name__ == "__main__":
    run_audit()
