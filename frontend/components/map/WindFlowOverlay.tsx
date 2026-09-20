'use client';

import React, { useMemo } from 'react';
import { Polyline } from 'react-leaflet';

export interface WindFlowOverlayProps {
  windSpeed?: number;
  windDirectionDeg?: number;
  directionLabel?: string;
  className?: string;
}

interface WindVectorItem {
  id: string;
  start: [number, number];
  end: [number, number];
  wing1: [number, number];
  wing2: [number, number];
}

// Generate an aerodynamically aligned grid of wind vectors across Delhi NCR (NW 315° to SE 135°)
function generateNcrWindGrid(): WindVectorItem[] {
  const lats = [28.94, 28.82, 28.70, 28.58, 28.46, 28.34];
  const lngs = [76.88, 77.02, 77.16, 77.30, 77.44];

  // Vector offset for ~4.5 km atmospheric flow line (from NW towards SE)
  const dLat = -0.032;
  const dLng = 0.038;

  const vectors: WindVectorItem[] = [];

  lats.forEach((lat, rIdx) => {
    lngs.forEach((lng, cIdx) => {
      // Stagger alternating rows slightly for natural atmospheric fluidity
      const stagger = (rIdx % 2 === 1) ? 0.04 : 0;
      const startLat = lat;
      const startLng = lng + stagger;

      const endLat = startLat + dLat;
      const endLng = startLng + dLng;

      // Precision chevron arrowhead branching backward toward Northwest
      const wing1Lat = endLat + 0.011;
      const wing1Lng = endLng - 0.004;

      const wing2Lat = endLat + 0.003;
      const wing2Lng = endLng - 0.013;

      vectors.push({
        id: `wind-vec-${rIdx}-${cIdx}`,
        start: [startLat, startLng],
        end: [endLat, endLng],
        wing1: [wing1Lat, wing1Lng],
        wing2: [wing2Lat, wing2Lng],
      });
    });
  });

  return vectors;
}

// 3 Continuous regional atmospheric transport corridors traversing the NCR airshed
const NCR_REGIONAL_CORRIDORS: [number, number][][] = [
  // 1. Northern agricultural buffer & industrial corridor (Sonipat -> Bawana -> Ghaziabad)
  [
    [28.96, 76.94],
    [28.85, 77.10],
    [28.76, 77.28],
    [28.66, 77.48],
  ],
  // 2. Central urban transport corridor (Jhajjar -> West Delhi -> Central Delhi -> Noida)
  [
    [28.82, 76.86],
    [28.70, 77.06],
    [28.60, 77.26],
    [28.48, 77.46],
  ],
  // 3. Southern perimeter corridor (Manesar -> Gurugram -> Faridabad -> Greater Noida)
  [
    [28.68, 76.84],
    [28.54, 77.02],
    [28.42, 77.22],
    [28.32, 77.42],
  ],
];

export const WindFlowOverlay: React.FC<WindFlowOverlayProps> = ({
  windSpeed = 12,
  windDirectionDeg = 315,
  directionLabel = 'NW',
  className = '',
}) => {
  const vectors = useMemo(() => generateNcrWindGrid(), []);

  // Compute CSS animation duration based on wind speed (faster wind = shorter animation cycle)
  const durationSec = useMemo(() => {
    const validSpeed = Math.max(windSpeed, 3);
    const calculated = 24 / validSpeed;
    return Math.max(0.9, Math.min(3.6, calculated)).toFixed(2);
  }, [windSpeed]);

  return (
    <>
      {/* Component-level scoped CSS for hardware-accelerated flow animation & reduced-motion */}
      <style>{`
        @keyframes vayuWindMotion {
          from {
            stroke-dashoffset: 28;
          }
          to {
            stroke-dashoffset: 0;
          }
        }

        .vayu-wind-streamline {
          pointer-events: none !important;
          animation: vayuWindMotion ${durationSec}s linear infinite !important;
        }

        .vayu-wind-arrowhead {
          pointer-events: none !important;
        }

        .vayu-wind-corridor {
          pointer-events: none !important;
          animation: vayuWindMotion ${(parseFloat(durationSec) * 1.5).toFixed(2)}s linear infinite !important;
        }

        @media (prefers-reduced-motion: reduce) {
          .vayu-wind-streamline,
          .vayu-wind-corridor {
            animation: none !important;
            stroke-dasharray: none !important;
          }
        }
      `}</style>

      {/* 1. Regional Sweeping Transport Streamlines */}
      {NCR_REGIONAL_CORRIDORS.map((corridor, idx) => (
        <Polyline
          key={`wind-corridor-${idx}`}
          positions={corridor}
          pathOptions={{
            color: '#0ea5e9',
            weight: 1.4,
            opacity: 0.32,
            dashArray: '12, 10',
            interactive: false,
          }}
          className="vayu-wind-corridor"
        />
      ))}

      {/* 2. Distributed Directional Vector Streamlines with Chevrons */}
      {vectors.map((vec) => (
        <React.Fragment key={vec.id}>
          {/* Main Flow Vector Line */}
          <Polyline
            positions={[vec.start, vec.end]}
            pathOptions={{
              color: '#0284c7',
              weight: 1.8,
              opacity: 0.42,
              dashArray: '8, 6',
              interactive: false,
            }}
            className="vayu-wind-streamline"
          />

          {/* Precision Directional Chevron Arrowhead at Tip */}
          <Polyline
            positions={[vec.wing1, vec.end, vec.wing2]}
            pathOptions={{
              color: '#0369a1',
              weight: 2.0,
              opacity: 0.58,
              interactive: false,
            }}
            className="vayu-wind-arrowhead"
          />
        </React.Fragment>
      ))}
    </>
  );
};

export default WindFlowOverlay;
