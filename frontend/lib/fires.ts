/**
 * VayuNet Fire Detection Layer - Synthetic Demonstration Dataset
 *
 * NOTE: All fire coordinates, timestamps, intensities, satellite evidence flags,
 * and pollution relationships in this file are SYNTHETIC DEMONSTRATION DATA for
 * frontend prototyping. They do NOT represent live satellite thermal feeds or
 * real-world confirmed incidents.
 */

export type FireStatus = 'ACTIVE' | 'HISTORICAL';
export type FireIntensity = 'LOW' | 'MODERATE' | 'HIGH';

export interface FireDetection {
  id: string;
  latitude: number;
  longitude: number;
  locationName: string;
  detectionTime: string;
  status: FireStatus;
  intensity: FireIntensity;
  sizeHectares?: number;
  satelliteEvidence?: string;
  pollutionRelationship?: string;
  pm25Contribution?: 'LOW' | 'MODERATE' | 'HIGH' | 'NOT_ESTABLISHED';
}

// Representative synthetic demonstration fires in and around Delhi NCR
export const MOCK_FIRE_DETECTIONS: FireDetection[] = [
  {
    id: 'fire_ncr_001',
    latitude: 28.7450,
    longitude: 77.0350,
    locationName: 'Bawana Agricultural Buffer',
    detectionTime: '13:40',
    status: 'ACTIVE',
    intensity: 'HIGH',
    sizeHectares: 2.4,
    satelliteEvidence: 'Available (Thermal anomaly simulation)',
    pollutionRelationship: 'Potential relationship with nearby Narela corridor PM2.5 event',
    pm25Contribution: 'HIGH',
  },
  {
    id: 'fire_ncr_002',
    latitude: 28.6180,
    longitude: 77.3820,
    locationName: 'East Delhi Open Waste Fringe',
    detectionTime: '12:15',
    status: 'ACTIVE',
    intensity: 'MODERATE',
    sizeHectares: 1.1,
    satelliteEvidence: 'Available (Simulation)',
    pollutionRelationship: 'Potential relationship with nearby Anand Vihar pollution event',
    pm25Contribution: 'MODERATE',
  },
  {
    id: 'fire_ncr_003',
    latitude: 28.4350,
    longitude: 77.0120,
    locationName: 'South Gurugram Perimeter',
    detectionTime: '11:30',
    status: 'ACTIVE',
    intensity: 'LOW',
    sizeHectares: 0.5,
    satelliteEvidence: 'Available (Simulation)',
    pollutionRelationship: undefined, // Demonstrates "Not established" fallback
    pm25Contribution: 'NOT_ESTABLISHED',
  },
  {
    id: 'fire_ncr_004',
    latitude: 28.8750,
    longitude: 77.2150,
    locationName: 'North Delhi / Sonipat Border',
    detectionTime: '06:10',
    status: 'HISTORICAL',
    intensity: 'HIGH',
    sizeHectares: 4.2,
    satelliteEvidence: 'Available (Simulation)',
    pollutionRelationship: 'Potential relationship with downwind morning PM2.5 elevation',
    pm25Contribution: 'HIGH',
  },
  {
    id: 'fire_ncr_005',
    latitude: 28.5020,
    longitude: 77.4050,
    locationName: 'Noida-Greater Noida Buffer',
    detectionTime: '04:45',
    status: 'HISTORICAL',
    intensity: 'LOW',
    sizeHectares: 0.8,
    satelliteEvidence: 'Not available',
    pollutionRelationship: undefined,
    pm25Contribution: 'NOT_ESTABLISHED',
  },
];
