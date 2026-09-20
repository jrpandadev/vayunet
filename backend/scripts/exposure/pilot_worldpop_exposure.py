"""VayuNet — WorldPop Population Exposure Pilot Extraction

Extracts population exposure context for ONE verified NCR monitoring station
using the WorldPop SDI REST API (wpgppop dataset, 2020) and a 5 km geodesic buffer.
"""

import os
import sys
import math
import json
import time
import urllib.parse
from datetime import datetime, timezone
import requests
import pandas as pd


def geodesic_endpoint_wgs84(lat1: float, lon1: float, azimuth_deg: float, distance_m: float):
    """
    Computes direct geodesic endpoint on WGS-84 reference ellipsoid
    given starting coordinate, forward azimuth, and distance in meters.
    Formula: Vincenty direct method.
    """
    a = 6378137.0  # WGS-84 semi-major axis (meters)
    f = 1.0 / 298.257223563  # WGS-84 flattening
    b = (1.0 - f) * a

    alpha1 = math.radians(azimuth_deg)
    sin_alpha1 = math.sin(alpha1)
    cos_alpha1 = math.cos(alpha1)

    tan_u1 = (1.0 - f) * math.tan(math.radians(lat1))
    cos_u1 = 1.0 / math.sqrt(1.0 + tan_u1**2)
    sin_u1 = tan_u1 * cos_u1

    sigma1 = math.atan2(tan_u1, cos_alpha1)
    sin_alpha = cos_u1 * sin_alpha1
    cos2_alpha = 1.0 - sin_alpha**2

    u_sq = cos2_alpha * (a**2 - b**2) / (b**2)
    A = 1.0 + u_sq / 16384.0 * (4096.0 + u_sq * (-768.0 + u_sq * (320.0 - 175.0 * u_sq)))
    B = u_sq / 1024.0 * (256.0 + u_sq * (-128.0 + u_sq * (74.0 - 47.0 * u_sq)))

    sigma = distance_m / (b * A)
    for _ in range(100):
        cos_2sigma_m = math.cos(2.0 * sigma1 + sigma)
        sin_sigma = math.sin(sigma)
        cos_sigma = math.cos(sigma)
        delta_sigma = B * sin_sigma * (
            cos_2sigma_m
            + B / 4.0 * (
                cos_sigma * (-1.0 + 2.0 * cos_2sigma_m**2)
                - B / 6.0 * cos_2sigma_m * (-3.0 + 4.0 * sin_sigma**2) * (-3.0 + 4.0 * cos_2sigma_m**2)
            )
        )
        sigma_prev = sigma
        sigma = distance_m / (b * A) + delta_sigma
        if abs(sigma - sigma_prev) < 1e-12:
            break

    tmp = sin_u1 * sin_sigma - cos_u1 * cos_sigma * cos_alpha1
    lat2 = math.atan2(
        sin_u1 * cos_sigma + cos_u1 * sin_sigma * cos_alpha1,
        (1.0 - f) * math.sqrt(sin_alpha**2 + tmp**2)
    )
    lam = math.atan2(
        sin_sigma * sin_alpha1,
        cos_u1 * cos_sigma - sin_u1 * sin_sigma * cos_alpha1
    )
    C = f / 16.0 * cos2_alpha * (4.0 + f * (4.0 - 3.0 * cos2_alpha))
    L = lam - (1.0 - C) * f * sin_alpha * (
        sigma + C * sin_sigma * (cos_2sigma_m + C * cos_sigma * (-1.0 + 2.0 * cos_2sigma_m**2))
    )

    lon2 = math.radians(lon1) + L
    return math.degrees(lat2), math.degrees(lon2)


def generate_geodesic_buffer_geojson(lat: float, lon: float, radius_km: float = 5.0, num_vertices: int = 64):
    """
    Generates a GeoJSON FeatureCollection polygon representing a geodesic circle
    of radius_km on the WGS-84 ellipsoid around (lat, lon).
    Coordinates are in [longitude, latitude] per RFC 7946 GeoJSON specification.
    """
    radius_m = radius_km * 1000.0
    ring = []
    for i in range(num_vertices):
        azimuth = (360.0 / num_vertices) * i
        pt_lat, pt_lon = geodesic_endpoint_wgs84(lat, lon, azimuth, radius_m)
        ring.append([round(pt_lon, 6), round(pt_lat, 6)])

    # Close linear ring
    ring.append(ring[0])

    geojson_feature_collection = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [ring]
                }
            }
        ]
    }
    return geojson_feature_collection, ring


def point_in_polygon(x: float, y: float, poly: list) -> bool:
    """
    Ray-casting algorithm to test if point (x=lon, y=lat) is inside polygon ring.
    poly: list of [x, y] coordinates.
    """
    inside = False
    n = len(poly)
    p1x, p1y = poly[0]
    for i in range(n + 1):
        p2x, p2y = poly[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def run_worldpop_pilot():
    metadata_path = "backend/data/processed/delhi_ncr/ncr_station_metadata.csv"
    if not os.path.exists(metadata_path):
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")

    df_meta = pd.read_csv(metadata_path)

    # Target station: CPCB_1430 (Rohini, Delhi) with verified official coordinates
    target_id = "CPCB_1430"
    station_row = df_meta[df_meta["station_id"] == target_id]
    if station_row.empty:
        raise ValueError(f"Station {target_id} not found in metadata")

    station = station_row.iloc[0]
    station_id = station["station_id"]
    station_name = station["station_name"]
    lat = float(station["latitude"])
    lon = float(station["longitude"])
    radius_km = 5.0
    dataset = "wpgppop"
    year = 2020
    dataset_version = "WorldPop 100m Unconstrained Global per country 2000-2020"

    print(f"--- Pilot Station Selected ---")
    print(f"Station ID:   {station_id}")
    print(f"Station Name: {station_name}")
    print(f"Latitude:     {lat:.6f}")
    print(f"Longitude:    {lon:.6f}")
    print(f"Buffer:       {radius_km} km (Geodesic on WGS-84 Ellipsoid)")

    # 1. Generate buffer
    geojson_obj, ring = generate_geodesic_buffer_geojson(lat, lon, radius_km=radius_km, num_vertices=64)

    # 2. Validate geometry
    is_inside = point_in_polygon(lon, lat, ring)
    assert is_inside, f"Validation failure: Center station ({lon}, {lat}) is not inside generated buffer polygon!"
    assert ring[0] == ring[-1], "Validation failure: Buffer polygon linear ring is not closed!"
    print(f"Spatial validation: Station coordinate verified INSIDE polygon. Ring is closed (65 points).")

    # 3. Query WorldPop API
    geojson_json_str = json.dumps(geojson_obj)
    base_api_url = "https://api.worldpop.org/v1/services/stats"
    query_url = f"{base_api_url}?dataset={dataset}&year={year}&geojson={urllib.parse.quote(geojson_json_str)}"

    query_timestamp = datetime.now(timezone.utc).isoformat()
    print(f"Submitting query to WorldPop SDI REST API...")
    resp = requests.get(query_url, timeout=30)

    if resp.status_code != 200:
        raise RuntimeError(f"WorldPop API submission failed with HTTP {resp.status_code}: {resp.text}")

    submit_json = resp.json()
    task_id = submit_json.get("taskid")
    if not task_id:
        raise RuntimeError(f"No taskid returned in response: {submit_json}")

    print(f"Task created successfully. Task ID: {task_id}")

    # 4. Poll task endpoint
    task_url = f"https://api.worldpop.org/v1/tasks/{task_id}"
    print(f"Polling task status at {task_url}...")

    final_data = None
    for attempt in range(20):
        time.sleep(2)
        task_resp = requests.get(task_url, timeout=15)
        if task_resp.status_code != 200:
            print(f"Warning: Poll attempt {attempt+1} HTTP {task_resp.status_code}")
            continue

        tjson = task_resp.json()
        status = tjson.get("status")
        print(f"Poll attempt {attempt+1}: status = {status}")
        if status == "finished":
            final_data = tjson
            break
        elif status == "failed" or tjson.get("error"):
            raise RuntimeError(f"WorldPop task failed: {tjson}")

    if not final_data:
        raise TimeoutError("WorldPop task polling timed out after 40 seconds.")

    # 5. Extract results & validation checks
    raw_data = final_data.get("data", {})
    population_total = raw_data.get("total_population")

    print(f"\n--- Phase 5 Validation Checks ---")
    print(f"1. API response status:  {final_data.get('status')} (status_code: {final_data.get('status_code')})")
    assert final_data.get("status") == "finished", "Task status is not 'finished'"
    assert final_data.get("status_code") == 200, "Task status code is not 200"

    print(f"2. Population value:     {population_total}")
    assert population_total is not None, "Population total is None"
    assert isinstance(population_total, (int, float)), "Population total is not numeric"

    print(f"3. Non-negative check:   Passed ({population_total} >= 0)")
    assert population_total >= 0, "Population total is negative"

    print(f"4. Non-NaN check:        Passed (not math.isnan)")
    assert not math.isnan(population_total), "Population total is NaN"

    buffer_area_km2 = math.pi * (radius_km ** 2)
    pop_density = population_total / buffer_area_km2
    print(f"5. Buffer area:          {buffer_area_km2:.2f} km^2")
    print(f"6. Implied pop density:  {pop_density:.1f} persons/km^2")

    # Plausibility: Rohini / North West Delhi residential density typically 10,000 - 35,000 / km^2
    assert 5000 <= pop_density <= 60000, f"Implied population density {pop_density} is outside plausible urban range (5,000-60,000)"
    print(f"7. Reasonable magnitude: Passed ({pop_density:.1f} persons/km^2 matches Delhi NCT urban profile)")

    # 6. Save results
    output_record = {
        "station_id": station_id,
        "station_name": station_name,
        "latitude": lat,
        "longitude": lon,
        "population_dataset": dataset,
        "population_year": year,
        "population_version": dataset_version,
        "buffer_radius_km": radius_km,
        "buffer_area_km2": round(buffer_area_km2, 4),
        "population_total": round(population_total, 2),
        "population_density_per_km2": round(pop_density, 2),
        "query_timestamp": query_timestamp,
        "api_endpoint": base_api_url,
        "task_id": task_id,
        "task_url": task_url,
        "execution_time_sec": final_data.get("executionTime"),
        "verification_status": "VERIFIED_VALID"
    }

    out_csv = "backend/data/processed/exposure/worldpop_pilot_station.csv"
    pd.DataFrame([output_record]).to_csv(out_csv, index=False)
    print(f"\nSaved pilot record to: {out_csv}")

    out_json = "backend/data/processed/exposure/worldpop_pilot_response.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "request": {
                "dataset": dataset,
                "year": year,
                "station_id": station_id,
                "station_name": station_name,
                "coordinates": [lon, lat],
                "buffer_radius_km": radius_km,
                "num_vertices": 64,
                "query_timestamp": query_timestamp
            },
            "submission_response": submit_json,
            "task_response": final_data
        }, f, indent=2)
    print(f"Saved full API audit logs to: {out_json}")

    return output_record


if __name__ == "__main__":
    res = run_worldpop_pilot()
    print("\nPilot successfully finished. Strict STOP condition honored.")
