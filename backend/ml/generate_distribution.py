import os
import json

def generate_distribution():
    pilot_dir = "backend/reports/investigation/gemini_50_pilot"
    manifest_path = os.path.join(pilot_dir, "sample_manifest.json")
    bundle_dir = "backend/data/processed/evidence_bundles"

    with open(manifest_path, "r") as f:
        manifest = json.load(f)

    bundle_ids = manifest.get("bundle_ids", [])

    distribution = {
        "total_sample_size": len(bundle_ids),
        "station_distribution": {},
        "firms_present": 0,
        "nwp_present": 0,
        "s5p_present": 0,
        "duration_distribution": {
            "<= 24h": 0,
            "> 24h": 0
        },
        "pollution_magnitude": {
            "moderate (PM2.5 < 100)": 0,
            "severe (PM2.5 >= 100)": 0
        }
    }

    for bid in bundle_ids:
        bundle_path = os.path.join(bundle_dir, f"{bid}.json")
        with open(bundle_path, "r") as f:
            data = json.load(f)

        # Station
        station = data.get("station_id", "unknown")
        distribution["station_distribution"][station] = distribution["station_distribution"].get(station, 0) + 1

        # FIRMS
        fire_act = data.get("fire_activity", {})
        if fire_act and isinstance(fire_act, dict) and any(v for v in fire_act.values() if isinstance(v, (int, float)) and v > 0):
            distribution["firms_present"] += 1

        # NWP
        nwp = data.get("nwp", {})
        if nwp.get("forecast_6h") or nwp.get("forecast_24h") or nwp.get("forecast_72h"):
            distribution["nwp_present"] += 1

        # Sentinel-5P
        sat = data.get("satellite", {})
        if sat.get("sentinel5p_no2_latest"):
            distribution["s5p_present"] += 1

        # Duration
        duration = data.get("event", {}).get("duration_hours", 0)
        if duration <= 24:
            distribution["duration_distribution"]["<= 24h"] += 1
        else:
            distribution["duration_distribution"]["> 24h"] += 1

        # Pollution Magnitude
        peak = data.get("event", {}).get("peak_pm25", 0)
        if peak < 100:
            distribution["pollution_magnitude"]["moderate (PM2.5 < 100)"] += 1
        else:
            distribution["pollution_magnitude"]["severe (PM2.5 >= 100)"] += 1

    out_path = os.path.join(pilot_dir, "sample_distribution_audit.json")
    with open(out_path, "w") as f:
        json.dump(distribution, f, indent=2)

    print(f"Saved distribution to {out_path}")

if __name__ == '__main__':
    generate_distribution()
