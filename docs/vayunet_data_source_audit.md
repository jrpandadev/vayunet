# VayuNet Data-Source Audit

## 1. Dashboard Values and their Sources

| UI Value | Source File | Backend/API | Actual Source | Real/Simulated | Fallback? |
| -------- | ----------- | ----------- | ------------- | -------------- | --------- |
| Observed PM Peak | `frontend/app/dashboard/page.tsx` | `/api/events` (mocked in `getEvents`) | `frontend/lib/observations.ts` (MOCK_EVENTS) | Simulated | YES (API failure falls back to mock) |
| Active Events | `frontend/app/dashboard/page.tsx` | `/api/events` (mocked) | `frontend/lib/observations.ts` | Simulated | YES |
| High-Risk Zones | `frontend/app/dashboard/page.tsx` | None | `frontend/lib/riskZones.ts` (MOCK_RISK_ZONES) | Simulated | N/A (Always mock) |
| Active Fires | `frontend/app/dashboard/page.tsx` | None | `frontend/lib/fires.ts` (MOCK_FIRE_DETECTIONS) | Simulated | N/A (Always mock) |
| Emission Hotspots | `frontend/app/dashboard/page.tsx` | None | `frontend/lib/hotspots.ts` (MOCK_EMISSION_HOTSPOTS) | Simulated | N/A (Always mock) |
| 24h Forecast Peak | `frontend/app/dashboard/page.tsx` | None (for NCR) | `MOCK_RISK_ZONES` (NCR) or `MOCK_EVENTS` (Other) | Simulated | N/A (Always mock) |
| Incident Feed | `frontend/app/dashboard/page.tsx` | `/api/events` (mocked) | `frontend/lib/observations.ts` | Simulated | YES |
| Map Markers / Polygons | `frontend/components/map/LeafletMap.tsx` | None | `MOCK_FIRE_DETECTIONS`, `MOCK_EMISSION_HOTSPOTS`, `MOCK_RISK_ZONES` | Simulated | N/A (Always mock) |
| Satellite Indicators | `frontend/app/dashboard/page.tsx` | `/api/events` (mocked) | `frontend/lib/observations.ts` | Simulated | YES |
| Citizen Evidence | `frontend/app/dashboard/page.tsx` | `/api/events` (mocked) | `frontend/lib/observations.ts` | Simulated | YES |
| Weather | `frontend/app/dashboard/page.tsx` | `/api/events` (mocked) | `frontend/lib/observations.ts` | Simulated | YES |
| Forecast Charts | `frontend/app/dashboard/forecast/page.tsx` | `/api/forecast` (mocked) | `frontend/lib/api.ts` (generateMockForecast) | Simulated | YES |

## 2. Simulation / Mock Data Locations

- `frontend/lib/observations.ts` (MOCK_EVENTS - `evt_001`, `evt_008`, `192 µg/m³`)
- `frontend/lib/fires.ts` (MOCK_FIRE_DETECTIONS)
- `frontend/lib/hotspots.ts` (MOCK_EMISSION_HOTSPOTS)
- `frontend/lib/riskZones.ts` (MOCK_RISK_ZONES - `320 µg/m³`)
- `frontend/lib/alerts.ts` (MOCK_ALERTS)
- `frontend/lib/api.ts` (`generateMockForecast`)
- `backend/main.py` (Silent fallbacks returning `180.0` PM2.5 on exception)

## 3. Live-Data Endpoints (Backend)

The existing FastAPI backend has the following endpoints intended for real data:
- `POST /api/report`: Accepts real citizen evidence, fetches real CPCB data, Open-Meteo weather, and Sentinel-5P features, and runs the fusion engine.
- `GET /api/evidence/url`: Retrieves signed URLs from real Supabase storage.
- `GET /api/sih_forecast`: Fetches weather, inversion proxy, and calls the actual ForecastService ML model.

## 4. Unsafe Fallback Locations

1. **Frontend `api.ts`**:
   `getEvents()` and `getForecast()` wrap `fetch()` in a `try/catch`. If the API fails, they catch the error, log a warning, and immediately return `MOCK_EVENTS` or `generateMockForecast()`. This is an unsafe silent fallback.

2. **Backend `main.py`**:
   `submit_report()` has `try/except` blocks around CPCB, Weather, and Sentinel-5P data fetches. Instead of failing or setting status to `UNAVAILABLE`, they hardcode values:
   - CPCB: Returns `180.0` for PM2.5.
   - Weather: Returns `2.0` wind speed.
   - Sentinel-5P: Returns `18.2` NO2 index.

## 5. Origin of Specific Screenshot Values

- `192 µg/m³`: Computed as `peakPm25` in `app/dashboard/page.tsx` from `filteredEvents`. The highest value in `MOCK_EVENTS` (`frontend/lib/observations.ts`) is 192 for `evt_001`.
- `320 µg/m³`: Computed from `Math.max(...MOCK_RISK_ZONES.map(z => z.predicted_pm25))` in `app/dashboard/page.tsx`. `zone_ncr_001` in `riskZones.ts` has `predicted_pm25: 320`.
- `6 active events`: There are 6 mock events in `MOCK_EVENTS` that are not resolved.
- `2 high risk zones`: In NCR, `MOCK_RISK_ZONES` has 2 zones that are CRITICAL/VERY_HIGH.
- `3 active fires`: `MOCK_FIRE_DETECTIONS` has 3 active fires.
- `3 emission hotspots`: `MOCK_EMISSION_HOTSPOTS` has 3 active hotspots.
- `evt_001`, `evt_008`: Hardcoded IDs in `MOCK_EVENTS`.
- Delhi, Mumbai, Bhubaneswar: Hardcoded cities in `MOCK_EVENTS`.

---

## 6. Audit Remediation Results (Execution)

### 1. Backend Fallbacks Removed
The unsafe numerical fallbacks in `backend/main.py` were fully remediated.
- **CPCB**: Now falls back to `{"status": "UNAVAILABLE", "pm25": null, "pm10": null, "anomaly_score": null}`. The numerical anomaly score default was safely changed to `0.0` for internal calculations, keeping it out of the UI.
- **Weather**: Now falls back to `{"status": "UNAVAILABLE", "wind_speed_kmh": null, "humidity_percent": null}`.
- **Sentinel-5P**: Now falls back to `{"status": "UNAVAILABLE", "no2_index": null, "aerosol_index": null}`.

### 2. Frontend API Fallbacks Fixed
The `getEvents()` and `getForecast()` functions in `frontend/lib/api.ts` were updated to enforce a strict `isSimulation` condition.
- **LIVE Mode**: Throws an error on backend failure instead of returning `MOCK_EVENTS`.
- **SIMULATION Mode**: Continues to return the robust demonstration dataset.

### 3. Dashboard UI Fixed
`app/dashboard/page.tsx` and `app/dashboard/forecast/page.tsx` have been updated to explicitly catch API errors and display a distinct "UNAVAILABLE" state.
- **Null Safety**: Updated `frontend/components/map/MapInfoPanel.tsx` and `frontend/components/ai/AIModelPanel.tsx` to handle `null` properly instead of masking them with `0` or `0.8`.
- **Map Overlays**: `MOCK_FIRE_DETECTIONS`, `MOCK_EMISSION_HOTSPOTS`, and `MOCK_RISK_ZONES` are now strictly disabled (set to empty array) when `isSimulation === false`.

### 4. Deployment Architecture
- **Backend Deployment**: Created a `Dockerfile` and `render.yaml` to deploy the FastAPI backend. For demonstration, the backend is temporarily exposed via Localtunnel.
- **Frontend Deployment**: Deployed the Next.js app to Firebase Hosting, properly wired to the backend URL via `.env.production`.

### Remaining Simulation Data (Only Active if isSimulation === true)
- `MOCK_EVENTS`
- `MOCK_FIRE_DETECTIONS`
- `MOCK_EMISSION_HOTSPOTS`
- `MOCK_RISK_ZONES`
- `MOCK_CITIZEN_OBSERVATIONS`
- Simulated Forecast Curved Math
