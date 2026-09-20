'use client';

import React from 'react';
import { Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import { EmissionHotspot, EmissionSeverity } from '@/lib/hotspots';
import { CloudFog, MapPin, Clock, Gauge, ShieldAlert, Sparkles, Wind } from 'lucide-react';

interface EmissionHotspotMarkerProps {
  hotspot: EmissionHotspot;
  onSelect?: (id: string) => void;
}

const SEVERITY_COLORS: Record<
  EmissionSeverity,
  {
    hex: string;
    label: string;
    bgBadge: string;
    textBadge: string;
    borderBadge: string;
    smokeOpacity: number;
    size: number;
  }
> = {
  LOW: {
    hex: '#22c55e',
    label: 'Low',
    bgBadge: 'bg-emerald-50',
    textBadge: 'text-emerald-700',
    borderBadge: 'border-emerald-200',
    smokeOpacity: 0.22,
    size: 26,
  },
  MODERATE: {
    hex: '#eab308',
    label: 'Moderate',
    bgBadge: 'bg-amber-50',
    textBadge: 'text-amber-800',
    borderBadge: 'border-amber-200',
    smokeOpacity: 0.32,
    size: 30,
  },
  HIGH: {
    hex: '#f97316',
    label: 'High',
    bgBadge: 'bg-orange-50',
    textBadge: 'text-orange-800',
    borderBadge: 'border-orange-200',
    smokeOpacity: 0.42,
    size: 34,
  },
  VERY_HIGH: {
    hex: '#ef4444',
    label: 'Very High',
    bgBadge: 'bg-rose-50',
    textBadge: 'text-rose-800',
    borderBadge: 'border-rose-200',
    smokeOpacity: 0.52,
    size: 38,
  },
  CRITICAL: {
    hex: '#9333ea',
    label: 'Critical',
    bgBadge: 'bg-purple-50',
    textBadge: 'text-purple-800',
    borderBadge: 'border-purple-200',
    smokeOpacity: 0.62,
    size: 42,
  },
};

// Generates an SVG/CSS circular hotspot marker with subtle animated smoke dispersion
function createHotspotIcon(hotspot: EmissionHotspot) {
  const config = SEVERITY_COLORS[hotspot.severity] || SEVERITY_COLORS.MODERATE;
  const color = config.hex;
  const size = config.size;
  const containerSize = Math.max(48, size + 16);
  const coreSize = Math.round(size * 0.42);

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
      <!-- Outer Dispersing Smoke Ring (Simulated physical plume dispersion) -->
      <div class="hotspot-smoke-ring" style="
        position: absolute;
        width: ${size}px;
        height: ${size}px;
        border-radius: 50%;
        background: radial-gradient(circle, ${color} 20%, rgba(100, 116, 139, ${config.smokeOpacity}) 60%, transparent 100%);
        filter: blur(1.5px);
      "></div>

      <!-- Secondary Dispersing Smoke Plume Layer (Offset timing for natural drift) -->
      <div class="hotspot-smoke-ring" style="
        position: absolute;
        width: ${Math.round(size * 0.85)}px;
        height: ${Math.round(size * 0.85)}px;
        border-radius: 50%;
        background: radial-gradient(circle, ${color} 30%, transparent 80%);
        animation-delay: 1.8s;
        filter: blur(2px);
      "></div>

      <!-- Active / Recent Hotspot Subtle Pulse Ring -->
      ${
        hotspot.isActiveRecent
          ? `<div class="hotspot-pulse-ring" style="
              position: absolute;
              width: ${size + 6}px;
              height: ${size + 6}px;
              border-radius: 50%;
              border: 1.5px solid ${color};
              opacity: 0.6;
            "></div>`
          : ''
      }

      <!-- High-Intensity Concentric Ring -->
      <div style="
        position: absolute;
        width: ${coreSize + 10}px;
        height: ${coreSize + 10}px;
        border-radius: 50%;
        border: 1.5px dashed ${color};
        opacity: 0.75;
      "></div>

      <!-- Central Emission Plume Core -->
      <div style="
        position: relative;
        z-index: 3;
        width: ${coreSize}px;
        height: ${coreSize}px;
        border-radius: 50%;
        background-color: ${color};
        border: 2px solid #ffffff;
        box-shadow: 0 0 8px ${color}, inset 0 0 3px rgba(0, 0, 0, 0.4);
      "></div>
    </div>
  `;

  return L.divIcon({
    className: 'vayu-emission-hotspot-pin',
    html,
    iconSize: [containerSize, containerSize],
    iconAnchor: [containerSize / 2, containerSize / 2],
    popupAnchor: [0, -containerSize / 2 + 4],
  });
}

export const EmissionHotspotMarker: React.FC<EmissionHotspotMarkerProps> = ({
  hotspot,
  onSelect,
}) => {
  const icon = React.useMemo(() => createHotspotIcon(hotspot), [hotspot]);
  const config = SEVERITY_COLORS[hotspot.severity] || SEVERITY_COLORS.MODERATE;
  const confidencePct = Math.round(hotspot.confidence * 100);

  return (
    <Marker
      position={[hotspot.latitude, hotspot.longitude]}
      icon={icon}
      eventHandlers={{
        click: () => {
          if (onSelect) {
            onSelect(hotspot.id);
          }
        },
      }}
    >
      <Popup
        className="vayu-leaflet-popup"
        minWidth={270}
        maxWidth={320}
        autoPan={true}
        autoPanPaddingTopLeft={[50, 70]}
        autoPanPaddingBottomRight={[50, 50]}
      >
        <div className="p-1 select-none font-sans text-slate-800">
          {/* Header */}
          <div className="flex items-start justify-between gap-2 pb-2 border-b border-slate-100 mb-2">
            <div>
              <div className="flex items-center gap-1.5 font-bold text-xs uppercase tracking-wider text-slate-900">
                <Wind className="w-3.5 h-3.5 text-purple-600" />
                <span>EMISSION HOTSPOT</span>
              </div>
              <span className="text-[10px] font-mono text-slate-500 bg-slate-100 px-1.5 py-0.2 rounded mt-0.5 inline-block">
                {hotspot.id}
              </span>
            </div>

            {/* Honest Prototype Simulation Label */}
            <span className="text-[9px] font-semibold uppercase px-1.5 py-0.5 rounded bg-amber-50 text-amber-900 border border-amber-200">
              Prototype simulation data
            </span>
          </div>

          {/* Core Hotspot Attributes */}
          <div className="space-y-2 text-xs mb-3 bg-slate-50/80 p-2.5 rounded-lg border border-slate-200">
            {/* Location */}
            <div>
              <span className="text-[10px] font-semibold uppercase text-slate-500 block mb-0.5">
                Location
              </span>
              <div className="flex items-start gap-1 text-slate-900 font-medium">
                <MapPin className="w-3.5 h-3.5 text-slate-500 shrink-0 mt-0.5" />
                <span>{hotspot.locationName}</span>
              </div>
            </div>

            {/* Estimated PM2.5 & Severity */}
            <div className="grid grid-cols-2 gap-2 pt-1.5 border-t border-slate-200/60">
              <div>
                <span className="text-[10px] text-slate-500 block">Estimated PM2.5</span>
                <span className="font-mono font-bold text-slate-900 text-sm tabular-telemetry">
                  {hotspot.estimatedPm25} µg/m³
                </span>
              </div>

              <div>
                <span className="text-[10px] text-slate-500 block">Emission Intensity</span>
                <span
                  className={`inline-flex items-center gap-1 font-semibold text-[11px] px-1.5 py-0.5 rounded border ${config.bgBadge} ${config.textBadge} ${config.borderBadge}`}
                >
                  <span
                    className="w-1.5 h-1.5 rounded-full"
                    style={{ backgroundColor: config.hex }}
                  />
                  <span>{config.label}</span>
                </span>
              </div>
            </div>

            {/* Detection Time & Confidence */}
            <div className="grid grid-cols-2 gap-2 pt-1.5 border-t border-slate-200/60 text-[11px]">
              <div>
                <span className="text-[10px] text-slate-500 block">Detected</span>
                <span className="font-mono text-slate-700 flex items-center gap-1">
                  <Clock className="w-3 h-3 text-slate-400" />
                  <span>{hotspot.detectionTime}</span>
                </span>
              </div>

              <div>
                <span className="text-[10px] text-slate-500 block">Detection Confidence</span>
                <span className="font-mono font-medium text-slate-800">
                  {confidencePct}%
                </span>
              </div>
            </div>

            {/* Possible Source with Simulation Qualifier */}
            <div className="pt-1.5 border-t border-slate-200/60">
              <span className="text-[10px] text-slate-500 block">
                {hotspot.possibleSource
                  ? 'Possible source (simulation):'
                  : 'Possible source:'}
              </span>
              <span className="text-slate-800 font-medium capitalize text-[11px] block mt-0.5">
                {hotspot.possibleSource || 'Not available'}
              </span>
            </div>
          </div>

          {/* Simulation Disclaimer Footer */}
          <div className="text-[10px] text-slate-400 font-mono text-center pt-1 border-t border-slate-100">
            Synthetic Plume Dispersion Prototype
          </div>
        </div>
      </Popup>
    </Marker>
  );
};

export default EmissionHotspotMarker;
