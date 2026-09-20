import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _create_test_image_bytes(fmt: str = "JPEG", size=(100, 100), color=(200, 50, 50)) -> bytes:
    """Helper to generate valid in-memory image bytes."""
    buf = io.BytesIO()
    mode = "RGBA" if fmt.upper() == "PNG" else "RGB"
    img = Image.new(mode, size, color=color)
    img.save(buf, format=fmt)
    return buf.getvalue()


# 1. Valid report submission
def test_valid_report_submission_with_text():
    jpeg_bytes = _create_test_image_bytes("JPEG")
    files = {
        "photo": ("incident.jpg", io.BytesIO(jpeg_bytes), "image/jpeg")
    }
    data = {
        "latitude": 28.6139,
        "longitude": 77.2090,
        "timestamp": "2026-09-17T12:00:00Z",
        "text": "Thick black industrial smoke visible near Okhla Phase 2"
    }
    response = client.post("/api/v1/reports", data=data, files=files)
    assert response.status_code == 200, response.text
    res = response.json()
    assert res["status"] == "received"
    assert res["location"]["latitude"] == 28.6139
    assert res["location"]["longitude"] == 77.2090
    assert res["timestamp"] == "2026-09-17T12:00:00Z"
    assert res["photo_received"] is True
    assert res["text_received"] is True
    assert res["report_id"].startswith("rep_")


# 2. Missing photo (omitted from multipart form)
def test_missing_photo():
    data = {
        "latitude": 28.6139,
        "longitude": 77.2090,
        "timestamp": "2026-09-17T12:00:00Z",
        "text": "Reporting smoke without photo"
    }
    response = client.post("/api/v1/reports", data=data)
    assert response.status_code == 422


# 3. Invalid image (corrupted / text disguised as photo)
def test_invalid_corrupted_image():
    corrupted_bytes = b"This is not a real image at all, just plain text disguised as jpg."
    files = {
        "photo": ("fake.jpg", io.BytesIO(corrupted_bytes), "image/jpeg")
    }
    data = {
        "latitude": 28.6139,
        "longitude": 77.2090,
        "timestamp": "2026-09-17T12:00:00Z",
    }
    response = client.post("/api/v1/reports", data=data, files=files)
    # Magic bytes check or PIL verify will catch this
    assert response.status_code in (400, 415)


# 4. Unsupported image type (e.g. GIF)
def test_unsupported_image_type():
    gif_bytes = _create_test_image_bytes("GIF")
    files = {
        "photo": ("animation.gif", io.BytesIO(gif_bytes), "image/gif")
    }
    data = {
        "latitude": 28.6139,
        "longitude": 77.2090,
        "timestamp": "2026-09-17T12:00:00Z",
    }
    response = client.post("/api/v1/reports", data=data, files=files)
    assert response.status_code == 415
    assert "Unsupported image format" in response.json()["detail"]


# 5. Oversized image (> 10MB)
def test_oversized_image():
    # 10MB + 1024 bytes of dummy payload starting with JPEG header
    oversized_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * (10 * 1024 * 1024 + 1024)
    files = {
        "photo": ("giant.jpg", io.BytesIO(oversized_bytes), "image/jpeg")
    }
    data = {
        "latitude": 28.6139,
        "longitude": 77.2090,
        "timestamp": "2026-09-17T12:00:00Z",
    }
    response = client.post("/api/v1/reports", data=data, files=files)
    assert response.status_code == 413
    assert "exceeds maximum allowed size" in response.json()["detail"]


# 6. Invalid latitude (out of -90 to 90 range or non-numeric)
@pytest.mark.parametrize("bad_lat", [95.0, -91.5, "not_a_number"])
def test_invalid_latitude(bad_lat):
    jpeg_bytes = _create_test_image_bytes("JPEG")
    files = {
        "photo": ("incident.jpg", io.BytesIO(jpeg_bytes), "image/jpeg")
    }
    data = {
        "latitude": bad_lat,
        "longitude": 77.2090,
        "timestamp": "2026-09-17T12:00:00Z",
    }
    response = client.post("/api/v1/reports", data=data, files=files)
    assert response.status_code == 422


# 7. Invalid longitude (out of -180 to 180 range or non-numeric)
@pytest.mark.parametrize("bad_lng", [185.0, -190.0, "not_a_number"])
def test_invalid_longitude(bad_lng):
    jpeg_bytes = _create_test_image_bytes("JPEG")
    files = {
        "photo": ("incident.jpg", io.BytesIO(jpeg_bytes), "image/jpeg")
    }
    data = {
        "latitude": 28.6139,
        "longitude": bad_lng,
        "timestamp": "2026-09-17T12:00:00Z",
    }
    response = client.post("/api/v1/reports", data=data, files=files)
    assert response.status_code == 422


# 8. Invalid timestamp
@pytest.mark.parametrize("bad_ts", ["not-a-timestamp", "2026-13-45", "", "31/12/2026"])
def test_invalid_timestamp(bad_ts):
    jpeg_bytes = _create_test_image_bytes("JPEG")
    files = {
        "photo": ("incident.jpg", io.BytesIO(jpeg_bytes), "image/jpeg")
    }
    data = {
        "latitude": 28.6139,
        "longitude": 77.2090,
        "timestamp": bad_ts,
    }
    response = client.post("/api/v1/reports", data=data, files=files)
    assert response.status_code == 422


# 9. Optional text handling (text omitted vs present)
def test_optional_text_handling():
    png_bytes = _create_test_image_bytes("PNG")
    files = {
        "photo": ("incident.png", io.BytesIO(png_bytes), "image/png")
    }
    data = {
        "latitude": 28.6139,
        "longitude": 77.2090,
        "timestamp": "2026-09-17T12:00:00+05:30",
        # text field omitted
    }
    response = client.post("/api/v1/reports", data=data, files=files)
    assert response.status_code == 200
    res = response.json()
    assert res["photo_received"] is True
    assert res["text_received"] is False


# 10. Correct JSON response structure
def test_correct_json_response_structure():
    webp_bytes = _create_test_image_bytes("WEBP")
    files = {
        "photo": ("incident.webp", io.BytesIO(webp_bytes), "image/webp")
    }
    data = {
        "latitude": 19.0760,
        "longitude": 72.8777,
        "timestamp": "2026-09-17T06:30:00Z",
        "text": "Haze observation in Mumbai"
    }
    response = client.post("/api/v1/reports", data=data, files=files)
    assert response.status_code == 200
    res = response.json()

    # Exact expected response keys
    expected_keys = {"report_id", "status", "location", "timestamp", "photo_received", "text_received"}
    assert set(res.keys()) == expected_keys
    assert set(res["location"].keys()) == {"latitude", "longitude"}
    assert res["status"] == "received"
    assert res["photo_received"] is True
    assert res["text_received"] is True

    # Critical requirement: Ensure no fabricated environmental verdicts, scores, or claims exist
    forbidden_keys = {"verdict", "confidence", "confidence_score", "pollution_type", "evidence", "prediction", "explanation"}
    for key in forbidden_keys:
        assert key not in res, f"Forbidden key '{key}' found in Stage 1 response"


# 11. Report ID generation uniqueness
def test_report_id_generation_unique():
    jpeg_bytes = _create_test_image_bytes("JPEG")
    ids = set()
    for _ in range(5):
        files = {
            "photo": ("photo.jpg", io.BytesIO(jpeg_bytes), "image/jpeg")
        }
        data = {
            "latitude": 28.6139,
            "longitude": 77.2090,
            "timestamp": "2026-09-17T12:00:00Z",
        }
        response = client.post("/api/v1/reports", data=data, files=files)
        assert response.status_code == 200
        rep_id = response.json()["report_id"]
        assert rep_id.startswith("rep_")
        assert rep_id not in ids
        ids.add(rep_id)
    assert len(ids) == 5


# 12. No accidental modification of existing endpoints
def test_existing_endpoints_unmodified():
    # Test GET /
    r_root = client.get("/")
    assert r_root.status_code == 200
    assert r_root.json()["status"] == "VayuNet backend running"

    # Test GET /health
    r_health = client.get("/health")
    assert r_health.status_code == 200
    assert r_health.json()["status"] == "healthy"
    assert r_health.json()["service"] == "VayuNet Ingestion & Event API"
