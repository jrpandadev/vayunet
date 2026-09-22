# Post-Refactor Data Lineage Re-Audit

This table confirms the structural corrections to the VayuNet architecture, verifying that the frontend fields are now properly decoupled from `EVENTS_STORE` where appropriate and explicitly calling out unimplemented or unavailable fields.

## Final Lineage Table

| Dashboard Field | Frontend Component | API Endpoint | Backend Function | Authoritative Source | Availability Semantics | EVENTS_STORE Involved? |
|---|---|---|---|---|---|---|
| **Observed PM2.5 Peak** | `page.tsx` (`StatCard`) | `GET /api/environment/observations` | `sensor_data.load_cpcb_data()` | CPCB Telemetry (Live) | Real-time / UNAVAILABLE if API fails | **No** |
| **Active Events** | `page.tsx` (`StatCard`) | `GET /api/events` | `get_all_events()` | In-memory `EVENTS_STORE` | Live (returns list length) | **Yes** (Length) |
| **High Risk Zones** | `page.tsx` (`StatCard`) | None | None | None | **UNAVAILABLE** (Hardcoded) | **No** |
| **Active Fires** | `page.tsx` (`StatCard`) | None | None | None | **UNAVAILABLE** (Hardcoded) | **No** |
| **Emission Hotspots** | `page.tsx` (`StatCard`) | None | None | None | **UNAVAILABLE** (Hardcoded) | **No** |
| **24h Forecast Peak** | `page.tsx` (`StatCard`) | `GET /api/sih_forecast` | `ForecastService.predict()` | ML Model Inference (XGBoost) | Real / UNAVAILABLE if model fails | **No** |
| **PM2.5 Trajectory** | `forecast/page.tsx` | `GET /api/sih_forecast` | `ForecastService.predict()` | ML Model Inference (XGBoost) | Real / UNAVAILABLE if model fails | **No** |
| **PM10** | `forecast/page.tsx` | `GET /api/sih_forecast` | None (Mocked response) | None | **UNAVAILABLE** (Hardcoded) | **No** |
| **NOx** | `forecast/page.tsx` | `GET /api/sih_forecast` | None (Mocked response) | None | **UNAVAILABLE** (Hardcoded) | **No** |
| **O3** | `forecast/page.tsx` | `GET /api/sih_forecast` | None (Mocked response) | None | **UNAVAILABLE** (Hardcoded) | **No** |
| **Map Event Markers** | `LeafletMap.tsx` | `GET /api/events` | `get_all_events()` | In-memory `EVENTS_STORE` | Live based on valid events | **Yes** |
| **Event Evidence** | `EvidenceObservationPanel.tsx` | `GET /api/events` | `services/*` | Multi-source APIs | Live / Snapshot per event | **Yes** |

## Implementation Status

### IMPLEMENTED
- independent telemetry lineage;
- independent forecast lineage;
- REPORTS_STORE isolation;
- availability semantics;
- six lineage tests.

### NOT IMPLEMENTED
- authoritative Delhi-NCR geographic boundary enforcement;
- formal citizen-report -> Pollution Event promotion rule.

### 4. What is Simulation-Only
- There are strictly **no synthetic environmental values** in LIVE mode. Simulated telemetry arrays, fabricated mock events, and placeholder hotspots have been severed from the data lineage in production contexts.
