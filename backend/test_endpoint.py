from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_api():
    print("Testing GET / ...")
    r = client.get("/")
    print("GET / Response:", r.status_code, r.json())
    assert r.status_code == 200

    print("\nTesting POST /api/report (Text + Location)...")
    payload = {
        "text": "Dense dark smoke rising from an industrial facility near Okhla Phase 2.",
        "lat": 28.6139,
        "lng": 77.2090,
        "city": "delhi"
    }
    
    with open("test_images/smoke_industrial.jpg", "rb") as f:
        files = {"photo": ("smoke_industrial.jpg", f, "image/jpeg")}
        r = client.post("/api/report", data=payload, files=files)
    
    print("POST /api/report Status:", r.status_code)
    import json
    print("Response JSON:\n", json.dumps(r.json(), indent=2))
    assert r.status_code == 200

if __name__ == "__main__":
    test_api()
