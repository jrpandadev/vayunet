/**
 * VayuNet Frontend API Abstraction Layer
 * Exclusive data-access layer for all UI components.
 * Components must NEVER import events.json directly.
 *
 * Supports instant transition between mock data and real FastAPI endpoints.
 * Provides resilient offline/demo fallback insurance if the backend is offline or fails.
 */

import mockEventsData from '../mock_data/events.json';
import {
  PollutionEvent,
  AuthorityAction,
  CitizenReportSubmission,
  ForecastPoint,
  RiskLevel
} from './types';
import { auth } from './firebase';

// In-memory working copy to support client-side optimistic updates (confirm, investigate, dismiss)
const eventsCache: PollutionEvent[] = JSON.parse(JSON.stringify(mockEventsData));

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const USE_REAL_BACKEND = process.env.NEXT_PUBLIC_USE_REAL_BACKEND !== 'false';
const REQUEST_TIMEOUT_MS = 5000;

export interface ApiStatus {
  isSimulation: boolean;
  isConnected: boolean;
  backendConfigured: boolean;
  backendUrl: string;
  lastError: string | null;
}

// Track runtime connection status
let isBackendReachable = false;
let lastApiError: string | null = null;

type StatusListener = (status: ApiStatus) => void;
const listeners = new Set<StatusListener>();

export function getIsSimulationMode(): boolean {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('vayunet_simulation_mode') === 'true';
  }
  return true; // Default to true during SSR/SSG to prevent build errors
}

export function getApiStatus(): ApiStatus {
  return {
    isSimulation: getIsSimulationMode(),
    isConnected: isBackendReachable,
    backendConfigured: USE_REAL_BACKEND && Boolean(API_BASE_URL),
    backendUrl: API_BASE_URL,
    lastError: lastApiError,
  };
}

export function subscribeApiStatus(listener: StatusListener): () => void {
  listeners.add(listener);
  listener(getApiStatus());
  return () => {
    listeners.delete(listener);
  };
}

function notifyStatusChange(reachable: boolean, error: string | null = null) {
  if (isBackendReachable !== reachable || lastApiError !== error) {
    isBackendReachable = reachable;
    lastApiError = error;
    const current = getApiStatus();
    listeners.forEach((fn) => fn(current));
  }
}

/**
 * Helper to fetch with an abort timeout
 */
async function fetchWithTimeout(url: string, options: RequestInit = {}): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    return await fetch(url, {
      ...options,
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timeoutId);
  }
}

const CITIES = [
  { name: 'Delhi', lat: 28.6139, lng: 77.2090 }
];

/**
 * Fetch all pollution events
 * Backend: GET /api/sih_forecast?lat={lat}&lng={lng}&city={city}
 * Fallback: mock_data/events.json in-memory cache
 */
export async function getEvents(): Promise<PollutionEvent[]> {
  if (USE_REAL_BACKEND && API_BASE_URL) {
    try {
      const res = await fetchWithTimeout(`${API_BASE_URL}/api/events`);
      if (res.ok) {
        const data: PollutionEvent[] = await res.json();
        notifyStatusChange(true, null);
        return data;
      }
      let errorBody = '';
      try {
        errorBody = await res.text();
      } catch (e) {
        // ignore
      }
      throw new Error(`Backend returned status ${res.status}: ${res.statusText} - ${errorBody}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      notifyStatusChange(false, msg);
      throw err;
    }
  } else {
    notifyStatusChange(false, null);
    notifyStatusChange(false, null);
    throw new Error("Real backend is disabled.");
  }
}

/**
 * Fetch a single pollution event by ID
 * Backend: GET /api/events/{event_id}
 * Fallback: mock_data/events.json in-memory cache
 */
export async function getEventById(id: string): Promise<PollutionEvent | null> {
  const allEvents = await getEvents();
  const found = allEvents.find((e) => e.event_id === id);
  return Promise.resolve(found ? { ...found } : null);
}

/**
 * Submit an authority response action for an event
 * Backend: POST /api/events/{event_id}/action
 * Contract: { action: "confirm" | "investigate" | "dismiss" }
 * Fallback: In-memory optimistic update clearly marked as simulation
 */
export async function updateEventAction(
  id: string,
  action: AuthorityAction
): Promise<{ success: boolean; event: PollutionEvent; isSimulation?: boolean }> {
  // Mock optimistic update for integration demo
  const allEvents = await getEvents();
  const current = allEvents.find((e) => e.event_id === id);
  if (!current) {
    throw new Error(`Event with id ${id} not found`);
  }

  const updated: PollutionEvent = {
    ...current,
    response: {
      ...current.response,
      status: 'acknowledged',
      alert_sent: action !== 'dismiss',
    },
    outcome:
      action === 'confirm'
        ? 'confirmed'
        : action === 'dismiss'
        ? 'false_alarm'
        : current.outcome,
    timeline: [
      ...current.timeline,
      {
        time: new Date().toISOString().substring(11, 16),
        event: `authority_action_${action}`,
      },
    ],
  };

  return Promise.resolve({ success: false, event: current, isSimulation: false });
}

/**
 * Submit citizen pollution observation
 * Backend: POST /api/report
 * Body: { photo?: File, text: string, lat: number, lng: number }
 * Fallback: Simulated report ingestion marked as simulation mode
 */
export async function submitReport(
  report: CitizenReportSubmission
): Promise<{ success: boolean; event_id: string; message: string; isSimulation?: boolean }> {
  if (USE_REAL_BACKEND && API_BASE_URL) {
    try {
      const formData = new FormData();
      if (report.photo instanceof File) {
        formData.append('photo', report.photo);
      }
      formData.append('text', report.text);
      formData.append('lat', String(report.lat));
      formData.append('lng', String(report.lng));
      formData.append('city', 'Delhi');

      const headers: Record<string, string> = {};
      const user = auth.currentUser;
      if (user) {
        const token = await user.getIdToken();
        headers['Authorization'] = `Bearer ${token}`;
      }

      const res = await fetchWithTimeout(`${API_BASE_URL}/api/report`, {
        method: 'POST',
        headers,
        body: formData,
      });
      if (res.ok) {
        const data = await res.json();
        notifyStatusChange(true, null);
        return { ...data, success: true, message: 'Report received', isSimulation: false };
      }
      throw new Error(`Backend returned status ${res.status}: ${res.statusText}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      console.warn(`[VayuNet API] Report submission to backend failed (${msg}). Falling back to simulation receipt.`);
      notifyStatusChange(false, msg);
    }
  } else {
    notifyStatusChange(false, null);
  }

  // No mock ingestion fallback
  return Promise.resolve({
    success: false,
    event_id: '',
    message: 'Backend is unavailable',
    isSimulation: false,
  });
}

/**
 * Fetch forecast series points for a given city and horizon
 * Backend: GET /api/forecast?city={city}&hours={hours}
 * Fallback: Local mathematical progression based on mock event forecast
 */
export async function getForecast(
  city: string,
  hours: 6 | 24 | 72 = 24
): Promise<ForecastPoint[]> {
  if (USE_REAL_BACKEND && API_BASE_URL) {
    try {
      const headers: Record<string, string> = {};
      const user = auth.currentUser;
      if (user) {
        const token = await user.getIdToken();
        headers['Authorization'] = `Bearer ${token}`;
      }

      const targetCity = CITIES.find(c => c.name.toLowerCase() === city.toLowerCase()) || CITIES[0];
      const res = await fetchWithTimeout(
        `${API_BASE_URL}/api/sih_forecast?lat=${targetCity.lat}&lng=${targetCity.lng}&city=${targetCity.name}`,
        { headers }
      );
      if (res.ok) {
        const data = await res.json();
        if (data.forecasts?.pm25?.status === 'AVAILABLE') {
          const forecastObj = data.forecasts.pm25.forecast;

          const points: ForecastPoint[] = [];
          const now = new Date();

          const maxIdx = hours === 6 ? 1 : hours === 24 ? 4 : 12;
          for (let i = 0; i <= maxIdx; i++) {
            const future = new Date(now.getTime() + i * 6 * 3600 * 1000);

            // Try to pull real values, else return null/unavailable
            let pm25_val: number | null = null;
            if (i === 0 || i === 1) pm25_val = forecastObj['6h'] ?? null;
            else if (i <= 4) pm25_val = forecastObj['24h'] ?? null;
            else pm25_val = forecastObj['72h'] ?? null;

            points.push({
              time: future.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              hour: i * 6,
              pm25: pm25_val,
              who_limit: 15,
              naaqs_limit: 60,
            });
          }
          notifyStatusChange(true, null);
          return points;
        } else {
          notifyStatusChange(true, null);
          return [];
        }
      }
      throw new Error(`Backend returned status ${res.status}: ${res.statusText}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      notifyStatusChange(false, msg);
      throw err;
    }
  } else {
    notifyStatusChange(false, null);
    throw new Error("Real backend is disabled.");
  }
}

export interface ObservationResult {
  status: string;
  value: number | null;
  unit: string;
  source: string;
}

/**
 * Fetch authoritative PM2.5 telemetry
 * Backend: GET /api/environment/observations?city={city}
 */
export async function getObservations(city: string): Promise<ObservationResult> {
  if (USE_REAL_BACKEND && API_BASE_URL) {
    try {
      const headers: Record<string, string> = {};
      const user = auth.currentUser;
      if (user) {
        const token = await user.getIdToken();
        headers['Authorization'] = `Bearer ${token}`;
      }

      const res = await fetchWithTimeout(
        `${API_BASE_URL}/api/environment/observations?city=${encodeURIComponent(city)}`,
        { headers }
      );
      
      if (res.ok) {
        const data = await res.json();
        return data as ObservationResult;
      }
      throw new Error(`Backend returned status ${res.status}`);
    } catch (err: unknown) {
      console.warn("Failed to fetch observations", err);
      return {
        status: "UNAVAILABLE",
        value: null,
        unit: "µg/m³",
        source: "CPCB"
      };
    }
  }
  return {
    status: "UNAVAILABLE",
    value: null,
    unit: "µg/m³",
    source: "CPCB"
  };
}

export async function getEvidenceUrl(path: string): Promise<string | null> {
  if (USE_REAL_BACKEND && API_BASE_URL) {
    try {
      const headers: Record<string, string> = {};
      const user = auth.currentUser;
      if (user) {
        const token = await user.getIdToken();
        headers['Authorization'] = `Bearer ${token}`;
      }

      const res = await fetchWithTimeout(`${API_BASE_URL}/api/evidence/url?path=${encodeURIComponent(path)}`, {
        headers,
      });

      if (res.ok) {
        const data = await res.json();
        return data.url;
      }
    } catch (e) {
      console.warn("Failed to fetch evidence URL:", e);
    }
  }
  return null;
}
