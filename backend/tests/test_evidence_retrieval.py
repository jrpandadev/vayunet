import io
import math
from datetime import datetime, timezone
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from main import app
from schemas.evidence import DataAvailability
from schemas.report import InternalReport, LocationCoords, PhotoMetadata
from services.geo_utils import haversine_distance, find_nearest_point
from services.evidence_retriever import (
    retrieve_cpcb_evidence,
    retrieve_weather_evidence,
    retrieve_firms_evidence,
    retrieve_owbeii_evidence,
    detect_conflicts,
    build_evidence_package,
)

client = TestClient(app)


def _create_sample_jpeg_bytes() -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (100, 100), color=(180, 80, 50))
    img.save(buf, format="JPEG")
    return buf.getvalue()


# 1. Valid report evidence retrieval via API
def test_valid_report_evidence_retrieval():
    jpeg_bytes = _create_sample_jpeg_bytes()
    # Ingest a report first (Anand Vihar coordinates in Jan 2024 where CPCB & weather data exist)
    files = {"photo": ("evidence_test.jpg", io.BytesIO(jpeg_bytes), "image/jpeg")}
    data = {
        "latitude": 28.6468,
        "longitude": 77.3157,
        "timestamp": "2024-01-15T12:00:00Z",
        "text": "Dense smoke near Anand Vihar ISBT"
    }
    ingest_resp = client.post("/api/v1/reports", data=data, files=files)
    assert ingest_resp.status_code == 200
    report_id = ingest_resp.json()["report_id"]

    # Now retrieve evidence package
    resp = client.post(f"/api/v1/reports/{report_id}/evidence")
    assert resp.status_code == 200, resp.text
    pkg = resp.json()

    assert pkg["report_id"] == report_id
    assert pkg["location"]["latitude"] == 28.6468
    assert pkg["location"]["longitude"] == 77.3157
    assert "cpcb" in pkg
    assert "weather" in pkg
    assert "satellite" in pkg
    assert "firms" in pkg
    assert "static_sources" in pkg
    assert "retrieved_at" in pkg


# 2. Report not found (404)
def test_report_not_found():
    resp = client.post("/api/v1/reports/rep_nonexistent_99999/evidence")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# 3. CPCB evidence retrieval & values
def test_cpcb_evidence_retrieval():
    target_dt = datetime(2024, 1, 15, 12, 0, 0)
    cpcb = retrieve_cpcb_evidence(28.6468, 77.3157, target_dt)
    assert cpcb.status in (DataAvailability.AVAILABLE, DataAvailability.STALE)
    assert cpcb.station_id == "anand vihar"
    assert cpcb.distance_km is not None
    assert cpcb.distance_km <= 1.0  # Anand Vihar station should be ~0km away
    assert cpcb.provenance.startswith("CPCB_CAAQMS_")

    # Check pollutant preservation
    assert "PM2.5" in cpcb.pollutants or "PM10" in cpcb.pollutants
    for p_name, p_obs in cpcb.pollutants.items():
        assert p_obs.value >= 0.0
        assert p_obs.unit in ("µg/m³", "mg/m³")
        assert p_obs.observation_time is not None


# 4. Weather evidence retrieval
def test_weather_evidence_retrieval():
    target_dt = datetime(2024, 1, 15, 12, 0, 0)
    weather = retrieve_weather_evidence(28.6468, 77.3157, target_dt)
    assert weather.status in (DataAvailability.AVAILABLE, DataAvailability.STALE)
    assert weather.temperature_c is not None
    assert -10.0 <= weather.temperature_c <= 55.0
    assert weather.relative_humidity_pct is not None
    assert 0.0 <= weather.relative_humidity_pct <= 100.0
    assert weather.wind_speed_kmh is not None
    assert weather.provenance is not None


# 5. Sentinel-5P evidence retrieval
def test_sentinel5p_evidence_retrieval():
    target_dt = datetime(2024, 1, 15, 12, 0, 0)
    from services.evidence_retriever import retrieve_sentinel5p_evidence
    sat = retrieve_sentinel5p_evidence(28.6468, 77.3157, target_dt)
    assert sat.status in (DataAvailability.AVAILABLE, DataAvailability.STALE)
    assert sat.no2_column_number_density is not None
    assert sat.absorbing_aerosol_index is not None
    assert sat.provenance is not None


# 6. FIRMS evidence retrieval
def test_firms_evidence_retrieval():
    target_dt = datetime(2024, 1, 15, 12, 0, 0)
    firms = retrieve_firms_evidence(28.6468, 77.3157, target_dt, search_radius_km=50.0, window_hours=72.0)
    assert firms.status == DataAvailability.AVAILABLE
    assert firms.detection_count >= 0
    assert firms.search_radius_km == 50.0
    assert firms.temporal_window_hours == 72.0
    assert firms.provenance.startswith("NASA_FIRMS_")
    if firms.detection_count > 0:
        assert firms.nearest_fire_distance_km is not None
        assert firms.nearest_fire_distance_km <= 50.0
        for f in firms.fires:
            assert f.distance_km <= 50.0
            assert f.frp >= 0.0


# 7. Static-source retrieval (OWBEII)
def test_static_source_retrieval():
    owbeii = retrieve_owbeii_evidence(28.6468, 77.3157)
    assert owbeii.status == DataAvailability.AVAILABLE
    assert owbeii.source_type == "OWBEII_open_waste_burning"
    assert owbeii.distance_km is not None
    assert owbeii.distance_km < 25.0  # Grid is 0.1 deg (~10 km)
    assert owbeii.annual_emission_val is not None
    assert owbeii.unit == "kg yr-1"
    assert owbeii.provenance == "OWBEII_Static_Emissions_Inventory"


# 8. Spatial filtering (distance calculation and cutoff)
def test_spatial_filtering():
    # Query coordinates far outside Delhi (e.g. London UK: 51.5074, -0.1278)
    far_dt = datetime(2024, 1, 15, 12, 0, 0)
    cpcb_far = retrieve_cpcb_evidence(51.5074, -0.1278, far_dt, max_distance_km=35.0)
    assert cpcb_far.status == DataAvailability.MISSING
    assert cpcb_far.distance_km is not None
    assert cpcb_far.distance_km > 1000.0  # Thousands of km away


# 9. Temporal filtering (preceding window respected)
def test_temporal_filtering():
    # FIRMS with 12 hour window vs 72 hour window
    target_dt = datetime(2023, 11, 5, 12, 0, 0)  # Peak stubble burning season
    firms_72h = retrieve_firms_evidence(28.6468, 77.3157, target_dt, search_radius_km=100.0, window_hours=72.0)
    firms_12h = retrieve_firms_evidence(28.6468, 77.3157, target_dt, search_radius_km=100.0, window_hours=12.0)
    # 72h window must have >= detection count than 12h window
    assert firms_72h.detection_count >= firms_12h.detection_count


# 10. Future-data rejection (observation_time > report_time strictly rejected)
def test_future_data_rejection():
    # Request historical timestamp in 2021 before Delhi dataset begins (starts 2022)
    past_dt = datetime(2021, 1, 1, 12, 0, 0)
    cpcb = retrieve_cpcb_evidence(28.6468, 77.3157, past_dt)
    # Cannot use future 2022+ observations to validate a 2021 report!
    assert cpcb.status == DataAvailability.MISSING
    assert cpcb.observation_time is None or datetime.fromisoformat(cpcb.observation_time) <= past_dt


# 11. Missing-data handling (no zero-filling or synthetic values)
def test_missing_data_handling():
    # Coordinate with no CPCB station nearby
    cpcb_empty = retrieve_cpcb_evidence(0.0, 0.0, datetime(2024, 1, 1))
    assert cpcb_empty.status == DataAvailability.MISSING
    assert len(cpcb_empty.pollutants) == 0  # Not zero-filled!


# 12. Provenance preservation
def test_provenance_preservation():
    report = InternalReport(
        report_id="rep_test_prov_001",
        location=LocationCoords(latitude=28.6468, longitude=77.3157),
        timestamp="2024-01-15T12:00:00Z",
        photo_metadata=PhotoMetadata(
            filename="sample.jpg",
            content_type="image/jpeg",
            size_bytes=1024,
            format="JPEG",
            width=100,
            height=100
        ),
        status="received"
    )
    pkg = build_evidence_package(report)
    assert pkg.cpcb.provenance is not None and len(pkg.cpcb.provenance) > 0
    assert pkg.weather.provenance is not None and len(pkg.weather.provenance) > 0
    assert pkg.satellite.provenance is not None and len(pkg.satellite.provenance) > 0
    assert pkg.firms.provenance is not None and len(pkg.firms.provenance) > 0
    for src in pkg.static_sources:
        assert src.provenance is not None and len(src.provenance) > 0


# 13. Unit preservation
def test_unit_preservation():
    target_dt = datetime(2024, 1, 15, 12, 0, 0)
    cpcb = retrieve_cpcb_evidence(28.6468, 77.3157, target_dt)
    if "PM2.5" in cpcb.pollutants:
        assert cpcb.pollutants["PM2.5"].unit == "µg/m³"
    if "CO" in cpcb.pollutants:
        assert cpcb.pollutants["CO"].unit == "mg/m³"

    owbeii = retrieve_owbeii_evidence(28.6468, 77.3157)
    assert owbeii.unit == "kg yr-1"


# 14. Distance calculation accuracy (Haversine reference check)
def test_distance_calculation():
    # Distance between New Delhi (28.6139, 77.2090) and Mumbai (19.0760, 72.8777)
    # Reference distance is approximately 1148 - 1152 km
    dist = haversine_distance(28.6139, 77.2090, 19.0760, 72.8777)
    assert 1145.0 <= dist <= 1155.0, f"Unexpected distance: {dist} km"

    # Same point distance should be 0.0
    assert haversine_distance(28.6139, 77.2090, 28.6139, 77.2090) == 0.0


# 15. Conflicting evidence preservation
def test_conflicting_evidence_preservation():
    from schemas.evidence import PollutantObservation, CPCBStationEvidence, WeatherEvidence, FIRMSEvidence, Sentinel5PEvidence
    cpcb_mock = CPCBStationEvidence(
        status=DataAvailability.AVAILABLE,
        pollutants={"PM2.5": PollutantObservation(pollutant="PM2.5", value=350.0, unit="µg/m³", observation_time="2024-01-01T12:00:00")}
    )
    weather_mock = WeatherEvidence(
        status=DataAvailability.AVAILABLE,
        wind_speed_kmh=25.0
    )
    firms_mock = FIRMSEvidence(
        status=DataAvailability.AVAILABLE,
        detection_count=0
    )
    sat_mock = Sentinel5PEvidence(
        status=DataAvailability.AVAILABLE,
        absorbing_aerosol_index=1.0
    )
    conflicts = detect_conflicts(cpcb_mock, weather_mock, firms_mock, sat_mock)
    assert len(conflicts) >= 1
    # Both conflict signals are preserved without smoothing or dropping
    assert any("high wind speed" in c.lower() for c in conflicts)
    assert any("zero active fire" in c.lower() for c in conflicts)


# 16. No fabricated values
def test_no_fabricated_values():
    report = InternalReport(
        report_id="rep_test_integrity_001",
        location=LocationCoords(latitude=28.6468, longitude=77.3157),
        timestamp="2024-01-15T12:00:00Z",
        photo_metadata=PhotoMetadata(
            filename="sample.jpg",
            content_type="image/jpeg",
            size_bytes=1024,
            format="JPEG",
            width=100,
            height=100
        ),
        status="received"
    )
    pkg = build_evidence_package(report)
    pkg_dict = pkg.model_dump()
    forbidden_keys = ["verdict", "confidence_score", "gemini_reasoning", "ai_verdict", "prediction"]
    for k in forbidden_keys:
        assert k not in pkg_dict


# 17. Existing Stage 1 tests still pass
def test_stage_1_regression_check():
    jpeg_bytes = _create_sample_jpeg_bytes()
    files = {"photo": ("reg_test.jpg", io.BytesIO(jpeg_bytes), "image/jpeg")}
    data = {
        "latitude": 28.6139,
        "longitude": 77.2090,
        "timestamp": "2026-09-17T12:00:00Z",
        "text": "Smoke report regression test"
    }
    resp = client.post("/api/v1/reports", data=data, files=files)
    assert resp.status_code == 200
    res = resp.json()
    assert res["status"] == "received"
    assert res["photo_received"] is True
    assert res["text_received"] is True
