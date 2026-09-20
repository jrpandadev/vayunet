import unittest
from pathlib import Path
import tempfile
import json

from ml.run_sequential_investigator import (
    classify_exception,
    extract_retry_delay_hint,
    check_already_completed,
    ErrorCategory,
)

class TestSequentialRunnerLogic(unittest.TestCase):
    def test_classify_503(self):
        e = Exception("503 UNAVAILABLE. This model is currently experiencing high demand.")
        cat, reason = classify_exception(e)
        self.assertEqual(cat, ErrorCategory.RETRYABLE_503)

    def test_classify_429(self):
        e = Exception("429 RESOURCE_EXHAUSTED. Quota exceeded for quota metric.")
        cat, reason = classify_exception(e)
        self.assertEqual(cat, ErrorCategory.RETRYABLE_429)

    def test_classify_network(self):
        e = Exception("Connection reset by peer")
        cat, reason = classify_exception(e)
        self.assertEqual(cat, ErrorCategory.NETWORK_ERROR)

    def test_classify_non_retryable(self):
        e = Exception("400 INVALID_ARGUMENT: Bad request")
        cat, reason = classify_exception(e)
        self.assertEqual(cat, ErrorCategory.NON_RETRYABLE_API_ERROR)

    def test_extract_retry_delay(self):
        err = "Rate limit exceeded. Please retry after 12.5s."
        hint = extract_retry_delay_hint(err)
        self.assertEqual(hint, 12.5)

    def test_resume_safety(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = Path(tmpdir) / "test_out.json"

            # Non-existent
            self.assertIsNone(check_already_completed(fpath))

            # Incomplete / error
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump({"status": "API_ERROR", "is_mock": False}, f)
            self.assertIsNone(check_already_completed(fpath))

            # Valid genuine completion
            valid_doc = {
                "status": "SUCCESS",
                "provider": "Google Gemini",
                "execution_path": "genuine_gemini",
                "is_mock": False,
                "report": {"some": "data"}
            }
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(valid_doc, f)

            completed = check_already_completed(fpath)
            self.assertIsNotNone(completed)
            self.assertEqual(completed["status"], "SUCCESS")

if __name__ == "__main__":
    unittest.main()
