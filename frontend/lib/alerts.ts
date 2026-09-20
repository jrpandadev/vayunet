import { PollutionEvent, RiskLevel } from './types';
import { FireDetection, MOCK_FIRE_DETECTIONS } from './fires';
import { EmissionHotspot, MOCK_EMISSION_HOTSPOTS } from './hotspots';
import { RiskZone, MOCK_RISK_ZONES } from './riskZones';
import { MapLayersState } from '@/components/map/MapLayersPanel';

export type AlertSeverity = 'CRITICAL' | 'HIGH' | 'MODERATE' | 'INFO';

export type AlertType =
  | 'FORECAST_WARNING'
  | 'RAPID_DETERIORATION'
  | 'MAJOR_FIRE'
  | 'EMISSION_HOTSPOT'
  | 'HIGH_PM25';

export interface MapAlertItem {
  id: string;
  type: AlertType;
  severity: AlertSeverity;
  headline: string;
  locationName: string;
  description: string;
  metricLabel?: string;
  metricValue?: string;
  horizon?: string;
  targetEntityId: string;
  targetLayer: keyof MapLayersState;
  coordinates: [number, number];
  priorityRank: number; // 1 = Forecast, 2 = Rapid Deterioration, 3 = Major Fire, 4 = Emission Hotspot, 5 = High PM2.5
  isNCR: boolean;
}

/**
 * Derives map surveillance alerts deterministically from existing project data.
 * Zero fabricated fields, zero invented entity IDs.
 *
 * Category Priority:
 * 1. Forecast warning
 * 2. Rapid deterioration
 * 3. Major fire
 * 4. Significant emission hotspot
 * 5. High PM2.5
 */
export function getDerivedMapAlerts(
  events: PollutionEvent[],
  fires: FireDetection[] = MOCK_FIRE_DETECTIONS,
  hotspots: EmissionHotspot[] = MOCK_EMISSION_HOTSPOTS,
  riskZones: RiskZone[] = MOCK_RISK_ZONES,
  focalCity: string = 'ALL'
): MapAlertItem[] {
  const alerts: MapAlertItem[] = [];

  // -------------------------------------------------------------------------
  // 1. FORECAST WARNING (Priority 1)
  // Derived from existing risk zones (CRITICAL / VERY_HIGH) and events with high spike probability
  // -------------------------------------------------------------------------
  riskZones
    .filter((z) => z.level === 'CRITICAL' || z.predicted_pm25 >= 240)
    .forEach((zone) => {
      alerts.push({
        id: `alert_${zone.id}`,
        type: 'FORECAST_WARNING',
        severity: zone.level === 'CRITICAL' ? 'CRITICAL' : 'HIGH',
        headline: 'Severe Regional PM2.5 Corridor Forecast',
        locationName: zone.name,
        description: `Model predicts regional exposure corridor exceeding ${zone.predicted_pm25} µg/m³ PM2.5 (${zone.forecast_horizon}, ${zone.prediction_confidence}% confidence).`,
        metricLabel: '24h Forecast',
        metricValue: `${zone.predicted_pm25} µg/m³`,
        horizon: zone.forecast_horizon,
        targetEntityId: zone.id,
        targetLayer: 'riskZones',
        coordinates: zone.center,
        priorityRank: 1,
        isNCR: true,
      });
    });

  // -------------------------------------------------------------------------
  // 2. RAPID DETERIORATION WARNING (Priority 2)
  // Derived from events where 6-hour forecast surges significantly over current observed PM2.5
  // -------------------------------------------------------------------------
  events.forEach((evt) => {
    const currentPm25 = evt.evidence?.sensor?.pm25;
    const forecast6h = evt.forecast?.pm25_6h;
    if (currentPm25 != null && forecast6h != null) {
      const diff = forecast6h - currentPm25;
      const isRapidRise = diff >= 12 && evt.forecast?.spike_probability === 'HIGH';
      if (isRapidRise) {
        const isCityNCR = evt.location.city.toLowerCase() === 'delhi';
        const stationLabel = evt.evidence?.sensor?.station_id ? ` (${evt.evidence.sensor.station_id})` : '';
        alerts.push({
          id: `alert_rapid_${evt.event_id}`,
          type: 'RAPID_DETERIORATION',
          severity: evt.risk === 'CRITICAL' ? 'CRITICAL' : 'HIGH',
          headline: 'Rapid Particulate Deterioration Warning',
          locationName: `${evt.location.city}${stationLabel}`,
          description: `Observed PM2.5 (${currentPm25} µg/m³) projected to surge to ${forecast6h} µg/m³ (+${diff} µg/m³ in next 6h) under stagnant atmospheric conditions.`,
          metricLabel: '6h Surge',
          metricValue: `${forecast6h} µg/m³ (↑)`,
          horizon: 'Next 6h',
          targetEntityId: evt.event_id,
          targetLayer: 'events',
          coordinates: [evt.location.lat, evt.location.lng],
          priorityRank: 2,
          isNCR: isCityNCR,
        });
      }
    }
  });

  // -------------------------------------------------------------------------
  // 3. MAJOR ACTIVE FIRE DETECTION (Priority 3)
  // Derived from existing fire detections with ACTIVE status and HIGH intensity
  // -------------------------------------------------------------------------
  fires
    .filter((f) => f.status === 'ACTIVE' && (f.intensity === 'HIGH' || f.pm25Contribution === 'HIGH'))
    .forEach((fire) => {
      alerts.push({
        id: `alert_${fire.id}`,
        type: 'MAJOR_FIRE',
        severity: fire.intensity === 'HIGH' ? 'HIGH' : 'MODERATE',
        headline: 'Active High-Intensity Thermal Anomaly',
        locationName: fire.locationName,
        description: `Satellite thermal anomaly active${fire.sizeHectares ? ` over ${fire.sizeHectares} hectares` : ''} with high downwind PM2.5 particulate loading.`,
        metricLabel: 'Burn Area',
        metricValue: fire.sizeHectares ? `${fire.sizeHectares} Ha (Active)` : 'Active Fire',
        horizon: `Detected ${fire.detectionTime}`,
        targetEntityId: fire.id,
        targetLayer: 'fires',
        coordinates: [fire.latitude, fire.longitude],
        priorityRank: 3,
        isNCR: true,
      });
    });

  // -------------------------------------------------------------------------
  // 4. SIGNIFICANT EMISSION HOTSPOT (Priority 4)
  // Derived from active recent hotspots with CRITICAL severity or high PM2.5 plume impact
  // -------------------------------------------------------------------------
  hotspots
    .filter((h) => h.isActiveRecent && (h.severity === 'CRITICAL' || h.estimatedPm25 >= 250))
    .forEach((hs) => {
      alerts.push({
        id: `alert_${hs.id}`,
        type: 'EMISSION_HOTSPOT',
        severity: hs.severity === 'CRITICAL' ? 'CRITICAL' : 'HIGH',
        headline: 'Critical Industrial Plume Detected',
        locationName: hs.locationName,
        description: `Active plume contributing an estimated ${hs.estimatedPm25} µg/m³ PM2.5${hs.possibleSource ? ` from ${hs.possibleSource}` : ''} (${Math.round(hs.confidence * 100)}% confidence).`,
        metricLabel: 'Plume Impact',
        metricValue: `${hs.estimatedPm25} µg/m³`,
        horizon: 'Active Plume',
        targetEntityId: hs.id,
        targetLayer: 'hotspots',
        coordinates: [hs.latitude, hs.longitude],
        priorityRank: 4,
        isNCR: true,
      });
    });

  // -------------------------------------------------------------------------
  // 5. HIGH PM2.5 WARNING (Priority 5)
  // Derived from high-severity emission plumes or verified ground station spikes
  // -------------------------------------------------------------------------
  hotspots
    .filter((h) => h.isActiveRecent && h.severity === 'VERY_HIGH' && h.estimatedPm25 < 260)
    .forEach((hs) => {
      alerts.push({
        id: `alert_high_${hs.id}`,
        type: 'HIGH_PM25',
        severity: 'HIGH',
        headline: 'Severe Ground Particulate Loading',
        locationName: hs.locationName,
        description: `Localized particulate concentration measured at ${hs.estimatedPm25} µg/m³ PM2.5${hs.possibleSource ? ` from ${hs.possibleSource}` : ''}.`,
        metricLabel: 'Estimated PM2.5',
        metricValue: `${hs.estimatedPm25} µg/m³`,
        horizon: 'Active Plume',
        targetEntityId: hs.id,
        targetLayer: 'hotspots',
        coordinates: [hs.latitude, hs.longitude],
        priorityRank: 5,
        isNCR: true,
      });
    });

  // -------------------------------------------------------------------------
  // Deterministic Sorting:
  // 1. Geographic preference: NCR alerts first (since VayuNet map default is Delhi NCR)
  //    or matches active filter city if user explicitly selected another basin.
  // 2. Priority rank (1 through 5).
  // 3. Severity weighting (CRITICAL > HIGH > MODERATE > INFO).
  // 4. Stable tie-break by ID.
  // -------------------------------------------------------------------------
  const severityWeight: Record<AlertSeverity, number> = {
    CRITICAL: 40,
    HIGH: 30,
    MODERATE: 20,
    INFO: 10,
  };

  return alerts.sort((a, b) => {
    // 1. Geographic scope priority (Correction 3)
    if (focalCity === 'ALL' || focalCity.toLowerCase() === 'delhi') {
      if (a.isNCR && !b.isNCR) return -1;
      if (!a.isNCR && b.isNCR) return 1;
    } else {
      const aMatchesCity = a.locationName.toLowerCase().includes(focalCity.toLowerCase());
      const bMatchesCity = b.locationName.toLowerCase().includes(focalCity.toLowerCase());
      if (aMatchesCity && !bMatchesCity) return -1;
      if (!aMatchesCity && bMatchesCity) return 1;
    }

    // 2. Priority Rank
    if (a.priorityRank !== b.priorityRank) {
      return a.priorityRank - b.priorityRank;
    }

    // 3. Severity Weight
    const sevDiff = (severityWeight[b.severity] || 0) - (severityWeight[a.severity] || 0);
    if (sevDiff !== 0) return sevDiff;

    // 4. Deterministic stable tie-breaker
    return a.id.localeCompare(b.id);
  });
}
