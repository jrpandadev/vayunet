/**
 * VayuNet Citizen Observations / Uploaded Picture Evidence Layer
 *
 * NOTE: All photographic observations, coordinates, timestamps, descriptions,
 * and PM2.5 values in this file are SYNTHETIC DEMONSTRATION DATA for frontend
 * prototyping. They do NOT represent live submissions from real citizens or
 * confirmed ground sensor telemetry.
 *
 * Mandatory Classification & Labeling:
 * - "Prototype simulation data"
 * - "Citizen observation (simulation)"
 */

export type ObservationSourceType = 'CITIZEN_SUBMITTED';

export interface CitizenObservation {
  id: string;
  latitude: number;
  longitude: number;
  locationName: string;
  image?: string | null;
  uploadedAt: string; // e.g. "14:15"
  pm25AtLocation: number; // Measured/estimated at location in µg/m³
  description?: string;
  sourceType: ObservationSourceType;
  relatedEventId?: string | null; // e.g. "evt_001" or null ("Model relationship: Not established")
  isSimulation: true;
}

// 7 Focused synthetic demonstration observations in and around Delhi NCR
export const MOCK_CITIZEN_OBSERVATIONS: CitizenObservation[] = [
  {
    id: 'obs_ncr_001',
    latitude: 28.6508,
    longitude: 77.3152,
    locationName: 'Anand Vihar Transit Corridor',
    image: '/mock_photos/smoke1.jpg',
    uploadedAt: '14:15',
    pm25AtLocation: 195,
    description: 'Dense particulate haze and black diesel exhaust visible along arterial roadside corridor.',
    sourceType: 'CITIZEN_SUBMITTED',
    relatedEventId: 'evt_001',
    isSimulation: true,
  },
  {
    id: 'obs_ncr_002',
    latitude: 28.5355,
    longitude: 77.2410,
    locationName: 'Ring Road near Okhla Flyover',
    image: '/mock_photos/traffic1.jpg',
    uploadedAt: '13:50',
    pm25AtLocation: 165,
    description: 'Gridlocked vehicular congestion emitting heavy exhaust smoke under stagnant wind conditions.',
    sourceType: 'CITIZEN_SUBMITTED',
    relatedEventId: 'evt_004',
    isSimulation: true,
  },
  {
    id: 'obs_ncr_003',
    latitude: 28.6985,
    longitude: 77.1645,
    locationName: 'Wazirpur Industrial Cluster',
    image: '/mock_photos/smoke2.jpg',
    uploadedAt: '12:40',
    pm25AtLocation: 210,
    description: 'Dark industrial plume billowing from metal coating facility stack near railway crossing.',
    sourceType: 'CITIZEN_SUBMITTED',
    relatedEventId: null, // Demonstrates "Model relationship: Not established"
    isSimulation: true,
  },
  {
    id: 'obs_ncr_004',
    latitude: 28.7041,
    longitude: 77.1025,
    locationName: 'Rohini Sector 16 Market',
    image: '/mock_photos/smudge.jpg',
    uploadedAt: '11:20',
    pm25AtLocation: 42,
    description: 'Reported chemical fog but camera lens was partially obscured by dust smudge.',
    sourceType: 'CITIZEN_SUBMITTED',
    relatedEventId: 'evt_007',
    isSimulation: true,
  },
  {
    id: 'obs_ncr_005',
    latitude: 28.6280,
    longitude: 77.1180,
    locationName: 'Mayapuri Mechanical Cluster',
    image: '/mock_photos/dust1.jpg',
    uploadedAt: '10:15',
    pm25AtLocation: 130,
    description: 'Uncovered scrap cutting and metal grinding particulate dust spreading into roadway.',
    sourceType: 'CITIZEN_SUBMITTED',
    relatedEventId: null, // Demonstrates "Model relationship: Not established"
    isSimulation: true,
  },
  {
    id: 'obs_ncr_006',
    // Shares exact latitude & longitude with obs_ncr_001 to demonstrate multiple observations at same location
    latitude: 28.6508,
    longitude: 77.3152,
    locationName: 'Anand Vihar ISBT Bus Depot',
    image: '/mock_photos/depot1.jpg',
    uploadedAt: '09:30',
    pm25AtLocation: 180,
    description: 'Long queue of idling interstate buses with concentrated particulate exhaust within depot perimeter.',
    sourceType: 'CITIZEN_SUBMITTED',
    relatedEventId: 'evt_001',
    isSimulation: true,
  },
  {
    id: 'obs_ncr_007',
    latitude: 28.8420,
    longitude: 77.0980,
    locationName: 'Narela Industrial Buffer',
    image: null, // Demonstrates "Image preview unavailable" fallback
    uploadedAt: '08:45',
    pm25AtLocation: 155,
    description: 'Smoldering scrap ditch along road edge; smartphone camera failed to capture photo file.',
    sourceType: 'CITIZEN_SUBMITTED',
    relatedEventId: null, // Demonstrates "Model relationship: Not established"
    isSimulation: true,
  },
];

export async function getObservations(): Promise<CitizenObservation[]> {
  return Promise.resolve([...MOCK_CITIZEN_OBSERVATIONS]);
}
