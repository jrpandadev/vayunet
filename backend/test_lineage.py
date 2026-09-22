import sys
import os
import unittest
from fastapi.testclient import TestClient
import pandas as pd

# Add current dir to path to import main
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from main import app, EVENTS_STORE, REPORTS_STORE
from unittest.mock import patch

client = TestClient(app)

# Override auth dependency for testing
from services.auth_service import get_current_user, require_authority
app.dependency_overrides[get_current_user] = lambda: {"uid": "test_user"}
app.dependency_overrides[require_authority] = lambda: {"uid": "test_auth_user"}

class TestVayuNetLineage(unittest.TestCase):
    
    def setUp(self):
        # Ensure empty stores
        EVENTS_STORE.clear()
        REPORTS_STORE.clear()

    @patch('main.load_cpcb_data')
    @patch('main.get_latest_reading')
    def test_empty_events_valid_telemetry(self, mock_latest, mock_load):
        # 1. empty EVENTS_STORE + valid telemetry -> observed PM2.5 still available;
        mock_latest.return_value = {"pm25": 150.0, "station": "Test Station"}
        mock_load.return_value = pd.DataFrame()
        
        response = client.get("/api/environment/observations?city=delhi")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "AVAILABLE")
        self.assertEqual(data["value"], 150.0)
        self.assertEqual(len(EVENTS_STORE), 0)

    @patch('main.ForecastService.predict')
    @patch('main.get_weather')
    def test_empty_events_valid_forecast(self, mock_weather, mock_predict):
        # 2. empty EVENTS_STORE + valid forecast -> 24h forecast still available;
        mock_predict.return_value = {
            "forecast": [{"pm25": 200.0, "timestamp": "2024-01-01T00:00:00"}],
            "spike_risk": {"level": "HIGH"}
        }
        
        response = client.get("/api/sih_forecast?lat=28.6&lng=77.2&city=delhi")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["forecasts"]["pm25"]["status"], "AVAILABLE")
        self.assertTrue(len(data["forecasts"]["pm25"]["forecast"]) > 0)
        self.assertEqual(len(EVENTS_STORE), 0)

    @patch('main.extract_evidence')
    @patch('main.load_cpcb_data')
    @patch('main.get_weather')
    @patch('main.get_sentinel5p_features')
    @patch('main.calculate_event_confidence')
    @patch('main.identify_supporting_contradicting')
    def test_citizen_report_submission(self, mock_ident, mock_calc, mock_sent, mock_weat, mock_cpcb, mock_extr):
        # 3. citizen report submission -> report stored but NOT active event;
        # 4. report alone cannot trigger an alert;
        mock_extr.return_value = {"gemini_output": {"confidence": 0.8}}
        mock_calc.return_value = {"confidence": 0.8, "level": "HIGH"}
        mock_ident.return_value = {"supporting_evidence": ["citizen"]}
        
        response = client.post("/api/report", data={
            "text": "Smoke seen", "lat": 28.6, "lng": 77.2, "city": "delhi"
        })
        
        self.assertEqual(response.status_code, 200)
        
        # Ensure it went to REPORTS_STORE and NOT EVENTS_STORE
        self.assertEqual(len(EVENTS_STORE), 0)
        self.assertEqual(len(REPORTS_STORE), 1)

    @patch('main.load_cpcb_data')
    def test_telemetry_failure(self, mock_load):
        # 5. API telemetry failure -> UNAVAILABLE/ERROR, never zero;
        mock_load.side_effect = Exception("API Down")
        
        response = client.get("/api/environment/observations?city=delhi")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "UNAVAILABLE")
        self.assertIsNone(data["value"])
        self.assertNotEqual(data["value"], 0)
        self.assertEqual(data["error"], "API Down")

    @patch('main.ForecastService.predict')
    def test_forecast_failure(self, mock_predict):
        # 6. forecast failure -> UNAVAILABLE/ERROR, never zero;
        mock_predict.side_effect = Exception("Model Down")
        
        response = client.get("/api/sih_forecast?lat=28.6&lng=77.2&city=delhi")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["forecasts"]["pm25"]["status"], "UNAVAILABLE")
        self.assertNotIn("forecast", data["forecasts"]["pm25"])

    @patch('main.load_cpcb_data')
    def test_geographic_scope(self, mock_load):
        # 7. invalid/non-authoritative geographic scope is rejected only if an authoritative Delhi NCR boundary exists.
        # Since it is NOT implemented, it should pass (not return 400).
        mock_load.side_effect = Exception("Not Found") # To avoid actually loading data
        response = client.get("/api/environment/observations?city=mumbai")
        # Should return 200, but perhaps UNAVAILABLE if data is not found, but NOT 400.
        self.assertNotEqual(response.status_code, 400)

if __name__ == '__main__':
    unittest.main()
