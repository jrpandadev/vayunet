'use client';

import React from 'react';
import { Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import { FireDetection, FireIntensity, FireStatus } from '@/lib/fires';
import { Flame, MapPin, Clock, ShieldAlert, Satellite, ArrowDown, Activity } from 'lucide-react';

interface FireDetectionMarkerProps {
  fire: FireDetection;
  onSelect?: (id: string) => void;
}

const INTENSITY_CONFIG: Record<
  FireIntensity,
  {
    primaryHex: string;
    secondaryHex: string;
    label: string;
    badgeBg: string;
    badgeText: string;
    badgeBorder: string;
    activeCoreSize: number;
    containerSize: number;
  }
> = {
  HIGH: {
    primaryHex: '#dc2626',
    secondaryHex: '#ea580c',
    label: 'High',
    badgeBg: 'bg-red-50',
    badgeText: 'text-red-700',
    badgeBorder: 'border-red-200',
    activeCoreSize: 22,
    containerSize: 42,
  },
  MODERATE: {
    primaryHex: '#ea580c',
    secondaryHex: '#f59e0b',
    label: 'Moderate',
    badgeBg: 'bg-orange-50',
    badgeText: 'text-orange-800',
    badgeBorder: 'border-orange-200',
    activeCoreSize: 19,
    containerSize: 38,
  },
  LOW: {
    primaryHex: '#f59e0b',
    secondaryHex: '#fbbf24',
    label: 'Low',
    badgeBg: 'bg-amber-50',
    badgeText: 'text-amber-800',
    badgeBorder: 'border-amber-200',
    activeCoreSize: 16,
    containerSize: 34,
  },
};

// Generates an SVG/CSS fire marker with clear ACTIVE vs HISTORICAL visual distinction
function createFireIcon(fire: FireDetection) {
  const config = INTENSITY_CONFIG[fire.intensity] || INTENSITY_CONFIG.MODERATE;
  const isActive = fire.status === 'ACTIVE';
  const containerSize = config.containerSize;
  const coreSize = isActive ? config.activeCoreSize : config.activeCoreSize - 2;
  const primaryColor = isActive ? config.primaryHex : '#9a3412';
  const secondaryColor = isActive ? config.secondaryHex : '#78350f';

  // SVG Flame glyph for crisp geospatial rendering
  const flameSvg = `
    <svg viewBox="0 0 24 24" width="${Math.round(coreSize * 0.65)}" height="${Math.round(coreSize * 0.65)}" fill="none" stroke="${isActive ? '#ffffff' : '#fed7aa'}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"></path>
    </svg>
  `;

  const html = `
    <div style="
      position: relative;
      width: ${containerSize}px;
      height: ${containerSize}px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
    ">
      ${
        isActive
          ? `
            <!-- Outer Thermal Pulse Aura for Active Fires -->
            <div class="fire-active-pulse" style="
              position: absolute;
              width: ${coreSize + 14}px;
              height: ${coreSize + 14}px;
              border-radius: 50%;
              background: radial-gradient(circle, ${secondaryColor} 10%, rgba(220, 38, 38, 0.4) 50%, transparent 80%);
            "></div>

            <!-- Glowing Thermal Perimeter Ring -->
            <div style="
              position: absolute;
              width: ${coreSize + 8}px;
              height: ${coreSize + 8}px;
              border-radius: 50%;
              border: 1.5px solid ${primaryColor};
              opacity: 0.85;
              box-shadow: 0 0 8px ${secondaryColor};
            "></div>
          `
          : `
            <!-- Historical Fire Static Muted Ring -->
            <div style="
              position: absolute;
              width: ${coreSize + 6}px;
              height: ${coreSize + 6}px;
              border-radius: 50%;
              border: 1.5px dashed #9a3412;
              opacity: 0.55;
            "></div>
          `
      }

      <!-- Core Flame Capsule -->
      <div class="${isActive ? 'fire-active-glow' : ''}" style="
        position: relative;
        z-index: 2;
        width: ${coreSize}px;
        height: ${coreSize}px;
        border-radius: 50%;
        background: ${
          isActive
            ? `radial-gradient(circle at 35% 35%, #fef08a 0%, ${secondaryColor} 50%, ${primaryColor} 100%)`
            : 'radial-gradient(circle, #78350f 0%, #451a03 100%)'
        };
        border: ${isActive ? '2px solid #ffffff' : '1.5px solid #fed7aa'};
        box-shadow: ${
          isActive
            ? `0 0 10px rgba(234, 88, 12, 0.75), 0 2px 5px rgba(0, 0, 0, 0.35)`
            : '0 1px 3px rgba(0, 0, 0, 0.4)'
        };
        display: flex;
        align-items: center;
        justify-content: center;
        opacity: ${isActive ? '1' : '0.8'};
      ">
        ${flameSvg}
      </div>
    </div>
  `;

  return L.divIcon({
    className: 'vayu-fire-detection-pin',
    html,
    iconSize: [containerSize, containerSize],
    iconAnchor: [containerSize / 2, containerSize / 2],
    popupAnchor: [0, -containerSize / 2 + 4],
  });
}

export const FireDetectionMarker: React.FC<FireDetectionMarkerProps> = ({
  fire,
  onSelect,
}) => {
  const icon = React.useMemo(() => createFireIcon(fire), [fire]);
  const config = INTENSITY_CONFIG[fire.intensity] || INTENSITY_CONFIG.MODERATE;
  const isActive = fire.status === 'ACTIVE';

  return (
    <Marker
      position={[fire.latitude, fire.longitude]}
      icon={icon}
      eventHandlers={{
        click: () => {
          if (onSelect) {
            onSelect(fire.id);
          }
        },
      }}
    >
      <Popup
        className="vayu-leaflet-popup"
        minWidth={280}
        maxWidth={340}
        autoPan={true}
        autoPanPaddingTopLeft={[50, 75]}
        autoPanPaddingBottomRight={[50, 55]}
      >
        <div className="p-1 select-none font-sans text-slate-800">
          {/* Header */}
          <div className="flex items-start justify-between gap-2 pb-2 border-b border-slate-100 mb-2">
            <div>
              <div className="flex items-center gap-1.5 font-bold text-xs uppercase tracking-wider text-slate-900">
                <Flame className={`w-3.5 h-3.5 ${isActive ? 'text-orange-600' : 'text-amber-800'}`} />
                <span>FIRE DETECTION</span>
              </div>
              <span className="text-[10px] font-mono text-slate-500 bg-slate-100 px-1.5 py-0.2 rounded mt-0.5 inline-block">
                {fire.id}
              </span>
            </div>

            {/* Prototype Simulation Notice */}
            <span className="text-[9px] font-semibold uppercase px-1.5 py-0.5 rounded bg-amber-50 text-amber-900 border border-amber-200 shrink-0">
              Prototype simulation data
            </span>
          </div>

          {/* Status & Intensity Bar */}
          <div className="flex items-center justify-between gap-2 mb-2">
            <span
              className={`inline-flex items-center gap-1 text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                isActive
                  ? 'bg-red-100 text-red-800 border border-red-200'
                  : 'bg-slate-100 text-slate-700 border border-slate-200'
              }`}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  isActive ? 'bg-red-500 animate-ping' : 'bg-slate-400'
                }`}
              />
              <span>{isActive ? 'Active Fire' : 'Historical Fire'}</span>
            </span>

            <span
              className={`text-[10px] font-semibold px-2 py-0.5 rounded-md border ${config.badgeBg} ${config.badgeText} ${config.badgeBorder}`}
            >
              Fire intensity: {config.label}
            </span>
          </div>

          {/* Core Fire Attributes Grid */}
          <div className="space-y-1.5 text-xs mb-2.5 bg-slate-50/90 p-2.5 rounded-lg border border-slate-200">
            {/* Location */}
            <div>
              <span className="text-[10px] font-semibold uppercase text-slate-500 block mb-0.5">
                Location
              </span>
              <div className="flex items-start gap-1 text-slate-900 font-medium">
                <MapPin className="w-3.5 h-3.5 text-slate-500 shrink-0 mt-0.5" />
                <span>{fire.locationName}</span>
              </div>
              <span className="text-[10px] font-mono text-slate-400 ml-4.5 block">
                {fire.latitude.toFixed(4)}°N, {fire.longitude.toFixed(4)}°E
                {fire.sizeHectares && ` • ~${fire.sizeHectares} ha estimated area`}
              </span>
            </div>

            {/* Detection Time */}
            <div className="pt-1 border-t border-slate-200/60 flex items-center justify-between text-[11px]">
              <span className="text-slate-500 flex items-center gap-1">
                <Clock className="w-3 h-3 text-slate-400" />
                <span>Detected:</span>
              </span>
              <span className="font-mono font-medium text-slate-800">
                {fire.detectionTime} (Simulation)
              </span>
            </div>

            {/* Satellite Evidence */}
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-slate-500 flex items-center gap-1">
                <Satellite className="w-3 h-3 text-slate-400" />
                <span>Satellite evidence:</span>
              </span>
              <span
                className={`font-medium ${
                  fire.satelliteEvidence && fire.satelliteEvidence !== 'Not available'
                    ? 'text-sky-700'
                    : 'text-slate-500'
                }`}
              >
                {fire.satelliteEvidence || 'Not available'}
              </span>
            </div>

            {/* Potential PM2.5 Contribution */}
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-slate-500 flex items-center gap-1">
                <Activity className="w-3 h-3 text-slate-400" />
                <span>Possible PM2.5 contribution:</span>
              </span>
              <span
                className={`font-semibold capitalize ${
                  fire.pm25Contribution === 'HIGH'
                    ? 'text-red-700'
                    : fire.pm25Contribution === 'MODERATE'
                    ? 'text-orange-700'
                    : fire.pm25Contribution === 'LOW'
                    ? 'text-amber-700'
                    : 'text-slate-500'
                }`}
              >
                {fire.pm25Contribution && fire.pm25Contribution !== 'NOT_ESTABLISHED'
                  ? fire.pm25Contribution.toLowerCase()
                  : 'Not established'}
              </span>
            </div>
          </div>

          {/* FIRE → POLLUTION RELATIONSHIP INDICATOR (Cautious Wording) */}
          <div className="p-2 rounded-lg bg-orange-50/80 border border-orange-200/80 text-xs">
            <span className="text-[10px] font-bold uppercase tracking-wider text-orange-900 block mb-1">
              Fire → Pollution Relationship
            </span>

            {fire.pollutionRelationship ? (
              <div className="space-y-1.5">
                <div className="flex items-center gap-1.5 text-[11px] text-slate-700">
                  <Flame className="w-3 h-3 text-orange-600 shrink-0" />
                  <span className="font-medium">
                    {isActive ? 'Active Fire Source' : 'Historical Fire Location'}
                  </span>
                </div>

                <div className="flex items-center gap-1 text-[10px] text-orange-700 pl-3">
                  <ArrowDown className="w-3 h-3" />
                  <span className="italic">Potential PM2.5 dispersion contribution</span>
                </div>

                <div className="flex items-center gap-1.5 text-[11px] text-slate-800 bg-white/80 p-1.5 rounded border border-orange-200">
                  <ShieldAlert className="w-3 h-3 text-amber-600 shrink-0" />
                  <span>{fire.pollutionRelationship}</span>
                </div>

                <p className="text-[9px] text-slate-500 italic mt-1 leading-tight">
                  Simulation indicator: expresses potential spatial association, not confirmed causal attribution.
                </p>
              </div>
            ) : (
              <p className="text-[11px] text-slate-600 italic">
                Pollution relationship: Not established in current simulation dataset.
              </p>
            )}
          </div>
        </div>
      </Popup>
    </Marker>
  );
};

export default FireDetectionMarker;
