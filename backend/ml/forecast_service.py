import json
import logging
from pathlib import Path
from typing import Dict, Any, List

import joblib
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models"
HORIZON_FEATURES_FILE = MODELS_DIR / "horizon_features.json"

EXPECTED_FEATURE_COUNTS = {
    "6h": 47,
    "24h": 44,
    "72h": 42,
}

MODEL_FILENAMES = {
    "6h": "xgb_weather_pm25_6h_tuned.joblib",
    "24h": "xgb_weather_pm25_24h_tuned.joblib",
    "72h": "xgb_weather_pm25_72h_tuned.joblib",
}


class ForecastService:
    def __init__(self):
        self.models = {}
        self.horizon_features: Dict[str, List[str]] = {}
        self.feature_cols: List[str] = []
        self._load_resources()

    def _load_resources(self):
        """Loads models and horizon feature metadata once during initialization."""
        if not HORIZON_FEATURES_FILE.exists():
            raise FileNotFoundError(f"Horizon features file not found at {HORIZON_FEATURES_FILE}")

        with open(HORIZON_FEATURES_FILE, "r") as f:
            horizon_meta = json.load(f)

        if "horizon_features" not in horizon_meta:
            raise KeyError("Key 'horizon_features' missing in horizon_features.json")

        self.horizon_features = horizon_meta["horizon_features"]

        horizons = ["6h", "24h", "72h"]
        all_feature_cols = []

        for h in horizons:
            if h not in self.horizon_features:
                raise KeyError(f"Horizon '{h}' not found in horizon_features definition")

            cols = self.horizon_features[h]
            expected_cnt = EXPECTED_FEATURE_COUNTS[h]

            if len(cols) != expected_cnt:
                raise ValueError(
                    f"Feature count mismatch for horizon '{h}': got {len(cols)}, expected {expected_cnt}"
                )

            for col in cols:
                if col not in all_feature_cols:
                    all_feature_cols.append(col)

            model_filename = MODEL_FILENAMES[h]
            model_path = MODELS_DIR / model_filename
            if not model_path.exists():
                raise FileNotFoundError(f"Model file not found at {model_path}")

            model = joblib.load(model_path)

            model_n_features = getattr(model, "n_features_in_", None)
            if model_n_features is not None and model_n_features != expected_cnt:
                raise ValueError(
                    f"Model '{model_filename}' expects {model_n_features} features, but horizon '{h}' specifies {expected_cnt}"
                )

            self.models[h] = model
            logger.info(f"Loaded {h} tuned champion model ({model_filename}) with {len(cols)} features.")

        self.feature_cols = all_feature_cols
        logger.info(f"Initialized ForecastService across all horizons ({len(self.feature_cols)} unique total features required).")

    def predict(self, features: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate 6h, 24h, and 72h forecasts for the provided feature vector.
        Returns the forecasted values and a heuristic spike risk.
        """
        if not isinstance(features, pd.DataFrame):
            features = pd.DataFrame(features)

        # 1. Reject future targets being passed as features
        target_cols = ["target_pm25_6h", "target_pm25_24h", "target_pm25_72h"]
        for target in target_cols:
            if target in features.columns:
                raise ValueError(f"Target column '{target}' cannot be passed as an input feature.")

        # 2. Validate that all required features exist for each horizon
        missing_by_horizon = {}
        for h in ["6h", "24h", "72h"]:
            missing = [col for col in self.horizon_features[h] if col not in features.columns]
            if missing:
                missing_by_horizon[h] = missing

        if missing_by_horizon:
            raise ValueError(f"Missing required features in input by horizon: {missing_by_horizon}")

        # 3. Generate forecasts strictly sliced and ordered per horizon
        forecasts = {}
        for h in ["6h", "24h", "72h"]:
            h_cols = self.horizon_features[h]
            X_h = features[h_cols].copy()
            pred = self.models[h].predict(X_h)
            # Assuming a single row prediction for API return
            forecasts[h] = float(pred[0])

        # 4. Evaluate heuristic risk
        risk_evaluation = self._calculate_spike_risk(forecasts)

        return {
            "forecast": forecasts,
            "spike_risk": risk_evaluation
        }

    def _calculate_spike_risk(self, forecasts: Dict[str, float]) -> Dict[str, Any]:
        """
        Converts forecasts into a simple heuristic spike-risk label.
        THIS IS NOT A CALIBRATED PROBABILITY.
        """
        max_forecast = max(forecasts.values())

        if max_forecast >= 150.0:
            level = "HIGH"
            basis = f"Maximum forecasted PM2.5 is {max_forecast:.1f} >= 150 µg/m³"
        elif max_forecast >= 100.0:
            level = "MEDIUM"
            basis = f"Maximum forecasted PM2.5 is {max_forecast:.1f} >= 100 µg/m³"
        else:
            level = "LOW"
            basis = "All forecasted PM2.5 values are below 100 µg/m³"

        return {
            "level": level,
            "basis": basis,
            "is_heuristic": True
        }


def _run_demo():
    print("======================================================")
    print("VAYUNET FORECAST SERVICE DEMO")
    print("======================================================")

    try:
        service = ForecastService()
    except Exception as e:
        print(f"Failed to initialize ForecastService: {e}")
        return

    processed_file = BASE_DIR / "data" / "processed" / "delhi_forecasting_weather.csv"
    if not processed_file.exists():
        processed_file = BASE_DIR / "data" / "processed" / "delhi_forecasting.csv"

    if not processed_file.exists():
        print(f"Processed data file not found at {processed_file}. Cannot run demo.")
        return

    print(f"\nLoading sample data from {processed_file.name}...")
    df = pd.read_csv(processed_file)

    # Replicate the one-hot encoding for station_id done in training
    df_encoded = pd.get_dummies(df, columns=["station_id"], dummy_na=False)

    # Isolate a row with high pollution to make the demo interesting
    high_pollution_mask = df_encoded["PM2.5"] > 250
    if high_pollution_mask.any():
        sample_row = df_encoded[high_pollution_mask].iloc[[0]].copy()
    else:
        sample_row = df_encoded.iloc[[0]].copy()

    # Ensure all required features across all horizons exist
    for col in service.feature_cols:
        if col not in sample_row.columns:
            sample_row[col] = 0

    # Convert bools to ints to prevent XGBoost warnings/errors
    for col in sample_row.select_dtypes(include=['bool']).columns:
        sample_row[col] = sample_row[col].astype(int)

    ts_col = "timestamp" if "timestamp" in sample_row.columns else "Timestamp"
    print(f"\nEvaluating sample row from {sample_row[ts_col].values[0]}")
    print(f"Current Observed PM2.5: {sample_row['PM2.5'].values[0]} µg/m³")

    # Drop targets so predict() doesn't complain
    for target in ["target_pm25_6h", "target_pm25_24h", "target_pm25_72h"]:
        if target in sample_row.columns:
            sample_row = sample_row.drop(columns=[target])

    try:
        result = service.predict(sample_row)
        print("\n--- FORECAST RESULT ---")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Prediction failed: {e}")


if __name__ == "__main__":
    _run_demo()
