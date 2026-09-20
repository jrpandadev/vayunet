/**
 * VayuNet PM2.5 Risk Zones Layer - Synthetic Demonstration Dataset
 *
 * NOTE: All polygon coordinates, predicted PM2.5 values, risk levels, and
 * forecast metrics in this file are SYNTHETIC DEMONSTRATION DATA for frontend
 * prototyping. They do NOT represent live CPCB telemetry, operational NCMRWF
 * dispersion models, or official statutory air quality forecasts.
 *
 * Mandatory Labeling Requirement:
 * "Prototype simulation data — not live PM2.5 prediction output"
 */

export type RiskZoneLevel = 'LOW' | 'MODERATE' | 'HIGH' | 'VERY_HIGH' | 'CRITICAL';
export type ForecastUncertaintyLevel = 'Low' | 'Moderate' | 'High';

export interface RiskZone {
  id: string;
  name: string;
  level: RiskZoneLevel;
  predicted_pm25: number;
  coordinates: [number, number][]; // [latitude, longitude] polygon vertices
  center: [number, number]; // [latitude, longitude] geographic centroid
  forecast_horizon: string; // e.g. "Next 24 Hours"
  forecast_uncertainty: string; // e.g. "±24 µg/m³ (Moderate)"
  prediction_confidence: number; // e.g. 88 (%)
  simulation_disclaimer: string;
}

export const RISK_ZONE_HEX: Record<RiskZoneLevel, string> = {
  LOW: '#22c55e',
  MODERATE: '#eab308',
  HIGH: '#f97316',
  VERY_HIGH: '#ef4444',
  CRITICAL: '#9333ea',
};

// Base fill opacities engineered to remain clearly semi-transparent so roads, satellite imagery,
// and base map labels remain legible at all times without excessive visual weight.
export const RISK_ZONE_BASE_OPACITY: Record<RiskZoneLevel, number> = {
  LOW: 0.15,
  MODERATE: 0.17,
  HIGH: 0.19,
  VERY_HIGH: 0.21,
  CRITICAL: 0.23,
};

// 6 Plausible non-overlapping regional exposure corridors in Delhi NCR
export const MOCK_RISK_ZONES: RiskZone[] = [
  {
    id: 'zone_ncr_001',
    name: 'Bawana–Narela Industrial Corridor',
    level: 'CRITICAL',
    predicted_pm25: 320,
    coordinates: [
      [28.7750, 77.0300],
      [28.8400, 77.0600],
      [28.8550, 77.1250],
      [28.8050, 77.1400],
      [28.7600, 77.0900],
      [28.7500, 77.0450],
    ],
    center: [28.7975, 77.0800],
    forecast_horizon: 'Next 24 Hours',
    forecast_uncertainty: '±24 µg/m³ (Moderate)',
    prediction_confidence: 88,
    simulation_disclaimer: 'Prototype simulation data — not live PM2.5 prediction output',
  },
  {
    id: 'zone_ncr_002',
    name: 'Anand Vihar – Trans-Yamuna Transit Basin',
    level: 'VERY_HIGH',
    predicted_pm25: 245,
    coordinates: [
      [28.6250, 77.2950],
      [28.6650, 77.3000],
      [28.6800, 77.3550],
      [28.6400, 77.3650],
      [28.6150, 77.3350],
    ],
    center: [28.6450, 77.3300],
    forecast_horizon: 'Next 24 Hours',
    forecast_uncertainty: '±18 µg/m³ (Low)',
    prediction_confidence: 84,
    simulation_disclaimer: 'Prototype simulation data — not live PM2.5 prediction output',
  },
  {
    id: 'zone_ncr_003',
    name: 'Okhla – Badarpur Industrial & Transit Sector',
    level: 'HIGH',
    predicted_pm25: 185,
    coordinates: [
      [28.5100, 77.2650],
      [28.5550, 77.2750],
      [28.5500, 77.3200],
      [28.4950, 77.3300],
      [28.4850, 77.2850],
    ],
    center: [28.5190, 77.2950],
    forecast_horizon: 'Next 24 Hours',
    forecast_uncertainty: '±15 µg/m³ (Low)',
    prediction_confidence: 81,
    simulation_disclaimer: 'Prototype simulation data — not live PM2.5 prediction output',
  },
  {
    id: 'zone_ncr_004',
    name: 'Mayapuri – Najafgarh Arterial Corridor',
    level: 'HIGH',
    predicted_pm25: 160,
    coordinates: [
      [28.6200, 77.1050],
      [28.6600, 77.1150],
      [28.6650, 77.1650],
      [28.6300, 77.1600],
      [28.6050, 77.1250],
    ],
    center: [28.6360, 77.1340],
    forecast_horizon: 'Next 24 Hours',
    forecast_uncertainty: '±16 µg/m³ (Moderate)',
    prediction_confidence: 79,
    simulation_disclaimer: 'Prototype simulation data — not live PM2.5 prediction output',
  },
  {
    id: 'zone_ncr_005',
    name: 'Central Administrative & Institutional Buffer',
    level: 'MODERATE',
    predicted_pm25: 110,
    coordinates: [
      [28.5850, 77.1900],
      [28.6300, 77.1950],
      [28.6400, 77.2400],
      [28.6000, 77.2450],
      [28.5750, 77.2150],
    ],
    center: [28.6060, 77.2170],
    forecast_horizon: 'Next 24 Hours',
    forecast_uncertainty: '±12 µg/m³ (Low)',
    prediction_confidence: 85,
    simulation_disclaimer: 'Prototype simulation data — not live PM2.5 prediction output',
  },
  {
    id: 'zone_ncr_006',
    name: 'Southern Aravalli Ridge Green Buffer',
    level: 'LOW',
    predicted_pm25: 45,
    coordinates: [
      [28.4450, 77.1500],
      [28.5050, 77.1600],
      [28.5150, 77.2100],
      [28.4600, 77.2150],
      [28.4350, 77.1800],
    ],
    center: [28.4720, 77.1830],
    forecast_horizon: 'Next 24 Hours',
    forecast_uncertainty: '±8 µg/m³ (Low)',
    prediction_confidence: 90,
    simulation_disclaimer: 'Prototype simulation data — not live PM2.5 prediction output',
  },
];
