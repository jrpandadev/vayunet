# VayuNet — MASTER ARCHITECTURE DOCUMENT

## Environmental Intelligence Platform — Delhi NCR

### Status: FROZEN ARCHITECTURE (Target System) | Documentation Version 2.0

> **Important distinction:** This document describes the **frozen target architecture** — the full system as designed. Architecture and implementation status are explicitly separated throughout. Components are labelled `[IMPLEMENTED]`, `[PARTIAL]`, or `[PLANNED]` where known. The architecture is not a claim of current completion.

---

## System Overview

VayuNet is an environmental intelligence platform that combines multi-source observations, data fusion and assimilation, coupled atmospheric forecasting, AI/ML enhancement, environmental event intelligence, evidence-grounded verification, actionable forecasting, and continuous validation — specifically for Delhi NCR.

> VayuNet is **not merely an AQI dashboard.** The platform is organised around the **Pollution Event** as its core object, providing detection, evidence verification, forecast, risk assessment, explanation, authority routing, and learning.

---

## Eight-Stage Architecture — LOCKED

```text
OBSERVE
   ↓
FUSE & ASSIMILATE
   ↓
COUPLED ATMOSPHERE
   ↓
AI/ML INTELLIGENCE
   ↓
ENVIRONMENTAL INTELLIGENCE
   ↓
EVIDENCE VERIFICATION
   ↓
ACTION
   ↓
VALIDATE & IMPROVE
   ↺
```

This eight-stage structure is frozen. New components must be mapped to an existing stage. No ninth stage may be introduced without explicit architecture review.

---

## Stage 1 — OBSERVE: Data & Observations

**Role:** Ingest all raw environmental signals that VayuNet reasons over.

### Ground Observations `[PARTIAL]`
- CPCB / CAAQMS station network
- PM2.5
- PM10
- O₃
- NO₂
- CO (where available)

### Weather & NWP `[PARTIAL]`
- Temperature
- Wind speed / direction
- Relative humidity
- Atmospheric pressure
- Planetary Boundary Layer (PBL) height
- Meteorological boundary / forcing data (required for Stage 3 initialisation)

### Satellite `[PARTIAL]`
- Sentinel-5P
- Tropospheric NO₂ column density
- UV Aerosol Index
- Other relevant Earth-observation products

### Fire & Emissions `[PARTIAL]`
- NASA FIRMS
- Fire timing and location
- Fire Radiative Power (FRP)
- Regional emission inventories (industrial, transport, power, residential, construction, biomass/stubble burning)

### Citizen Observations `[IMPLEMENTED]`
- Photos
- Voice (transcribed before use)
- Text
- Location
- Timestamp

### Historical & Contextual Data `[PARTIAL]`
- Historical pollution observations
- Emission inventory baselines by sector:
  - Industrial
  - Transport
  - Power
  - Residential
  - Construction
  - Biomass / stubble burning

---

## Stage 2 — FUSE & ASSIMILATE: Data Engineering & Assimilation

**Role:** Transform raw, heterogeneous observations into coherent, model-ready inputs.

**Responsibilities:**
- Data quality control
- Missing / stale-data handling
- Spatial alignment
- Temporal alignment
- Deduplication
- Feature engineering
- Multi-source data fusion
- Emission-inventory preprocessing (disaggregation, spatial allocation, speciation → Stage 3 input format)
- Model state preparation (observations → initial conditions)
- Boundary-condition preparation (global NWP → lateral boundary conditions for Stage 3)
- **Optional / planned:** Runtime data assimilation / FDDA during model simulation `[PLANNED]`

> **Architectural note:** The specific data-assimilation method (3D-Var, FDDA, nudging, or other) is an implementation choice. The architecture does not mandate any particular DA technique.

---

## Stage 3 — COUPLED ATMOSPHERE: Scientific Forecasting Core

**Role:** Produce physically consistent forecasts of atmospheric state, chemistry, and pollutant transport using a coupled meteorology–chemistry model.

**Core engine:** WRF-Chem (or an appropriate coupled atmospheric modelling framework) `[PARTIAL]`

> WRF-Chem is the **scientific core of VayuNet**, not an optional component. It is not equivalent to the ML forecast layer. The ML layer enhances WRF-Chem output; it does not replace the physical model.

### Meteorology–Chemistry Coupling

```text
Meteorology  ↔  Chemistry
       ↕
Aerosol–Radiation–PBL Feedback
```

### Meteorological Variables / Processes
- Temperature profiles
- Wind (speed, direction, vertical motion)
- Pressure
- Humidity
- Radiation
- PBL height
- Atmospheric stability
- Thermal inversion conditions

### Chemistry
- PM2.5
- PM10
- Ground-level O₃
- NOx
- VOCs
- Aerosols (formation, growth, optical properties)
- Chemical transformation (gas-phase, aqueous-phase)
- Dry and wet deposition

### Coupled Processes

```text
Emissions (preprocessed inventories + FIRMS fire injection)
   ↓
Injection
   ↓
Advection / Transport
   ↓
Diffusion / Mixing
   ↓
Chemical Transformation
   ↓
Deposition
   ↓
Pollutant Concentration Fields
(PM2.5 / PM10 / O₃ / NOx / Aerosols)
```

Two-way coupling ensures:
- Aerosol effects on radiation and boundary layer are physically modelled
- Chemistry affects meteorology (not one-directional)

### Spatial Domain Configuration `[PARTIAL]`
- Delhi NCR high-resolution nested atmospheric domain
- Regional outer domain for boundary transport (Punjab/Haryana/UP corridors)
- Global NWP (e.g. ERA5 / GFS) provides lateral boundary conditions

---

## Stage 4 — AI/ML INTELLIGENCE

**Role:** Enhance, interpret, and add intelligence to the outputs of Stage 3 and the observations from Stage 1. This layer **augments** the physical model; it does not replace it.

### Forecast Enhancement `[PARTIAL]`
Applied to WRF-Chem output fields:
- Statistical bias correction against CPCB observations
- Forecast refinement
- Statistical downscaling (sub-grid resolution enhancement)
- Forecast anomaly / pollution-spike detection

### Observational Intelligence `[IMPLEMENTED]`
Applied to sensor streams:
- Pollution anomaly detection
- Unusual pollutant combination detection
- Cross-source inconsistency detection

### Environmental Computer Vision `[PARTIAL]`

```text
Photo
 ↓
CV Model
 ↓
Probabilities (per class)
 ↓
Deterministic structured evidence output
```

**CV label classes:**
- Image relevance
- Smoke
- Dust
- Open burning
- Plume
- Industrial source
- Construction activity

CV outputs feed into:
1. Event Intelligence (this stage)
2. Evidence Package for Stage 6

> **Architectural boundary:** CV does not directly act as a WRF-Chem emissions model. Any future research coupling CV detections to emission estimates is an extension, not a core architectural dependency.

### Event Intelligence `[IMPLEMENTED]`
- Pollution-event detection
- Event classification
- Risk scoring
- Evidence prioritisation

---

## Stage 5 — ENVIRONMENTAL INTELLIGENCE: Delhi NCR

**Role:** Apply domain-specific atmospheric and environmental science to produce intelligence relevant to Delhi NCR conditions.

### Atmospheric Inversion Intelligence `[PARTIAL]`
Diagnosed from WRF-Chem meteorological output:
- Inversion strength
- Inversion height
- PBL / mixing layer depth and conditions
- Diagnosed atmospheric stability

### Stubble-Burning Intelligence `[PARTIAL]`

```text
FIRMS Fire Detection
        ↓
Fire / FRP Evidence
        ↓
Potential Emission Signal
        ↓
Transport Conditions (WRF-Chem wind / PBL fields)
        ↓
Plume / Impact Analysis
```

> **Scientific note:** FRP → emission rate and plume injection height require explicit parameterisation (e.g. FINN inventory, 1D plume-rise model). FRP is not an exact emission quantity. This step involves modelling assumptions that must be documented.

### Pollution Transport Analysis `[PARTIAL]`
Derived from WRF-Chem concentration fields:
- Wind-driven pollutant transport
- Plume movement
- Transport pathways
- Potential plume-origin indicators
- Regional influence indicators

> **Terminology boundary:** This is **transport pathway analysis** and **plume-origin indication**, not quantitative source apportionment. Source apportionment (percentage contributions from named sources) requires dedicated receptor modelling (e.g. PSCF, CMB, FLEXPART tagged-tracer runs) that is not part of the current architecture.

### AQI Engine `[IMPLEMENTED]`

```text
PM2.5 / PM10 / O₃ / (other applicable pollutants)
          ↓
   AQI Sub-indices (CPCB methodology)
          ↓
     AQI Composite
          ↓
   6h / 24h / 72h Forecast
```

### Risk & Event Assessment `[IMPLEMENTED]`
- Pollution spike prediction
- Exposure severity scoring
- Event status classification
- Confidence grading

---

## Stage 6 — EVIDENCE VERIFICATION

**Role:** Verify citizen pollution reports using multi-source environmental evidence, AI reasoning, and a human review gate. This stage is logically independent of the atmospheric forecasting pipeline.

### Citizen Intelligence Path

```text
Citizen Report
      ↓
Photo + Text + Voice (transcribed)
      ↓
Evidence Retrieval
      ↓
Environmental Evidence Package
      ↓
CV Assessment + Environmental Evidence
      ↓
Grounded LLM Reasoning
      ↓
Verification Verdict
      ↓
Human Review Gate
```

### Evidence Sources
The evidence package is assembled **before** LLM invocation and may include:
- Citizen photo (CV-assessed)
- Citizen claim text
- CPCB / CAAQMS sensor observations
- Weather conditions
- NWP / WRF-Chem model outputs
- Sentinel-5P satellite data
- NASA FIRMS fire data
- Emission / source context
- Historical / contextual evidence

### LLM / AI Investigator `[IMPLEMENTED]`

> The LLM (implemented with Gemini) acts as a **reasoning and verification layer** over pre-retrieved, grounded evidence. It is not the primary environmental data source. It does not replace CPCB, satellite, FIRMS, NWP, or WRF-Chem data.

### Allowed Verification Outcomes

```text
SUPPORTED
NOT_SUPPORTED
INCONCLUSIVE
```

All claims must remain grounded in retrieved evidence. The LLM may not hallucinate measurements or invent data sources.

### Human Review Gate `[PARTIAL]`
A distinct mandatory gate activated when:
- Verdict confidence falls below threshold
- Verdict is INCONCLUSIVE
- Event severity requires authority-level confirmation

Human review is an architectural component, not an optional afterthought.

---

## Stage 7 — ACTION: Application & Response

**Role:** Present environmental intelligence, forecasts, and verified events to citizens and authorities in actionable form.

> The product is an **environmental intelligence platform**, not merely an AQI map.

### Operational Delhi NCR Forecast Dashboard `[PARTIAL]`

> Dashboard content is updated **per forecast cycle** (when WRF-Chem completes a cycle and ML post-processing is applied). Sensor overlays are updated continuously from live feeds. These are distinct update frequencies.

Displays:
- Current sensor observations
- Forecast pollutant fields (PM2.5 / PM10 / O₃)
- 6h / 24h / 72h forecasts
- Pollution hotspots
- Inversion / PBL condition indicators
- Fire / stubble-burning signals
- Transport / plume visualisation
- Environmental events
- Risk levels
- Evidence-backed citizen reports

### Alerts `[IMPLEMENTED]`
- Pollution spike early warnings
- High-risk atmospheric conditions
- Fire / stubble-burning transport alerts
- Evidence-backed pollution incident reports

### Interfaces `[PARTIAL]`
- Web application / PWA
- Mobile-friendly interface
- Voice interaction
- Multilingual support (English / Hindi / Odia)
- REST / API interfaces for authority and third-party integration
- Potential authority-facing integrations `[PLANNED]`

---

## Stage 8 — VALIDATE & IMPROVE

**Role:** Close the feedback loop between forecast outputs and actual observations to support controlled model improvement.

### Scientific Validation Channel

```text
WRF-Chem / ML Forecast
        ↓
Actual CPCB / CAAQMS Observations
        ↓
Error / Bias Analysis
(MAE, RMSE, spatial error, temporal error, bias)
        ↓
Scientific Model Improvement
        ↓
Emission Inventory / Parameter Refinement
        ↓
Updated Initial / Boundary Conditions → re-enters Stage 2
```

### ML Validation Channel

```text
ML Model Prediction
        ↓
Observed Outcome
        ↓
Error Analysis
        ↓
Bias / Reliability Analysis
        ↓
Controlled Model Improvement → re-enters Stage 4
```

### Validation Coverage
- Forecast vs observation (per station, per pollutant, per horizon)
- MAE, RMSE, and appropriate scientific metrics
- Spatial error analysis
- Temporal error analysis
- Bias analysis
- Reliability / calibration analysis
- Event detection validation (precision / recall / F1)
- CV model validation
- Evidence-verification outcome validation

> **Architectural boundary:** Model improvement is **controlled and validated**. The system does not automatically retrain all models every forecast cycle. Retraining requires analysis, validation, and explicit deployment.

---

## Scientific Spine — FROZEN

```text
Observations
     +
Emissions (preprocessed inventories)
     +
Boundary Conditions (global NWP)
     ↓
   WRF-Chem
     ↓
Meteorology ↔ Chemistry (two-way coupled)
     ↕
Aerosol–Radiation–PBL Feedback
     ↓
Transport + Transformation + Deposition
     ↓
PM2.5 / PM10 / O₃ / NOx / Aerosols
     ↓
AI/ML Bias Correction + Downscaling
     ↓
AQI + Risk + Environmental Intelligence
     ↓
Validation
     ↺
```

---

## Citizen Intelligence Spine — FROZEN

```text
Citizen Report
     ↓
Photo / Text / Voice
     ↓
Evidence Retrieval
     ↓
CV + Environmental Evidence (grounded)
     ↓
LLM Reasoning (Gemini)
     ↓
SUPPORTED / NOT_SUPPORTED / INCONCLUSIVE
     ↓
Human Review Gate
     ↓
Action / Authority Routing
```

---

## System-Level Data Flow

```text
Stage 1: OBSERVE
  (Sensors, NWP, Global BCs, Satellite, FIRMS, Citizen, Inventories)
        ↓
Stage 2: FUSE & ASSIMILATE
  (QC, Fusion, Emission Preprocessing, IC/BC Generation)
        ↓
Stage 3: COUPLED ATMOSPHERE
  (WRF-Chem: Meteorology ↔ Chemistry, Emissions, Transport)
        ↓
Stage 4: AI/ML INTELLIGENCE
  (Bias Correction, Downscaling, Anomaly Detection, CV, Event Intelligence)
        ↓
Stage 5: ENVIRONMENTAL INTELLIGENCE
  (Inversion, Stubble-Burning, Transport Analysis, AQI, Risk)
        ↓
Stage 6: EVIDENCE VERIFICATION     ←── also receives Stages 1, 3, 4
  (Evidence Retrieval, LLM Reasoning, Verdict, Human Review)
        ↓
Stage 7: ACTION
  (Dashboard, Alerts, Interfaces, APIs)
        ↓
Stage 8: VALIDATE & IMPROVE
  → Scientific feedback → Stage 2
  → ML feedback        → Stage 4
  ↺
```

---

## Architectural Boundaries — EXPLICIT

These boundaries are part of the frozen architecture and must be respected by all implementation decisions.

### 1. Architecture ≠ Implementation Status
The architecture describes the full target system. Not every component is currently implemented. See implementation status labels throughout this document.

### 2. Technology Choices Are Not Mandated by the Architecture
The following are implementation choices, not architectural requirements:
- Specific NWP product (ERA5, GFS, NCEP FNL, etc.)
- Specific DA method (3D-Var, FDDA, nudging)
- WRF-Chem chemistry scheme (MOZART, RADM2, CBMZ, etc.)
- WRF-Chem aerosol scheme (MOSAIC, MADE-SORGAM, etc.)
- Exact FRP → emission-rate parameterisation
- Exact plume injection-height parameterisation
- LLM vendor (Gemini is current; architecture is vendor-agnostic at design level)

### 3. Source Attribution Terminology
Use:
- **transport pathways**
- **plume-origin indicators**
- **regional influence indicators**

Do **not** describe outputs as **quantitative source apportionment** unless a dedicated methodology (e.g. PSCF, CMB, FLEXPART tagging) is implemented and validated.

### 4. WRF-Chem Is the Scientific Core
WRF-Chem is not an optional or decorative component. The ML layer (Stage 4) enhances and post-processes its output. ML does not substitute for the coupled atmospheric model.

### 5. AI/ML Enhances; It Does Not Replace
The AI/ML intelligence layer (Stage 4) improves WRF-Chem outputs (bias correction, downscaling, spike detection). It operates on WRF-Chem output, not instead of it.

### 6. LLM Is a Reasoning Layer, Not a Data Source
The LLM (Gemini in current implementation) reasons over pre-retrieved, grounded evidence. It is not a substitute for CPCB, Sentinel-5P, FIRMS, NWP, or WRF-Chem data. The evidence package is assembled deterministically before any LLM call.

### 7. Citizen Reports Are Evidence Candidates
Citizen reports are input to verification (Stage 6), not automatically accepted truth. They require corroboration from at least one independent data source before a high-confidence verdict can be issued.

### 8. Historical Evidence Bundles Are Context, Not Live Data
Historical evidence provides baseline context for anomaly assessment. It is not a substitute for current observations. Data freshness must be tracked and reported.

### 9. Future Components Must Fit Within the Eight Stages
Any future component (e.g. CV-to-emissions research, source apportionment module, additional ML models) must be mapped to an existing stage. Introducing a ninth architectural stage requires explicit architecture review.

### 10. Controlled Improvement Only
Model retraining and parameter updates occur through the Stage 8 validation pipeline. Automatic, unreviewed model updates to production are not permitted by this architecture.

---

## Implementation Status Summary

### Implemented / Verified
- VayuNet FastAPI backend
- Evidence retrieval and packaging pipeline
- Gemini-based environmental incident investigator
- Verification verdict schema (SUPPORTED / NOT_SUPPORTED / INCONCLUSIVE)
- AQI computation engine
- Ground sensor data ingestion (CPCB / CAAQMS)
- Sentinel-5P satellite ingest
- NASA FIRMS fire data retrieval
- Grounding validator (evidence numerical integrity checks)
- ML pollution event detector
- Event confidence scoring (weighted fusion)
- Human-in-the-loop authority routing
- Citizen PWA (photo / voice / text / location)
- Multilingual support (English / Hindi / Odia)

### Partially Implemented
- WRF-Chem domain configuration (feasibility audit and domain setup complete; full operational automated cycle not yet running)
- Emission inventory preprocessing (framework begun; not production-complete)
- ML forecast bias correction (schema designed; model not fully trained and validated)
- Environmental Computer Vision — Stage 3A (dataset acquisition complete; CV model not yet trained; benchmark locked)
- Forecast dashboard (backend exists; full pollutant field visualisation not complete)

### Planned / Not Yet Implemented
- Full automated WRF-Chem forecast cycle (scheduled, end-to-end)
- FDDA / observational nudging during WRF-Chem runtime
- Quantitative FRP → emission-rate parameterisation
- Statistical downscaling (beyond bias correction)
- CV production inference integrated into evidence pipeline
- Automated Stage 8 validation pipeline
- Controlled model retraining workflow
- Authority-facing REST API integrations
- Production mobile application

---

## Original System Information (Preserved)

The sections below preserve project context from the original architecture document version. They do not describe the frozen eight-stage architecture but provide relevant background for contributors.

### One-Line Pitch

> "VayuNet detects hidden pollution events by fusing citizen, sensor, satellite and weather evidence — using Gemini API for multimodal evidence interpretation and explanation, local machine learning for forecasting, and coupled atmospheric physics for scientific rigour — routing explainable, human-verified alerts to the right authority."

### The Problem

Major Indian cities monitor macro-level air quality but consistently miss **hyper-local pollution events** — industrial emissions, agricultural/stubble burning, seasonal smog, localised dust and construction events. The absence of real-time, granular, evidence-backed detection prevents coordinated climate action and directly threatens public health.

The relevant question is not "what is today's AQI" but:

> "Where is an abnormal pollution event happening, how credible is the evidence, how will it evolve, and which authority should respond?"

### Google AI Compliance

VayuNet satisfies SIH Google AI requirements through Gemini API integration for:
- Multimodal evidence interpretation (photo + text + voice)
- Structured evidence extraction
- Grounded reasoning and explanation
- Multilingual translation

Gemini performs load-bearing, non-decorative work in the evidence verification pipeline.

### Event Object Schema

The core Pollution Event carries: evidence bundle, detection confidence, WRF-Chem / ML forecast, risk level, LLM-generated explanation, authority routing, human review status, and outcome. Full schema is maintained in `docs/schema.json`.

### What Not to Claim

- ❌ "Gemini detects the pollution source with certainty." — Gemini produces a grounded hypothesis with confidence, not a factual attribution.
- ❌ "WRF-Chem and XGBoost are equivalent." — WRF-Chem is coupled 3D atmospheric physics; XGBoost is a statistical surrogate.
- ❌ "This is already deployed nationally."
- ❌ Any fabricated accuracy metrics or deployment claims.
- ❌ "Regional transport" = quantitative source apportionment.
- ❌ FRP values are exact emission rates (they require parameterisation).

---

*This document is the authoritative frozen architecture reference for VayuNet. Architecture version 2.0. All implementation decisions must align with the eight-stage structure and architectural boundaries defined above.*
