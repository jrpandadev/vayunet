"""
filter_bundles.py
=================
VAYUNET — FILTER_6452_EVIDENCE_BUNDLES
Phase 1: Profile all bundles.
Phase 2: Stratified candidate set generation (50 / 100 / 150 / 200).

Rules:
- NO LLM calls.
- NO modification of original bundles.
- NO modification of production code.
- All output goes to backend/reports/investigation/filter_candidates/
"""

import json
import math
import os
import random
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
BUNDLE_DIR = ROOT / "backend" / "data" / "processed" / "evidence_bundles"
OUTPUT_DIR = ROOT / "backend" / "reports" / "investigation" / "filter_candidates"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Deterministic seed — never change, guarantees reproducibility.
RANDOM_SEED = 42

# Target candidate set sizes
CANDIDATE_SIZES = [50, 100, 150, 200]

# ---------------------------------------------------------------------------
# Severity ordering (for stratification)
# ---------------------------------------------------------------------------
SEVERITY_ORDER = {
    "SEVERE_EVENT": 4,
    "POLLUTION_EVENT": 3,
    "MODERATE_EVENT": 2,
    "MILD_EVENT": 1,
    "UNKNOWN": 0,
}

# ---------------------------------------------------------------------------
# Season mapping (for Northern India — boreal calendar)
# ---------------------------------------------------------------------------
def get_season(month: int) -> str:
    if month in (12, 1, 2):
        return "winter"
    elif month in (3, 4, 5):
        return "spring"
    elif month in (6, 7, 8):
        return "monsoon"
    else:
        return "post_monsoon"


# ---------------------------------------------------------------------------
# Feature extraction — strictly from bundle fields, no computation beyond
# what's derivable from existing values.
# ---------------------------------------------------------------------------
def extract_features(bundle: dict, filename: str) -> dict:
    event_id = bundle.get("event_id", filename.replace(".json", ""))
    station_id = bundle.get("station_id", "unknown")

    event = bundle.get("event", {}) or {}
    pollution = bundle.get("pollution_dynamics", {}) or {}
    meteo = bundle.get("meteorology", {}) or {}
    nwp = bundle.get("nwp", {}) or {}
    satellite = bundle.get("satellite", {}) or {}
    fire = bundle.get("fire_activity", {}) or {}
    source = bundle.get("source_context", {}) or {}

    # --- Event temporal ---
    start_str = event.get("start_time")
    try:
        start_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S") if start_str else None
    except Exception:
        start_dt = None

    year = start_dt.year if start_dt else None
    month = start_dt.month if start_dt else None
    hour = start_dt.hour if start_dt else None
    season = get_season(month) if month else "unknown"

    # --- Event magnitude ---
    duration_hours = event.get("duration_hours")
    severity = event.get("severity", "UNKNOWN")
    severity_rank = SEVERITY_ORDER.get(severity, 0)
    peak_pm25 = event.get("peak_pm25")
    mean_pm25 = event.get("mean_pm25")
    min_pm25 = event.get("min_pm25")
    onset_growth = event.get("onset_growth")

    # --- Pollution dynamics ---
    pm25_mean = (pollution.get("pm25") or {}).get("mean")
    pm25_max = (pollution.get("pm25") or {}).get("max")
    pm10_mean = (pollution.get("pm10") or {}).get("mean")
    pm10_max = (pollution.get("pm10") or {}).get("max")
    no2_mean = (pollution.get("no2") or {}).get("mean")
    no2_max = (pollution.get("no2") or {}).get("max")

    has_pm25 = pm25_mean is not None
    has_pm10 = pm10_mean is not None
    has_no2 = no2_mean is not None

    # --- Meteorology ---
    temp_mean = (meteo.get("temperature") or {}).get("mean")
    rh_mean = (meteo.get("relative_humidity") or {}).get("mean")
    ws_mean = (meteo.get("wind_speed") or {}).get("mean")
    pblh_mean = (meteo.get("pblh") or {}).get("mean")
    wind_sin = (meteo.get("wind_direction") or {}).get("mean_sin")
    wind_cos = (meteo.get("wind_direction") or {}).get("mean_cos")

    has_temp = temp_mean is not None
    has_rh = rh_mean is not None
    has_ws = ws_mean is not None
    has_pblh = pblh_mean is not None
    has_wind_dir = wind_sin is not None and wind_cos is not None

    # --- NWP ---
    nwp_6h = nwp.get("forecast_6h")
    nwp_24h = nwp.get("forecast_24h")
    nwp_72h = nwp.get("forecast_72h")
    has_nwp_6h = nwp_6h is not None
    has_nwp_24h = nwp_24h is not None
    has_nwp_72h = nwp_72h is not None
    nwp_any = has_nwp_6h or has_nwp_24h or has_nwp_72h

    # --- Satellite ---
    s5p_no2 = satellite.get("sentinel5p_no2_latest")
    s5p_age = satellite.get("sentinel5p_no2_age_hours")
    has_s5p = s5p_no2 is not None

    # --- Fire ---
    firms = fire.get("firms_detections_72h_50km")
    has_fire = firms is not None
    fire_positive = isinstance(firms, (int, float)) and firms > 0

    # --- Source context ---
    owbeii = source.get("owbeii_waste_burned")
    has_owbeii = owbeii is not None
    owbeii_positive = isinstance(owbeii, (int, float)) and owbeii > 0

    # --- Evidence richness score (deterministic, 0–10) ---
    # Each available evidence type contributes 1 point.
    evidence_score = sum([
        has_pm25,
        has_pm10,
        has_no2,
        has_temp,
        has_rh,
        has_ws,
        has_pblh,
        has_wind_dir,
        has_s5p,
        has_fire,
    ])

    # --- Conflict indicators ---
    # High RH + high wind (dispersion unlikely; contradictory)
    conflict_high_rh_high_ws = (
        isinstance(rh_mean, float) and rh_mean > 80
        and isinstance(ws_mean, float) and ws_mean > 15
    )
    # Fire present despite high wind (transport event)
    conflict_fire_high_ws = (
        fire_positive
        and isinstance(ws_mean, float) and ws_mean > 15
    )
    # Severe event with low PBLH (classic trapping event)
    trapped_event = (
        severity_rank >= 3
        and isinstance(pblh_mean, float) and pblh_mean < 300
    )
    # High pm25 but fire = 0 and owbeii = 0 (unexplained source)
    unexplained_source = (
        isinstance(peak_pm25, float) and peak_pm25 > 300
        and not fire_positive
        and not owbeii_positive
    )

    conflict_count = sum([
        conflict_high_rh_high_ws,
        conflict_fire_high_ws,
        trapped_event,
        unexplained_source,
    ])

    return {
        # Identity
        "filename": filename,
        "event_id": event_id,
        "station_id": station_id,
        # Temporal
        "year": year,
        "month": month,
        "hour": hour,
        "season": season,
        # Event
        "duration_hours": duration_hours,
        "severity": severity,
        "severity_rank": severity_rank,
        "peak_pm25": peak_pm25,
        "mean_pm25": mean_pm25,
        "min_pm25": min_pm25,
        "onset_growth": onset_growth,
        # Pollution
        "pm25_mean": pm25_mean,
        "pm25_max": pm25_max,
        "pm10_mean": pm10_mean,
        "pm10_max": pm10_max,
        "no2_mean": no2_mean,
        "no2_max": no2_max,
        "has_pm25": has_pm25,
        "has_pm10": has_pm10,
        "has_no2": has_no2,
        # Meteorology
        "temp_mean": temp_mean,
        "rh_mean": rh_mean,
        "ws_mean": ws_mean,
        "pblh_mean": pblh_mean,
        "wind_sin": wind_sin,
        "wind_cos": wind_cos,
        "has_temp": has_temp,
        "has_rh": has_rh,
        "has_ws": has_ws,
        "has_pblh": has_pblh,
        "has_wind_dir": has_wind_dir,
        # NWP
        "has_nwp_6h": has_nwp_6h,
        "has_nwp_24h": has_nwp_24h,
        "has_nwp_72h": has_nwp_72h,
        "nwp_any": nwp_any,
        # Satellite
        "has_s5p": has_s5p,
        "s5p_no2": s5p_no2,
        "s5p_age_hours": s5p_age,
        # Fire
        "has_fire": has_fire,
        "fire_positive": fire_positive,
        "firms_72h": firms,
        # Source
        "has_owbeii": has_owbeii,
        "owbeii_positive": owbeii_positive,
        "owbeii_waste_burned": owbeii,
        # Derived
        "evidence_score": evidence_score,
        "conflict_count": conflict_count,
        "conflict_high_rh_high_ws": conflict_high_rh_high_ws,
        "conflict_fire_high_ws": conflict_fire_high_ws,
        "trapped_event": trapped_event,
        "unexplained_source": unexplained_source,
    }


# ---------------------------------------------------------------------------
# Phase 1 — Profile
# ---------------------------------------------------------------------------
def phase1_profile(bundle_files: list[Path]) -> list[dict]:
    print(f"[Phase 1] Profiling {len(bundle_files)} bundles...")
    rows = []
    errors = []
    for i, path in enumerate(bundle_files):
        if i % 500 == 0:
            print(f"  {i}/{len(bundle_files)}...")
        try:
            with open(path, "r", encoding="utf-8") as f:
                bundle = json.load(f)
            feat = extract_features(bundle, path.name)
            rows.append(feat)
        except Exception as e:
            errors.append({"filename": path.name, "error": str(e)})

    if errors:
        print(f"  [WARN] {len(errors)} parse errors:")
        for err in errors:
            print(f"    {err['filename']}: {err['error']}")

    print(f"[Phase 1] Done. {len(rows)} records extracted, {len(errors)} errors.")
    return rows


# ---------------------------------------------------------------------------
# Phase 1 — Summary statistics
# ---------------------------------------------------------------------------
def build_summary(rows: list[dict]) -> dict:
    n = len(rows)

    def safe_mean(vals):
        vals = [v for v in vals if v is not None]
        return sum(vals) / len(vals) if vals else None

    def safe_pct(vals, key):
        return round(100 * sum(1 for r in vals if r.get(key)) / n, 2)

    stations = defaultdict(int)
    severities = defaultdict(int)
    seasons = defaultdict(int)
    years = defaultdict(int)

    for r in rows:
        stations[r["station_id"]] += 1
        severities[r["severity"]] += 1
        seasons[r["season"]] += 1
        if r["year"]:
            years[str(r["year"])] += 1

    evidence_scores = [r["evidence_score"] for r in rows]
    peak_pm25_vals = [r["peak_pm25"] for r in rows if r["peak_pm25"] is not None]
    duration_vals = [r["duration_hours"] for r in rows if r["duration_hours"] is not None]

    return {
        "total_bundles": n,
        "station_counts": dict(sorted(stations.items())),
        "severity_counts": dict(sorted(severities.items())),
        "season_counts": dict(sorted(seasons.items())),
        "year_counts": dict(sorted(years.items())),
        "evidence_score": {
            "mean": round(safe_mean(evidence_scores), 3) if safe_mean(evidence_scores) else None,
            "min": min(evidence_scores) if evidence_scores else None,
            "max": max(evidence_scores) if evidence_scores else None,
            "distribution": {
                str(s): sum(1 for v in evidence_scores if v == s)
                for s in range(11)
            },
        },
        "peak_pm25": {
            "mean": round(safe_mean(peak_pm25_vals), 2) if peak_pm25_vals else None,
            "min": round(min(peak_pm25_vals), 2) if peak_pm25_vals else None,
            "max": round(max(peak_pm25_vals), 2) if peak_pm25_vals else None,
        },
        "duration_hours": {
            "mean": round(safe_mean(duration_vals), 2) if duration_vals else None,
            "min": min(duration_vals) if duration_vals else None,
            "max": max(duration_vals) if duration_vals else None,
        },
        "availability_pct": {
            "has_pm25": safe_pct(rows, "has_pm25"),
            "has_pm10": safe_pct(rows, "has_pm10"),
            "has_no2": safe_pct(rows, "has_no2"),
            "has_temp": safe_pct(rows, "has_temp"),
            "has_rh": safe_pct(rows, "has_rh"),
            "has_ws": safe_pct(rows, "has_ws"),
            "has_pblh": safe_pct(rows, "has_pblh"),
            "has_wind_dir": safe_pct(rows, "has_wind_dir"),
            "has_nwp_any": safe_pct(rows, "nwp_any"),
            "has_s5p": safe_pct(rows, "has_s5p"),
            "has_fire": safe_pct(rows, "has_fire"),
            "fire_positive": safe_pct(rows, "fire_positive"),
            "has_owbeii": safe_pct(rows, "has_owbeii"),
            "owbeii_positive": safe_pct(rows, "owbeii_positive"),
        },
        "conflict_counts": {
            "trapped_event": sum(1 for r in rows if r["trapped_event"]),
            "unexplained_source": sum(1 for r in rows if r["unexplained_source"]),
            "conflict_high_rh_high_ws": sum(1 for r in rows if r["conflict_high_rh_high_ws"]),
            "conflict_fire_high_ws": sum(1 for r in rows if r["conflict_fire_high_ws"]),
            "any_conflict": sum(1 for r in rows if r["conflict_count"] > 0),
        },
    }


# ---------------------------------------------------------------------------
# Phase 2 — Stratified sampling
# ---------------------------------------------------------------------------
def stratified_sample(rows: list[dict], n_target: int, rng: random.Random) -> list[dict]:
    """
    Produces a deterministic stratified sample of n_target bundles.

    Strata (priority order, no duplicates):
      A — Diversity stratum: one representative per (station × severity × season)
      B — Evidence richness: full evidence_score == 10 bundles
      C — Conflict/ambiguous: highest conflict_count bundles
      D — Edge cases: extreme duration or extreme peak_pm25
      E — Temporal coverage: one per (station × year) not yet included
      F — Random fill: remaining slots filled randomly from remainder
    """
    selected_ids: set[str] = set()
    selected: list[dict] = []

    def add(candidates: list[dict]):
        for r in candidates:
            if r["event_id"] not in selected_ids and len(selected) < n_target:
                selected_ids.add(r["event_id"])
                selected.append(r)

    # --- Stratum A: diversity grid (station × severity × season) ---
    grid: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        key = (r["station_id"], r["severity"], r["season"])
        grid[key].append(r)

    # For each cell pick the highest evidence_score bundle (deterministic: sort then take first)
    for key in sorted(grid.keys()):
        cell = sorted(grid[key], key=lambda r: (-r["evidence_score"], r["event_id"]))
        add([cell[0]])

    # --- Stratum B: evidence-richest bundles ---
    rich = sorted(
        [r for r in rows if r["evidence_score"] >= 8],
        key=lambda r: (-r["evidence_score"], -r["severity_rank"], r["event_id"])
    )
    add(rich[:max(0, n_target // 5)])

    # --- Stratum C: conflict / ambiguous bundles ---
    conflict = sorted(
        [r for r in rows if r["conflict_count"] > 0],
        key=lambda r: (-r["conflict_count"], -r["severity_rank"], r["event_id"])
    )
    add(conflict[:max(0, n_target // 10)])

    # --- Stratum D: edge cases ---
    # Longest events
    longest = sorted(
        [r for r in rows if r["duration_hours"] is not None],
        key=lambda r: (-r["duration_hours"], r["event_id"])
    )
    add(longest[:5])

    # Highest peak PM2.5
    highest_pm25 = sorted(
        [r for r in rows if r["peak_pm25"] is not None],
        key=lambda r: (-r["peak_pm25"], r["event_id"])
    )
    add(highest_pm25[:5])

    # Single-hour events (shortest)
    shortest = sorted(
        [r for r in rows if r["duration_hours"] == 1],
        key=lambda r: (r["severity_rank"], r["event_id"])
    )
    add(shortest[:3])

    # --- Stratum E: temporal coverage (station × year) ---
    year_grid: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        if r["year"] is not None:
            year_grid[(r["station_id"], r["year"])].append(r)

    for key in sorted(year_grid.keys()):
        cell = sorted(year_grid[key], key=lambda r: (-r["evidence_score"], r["event_id"]))
        add([cell[0]])

    # --- Stratum F: random fill ---
    remaining = [r for r in rows if r["event_id"] not in selected_ids]
    shuffled = sorted(remaining, key=lambda r: r["event_id"])  # stable sort before shuffle
    rng.shuffle(shuffled)
    add(shuffled)

    result = selected[:n_target]
    return result


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------
def write_markdown_profile(summary: dict, output_path: Path) -> None:
    lines = [
        "# VayuNet Evidence Bundle — Dataset Profile",
        "",
        f"**Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        f"**Total bundles**: {summary['total_bundles']:,}",
        "",
        "---",
        "",
        "## Station Distribution",
        "",
        "| Station | Count |",
        "|---------|-------|",
    ]
    for s, c in sorted(summary["station_counts"].items()):
        lines.append(f"| {s} | {c:,} |")

    lines += [
        "",
        "## Severity Distribution",
        "",
        "| Severity | Count |",
        "|----------|-------|",
    ]
    for sv, c in sorted(summary["severity_counts"].items()):
        lines.append(f"| {sv} | {c:,} |")

    lines += [
        "",
        "## Season Distribution",
        "",
        "| Season | Count |",
        "|--------|-------|",
    ]
    for s, c in sorted(summary["season_counts"].items()):
        lines.append(f"| {s} | {c:,} |")

    lines += [
        "",
        "## Year Distribution",
        "",
        "| Year | Count |",
        "|------|-------|",
    ]
    for y, c in sorted(summary["year_counts"].items()):
        lines.append(f"| {y} | {c:,} |")

    ep = summary["event_periods"] = {}  # placeholder, computed inline below
    ps = summary["peak_pm25"]
    dur = summary["duration_hours"]
    ev = summary["evidence_score"]

    lines += [
        "",
        "## Event Magnitude",
        "",
        f"| Metric | Min | Mean | Max |",
        f"|--------|-----|------|-----|",
        f"| Peak PM2.5 (µg/m³) | {ps['min']} | {ps['mean']} | {ps['max']} |",
        f"| Duration (hours) | {dur['min']} | {dur['mean']} | {dur['max']} |",
        f"| Evidence score (0–10) | {ev['min']} | {ev['mean']} | {ev['max']} |",
        "",
        "## Evidence Availability",
        "",
        "| Evidence Type | % Present |",
        "|--------------|-----------|",
    ]
    for field, pct in summary["availability_pct"].items():
        lines.append(f"| {field} | {pct}% |")

    lines += [
        "",
        "## Evidence Score Distribution",
        "",
        "| Score | Count |",
        "|-------|-------|",
    ]
    for s, c in sorted(summary["evidence_score"]["distribution"].items(), key=lambda x: int(x[0])):
        lines.append(f"| {s} | {c:,} |")

    cc = summary["conflict_counts"]
    lines += [
        "",
        "## Conflict / Edge-Case Indicators",
        "",
        "| Indicator | Count |",
        "|-----------|-------|",
        f"| Trapped events (severe + PBLH<300) | {cc['trapped_event']:,} |",
        f"| Unexplained source (peak>300, no fire/OWBEII) | {cc['unexplained_source']:,} |",
        f"| High RH + High WS conflict | {cc['conflict_high_rh_high_ws']:,} |",
        f"| Fire + High WS (transport) | {cc['conflict_fire_high_ws']:,} |",
        f"| Any conflict | {cc['any_conflict']:,} |",
    ]

    output_path.write_text("\n".join(lines), encoding="utf-8")


def write_candidate_manifest(candidates: list[dict], output_path: Path, n: int) -> None:
    manifest = {
        "generated_utc": datetime.utcnow().isoformat(),
        "random_seed": RANDOM_SEED,
        "target_size": n,
        "actual_size": len(candidates),
        "candidates": [r["event_id"] for r in candidates],
        "candidate_details": [
            {
                "event_id": r["event_id"],
                "filename": r["filename"],
                "station_id": r["station_id"],
                "severity": r["severity"],
                "season": r["season"],
                "year": r["year"],
                "evidence_score": r["evidence_score"],
                "conflict_count": r["conflict_count"],
                "peak_pm25": r["peak_pm25"],
                "duration_hours": r["duration_hours"],
            }
            for r in candidates
        ],
    }
    output_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("VAYUNET — FILTER_6452_EVIDENCE_BUNDLES")
    print("NO LLM. NO BUNDLE MODIFICATION. READ-ONLY.")
    print("=" * 70)

    # Collect all bundle files
    bundle_files = sorted(BUNDLE_DIR.glob("*.json"))
    print(f"Found {len(bundle_files)} bundle files in {BUNDLE_DIR}")

    if len(bundle_files) == 0:
        print("ERROR: No bundle files found. Check BUNDLE_DIR path.")
        sys.exit(1)

    # Phase 1 — Extract features
    rows = phase1_profile(bundle_files)

    # Save raw profile JSON
    profile_json_path = OUTPUT_DIR / "dataset_profile.json"
    with open(profile_json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
    print(f"[Phase 1] Raw profile saved: {profile_json_path}")

    # Build and save summary
    summary = build_summary(rows)
    summary_json_path = OUTPUT_DIR / "dataset_summary.json"
    with open(summary_json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"[Phase 1] Summary saved: {summary_json_path}")

    # Save markdown profile
    md_path = OUTPUT_DIR / "dataset_profile.md"
    write_markdown_profile(summary, md_path)
    print(f"[Phase 1] Markdown profile saved: {md_path}")

    # Phase 2 — Stratified sampling
    print()
    print("[Phase 2] Stratified candidate set generation...")
    rng = random.Random(RANDOM_SEED)

    for n_target in CANDIDATE_SIZES:
        # Re-seed identically per run for reproducibility
        rng_n = random.Random(RANDOM_SEED + n_target)
        candidates = stratified_sample(rows, n_target, rng_n)
        out_path = OUTPUT_DIR / f"candidates_{n_target}.json"
        write_candidate_manifest(candidates, out_path, n_target)
        print(f"  candidates_{n_target}.json — {len(candidates)} bundles selected")

        # Quick stratum breakdown
        sev_counts = defaultdict(int)
        season_counts = defaultdict(int)
        station_counts = defaultdict(int)
        for c in candidates:
            sev_counts[c["severity"]] += 1
            season_counts[c["season"]] += 1
            station_counts[c["station_id"]] += 1
        print(f"    Severity: {dict(sev_counts)}")
        print(f"    Seasons:  {dict(season_counts)}")
        print(f"    Stations: {dict(station_counts)}")

    print()
    print("=" * 70)
    print("COMPLETE. All outputs written to:")
    print(f"  {OUTPUT_DIR}")
    print("=" * 70)
    print()
    print("Outputs:")
    for p in sorted(OUTPUT_DIR.glob("*")):
        size_kb = round(p.stat().st_size / 1024, 1)
        print(f"  {p.name} ({size_kb} KB)")


if __name__ == "__main__":
    main()
