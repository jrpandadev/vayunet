import unittest
from backend.ml.grounding_validator import GroundingValidator

class TestGroundingValidatorNumeric(unittest.TestCase):
    def setUp(self):
        # Base bundle where numeric value is missing so we can see if it's extracted as a claim.
        self.bundle = {"nwp": {"forecast_6h": 1}, "fire_activity": {"firms_detections_72h_50km": 4}, "peak_pm25": 143.2}

    def _validate(self, text, bundle=None):
        b = bundle if bundle else self.bundle
        report = {"synthesis_narrative": text, "evaluated_hypotheses": []}
        return GroundingValidator.validate(report, b)

    # Test 1
    def test_72_hour_period(self):
        text = "FIRMS detections occurred within a 72-hour period."
        is_valid, errors = self._validate(text)
        self.assertTrue(is_valid, f"Expected valid, got errors: {errors}")

    # Test 2
    def test_72_hours(self):
        text = "FIRMS detections occurred over 72 hours."
        is_valid, errors = self._validate(text)
        self.assertTrue(is_valid, f"Expected valid, got errors: {errors}")

    # Test 3
    def test_50_km(self):
        text = "FIRMS detections occurred within 50 km."
        is_valid, errors = self._validate(text)
        self.assertTrue(is_valid, f"Expected valid, got errors: {errors}")

    # Test 4
    def test_4_thermal_detections_within_50_km(self):
        # The bundle has firms_detections = 4. 4 should be grounded, 50 should be ignored.
        text = "FIRMS recorded 4 thermal detections within 50 km."
        is_valid, errors = self._validate(text)
        self.assertTrue(is_valid, f"Expected valid, got errors: {errors}")

    # Test 5
    def test_pm25_reached(self):
        # Bundle has peak_pm25 = 143.2. If text says 287.6, it should fail. If text says 143.2, it should pass.
        # Wait, the test says: "Expected: 287.6 remains a numerical claim."
        text = "PM2.5 reached 287.6 µg/m³."
        is_valid, errors = self._validate(text)
        self.assertFalse(is_valid)
        self.assertTrue(any("287.6" in str(e) for e in errors))

    # Test 6
    def test_72_hours_and_pm25(self):
        text = "The event lasted 72 hours and PM2.5 reached 287.6 µg/m³."
        is_valid, errors = self._validate(text)
        self.assertFalse(is_valid)
        self.assertFalse(any("72" in str(e) for e in errors))
        self.assertTrue(any("287.6" in str(e) for e in errors))

    # Test 7
    def test_datetime_and_claim(self):
        text = "At 20:00 on 2026-08-23, PM2.5 was 143.2."
        is_valid, errors = self._validate(text)
        self.assertTrue(is_valid, f"Expected valid, got errors: {errors}")

    # Test 8
    def test_multiple_numeric_claims(self):
        text = "PM2.5 increased from 120.4 to 287.6 µg/m³."
        is_valid, errors = self._validate(text)
        self.assertFalse(is_valid)
        # 120.4 is a claim and 287.6 is a claim. Since neither are in bundle, both should fail.
        self.assertTrue(any("120.4" in str(e) for e in errors))
        self.assertTrue(any("287.6" in str(e) for e in errors))

    # Test 9
    def test_critical_hallucination_regression(self):
        text = "PM2.5 was 287.6"
        is_valid, errors = self._validate(text)
        self.assertFalse(is_valid)
        self.assertTrue(any("287.6" in str(e) for e in errors))

    # Test 10 (FIRMS Schema Regression)
    def test_firms_schema_regression(self):
        # Ensure that it doesn't fail on missing `firms_viirs`
        text = "FIRMS detections were 4"
        is_valid, errors = self._validate(text)
        self.assertTrue(is_valid, f"Expected valid, got errors: {errors}")

        # Test missing fire_activity triggering hallucination error
        bundle = {"nwp": {"forecast_6h": 1}, "fire_activity": {}, "peak_pm25": 143.2}
        is_valid, errors = self._validate(text, bundle)
        self.assertFalse(is_valid)
        self.assertTrue(any("FIRMS/VIIRS active fires mentioned despite being null/empty" in str(e) for e in errors))

if __name__ == '__main__':
    unittest.main()
