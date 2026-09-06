import json
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import joblib
from sklearn.metrics import mean_absolute_error, mean_squared_error

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DATA_FILE = BASE_DIR / "data" / "processed" / "delhi_forecasting.csv"
MODELS_DIR = BASE_DIR / "models"
REPORTS_DIR = BASE_DIR / "reports" / "backtest"

TARGETS = {
    "6h": "target_pm25_6h",
    "24h": "target_pm25_24h",
    "72h": "target_pm25_72h",
}

def load_data():
    df = pd.read_csv(PROCESSED_DATA_FILE, parse_dates=["Timestamp"])
    df = df.sort_values(by="Timestamp").reset_index(drop=True)
    return df

def chronological_test_split(df, train_frac=0.70, val_frac=0.15):
    n = len(df)
    train_end = int(n * train_frac)
    val_end = train_end + int(n * val_frac)
    test_df = df.iloc[val_end:].copy()
    return test_df

def find_episodes(df, threshold=150, min_duration=6):
    episodes = []
    
    for station in df["station_id"].unique():
        sdf = df[df["station_id"] == station].copy()
        sdf = sdf.sort_values("Timestamp").reset_index(drop=True)
        
        is_high = sdf["PM2.5"] >= threshold
        episode_id = (is_high != is_high.shift()).cumsum()
        
        for eid, group in sdf[is_high].groupby(episode_id):
            duration = len(group)
            if duration >= min_duration:
                episodes.append({
                    "station_id": station,
                    "start": group["Timestamp"].min(),
                    "end": group["Timestamp"].max(),
                    "duration": duration,
                    "peak_pm25": group["PM2.5"].max(),
                    "mean_pm25": group["PM2.5"].mean(),
                    "num_obs": duration
                })
                
    return pd.DataFrame(episodes)

def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    df = load_data()
    drop_cols = ["Timestamp", "segment_id"] + list(TARGETS.values())
    df_encoded = pd.get_dummies(df, columns=["station_id"], dtype=int)
    
    features_path = MODELS_DIR / "features.json"
    with open(features_path, "r") as f:
        feature_cols = json.load(f)
        
    test_df = chronological_test_split(df_encoded)
    
    # Also need original test_df to have station_id easily accessible
    test_orig = chronological_test_split(df)
    test_orig = test_orig.sort_values(["station_id", "Timestamp"]).reset_index(drop=True)
    
    print("======================================================================")
    print("VAYUNET BACKTESTING MODULE")
    print("======================================================================")
    print(f"Test period: {test_orig['Timestamp'].min()} to {test_orig['Timestamp'].max()}")
    
    episodes_df = find_episodes(test_orig, threshold=150, min_duration=12)
    episodes_df = episodes_df.sort_values("peak_pm25", ascending=False)
    
    print(f"Found {len(episodes_df)} distinct episodes (>= 150 µg/m³, >= 12h duration)")
    
    # Select Representative Episodes
    selected_episodes = []
    
    # 1. Severe (highest peak)
    if len(episodes_df) > 0:
        selected_episodes.append(("Severe", episodes_df.iloc[0]))
        
    # 2. Moderate (peak around 200)
    moderate_candidates = episodes_df[(episodes_df["peak_pm25"] >= 180) & (episodes_df["peak_pm25"] <= 250)]
    if len(moderate_candidates) > 0:
        selected_episodes.append(("Moderate", moderate_candidates.iloc[len(moderate_candidates)//2]))
        
    # 3. Rising trend (just taking another distinct one)
    if len(episodes_df) > 2:
        selected_episodes.append(("Rising", episodes_df.iloc[2]))
        
    models = {}
    for h in TARGETS.keys():
        models[h] = joblib.load(MODELS_DIR / f"xgb_pm25_{h}.joblib")
        
    results_list = []
        
    for ep_type, ep in selected_episodes:
        print("\n----------------------------------------------------------------------")
        print(f"[{ep_type}] Episode Selected")
        print(f"Station     : {ep['station_id']}")
        print(f"Time Window : {ep['start']} to {ep['end']}")
        print(f"Duration    : {ep['duration']} hours")
        print(f"Peak PM2.5  : {ep['peak_pm25']:.1f} µg/m³")
        print("----------------------------------------------------------------------")
        
        station = ep["station_id"]
        # Context window for plotting/evaluating: 2 days before, 2 days after
        start_context = ep['start'] - pd.Timedelta(days=2)
        end_context = ep['end'] + pd.Timedelta(days=2)
        
        # Get data for this context window
        mask = (test_orig["station_id"] == station) & (test_orig["Timestamp"] >= start_context) & (test_orig["Timestamp"] <= end_context)
        context_df = test_orig[mask].copy()
        
        if len(context_df) == 0:
            continue
            
        # Get the corresponding encoded rows using the exact same logical mask (adjusted for get_dummies naming)
        mask_encoded = (test_df[f"station_id_{station}"] == 1) & (test_df["Timestamp"] >= start_context) & (test_df["Timestamp"] <= end_context)
        context_encoded = test_df[mask_encoded].copy()
        # Sort both chronologically to be safe and ensure alignment
        context_df = context_df.sort_values("Timestamp").reset_index(drop=True)
        context_encoded = context_encoded.sort_values("Timestamp").reset_index(drop=True)
        
        X = context_encoded[feature_cols]
        
        plt.figure(figsize=(12, 6))
        plt.plot(context_df["Timestamp"], context_df["PM2.5"], label="Actual PM2.5", color="black", linewidth=2)
        plt.axhline(150, color='red', linestyle='--', alpha=0.5, label='Event Threshold (150)')
        plt.axvspan(ep['start'], ep['end'], color='gray', alpha=0.1, label='Actual Event Window')
        
        for h, target_col in TARGETS.items():
            model = models[h]
            # Predict
            preds = model.predict(X)
            
            # The prediction made at `Timestamp` is for `Timestamp + h`
            hours_shift = int(h.replace("h", ""))
            pred_times = context_df["Timestamp"] + pd.Timedelta(hours=hours_shift)
            
            # Calculate metrics exactly during the episode window
            # To do this, we need to match predicted times to actual times in the episode
            # We evaluate forecasts that fall within the episode window
            ep_mask = (pred_times >= ep['start']) & (pred_times <= ep['end'])
            
            pred_in_ep = preds[ep_mask]
            times_in_ep = pred_times[ep_mask]
            
            # Find actual values at these predicted times
            actuals_in_ep = []
            for t in times_in_ep:
                actual_row = context_df[context_df["Timestamp"] == t]
                if len(actual_row) > 0:
                    actuals_in_ep.append(actual_row["PM2.5"].values[0])
                else:
                    actuals_in_ep.append(np.nan)
                    
            actuals_in_ep = np.array(actuals_in_ep)
            
            valid_mask = ~np.isnan(actuals_in_ep)
            
            if valid_mask.sum() > 0:
                mae = mean_absolute_error(actuals_in_ep[valid_mask], pred_in_ep[valid_mask])
                rmse = np.sqrt(mean_squared_error(actuals_in_ep[valid_mask], pred_in_ep[valid_mask]))
                
                # Did it capture the spike? Defined as predicting >= 150 during the episode
                spike_captured = np.any(pred_in_ep[valid_mask] >= 150)
            else:
                mae, rmse, spike_captured = np.nan, np.nan, False
                
            print(f"{h}:")
            print(f"  MAE            : {mae:.2f}")
            print(f"  RMSE           : {rmse:.2f}")
            print(f"  Spike Captured : {'YES' if spike_captured else 'NO'} (criterion: forecast >= 150 during event)")
            
            results_list.append({
                "episode_type": ep_type,
                "station": station,
                "horizon": h,
                "mae": mae,
                "rmse": rmse,
                "spike_captured": spike_captured
            })
            
            plt.plot(pred_times, preds, label=f"{h} Forecast", linewidth=1.5, alpha=0.8)
            
        plt.title(f"[{ep_type}] Episode Backtest - {station.title()}")
        plt.ylabel("PM2.5 (µg/m³)")
        plt.xlabel("Time")
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        plot_path = REPORTS_DIR / f"episode_{ep_type.lower()}_{station.replace(' ', '_')}.png"
        plt.savefig(plot_path)
        print(f"\nPlot saved to: {plot_path}")
        plt.close()

    pd.DataFrame(results_list).to_csv(REPORTS_DIR / "backtest_results.csv", index=False)
    
    print("\n======================================================================")
    print("BACKTEST SUMMARY")
    print("======================================================================")
    print("Models were evaluated on specific out-of-sample pollution events.")
    print("Spike capture criterion: Did the forecast predict PM2.5 >= 150 µg/m³ within the true event window?")
    
if __name__ == "__main__":
    main()
