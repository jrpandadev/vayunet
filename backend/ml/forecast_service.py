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
FEATURES_FILE = MODELS_DIR / "features.json"

class ForecastService:
    def __init__(self):
        self.models = {}
        self.feature_cols: List[str] = []
        self._load_resources()
        
    def _load_resources(self):
        """Loads models and feature metadata once during initialization."""
        if not FEATURES_FILE.exists():
            raise FileNotFoundError(f"Features file not found at {FEATURES_FILE}")
            
        with open(FEATURES_FILE, "r") as f:
            self.feature_cols = json.load(f)
            
        logger.info(f"Loaded {len(self.feature_cols)} expected features from metadata.")
        
        horizons = ["6h", "24h", "72h"]
        for h in horizons:
            model_path = MODELS_DIR / f"xgb_pm25_{h}.joblib"
            if not model_path.exists():
                raise FileNotFoundError(f"Model file not found at {model_path}")
            self.models[h] = joblib.load(model_path)
            logger.info(f"Loaded {h} forecasting model successfully.")

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
                
        # 2. Validate that all required features exist
        missing_features = [col for col in self.feature_cols if col not in features.columns]
        if missing_features:
            raise ValueError(f"Missing required features in input: {missing_features}")
            
        # 3. Restrict and strictly order columns to match training exactly
        X = features[self.feature_cols].copy()
        
        # 4. Generate forecasts
        forecasts = {}
        for h in ["6h", "24h", "72h"]:
            # XGBoost handles missing NaNs in X natively
            pred = self.models[h].predict(X)
            # Assuming a single row prediction for API return
            forecasts[h] = float(pred[0])
            
        # 5. Evaluate heuristic risk
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
        
    # Ensure all required features exist (e.g. if one-hot encoding didn't generate all stations for a single row)
    for col in service.feature_cols:
        if col not in sample_row.columns:
            sample_row[col] = 0
            
    # Convert bools to ints to prevent XGBoost warnings/errors
    for col in sample_row.select_dtypes(include=['bool']).columns:
        sample_row[col] = sample_row[col].astype(int)
        
    print(f"\nEvaluating sample row from {sample_row['Timestamp'].values[0]}")
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
