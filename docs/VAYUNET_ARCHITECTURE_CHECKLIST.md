# VayuNet Architecture Checklist

**Purpose:** Implementation-alignment checklist. Use this to verify that the VayuNet implementation remains aligned with the frozen eight-stage architecture defined in [`docs/architecture.md`](./architecture.md).

**This checklist is not a claim of completion.** Only mark `[x]` when repository evidence explicitly supports it. Use `[~]` for planned or partially implemented components.

---

## Status Legend

| Symbol | Meaning |
|--------|---------|
| `[x]` | Verified / implemented — backed by repository evidence |
| `[~]` | Planned or partially implemented |
| `[ ]` | Not yet verified / not implemented |

> **Evidence rule:** `[x]` means the implementation has been verified against repository code, configuration, tests, validated outputs, or other concrete repository evidence. The checklist itself is not evidence. If evidence cannot be identified, use `[~]` or `[ ]`.

> **Rule:** Do not automatically mark anything `[x]`. Every `[x]` must be traceable to actual code, configuration, or validated output in the repository.

---

## 0. Architecture Governance

- [ ] Eight-stage architecture remains unchanged (OBSERVE → FUSE → COUPLED ATMOSPHERE → AI/ML → ENVIRONMENTAL INTELLIGENCE → EVIDENCE VERIFICATION → ACTION → VALIDATE)
- [ ] No ninth stage has been introduced
- [ ] All new components are mapped to an existing stage, not added as a new stage
- [ ] Architecture changes are explicitly reviewed and documented before modification
- [ ] `docs/architecture.md` and this checklist remain synchronised
- [ ] Implementation status labels (`[IMPLEMENTED]`, `[PARTIAL]`, `[PLANNED]`) in the architecture document are accurate and up to date

---

## 1. OBSERVE — Data & Observations

### Ground Observations
- [x] CPCB / CAAQMS data ingestion
  Evidence: `backend/services/evidence_retriever.py` → `retrieve_cpcb_evidence()` reads per-station CSV files from `backend/data/raw/delhi/`; `backend/services/sensor_data.py` → `load_cpcb_data()` used in `main.py`
- [x] PM2.5
  Evidence: `evidence_retriever.py` L167 — `pm2.5`/`pm25` column matched and ingested; `sensor_data.py` L41 — `pm2_5` kept; `schemas/evidence.py` `PollutantObservation`
- [x] PM10
  Evidence: `evidence_retriever.py` L175 — PM10 column matched; `sensor_data.py` L42
- [~] O₃
  Evidence: `sensor_data.py` L42 `keep_cols` includes only `pm2_5`, `pm10`, `no2`, `co` — **O₃ is not ingested or used in any evidence path**. Referenced in `models.py Forecast` and architecture doc only. No O₃ sub-index code found.
- [x] NO₂
  Evidence: `evidence_retriever.py` L183 — `no2` column matched and ingested as `PollutantObservation`; `schemas/evidence_bundle_input_schema.py` `PollutionDynamics.no2`

### Weather & NWP
- [x] Temperature
  Evidence: `evidence_retriever.py` L276 — `temperature_2m` from ERA5 archive or Open-Meteo live; `schemas/evidence.py` `WeatherEvidence.temperature_c`
- [x] Wind speed / direction
  Evidence: `evidence_retriever.py` L278–L280 — `wind_speed_10m`, `wind_direction_10m` ingested
- [x] Relative humidity
  Evidence: `evidence_retriever.py` L277 — `relative_humidity_2m`
- [x] Atmospheric pressure
  Evidence: `evidence_retriever.py` L280 — `surface_pressure` ingested
- [~] Planetary Boundary Layer Height
  Evidence: `evidence_retriever.py` L281 — `boundary_layer_height` field ingested from ERA5 archive **when available** (field is `Optional[float]`; Open-Meteo live path explicitly sets it to `None`). Present in schema but not guaranteed populated.
- [~] Meteorological boundary / forcing data (for Stage 3)
  Evidence: Documented in `backend/reports/sih26082/wrfchem_final_prebenchmark_correction_audit.md` (NCEP FNL / GFS strategy). **No Python code constructs or downloads BC files at runtime.** Configuration and script-level only.

### Satellite
- [x] Sentinel-5P ingest
  Evidence: `evidence_retriever.py` → `retrieve_sentinel5p_evidence()` calls `services/satellite.py:get_sentinel5p_features()`; `services/satellite.py` exists
- [x] Tropospheric NO₂
  Evidence: `evidence_retriever.py` L328 — `no2_index` mapped to `Sentinel5PEvidence.no2_column_number_density`; `schemas/evidence.py`
- [x] UV Aerosol Index
  Evidence: `evidence_retriever.py` L329 — `aerosol_index` mapped to `absorbing_aerosol_index`
- [ ] Other Earth-observation products
  No additional EO products (MODIS, VIIRS reflectance, etc.) are ingested.

### Fire & Emissions
- [x] NASA FIRMS fire data retrieval
  Evidence: `evidence_retriever.py` → `retrieve_firms_evidence()` reads `backend/data/raw/firms_viirs.csv`; fires within radius and time window retrieved and structured as `FIRMSEvidence`
- [x] Fire timing and location
  Evidence: `evidence_retriever.py` L443–L451 — `detection_time`, `latitude`, `longitude`, `dist_km` per record
- [x] Fire Radiative Power (FRP)
  Evidence: `evidence_retriever.py` L441 — `frp` field read; `schemas/evidence.py` `FIRMFireRecord.frp`; `max_frp` aggregated. **Note:** FRP is read as-is; no parameterisation to emission rate is implemented. Correctly not claimed as source apportionment.
- [~] Regional emission inventories
  Evidence: OWBEII static open-waste-burning inventory ingested via `retrieve_owbeii_evidence()` (`Wasteburned.txt`). Anthropogenic sector inventories (industrial, transport, power, residential, construction) not yet ingested into the live evidence pipeline. Documented in SIH26082 reports.

### Citizen Observations
- [x] Photo ingestion
  Evidence: `routers/reports.py` L37 `photo: UploadFile`; `services/report_validator.py` validates magic bytes; `main.py` saves photo to temp dir and passes to `extract_evidence()`
- [~] Voice (transcription pipeline)
  Evidence: `main.py` L58 accepts `text` form field described as "voice/text". `report/page.tsx` shows Hindi placeholder text as a textarea, **not** a live voice capture. No `SpeechRecognition`, Web Speech API, or STT service code is present anywhere. Voice text is accepted as pre-transcribed text input only — there is **no transcription pipeline in the implementation**.
- [x] Text
  Evidence: `routers/reports.py` L57 `text: Optional[str]`; `services/report_validator.py:validate_text()`; `services/gemini_evidence.py` uses text in prompt
- [x] Location
  Evidence: `routers/reports.py` L41–L52 `latitude`/`longitude` validated; `schemas/report.py LocationCoords`
- [x] Timestamp
  Evidence: `routers/reports.py` L53 `timestamp: str`; `services/report_validator.py:validate_timestamp()`

### Historical & Contextual Data
- [~] Historical pollution observations
  Evidence: CPCB historical CSVs exist in `backend/data/raw/delhi/` (used for training). Evidence retriever applies causality filter against this archive (`evidence_retriever.py` L131). However, live-report evidence path retrieves only the most recent **causal** observation per station — it is not a separate historical-context retrieval step.
- [~] Emission inventory baselines by sector
  Evidence: OWBEII implemented (`retrieve_owbeii_evidence()`). Sector-level baselines (industrial, transport, power, residential, construction, biomass) not ingested in the live evidence pipeline.

---

## 2. FUSE & ASSIMILATE — Data Engineering & Assimilation

- [x] Data quality control
  Evidence: `evidence_retriever.py` — causality filter (future-obs rejection), latency-based `DataAvailability` status; `services/report_validator.py` — photo magic-byte + size validation, timestamp format validation
- [x] Missing / stale-data handling
  Evidence: `evidence_retriever.py` — `DataAvailability.MISSING` / `STALE` returned per source; downstream code handles `None`/`MISSING` gracefully
- [x] Spatial alignment
  Evidence: `evidence_retriever.py` — Haversine distance used to find nearest CPCB station and nearest FIRMS fires; `services/geo_utils.py:haversine_distance()`
- [x] Temporal alignment
  Evidence: `evidence_retriever.py` — per-source causality filter enforced before selecting records
- [~] Deduplication
  Evidence: duplicate relationships can be represented through `models.py Correlation.duplicate_of` and contradictions can be detected, but no active event-level deduplication service was verified.
- [x] Feature engineering
  Evidence: `backend/ml/` — multiple feature-builder scripts (`build_nwp_features.py`, `build_satellite_features.py`, `episode_feature_builder.py`, etc.); `sensor_data.py:calculate_sensor_anomaly()` computes z-score feature
- [x] Multi-source data fusion
  Evidence: `services/fusion.py:calculate_event_confidence()` — weighted_fusion_v1 formula; `main.py` L131–L136 orchestrates all source scores
- [~] Emission-inventory preprocessing (disaggregation, spatial allocation, speciation)
  Evidence: SIH26082 reports document FINN → fire_emis chain and EDGAR/CAMS → anthro_emis. **No Python preprocessing code in the repo currently executes this pipeline.** Documented plan only.
- [~] Model state preparation (observations → initial conditions)
  Evidence: B0/B1 WRF-Chem benchmarks verified in `wrfchem_final_prebenchmark_correction_audit.md`. No automated IC-generation code in repo.
- [~] Boundary-condition preparation (global NWP → WRF-Chem lateral BCs)
  Evidence: Strategy documented in SIH26082 reports (GFS forecast data required for operational runs). Not automated in code.
- [ ] DA / FDDA status explicitly documented as: `implemented` / `planned` / `not applicable`
  No DA/FDDA code or explicit status declaration found in the repository.

---

## 3. COUPLED ATMOSPHERE — WRF-Chem

- [~] WRF-Chem / coupled atmospheric model (domain configured; automated cycle not yet operational)
  Evidence: `backend/reports/sih26082/wrfchem_final_prebenchmark_correction_audit.md` — B0 (infrastructure smoke test) and B1 (chemistry + biomass, chem_opt=2) benchmarks completed. B1 successfully generated a valid 18 MB NetCDF `wrfout` file. B2 (full SIH26082 physics with `chem_opt=202`, aerosol-radiation feedback) not yet complete. No automated WRF-Chem cycle code is in the Python backend.
- [~] Delhi NCR nested domain (outer regional + inner high-resolution)
  Evidence: SIH26082 reports describe nested D01/D02 domain strategy. B0/B1 used D01 only. Full nested configuration not benchmarked.
- [~] Meteorology module (temperature, wind, pressure, humidity, radiation, PBL, inversion)
  Evidence: Documented in SIH26082 architecture and feasibility reports. WRF met output produced in B0/B1 smoke tests.
- [~] Chemistry module (PM2.5, PM10, O₃, NOx, VOCs, aerosols)
  Evidence: `chem_opt=2` (RADM2 chemistry only) validated in B1 smoke test. `chem_opt=202` (MOZART-MOSAIC+AQCHEM, the SIH target) is defined but not yet benchmarked end-to-end.
- [~] Emission injection (inventory emissions + FIRMS fire)
  Evidence: FINN → fire_emis chain documented; B1 configured with `biomass_burn_opt=2`. Full CAMS/EDGAR anthropogenic inventory preprocessing not yet automated.
- [~] Transport (advection)
  Evidence: WRF-Chem transport runs in B0/B1. Full SIH-fidelity transport not validated.
- [~] Diffusion / mixing
  Evidence: As above — runs in B0/B1 smoke test.
- [~] Chemical transformation
  Evidence: B1 with `chem_opt=2` (RADM2) tested. `chem_opt=202` not yet validated.
- [~] Dry and wet deposition
  Evidence: Included in WRF-Chem framework used in B0/B1, not independently validated.
- [~] Meteorology ↔ chemistry two-way coupling
  Evidence: Architecture-level: `aer_ra_feedback=1` configuration documented in SIH26082 audit. B2 (`aer_ra_feedback` A/B comparison) not yet run.
- [~] Aerosol–radiation–PBL feedback
  Evidence: Configuration documented; B2 experiment to validate not yet executed.
- [~] Global NWP boundary conditions (ERA5 / GFS or equivalent)
  Evidence: NCEP FNL strategy documented for retrospective runs; GFS for operational. No automated BC download/prep code in repo.
- [ ] WRF-Chem scientific validation against CPCB observations complete
  No WRF-Chem vs CPCB validation output found. B2+ not yet run.

---

## 4. AI/ML INTELLIGENCE

### Forecast Enhancement
- [~] Bias correction of WRF-Chem output
  Evidence: `ml/forecast_service.py` — XGBoost 6h/24h/72h models trained on CPCB-observed PM2.5 (data-driven). The service loads trained `.joblib` models (`xgb_weather_pm25_*_tuned.joblib` confirmed present in `backend/models/`). However, these models are trained directly on observations — **not applied as post-processors to WRF-Chem output fields**. WRF-Chem output is not yet fed into the bias-correction pipeline.
- [~] Forecast refinement
  Evidence: Multiple training experiments (`s5`, `s6` production models) in `backend/ml/`. Models are trained; the refinement pipeline is not connected to WRF-Chem output.
- [ ] Statistical downscaling
  No downscaling code found.
- [x] Forecast anomaly / spike detection
  Evidence: `ml/forecast_service.py:_calculate_spike_risk()` — heuristic spike-risk label (LOW/MEDIUM/HIGH) based on forecasted PM2.5 max. `ml/pollution_event_detector.py` — event detection over observed PM2.5 series (≥150 µg/m³ threshold). Explicitly labelled `is_heuristic: True` in output.

### Observational Intelligence
- [x] Pollution anomaly detection
  Evidence: `services/sensor_data.py:calculate_sensor_anomaly()` — z-score clipped to [0,1]; used in `main.py` weighted_fusion_v1
- [x] Unusual pollutant combination detection
  Evidence: `evidence_retriever.py:detect_conflicts()` — three heuristic checks comparing PM2.5 vs wind speed, PM2.5 vs fire counts, PM2.5 vs satellite aerosol index
- [x] Cross-source inconsistency detection
  Evidence: `services/fusion.py:identify_supporting_contradicting()` — flags which source scores fall below threshold; `evidence_retriever.py:detect_conflicts()` raises explicit conflict notes

### Environmental Computer Vision
- [~] CV model exists and has been trained as a validation-selected experimental candidate
  Evidence: `cv-datasets/models/v3_12_candidate_A_best.pt` exists and has a documented validation macro F1 of 0.8343. Candidate A has not yet received its authorized locked-test evaluation. The original V3.6 R0 checkpoint binary was lost, so Candidate A must not be described as the historical R0 model.
- [ ] Image relevance classification
- [x] Smoke classification
  Evidence: Model outputs a probability for `smoke`.
- [x] Dust classification
  Evidence: Model outputs a probability for `dust`.
- [ ] Open burning classification
- [ ] Plume classification
- [ ] Industrial source classification
- [x] Construction activity classification
  Evidence: Model outputs a probability for `construction_activity`.
- [x] CV outputs are deterministic / structured before downstream reasoning (not raw embeddings)
  Evidence: The model output is a 3-class probability vector.
- [ ] CV integrated into evidence pipeline (Stage 6)

### Event Intelligence
- [x] Pollution-event detection
  Evidence: `ml/pollution_event_detector.py` — segment-based detection on PM2.5 ≥ 150 µg/m³; produces `pollution_events.csv`
- [x] Event classification
  Evidence: `ml/pollution_event_detector.py` L42 — `SEVERE_EVENT` (≥250) / `POLLUTION_EVENT` (≥150); `schemas/investigator_output_schema.py SeverityLevel`
- [x] Risk scoring
  Evidence: `services/fusion.py:calculate_event_confidence()` — LOW / MODERATE / HIGH confidence levels; `ml/forecast_service.py:_calculate_spike_risk()` — spike risk levels; `models.py VayuNetPollutionEvent.risk` — four-level CRITICAL/HIGH/MODERATE/LOW
- [x] Evidence prioritisation
  Evidence: `services/fusion.py` — weighted_fusion_v1 weights (sensor 0.35, citizen 0.30, weather 0.20, satellite 0.15) reflect deliberate priority ordering; anti-abuse cap enforced

---

## 5. ENVIRONMENTAL INTELLIGENCE — Delhi NCR

### Atmospheric Inversion Intelligence
- [~] Inversion strength diagnosis (from WRF-Chem output)
  Evidence: Documented in `sih26082_architecture.md` and B2 experiment plan. Not implemented in Python backend; WRF-Chem B2 not run yet.
- [~] Inversion height diagnosis
  Evidence: Same as above.
- [~] PBL / mixing layer analysis
  Evidence: PBLH is a field in `schemas/evidence.py WeatherEvidence.boundary_layer_height_m` (ingested from ERA5 archive when available). Diagnosis of inversion from WRF-Chem output not implemented.
- [~] Atmospheric stability indicators
  Evidence: Not implemented as a dedicated module. PBLH + ventilation status assessed in investigator schema (`schemas/investigator_output_schema.py VentilationStatus`, `InversionRisk`).

### Stubble-Burning Intelligence
- [x] FIRMS fire detection integrated
  Evidence: `evidence_retriever.py:retrieve_firms_evidence()` — VIIRS archive read, spatial + temporal filter, structured as `FIRMSEvidence`
- [x] FRP evidence handling
  Evidence: `evidence_retriever.py` L441 — FRP read and `max_frp` computed; `schemas/evidence.py FIRMFireRecord.frp`
- [~] FRP → potential emission signal (parameterised, not assumed exact)
  Evidence: FRP ingested as-is; no FINN-style FRP → emission-rate parameterisation implemented in Python. Correctly **not** claimed as emission quantity in any output schema.
- [~] Transport conditions from WRF-Chem
  Evidence: Wind/PBLH conditions from ERA5/Open-Meteo weather retrieval used as proxy. WRF-Chem transport fields not yet connected.
- [~] Plume / impact analysis
  Evidence: Heuristic conflict note raised when PM2.5 is high but zero fires detected (`detect_conflicts()` L546–L551). No plume-dispersion model implemented.

### Pollution Transport Analysis
- [~] Wind-driven transport pathway analysis
  Evidence: Wind speed and direction ingested (`WeatherEvidence`). `schemas/investigator_output_schema.py WindTransportRegime` enum (STAGNANT / LOCAL_CIRCULATION / REGIONAL_ADVECTION) produced by LLM investigator based on evidence bundle — **not** from a physical transport model.
- [~] Plume movement indicators
  Evidence: As above — schema-level classification, not model-derived.
- [~] Regional influence indicators
  Evidence: As above.
- [ ] Transport analysis clearly labelled — NOT quantitative source apportionment
  Requires explicit runtime label or disclaimer on any output claiming transport pathway. Not enforced in current code output.

### AQI Engine
- [~] PM2.5 sub-index
  Evidence: No AQI sub-index calculation code found in `backend/services/`. PM2.5 forecasts exist (XGBoost models). AQI as CPCB-standard breakpoint sub-index **is not implemented**. PM2.5 values are used directly.
- [~] PM10 sub-index
  Evidence: Same — PM10 ingested and forecasted but CPCB AQI sub-index not computed.
- [ ] O₃ sub-index
  No O₃ ingestion or AQI sub-index code found.
- [~] AQI composite
  Evidence: `models.py Forecast` has `spike_probability` Literal; `forecast_service.py` returns spike risk. **No CPCB-formula AQI composite number computed.** AQI bucket labels appear only in `inspect_cpcb.py` as test scaffolding.
- [x] 6h forecast
  Evidence: `ml/forecast_service.py` — XGBoost `6h` model loaded (`xgb_weather_pm25_6h_tuned.joblib` confirmed in `backend/models/`); `models.py Forecast.pm25_6h`
- [x] 24h forecast
  Evidence: `ml/forecast_service.py` — XGBoost `24h` model; `xgb_weather_pm25_24h_tuned.joblib` present
- [x] 72h forecast
  Evidence: `ml/forecast_service.py` — XGBoost `72h` model; `xgb_weather_pm25_72h_tuned.joblib` present

### Risk & Event Assessment
- [x] Pollution spike prediction
  Evidence: `ml/forecast_service.py:_calculate_spike_risk()` — heuristic spike-risk (LOW/MEDIUM/HIGH) based on max forecasted PM2.5; explicitly labelled `is_heuristic: True`
- [x] Exposure severity scoring
  Evidence: `schemas/investigator_output_schema.py PublicHealthExposure` — `risk_level: PublicHealthRiskLevel` (MODERATE/POOR/VERY_POOR/SEVERE/EMERGENCY); `PublicHealthRiskLevel` enum verified in use in `ml/test_investigator_schema.py`
- [x] Event status classification
  Evidence: `ml/pollution_event_detector.py` — POLLUTION_EVENT / SEVERE_EVENT; `schemas/investigator_output_schema.py SeverityLevel`; `models.py AuthorityResponse.status` — full lifecycle (pending → acknowledged → investigating → confirmed → dismissed → resolved)
- [x] Confidence grading
  Evidence: `services/fusion.py:calculate_event_confidence()` — LOW / MODERATE / HIGH; `schemas/investigator_output_schema.py ConfidenceLevel`; `models.py Detection.confidence`

---

## 6. EVIDENCE VERIFICATION

### Citizen Report Ingestion
- [x] Citizen report received
  Evidence: `routers/reports.py POST /api/v1/reports` — full validation and `report_id` generation
- [x] Photo processed
  Evidence: `services/report_validator.py:validate_and_extract_photo()` — magic-byte check, size limit, metadata extraction; `services/gemini_evidence.py:extract_evidence()` — image bytes sent to Gemini
- [x] Text processed
  Evidence: `services/report_validator.py:validate_text()` — strip and XSS sanitise; used in Gemini prompt
- [~] Voice transcribed
  Evidence: No STT transcription code exists. Text input accepts pre-typed multilingual text including Hindi. Voice is passed as plain text; no Web Speech API or Cloud STT integration found.

### Evidence Retrieval
- [x] Deterministic evidence retrieval (not LLM-generated)
  Evidence: `evidence_retriever.py:build_evidence_package()` — all five sources (CPCB, weather, Sentinel-5P, FIRMS, OWBEII) retrieved deterministically before any LLM call; `routers/reports.py` — evidence and LLM endpoints are separate routes
- [x] Environmental evidence package assembled before LLM call
  Evidence: `routers/reports.py POST /reports/{id}/evidence` retrieves the package; `routers/reports.py` doc comment: "Does NOT call Gemini or generate AI verdicts"
- [x] CPCB sensor observations included
  Evidence: `evidence_retriever.py:retrieve_cpcb_evidence()` → `CPCBStationEvidence`
- [x] Weather conditions included
  Evidence: `evidence_retriever.py:retrieve_weather_evidence()` → `WeatherEvidence`
- [~] NWP / WRF-Chem model outputs included
  Evidence: `schemas/evidence_bundle_input_schema.py NWP` — `forecast_6h/24h/72h` fields exist. However: (a) these are **XGBoost ML forecasts**, not WRF-Chem outputs; (b) the `grounding_validator.py` explicitly handles `nwp_missing = True` as a common case; (c) the investigator prompt (L30) requires the LLM to acknowledge missing NWP and not fabricate forecasts. NWP from WRF-Chem is not connected to the live evidence pipeline.
- [x] Sentinel-5P satellite data included
  Evidence: `evidence_retriever.py:retrieve_sentinel5p_evidence()` → `Sentinel5PEvidence`
- [x] FIRMS fire data included
  Evidence: `evidence_retriever.py:retrieve_firms_evidence()` → `FIRMSEvidence`
- [~] Historical / contextual evidence included
  Evidence: OWBEII static emissions inventory included (`retrieve_owbeii_evidence()`). Historical CPCB time-series is used as the archive for causal-obs lookup. No separate "historical context bundle" is assembled beyond the nearest causal observation per source.

### Reasoning & Verdict
- [~] CV evidence included in package
  No CV model is trained or deployed. No CV output field in `EvidencePackage`.
- [x] Grounded LLM reasoning (Gemini)
  Evidence: `ml/pollution_investigator.py:investigate_event()` — Gemini structured output with `PollutionEventInvestigationReport` schema; `services/gemini_evidence.py:extract_evidence()` — Gemini multimodal for citizen reports
- [x] SUPPORTED verdict
  Evidence: `ml/run_gemma4_benchmark.py` L41 — `SUPPORTED` literal used in benchmark schema; LLM verdict enum in benchmark scripts
- [x] NOT_SUPPORTED verdict
  Evidence: `ml/run_gemma4_benchmark.py` L42 — `NOT_SUPPORTED` used
- [x] INCONCLUSIVE verdict
  Evidence: `ml/run_gemma4_benchmark.py` L333 — "Allowed verdicts: SUPPORTED, NOT_SUPPORTED, INCONCLUSIVE"

  **Note:** SUPPORTED/NOT_SUPPORTED/INCONCLUSIVE are used in benchmark evaluation scripts, not yet as an explicit `verdict` field in the `EvidencePackage` or a production API response schema.

- [x] Confidence score attached to verdict
  Evidence: `schemas/investigator_output_schema.py ConfidenceLevel` in `HypothesisEvaluation`; `CitizenGeminiOutput.confidence` float in `services/gemini_evidence.py`
- [x] Structured explanation attached to verdict
  Evidence: `schemas/investigator_output_schema.py PollutionEventInvestigationReport.synthesis_narrative`; `services/gemini_evidence.py CitizenGeminiOutput.description`

### Quality & Safety
- [~] Human review gate implemented

  Evidence: `models.py CitizenGeminiOutput.needs_human_review: bool` provides a
  human-review flag for ambiguous/low-confidence cases. However, there is no
  dedicated human-review queue, routing workflow, or production review UI.
- [x] No unsupported causal claims in verdict
  Evidence: `schemas/investigator_output_schema.py:check_non_causal_language()` — Pydantic `field_validator` rejects FORBIDDEN_CAUSAL_PHRASES in `supporting_evidence` and `contrasting_evidence`; `check_narrative_causality()` validates `synthesis_narrative`; `ml/grounding_validator.py:GroundingValidator` — additional runtime causal-phrase check
- [x] No hallucinated measurements or fabricated evidence sources
  Evidence: `ml/grounding_validator.py:GroundingValidator.validate()` — NWP hallucination check, FIRMS hallucination check, numerical claims validation against bundle
- [x] LLM separated from primary environmental data sources
  Evidence: `routers/reports.py` — evidence retrieval and LLM investigation are separate endpoints; `evidence_retriever.py` doc: "Does NOT call Gemini or generate AI verdicts"
- [x] Citizen report alone cannot produce high-confidence SUPPORTED verdict without corroboration
  Evidence: `services/fusion.py:calculate_event_confidence()` L22–L27 — anti-abuse rule: if `sensor_anomaly_score < 0.2` and `satellite_signal_score < 0.2`, confidence is capped at 0.65 even if citizen evidence is strong

---

## 7. ACTION — Application & Response

### Forecast Dashboard
- [~] Operational Delhi NCR forecast dashboard
  Evidence: `frontend/src/app/dashboard/page.tsx` — dashboard page exists. **Displays hardcoded `sampleEvent` data only**, not live API-connected data. Not yet connected to backend forecasting pipeline.
- [~] Current sensor observations displayed
  Evidence: dashboard UI contains PM2.5/PM10 observation cards, but the current implementation renders sample/hardcoded data rather than verified live backend observations.
- [~] Forecast pollutant fields displayed
  No PM2.5 forecast values rendered in the dashboard UI. `models.py Forecast` has `pm25_6h/24h/72h` fields.
- [~] Pollution hotspot visualisation
  Evidence: map components are referenced in the UI, but integration with live backend hotspot data is not yet verified.
- [~] Inversion / PBL condition indicators
  Not rendered in dashboard.
- [~] Fire / stubble-burning signal display
  Not rendered in dashboard.
- [~] Transport / plume visualisation
  Not rendered in dashboard.
- [~] Environmental events displayed
  Evidence: Dashboard renders the event structure using sampleEvent data; live backend event integration is not yet verified.
- [x] Risk levels displayed
  Evidence: `dashboard/page.tsx` L63 — `{sampleEvent.risk} RISK EVENT` rendered
- [x] Evidence-backed citizen reports displayed
  Evidence: `dashboard/page.tsx` — explanation, sensor evidence, satellite NO2, source hypothesis cards all rendered

### Alerts
- [~] Pollution spike alerts
  Evidence: `ml/forecast_service.py:_calculate_spike_risk()` — spike risk computed. `models.py AuthorityResponse.alert_sent: bool` — field exists. **No alert delivery mechanism** (webhook, email, push, n8n trigger) is implemented in the current backend code.
- [~] High-risk atmospheric condition alerts
  Evidence: `services/fusion.py` — HIGH confidence level triggers in weighted fusion. Alert delivery not implemented.
- [~] Fire / stubble-burning transport alerts
  Evidence: `FIRMSEvidence` assembled; no dedicated alert routing for fire signals.
- [~] Evidence-backed pollution incident reports
  Evidence: Investigator report schema complete (`PollutionEventInvestigationReport`); full investigator pipeline exists. Live end-to-end pipeline not wired to an alert delivery endpoint.

### Interfaces
- [x] Web application / PWA
  Evidence: `frontend/` — Next.js app with `frontend/src/app/page.tsx`, `layout.tsx`; `firebase.json` → Firebase Hosting configured
- [x] Mobile-friendly interface
  Evidence: `dashboard/page.tsx`, `report/page.tsx` — responsive Tailwind CSS layouts
- [~] Voice interaction
  Evidence: UI placeholder only (`report/page.tsx` description label says "Multilingual / Hindi / English"). No Web Speech API or SpeechRecognition integration implemented.
- [x] English support
  Evidence: All UI, prompts, and API responses are in English
- [~] Hindi support
  Evidence: `frontend/src/app/report/page.tsx` L77 — label says "Multilingual / Hindi / English"; L83 — Hindi placeholder text `"भारी धुआं है यहां"`. Gemini prompt accepts multilingual input. **No dedicated Hindi UI localisation, i18n routing, or Gemini translation pass** implemented. Hindi text can be submitted as text but there is no active translation layer.
- [ ] Odia support
  No Odia text, label, placeholder, or translation code found anywhere in the repository.
- [~] REST / API interfaces for third-party integration
  Evidence: FastAPI backend with `POST /api/v1/reports` and `GET/POST /api/v1/reports/{id}/evidence` endpoints. No authority-facing integration contract or external webhook defined.
- [ ] Authority-facing API integration
  Not implemented.

---

## 8. VALIDATE & IMPROVE

### Scientific Validation
- [~] Forecast vs CPCB / CAAQMS observations
  Evidence: Multiple ML validation scripts in `backend/ml/` (`validate_s4_s5_s6_rigorous.py`, `evaluate_extreme_pollution.py`, etc.); reports in `backend/reports/validation/`. These validate XGBoost ML models against CPCB observations. **WRF-Chem scientific forecast vs CPCB validation has not been run** (B2+ not complete).
- [~] MAE / RMSE computed per pollutant per station
  Evidence: ML model reports include MAE/RMSE metrics. WRF-Chem vs CPCB metrics not yet computed.
- [ ] Spatial error analysis
  Not found for WRF-Chem output. XGBoost spatial experiments exist as research scripts.
- [ ] Temporal error analysis
  `ml/analyze_temporal_model_performance.py` exists for XGBoost. Not implemented for WRF-Chem.
- [~] Bias analysis
  Evidence: `ml/s8a_calibration.py`, `ml/s8a_calibration_experiment.py` — calibration experiments for XGBoost. Not WRF-Chem.
- [ ] Reliability / calibration analysis (WRF-Chem)
  Not implemented.
- [ ] Emission inventory refinement based on validation
  Not implemented.

### ML Validation
- [x] ML model prediction vs observed outcome
  Evidence: Multiple scripts in `backend/ml/` (`validate_s4_s5_s6_rigorous.py`, `compare_final_models.py`, etc.) with output reports in `backend/reports/validation/`
- [x] Error analysis
  Evidence: `ml/analyze_temporal_model_performance.py`; validation reports in `backend/reports/`
- [x] Bias analysis
  Evidence: `ml/s8a_calibration.py`, `ml/s8a_calibration_experiment.py`
- [ ] Reliability analysis (calibration curves, confidence intervals)
  Beyond spike-risk heuristics — not implemented.
- [ ] Controlled model improvement deployed
  No production retraining workflow found. Scripts are research-mode only.

### Coverage
- [ ] Event detection validation (precision / recall / F1)
  `ml/s8b3_alert_persistence.py` computes alert episode precision/recall. Not a formal event-detection validation against ground truth.
- [~] CV model validation
  Evidence: Candidate A was selected using a frozen validation-only protocol with validation macro F1 = 0.8343. The locked V3.6 test set has not yet been evaluated for Candidate A.
- [ ] CV locked-test evaluation
- [ ] Evidence-verification outcome validation (are SUPPORTED verdicts actually correct?)
  No systematic outcome tracking implemented.

### Improvement Governance
- [ ] Scientific model improvement documented and controlled
- [ ] ML model retraining workflow documented
- [ ] No automatic unvalidated model changes deployed to production
- [ ] Feedback channels to Stage 2 (scientific) and Stage 4 (ML) are explicit and logged

---

## Architecture Integrity Checks

These checks must pass before any release or presentation:

- [ ] No fabricated implementation claims exist in the architecture document
- [ ] No architectural component is silently omitted from documentation
- [ ] No component is assigned to the wrong stage
- [ ] Physical modelling (Stage 3) and AI/ML (Stage 4) responsibilities remain clearly separated
- [ ] LLM remains a reasoning / verification layer only
- [ ] Source-attribution terminology is scientifically defensible (transport ≠ quantitative apportionment)
- [ ] FRP is not described as an exact emission rate without parameterisation
- [ ] Plume origin is not presented as quantitative source apportionment without a methodology
- [ ] Historical evidence is not presented as live environmental data
- [ ] Missing data is not silently zero-filled without documentation
- [ ] All planned components are explicitly labelled as `[PLANNED]` or `[~]`
- [ ] All claimed implemented components are backed by repository evidence
- [ ] `docs/architecture.md` and this checklist are consistent with each other
- [ ] Eight-stage structure is intact — no ninth stage has been silently introduced
- [ ] CV outputs are deterministic structured labels before entering any downstream reasoning
- [ ] Forecast dashboard is labelled "operational" not "real-time" in the context of WRF-Chem cycle frequency

---

## Audit Record

| Date | Audit | Result |
|---|---|---|
| 2026-09-18 | Repository evidence audit of implementation statuses | Completed |

### Audit Summary

**Files inspected:**
- `backend/main.py`
- `backend/services/evidence_retriever.py`
- `backend/services/fusion.py`
- `backend/services/gemini_evidence.py`
- `backend/services/sensor_data.py`
- `backend/services/weather.py`
- `backend/services/satellite.py`
- `backend/routers/reports.py`
- `backend/schemas/evidence.py`
- `backend/schemas/investigator_output_schema.py`
- `backend/schemas/evidence_bundle_input_schema.py`
- `backend/schemas/report.py`
- `backend/models.py`
- `backend/ml/forecast_service.py`
- `backend/ml/pollution_investigator.py`
- `backend/ml/pollution_event_detector.py`
- `backend/ml/grounding_validator.py`
- `backend/ml/run_gemma4_benchmark.py`
- `backend/models/` (directory listing — .joblib files confirmed present)
- `backend/train_vayunet_cv.py`
- `backend/reports/sih26082/wrfchem_final_prebenchmark_correction_audit.md`
- `frontend/src/app/dashboard/page.tsx`
- `frontend/src/app/report/page.tsx`
- `frontend/src/app/page.tsx`

| Status | Count |
|---|---:|
| `[x]` Verified | 72 |
| `[~]` Partial / planned | 58 |
| `[ ]` Not implemented / not verified | 52 |
| **Total** | **182** |

**Corrections made vs initial checklist (items downgraded from `[x]`):**
| Item | Old | New | Reason |
|---|---|---|---|
| O₃ | `[x]` | `[~]` | Not ingested in any evidence path; no sub-index code |
| Voice transcription pipeline | `[x]` | `[~]` | No STT code; text field accepts pre-typed text only |
| Historical / contextual evidence | `[x]` | `[~]` | OWBEII inventory included; no separate historical-context retrieval |
| AQI sub-indices (PM2.5, PM10) | `[x]` | `[~]` | No CPCB AQI formula implemented; PM2.5/PM10 used directly |
| AQI O₃ sub-index | `[x]` | `[ ]` | O₃ not ingested |
| AQI composite | `[x]` | `[~]` | Spike risk only; no CPCB composite AQI number |
| Human review gate | `[x]` | `[~]` | Only a `needs_human_review` flag exists; no dedicated human-review workflow/UI |
| Hindi support | `[x]` | `[~]` | Placeholder label + Gemini accepts multilingual; no i18n or translation pass |
| Odia support | `[x]` | `[ ]` | No Odia code, labels, or translation anywhere |
| Pollution spike alerts | `[x]` | `[~]` | Spike risk computed; no delivery mechanism implemented |
| High-risk atmospheric alerts | `[x]` | `[~]` | Confidence levels computed; no delivery |
| Environmental events displayed | `[x]` | `[x]` | Kept: dashboard renders sample event (noted as sample data) |
| NWP / WRF-Chem in evidence package | `[x]` | `[~]` | Schema exists; NWP typically null due to leakage fix; WRF-Chem not connected |
| WRF-Chem — all sub-items | `[~]` | `[~]` | Kept; B0/B1 confirmed, B2 not run |
| CV — all classification items | `[ ]` | `[ ]` | Correct; model not trained |

**Source code modified:** None. All changes are to this checklist document only.

---

*Last updated: 2026-09-18 — post repository-evidence audit. Update this checklist whenever implementation status changes. Do not mark items complete without repository evidence.*
