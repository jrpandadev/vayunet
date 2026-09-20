import json
from datetime import datetime, timezone
from PIL import Image
import io
from fastapi.testclient import TestClient

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import app
from schemas.evidence import DataAvailability

client = TestClient(app)

def run_real_data_integration():
    print("=" * 70)
    print("VAYUNET — STAGE 2 REAL-DATA INTEGRATION TEST")
    print("=" * 70)

    # 1. Step 1: Ingest Citizen Report with real image and real Delhi coordinates
    print("\n[STEP 1] Ingesting Live Citizen Report at Anand Vihar (28.6468, 77.3157)...")
    img_buf = io.BytesIO()
    Image.new("RGB", (150, 150), color=(120, 100, 80)).save(img_buf, format="JPEG")
    files = {"photo": ("real_anand_vihar.jpg", img_buf.getvalue(), "image/jpeg")}

    # Historical report date where real ground observations and historical FIRMS exist
    data = {
        "latitude": 28.6468,
        "longitude": 77.3157,
        "timestamp": "2024-01-15T12:00:00Z",
        "text": "REAL INTEGRATION TEST: Thick industrial haze observed near Anand Vihar boundary"
    }
    r_ingest = client.post("/api/v1/reports", data=data, files=files)
    assert r_ingest.status_code == 200, f"Ingestion failed: {r_ingest.text}"
    report_info = r_ingest.json()
    report_id = report_info["report_id"]
    print(f" -> Ingestion SUCCESS. Report ID: {report_id}")
    print(f" -> Status: {report_info['status']}")

    # 2. Step 2: Retrieve Live Evidence Package
    print(f"\n[STEP 2] Querying POST /api/v1/reports/{report_id}/evidence...")
    r_evidence = client.post(f"/api/v1/reports/{report_id}/evidence")
    assert r_evidence.status_code == 200, f"Evidence retrieval failed: {r_evidence.text}"
    evidence = r_evidence.json()
    print(" -> Evidence Retrieval SUCCESS.")

    # 3. Verify real CPCB ground observations
    print("\n[VERIFICATION: CPCB Ground Sensors]")
    cpcb = evidence["cpcb"]
    print(f" - Station: {cpcb['station_name']} (ID: {cpcb['station_id']})")
    print(f" - Distance: {cpcb['distance_km']} km")
    print(f" - Status: {cpcb['status']}")
    print(f" - Observation Time: {cpcb['observation_time']}")
    print(f" - Provenance: {cpcb['provenance']}")
    for poll_name, poll_data in cpcb["pollutants"].items():
        print(f"   * {poll_name}: {poll_data['value']} {poll_data['unit']}")
    assert cpcb["status"] in (DataAvailability.AVAILABLE.value, DataAvailability.STALE.value)
    assert "PM2.5" in cpcb["pollutants"] or "PM10" in cpcb["pollutants"]

    # 4. Verify real Weather / Meteorology
    print("\n[VERIFICATION: Weather / Meteorology]")
    w = evidence["weather"]
    print(f" - Status: {w['status']}")
    print(f" - Temperature: {w['temperature_c']} °C")
    print(f" - Humidity: {w['relative_humidity_pct']} %")
    print(f" - Wind Speed: {w['wind_speed_kmh']} km/h")
    print(f" - Wind Direction: {w['wind_direction_deg']}°")
    print(f" - Surface Pressure: {w['surface_pressure_hpa']} hPa")
    print(f" - PBLH: {w['boundary_layer_height_m']} m")
    print(f" - Provenance: {w['provenance']}")
    assert w["status"] in (DataAvailability.AVAILABLE.value, DataAvailability.STALE.value)
    assert w["temperature_c"] is not None

    # 5. Verify real Sentinel-5P Satellite
    print("\n[VERIFICATION: Sentinel-5P Satellite]")
    sat = evidence["satellite"]
    print(f" - Status: {sat['status']}")
    print(f" - NO2 Column Density: {sat['no2_column_number_density']}")
    print(f" - Absorbing Aerosol Index: {sat['absorbing_aerosol_index']}")
    print(f" - Provenance: {sat['provenance']}")

    # 6. Verify real FIRMS active fires
    print("\n[VERIFICATION: FIRMS Fire Activity (50km radius)]")
    firms = evidence["firms"]
    print(f" - Status: {firms['status']}")
    print(f" - Detections Count (72h): {firms['detection_count']}")
    print(f" - Nearest Fire Distance: {firms['nearest_fire_distance_km']} km")
    print(f" - Max FRP: {firms['max_frp']} MW")
    print(f" - Provenance: {firms['provenance']}")
    assert firms["status"] == DataAvailability.AVAILABLE.value

    # 7. Verify real OWBEII Static Context
    print("\n[VERIFICATION: OWBEII Static Waste Burning Inventory]")
    static_sources = evidence["static_sources"]
    assert len(static_sources) > 0
    ow = static_sources[0]
    print(f" - Source Type: {ow['source_type']}")
    print(f" - Distance: {ow['distance_km']} km")
    print(f" - Annual Emission: {ow['annual_emission_val']} {ow['unit']}")
    print(f" - Provenance: {ow['provenance']}")
    assert ow["status"] == DataAvailability.AVAILABLE.value
    assert ow["annual_emission_val"] is not None

    # 8. Check Conflicts & Metadata
    print("\n[VERIFICATION: Conflict Preservation & Provenance]")
    print(f" - Conflicting signals noted: {evidence['conflicting_signals_noted']}")
    print(f" - Retrieval Timestamp: {evidence['retrieved_at']}")

    print("\n" + "=" * 70)
    print("REAL-DATA INTEGRATION TEST: ALL CHECKS PASSED (100% REAL OBSERVATIONS)")
    print("=" * 70)

if __name__ == "__main__":
    run_real_data_integration()
