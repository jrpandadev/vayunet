"""
VayuNet — Comprehensive XGBoost Forecast Model Analysis

Analyzes the trained 6h/24h/72h PM2.5 forecasting models WITHOUT retraining
or modifying any existing files.

Parts:
  1. Feature importance (gain)
  2. Overall test-set error metrics
  3. Error by pollution regime
  4. Error by station
  5. Error by season
  6. Extreme pollution analysis
  7. Bias / underprediction analysis
  8. Plots (scatter, residuals, regime bars, station bars)
  9. Printed final report + interpretation
"""

import json
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# ============================================================
# Paths
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DATA_FILE = BASE_DIR / "data" / "processed" / "delhi_forecasting.csv"
MODELS_DIR = BASE_DIR / "models"
FEATURES_FILE = MODELS_DIR / "features.json"

REPORTS_DIR = BASE_DIR / "reports"
ANALYSIS_DIR = REPORTS_DIR / "model_analysis"

TARGETS = {
    "6h": "target_pm25_6h",
    "24h": "target_pm25_24h",
    "72h": "target_pm25_72h",
}

HORIZONS = ["6h", "24h", "72h"]

REGIME_BINS = [
    ("LOW", 0, 60),
    ("MODERATE", 60, 120),
    ("HIGH", 120, 250),
    ("SEVERE", 250, np.inf),
]

SEASON_MAP = {
    12: "Winter", 1: "Winter", 2: "Winter",
    3: "Pre-monsoon", 4: "Pre-monsoon", 5: "Pre-monsoon",
    6: "Monsoon", 7: "Monsoon", 8: "Monsoon", 9: "Monsoon",
    10: "Post-monsoon", 11: "Post-monsoon",
}
SEASON_ORDER = ["Winter", "Pre-monsoon", "Monsoon", "Post-monsoon"]


# ============================================================
# Helpers — replicate train_forecast.py split exactly
# ============================================================

def load_and_split():
    """Load processed data and reproduce the exact chronological split."""
    df = pd.read_csv(PROCESSED_DATA_FILE, parse_dates=["Timestamp"])
    df = df.sort_values(by="Timestamp").reset_index(drop=True)

    # One-hot encode station_id (same as train_forecast.py)
    df_encoded = pd.get_dummies(df, columns=["station_id"], dtype=int)

    with open(FEATURES_FILE, "r") as f:
        feature_cols = json.load(f)

    # Chronological 70 / 15 / 15
    n = len(df_encoded)
    train_end = int(n * 0.70)
    val_end = train_end + int(n * 0.15)
    test_df = df_encoded.iloc[val_end:].copy()

    return test_df, feature_cols


def load_models():
    models = {}
    for h in HORIZONS:
        p = MODELS_DIR / f"xgb_pm25_{h}.joblib"
        if not p.exists():
            raise FileNotFoundError(p)
        models[h] = joblib.load(p)
    return models


def regime_label(val):
    for name, lo, hi in REGIME_BINS:
        if lo <= val < hi:
            return name
    return "SEVERE"  # catch-all for exactly 250


def season_label(ts):
    return SEASON_MAP[ts.month]


# ============================================================
# Main analysis
# ============================================================

def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

    test_df, feature_cols = load_and_split()
    models = load_models()

    print("=" * 70)
    print("VAYUNET — COMPREHENSIVE MODEL ANALYSIS")
    print("=" * 70)
    print(f"Test period : {test_df['Timestamp'].min()} -> {test_df['Timestamp'].max()}")
    print(f"Test rows   : {len(test_df):,}")
    print(f"Features    : {len(feature_cols)}")
    print()

    # ----------------------------------------------------------
    # Build predictions for every horizon on the test set
    # ----------------------------------------------------------
    preds = {}   # horizon → array
    actuals = {} # horizon → Series
    masks = {}   # horizon → boolean Series (valid rows)

    X_test = test_df[feature_cols]

    for h in HORIZONS:
        target_col = TARGETS[h]
        y = test_df[target_col]
        mask = y.notna()
        y_pred_all = models[h].predict(X_test)
        preds[h] = y_pred_all
        actuals[h] = y
        masks[h] = mask

    # ================================================================
    # PART 1 — Feature Importance (gain)
    # ================================================================
    print("=" * 70)
    print("PART 1 — FEATURE IMPORTANCE (by gain)")
    print("=" * 70)

    for h in HORIZONS:
        booster = models[h].get_booster()
        scores = booster.get_score(importance_type="gain")
        imp_df = (
            pd.DataFrame(
                [{"feature": k, "gain": v} for k, v in scores.items()]
            )
            .sort_values("gain", ascending=False)
            .reset_index(drop=True)
        )
        # Map internal fN names back to real feature names
        imp_df["feature"] = imp_df["feature"].apply(
            lambda f: feature_cols[int(f[1:])] if f.startswith("f") and f[1:].isdigit() else f
        )
        imp_df.to_csv(REPORTS_DIR / f"feature_importance_{h}.csv", index=False)

        print(f"\n--- {h} horizon (top 20) ---")
        for i, row in imp_df.head(20).iterrows():
            print(f"  {i+1:2d}. {row['feature']:30s}  gain={row['gain']:.1f}")

        # Bar chart — top 15
        top15 = imp_df.head(15)
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.barh(
            range(len(top15) - 1, -1, -1),
            top15["gain"].values,
            color="#3b82f6",
        )
        ax.set_yticks(range(len(top15) - 1, -1, -1))
        ax.set_yticklabels(top15["feature"].values, fontsize=9)
        ax.set_xlabel("Gain")
        ax.set_title(f"Top 15 Features by Gain — {h} Horizon")
        fig.tight_layout()
        fig.savefig(REPORTS_DIR / f"feature_importance_{h}.png", dpi=150)
        plt.close(fig)

    # ================================================================
    # PART 2 — Overall Test Metrics
    # ================================================================
    print("\n" + "=" * 70)
    print("PART 2 — OVERALL TEST METRICS")
    print("=" * 70)

    overall_metrics = {}
    header = f"{'Horizon':>8s} | {'MAE':>8s} | {'RMSE':>8s} | {'R²':>8s} | {'Bias':>9s} | {'MedAE':>8s} | {'MaxAE':>9s}"
    print(header)
    print("-" * len(header))

    for h in HORIZONS:
        m = masks[h]
        y_t = actuals[h][m].values
        y_p = preds[h][m]
        err = y_p - y_t

        mae = mean_absolute_error(y_t, y_p)
        rmse = np.sqrt(mean_squared_error(y_t, y_p))
        r2 = r2_score(y_t, y_p)
        bias = float(np.mean(err))
        medae = float(np.median(np.abs(err)))
        maxae = float(np.max(np.abs(err)))

        overall_metrics[h] = dict(mae=mae, rmse=rmse, r2=r2, bias=bias, medae=medae, maxae=maxae, n=int(m.sum()))
        print(f"{h:>8s} | {mae:8.2f} | {rmse:8.2f} | {r2:8.3f} | {bias:9.2f} | {medae:8.2f} | {maxae:9.2f}")

    # ================================================================
    # PART 3 — Error by Pollution Regime
    # ================================================================
    print("\n" + "=" * 70)
    print("PART 3 — ERROR BY POLLUTION REGIME")
    print("=" * 70)

    regime_rows = []
    for h in HORIZONS:
        m = masks[h]
        y_t = actuals[h][m].values
        y_p = preds[h][m]
        err = y_p - y_t
        labels = np.array([regime_label(v) for v in y_t])

        print(f"\n--- {h} ---")
        hdr = f"  {'Regime':>10s} | {'N':>7s} | {'MAE':>8s} | {'RMSE':>8s} | {'Bias':>9s} | {'MeanAE':>8s}"
        print(hdr)
        print("  " + "-" * (len(hdr) - 2))

        for rname, _, _ in REGIME_BINS:
            sel = labels == rname
            if sel.sum() == 0:
                continue
            r_mae = mean_absolute_error(y_t[sel], y_p[sel])
            r_rmse = np.sqrt(mean_squared_error(y_t[sel], y_p[sel]))
            r_bias = float(np.mean(err[sel]))
            r_meanae = float(np.mean(np.abs(err[sel])))
            n_sel = int(sel.sum())
            print(f"  {rname:>10s} | {n_sel:7d} | {r_mae:8.2f} | {r_rmse:8.2f} | {r_bias:9.2f} | {r_meanae:8.2f}")
            regime_rows.append(dict(horizon=h, regime=rname, n=n_sel, mae=r_mae, rmse=r_rmse, bias=r_bias, meanae=r_meanae))

    pd.DataFrame(regime_rows).to_csv(ANALYSIS_DIR / "error_by_regime.csv", index=False)

    # ================================================================
    # PART 4 — Error by Station
    # ================================================================
    print("\n" + "=" * 70)
    print("PART 4 — ERROR BY STATION")
    print("=" * 70)

    # Recover station name from one-hot columns
    station_cols = [c for c in feature_cols if c.startswith("station_id_")]
    station_names = [c.replace("station_id_", "") for c in station_cols]

    station_rows = []
    for h in HORIZONS:
        m = masks[h]
        y_t = actuals[h][m].values
        y_p = preds[h][m]
        err = y_p - y_t

        # Map each test row to its station
        station_labels = []
        test_valid = test_df[m]
        for _, row in test_valid[station_cols].iterrows():
            matched = [sn for sn, sc in zip(station_names, station_cols) if row[sc] == 1]
            station_labels.append(matched[0] if matched else "unknown")
        station_labels = np.array(station_labels)

        print(f"\n--- {h} ---")
        hdr = f"  {'Station':>25s} | {'N':>7s} | {'MAE':>8s} | {'RMSE':>8s} | {'R²':>8s} | {'Bias':>9s}"
        print(hdr)
        print("  " + "-" * (len(hdr) - 2))

        for sn in sorted(set(station_labels)):
            sel = station_labels == sn
            if sel.sum() < 2:
                continue
            s_mae = mean_absolute_error(y_t[sel], y_p[sel])
            s_rmse = np.sqrt(mean_squared_error(y_t[sel], y_p[sel]))
            s_r2 = r2_score(y_t[sel], y_p[sel])
            s_bias = float(np.mean(err[sel]))
            n_sel = int(sel.sum())
            print(f"  {sn:>25s} | {n_sel:7d} | {s_mae:8.2f} | {s_rmse:8.2f} | {s_r2:8.3f} | {s_bias:9.2f}")
            station_rows.append(dict(horizon=h, station=sn, n=n_sel, mae=s_mae, rmse=s_rmse, r2=s_r2, bias=s_bias))

    station_df = pd.DataFrame(station_rows)
    station_df.to_csv(REPORTS_DIR / "error_by_station.csv", index=False)

    # ================================================================
    # PART 5 — Error by Season
    # ================================================================
    print("\n" + "=" * 70)
    print("PART 5 — ERROR BY SEASON")
    print("=" * 70)

    season_rows = []
    for h in HORIZONS:
        m = masks[h]
        y_t = actuals[h][m].values
        y_p = preds[h][m]
        err = y_p - y_t

        # Determine target timestamp for season classification
        target_hours = {"6h": 6, "24h": 24, "72h": 72}
        target_ts = test_df.loc[m, "Timestamp"] + pd.Timedelta(hours=target_hours[h])
        season_labels = np.array([season_label(ts) for ts in target_ts])

        print(f"\n--- {h} ---")
        hdr = f"  {'Season':>15s} | {'N':>7s} | {'MAE':>8s} | {'RMSE':>8s} | {'R²':>8s} | {'Bias':>9s}"
        print(hdr)
        print("  " + "-" * (len(hdr) - 2))

        for sn in SEASON_ORDER:
            sel = season_labels == sn
            if sel.sum() < 2:
                continue
            s_mae = mean_absolute_error(y_t[sel], y_p[sel])
            s_rmse = np.sqrt(mean_squared_error(y_t[sel], y_p[sel]))
            s_r2 = r2_score(y_t[sel], y_p[sel])
            s_bias = float(np.mean(err[sel]))
            n_sel = int(sel.sum())
            print(f"  {sn:>15s} | {n_sel:7d} | {s_mae:8.2f} | {s_rmse:8.2f} | {s_r2:8.3f} | {s_bias:9.2f}")
            season_rows.append(dict(horizon=h, season=sn, n=n_sel, mae=s_mae, rmse=s_rmse, r2=s_r2, bias=s_bias))

    season_df = pd.DataFrame(season_rows)
    season_df.to_csv(REPORTS_DIR / "error_by_season.csv", index=False)

    # ================================================================
    # PART 6 — Extreme Pollution Analysis (actual >= 250)
    # ================================================================
    print("\n" + "=" * 70)
    print("PART 6 — EXTREME POLLUTION ANALYSIS (actual target >= 250 µg/m³)")
    print("=" * 70)

    for h in HORIZONS:
        m = masks[h]
        y_t = actuals[h][m].values
        y_p = preds[h][m]
        sel = y_t >= 250

        if sel.sum() == 0:
            print(f"\n--- {h}: no extreme observations ---")
            continue

        y_t_ext = y_t[sel]
        y_p_ext = y_p[sel]
        err_ext = y_p_ext - y_t_ext

        ext_mae = mean_absolute_error(y_t_ext, y_p_ext)
        ext_rmse = np.sqrt(mean_squared_error(y_t_ext, y_p_ext))
        ext_bias = float(np.mean(err_ext))
        capture_rate = float(np.mean(y_p_ext >= 150)) * 100

        print(f"\n--- {h} ---")
        print(f"  Sample count            : {int(sel.sum()):,}")
        print(f"  MAE                     : {ext_mae:.2f}")
        print(f"  RMSE                    : {ext_rmse:.2f}")
        print(f"  Mean error (pred-actual): {ext_bias:.2f}")
        print(f"  Median actual PM2.5     : {np.median(y_t_ext):.1f}")
        print(f"  Median predicted PM2.5  : {np.median(y_p_ext):.1f}")
        print(f"  Maximum actual PM2.5    : {np.max(y_t_ext):.1f}")
        print(f"  Maximum predicted PM2.5 : {np.max(y_p_ext):.1f}")
        print(f"  Extreme-event threshold capture rate (pred >= 150): {capture_rate:.1f}%")

    # ================================================================
    # PART 7 — Bias Analysis
    # ================================================================
    print("\n" + "=" * 70)
    print("PART 7 — BIAS / UNDERPREDICTION ANALYSIS")
    print("=" * 70)

    bias_categories = [
        ("All test observations", lambda yt: np.ones(len(yt), dtype=bool)),
        ("Actual >= 150", lambda yt: yt >= 150),
        ("Actual >= 250", lambda yt: yt >= 250),
    ]

    for h in HORIZONS:
        m = masks[h]
        y_t = actuals[h][m].values
        y_p = preds[h][m]

        print(f"\n--- {h} ---")
        for label, selector in bias_categories:
            sel = selector(y_t)
            if sel.sum() == 0:
                print(f"  {label:30s} : no samples")
                continue
            bias = float(np.mean(y_p[sel] - y_t[sel]))
            n = int(sel.sum())
            print(f"  {label:30s} : bias = {bias:+.2f}  (n={n:,})")

    # ================================================================
    # PART 8 — Plots
    # ================================================================
    print("\n" + "=" * 70)
    print("PART 8 — GENERATING PLOTS")
    print("=" * 70)

    for h in HORIZONS:
        m = masks[h]
        y_t = actuals[h][m].values
        y_p = preds[h][m]
        err = y_p - y_t

        # --- 8a. Actual vs Predicted scatter ---
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.scatter(y_t, y_p, alpha=0.15, s=6, color="#6366f1", edgecolors="none")
        lim_max = max(y_t.max(), y_p.max()) * 1.05
        ax.plot([0, lim_max], [0, lim_max], "k--", linewidth=0.8, label="Perfect forecast")
        ax.set_xlabel("Actual PM2.5 (µg/m³)")
        ax.set_ylabel("Predicted PM2.5 (µg/m³)")
        ax.set_title(f"Actual vs Predicted — {h} Horizon")
        ax.legend()
        ax.set_xlim(0, lim_max)
        ax.set_ylim(0, lim_max)
        fig.tight_layout()
        fig.savefig(ANALYSIS_DIR / f"scatter_{h}.png", dpi=150)
        plt.close(fig)
        print(f"  Saved scatter_{h}.png")

        # --- 8b. Residual distribution ---
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.hist(err, bins=100, color="#f59e0b", edgecolor="none", alpha=0.85)
        ax.axvline(0, color="black", linestyle="--", linewidth=0.8)
        ax.axvline(np.mean(err), color="red", linestyle="-", linewidth=1.2, label=f"Mean bias = {np.mean(err):.1f}")
        ax.set_xlabel("Residual (Predicted − Actual)")
        ax.set_ylabel("Count")
        ax.set_title(f"Residual Distribution — {h} Horizon")
        ax.legend()
        fig.tight_layout()
        fig.savefig(ANALYSIS_DIR / f"residuals_{h}.png", dpi=150)
        plt.close(fig)
        print(f"  Saved residuals_{h}.png")

    # --- 8c. MAE by pollution regime for each horizon ---
    regime_df = pd.DataFrame(regime_rows)
    for h in HORIZONS:
        sub = regime_df[regime_df["horizon"] == h]
        fig, ax = plt.subplots(figsize=(8, 5))
        colors = {"LOW": "#22c55e", "MODERATE": "#eab308", "HIGH": "#f97316", "SEVERE": "#ef4444"}
        bars = ax.bar(sub["regime"], sub["mae"], color=[colors.get(r, "#888") for r in sub["regime"]])
        for bar, val in zip(bars, sub["mae"]):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1, f"{val:.1f}", ha="center", fontsize=9)
        ax.set_xlabel("Pollution Regime")
        ax.set_ylabel("MAE (µg/m³)")
        ax.set_title(f"MAE by Pollution Regime — {h} Horizon")
        fig.tight_layout()
        fig.savefig(ANALYSIS_DIR / f"mae_regime_{h}.png", dpi=150)
        plt.close(fig)
        print(f"  Saved mae_regime_{h}.png")

    # --- 8d. MAE by station for each horizon ---
    for h in HORIZONS:
        sub = station_df[station_df["horizon"] == h].sort_values("mae", ascending=True)
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.barh(range(len(sub)), sub["mae"].values, color="#8b5cf6")
        ax.set_yticks(range(len(sub)))
        ax.set_yticklabels(sub["station"].values, fontsize=9)
        ax.set_xlabel("MAE (µg/m³)")
        ax.set_title(f"MAE by Station — {h} Horizon")
        fig.tight_layout()
        fig.savefig(ANALYSIS_DIR / f"mae_station_{h}.png", dpi=150)
        plt.close(fig)
        print(f"  Saved mae_station_{h}.png")

    # ================================================================
    # PART 9 — Interpretation
    # ================================================================
    print("\n" + "=" * 70)
    print("INTERPRETATION")
    print("=" * 70)

    print("""
NOTE: Feature importance reflects PREDICTIVE IMPORTANCE within the XGBoost
model, NOT physical causation. A feature being important for prediction does
not mean it causes PM2.5 concentrations to change.

1. WHAT FEATURES DOMINATE?
   Inspect the top-20 lists above. Lag features (PM2.5_lag_1h, lag_24h) and
   rolling statistics (PM2.5_rolling_24h_mean) typically dominate because
   pollution is highly autocorrelated hour-to-hour.

2. DOES IMPORTANCE CHANGE BETWEEN 6h, 24h, 72h?
   Short-horizon (6h) models lean heavily on very recent lags (lag_1h).
   Longer horizons shift weight toward rolling averages and meteorological
   features as the direct-lag signal decays.

3. WHICH STATIONS ARE HARDEST TO FORECAST?
   Compare MAE and R² across stations above. Stations near industrial zones
   or major traffic corridors typically exhibit higher variance and larger
   forecast errors.

4. WHICH POLLUTION REGIME IS HARDEST?
   SEVERE (>= 250 µg/m³) has the largest absolute errors because the model
   is trained on squared-error loss, which compresses predictions toward the
   mean of the training distribution. Extreme values are in the long right
   tail.

5. HOW BADLY DOES THE MODEL UNDERPREDICT EXTREME POLLUTION?
   Examine the bias column for actual >= 250. A large negative bias confirms
   systematic underprediction of extreme events — the model forecasts high
   concentrations but underestimates the true magnitude.

6. DOES PERFORMANCE DEGRADE 6h → 24h → 72h?
   Compare overall MAE/RMSE/R² across horizons. Expect monotonic degradation
   because atmospheric predictability decreases with time.

7. SHOULD WE IMPROVE THE MODEL BEFORE INTEGRATING?
   If the extreme-event threshold capture rate is high (>= 80%) and overall
   R² is reasonable (>= 0.5), the model is adequate for a hackathon-stage
   early-warning system. Magnitude accuracy on severe events can be improved
   later with quantile regression, asymmetric loss, or ensemble methods.
""")

    print("=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
