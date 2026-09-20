/**
 * VayuNet PM2.5 Emission Hotspots - Synthetic Demonstration Dataset
 *
 * NOTE: All locations, estimated PM2.5 values, severities, confidence scores,
 * and possible sources in this file are SYNTHETIC DEMONSTRATION DATA for frontend
 * prototyping. They do NOT represent live CPCB measurements or real-world sensor telemetry.
 */

export type EmissionSeverity = 'LOW' | 'MODERATE' | 'HIGH' | 'VERY_HIGH' | 'CRITICAL';

export interface EmissionHotspot {
  id: string;
  latitude: number;
  longitude: number;
  locationName: string;
  estimatedPm25: number;
  severity: EmissionSeverity;
  detectionTime: string;
  confidence: number;
  possibleSource?: string;
  isActiveRecent: boolean;
}

// Representative synthetic demonstration hotspots in Delhi NCR
export const MOCK_EMISSION_HOTSPOTS: EmissionHotspot[] = [
  {
    id: 'hs_ncr_001',
    latitude: 28.5285,
    longitude: 77.2785,
    locationName: 'Okhla Industrial Area Phase-II',
    estimatedPm25: 310,
    severity: 'CRITICAL',
    detectionTime: '14:25',
    confidence: 0.91,
    possibleSource: 'Industrial fuel combustion',
    isActiveRecent: true,
  },
  {
    id: 'hs_ncr_002',
    latitude: 28.6985,
    longitude: 77.1645,
    locationName: 'Wazirpur Industrial Cluster',
    estimatedPm25: 255,
    severity: 'VERY_HIGH',
    detectionTime: '14:10',
    confidence: 0.88,
    possibleSource: 'Metal coating & furnace emissions',
    isActiveRecent: true,
  },
  {
    id: 'hs_ncr_003',
    latitude: 28.6508,
    longitude: 77.3152,
    locationName: 'Anand Vihar Transit Corridor',
    estimatedPm25: 195,
    severity: 'HIGH',
    detectionTime: '13:45',
    confidence: 0.84,
    possibleSource: 'Heavy diesel transport corridor',
    isActiveRecent: true,
  },
  {
    id: 'hs_ncr_004',
    latitude: 28.8420,
    longitude: 77.0980,
    locationName: 'Narela Industrial Complex',
    estimatedPm25: 180,
    severity: 'HIGH',
    detectionTime: '13:15',
    confidence: 0.82,
    possibleSource: 'Plastic processing & solid fuel boilers',
    isActiveRecent: false,
  },
  {
    id: 'hs_ncr_005',
    latitude: 28.6690,
    longitude: 77.3480,
    locationName: 'Sahibabad Industrial Area',
    estimatedPm25: 135,
    severity: 'MODERATE',
    detectionTime: '12:30',
    confidence: 0.76,
    possibleSource: undefined, // Demonstrates "Not available" fallback
    isActiveRecent: false,
  },
  {
    id: 'hs_ncr_006',
    latitude: 28.6280,
    longitude: 77.1180,
    locationName: 'Mayapuri Mechanical Cluster',
    estimatedPm25: 120,
    severity: 'MODERATE',
    detectionTime: '11:50',
    confidence: 0.74,
    possibleSource: 'Automotive scrap & smelting',
    isActiveRecent: false,
  },
  {
    id: 'hs_ncr_007',
    latitude: 28.7950,
    longitude: 77.0450,
    locationName: 'Bawana Perimeter Buffer',
    estimatedPm25: 68,
    severity: 'LOW',
    detectionTime: '10:15',
    confidence: 0.69,
    possibleSource: undefined, // Demonstrates "Not available" fallback
    isActiveRecent: false,
  },
];

export async function getEmissionHotspots(): Promise<EmissionHotspot[]> {
  return Promise.resolve([...MOCK_EMISSION_HOTSPOTS]);
}
